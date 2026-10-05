"""AI dialogs: OpenRouter song suggestions.

Extracted 1:1 from gui/dialogs.py in the big-module split; gui.dialogs
re-exports the class(es), so existing importers keep working unchanged."""
import datetime
import logging
import re
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableWidgetItem, QPushButton, QLabel,
    QComboBox, QLineEdit, QHeaderView, QAbstractItemView, QMessageBox,
    QDialog, QSpinBox, QPlainTextEdit, QRadioButton, QGroupBox, QButtonGroup,
    QProgressBar, QApplication, QScrollArea, QFrame, QWidget, QSizePolicy,
    QCheckBox, QSlider, QTableWidget,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal,
)
from PySide6.QtGui import (
    QFontDatabase,
)

from planner.ai import (
    DEFAULT_API_BASE,
    load_openrouter_config,
    save_openrouter_config,
    build_track_prompt,
    parse_ai_suggestions,
    match_suggestions_to_library,
    FREE_MODELS_FALLBACK,
)
from planner import event_plan, i18n
from planner.competition import CompetitionSpec, parse_competition_schedule
from planner.models import DANCE_NAMES, DEFAULT_DANCES
from gui.workers import (
    OpenRouterChatWorker, OpenRouterModelsWorker,
)
from planner import llm
from gui.common import (  # noqa: F401  (shared primitives)
    _sanitize_filename,
    apply_taskbar_icon,
    _lbl,
    LoadingDialog,
    _fmt_duration,
    BusyDialog,
    _C_ROUND_BG,
    _C_ROUND_FG,
    _C_DANCE_BG,
    _C_DANCE_FG,
    _C_ROW_EVEN,
    _C_ROW_ODD,
    _C_POP_FG,
    _C_NEW_FG,
    _C_SIM_FG,
    _C_WARN_FG,
    _C_DEFAULT,
    _fmt_track_secs,
    _entry_tooltip,
    _open_in_default_player,
    _open_folder,
    reveal_in_explorer,
    _DragTable,
    DropZone,
    _PathListWidget,
    _DroppedFilesList,
    _MultiFileDropZone,
)

log = logging.getLogger("dancesport.gui")


# ─────────────────────────────────────────────────────────────────────────────
# AI Suggestions Dialog (OpenRouter)
# ─────────────────────────────────────────────────────────────────────────────
class AiSuggestDialog(QDialog):
    """Ask a free OpenRouter model for song ideas, cross-referenced with the library."""

    _COLS = ["▶", "Lib", "Artist", "Title", "Local match"]

    def __init__(self, lib, parent=None, play_cb=None,
                 dance=None, seed_title=None, theme=None):
        super().__init__(parent)
        self.setWindowTitle("AI Song Suggestions (OpenRouter)")
        self.resize(620, 520)
        self._lib       = lib
        self._play_cb   = play_cb
        self._dance     = dance
        self._theme     = theme
        self._row_paths: list[Path | None] = []
        self._cur_row   = -1
        self._chat: OpenRouterChatWorker | None   = None
        self._models: OpenRouterModelsWorker | None = None

        cfg = load_openrouter_config()
        lyt = QVBoxLayout(self)

        # Where to ask — OpenRouter unless another OpenAI-compatible host is named
        brow = QHBoxLayout()
        brow.addWidget(QLabel("API base URL:"))
        self._base_edit = QComboBox()
        self._base_edit.setEditable(True)
        self._base_edit.addItems([DEFAULT_API_BASE, "https://api.mammouth.ai/v1"])
        self._base_edit.setCurrentText(cfg.get("base_url", "") or DEFAULT_API_BASE)
        self._base_edit.setToolTip(
            i18n.t("Any OpenAI-compatible /chat/completions host.") + "\n"
            "OpenRouter: " + DEFAULT_API_BASE + "\n"
            "Mammouth:   https://api.mammouth.ai/v1")  # i18n: data
        brow.addWidget(self._base_edit, stretch=1)
        lyt.addLayout(brow)

        # API key
        lyt.addWidget(QLabel("API key  (free OpenRouter key from openrouter.ai/keys):"))
        self._key_edit = QLineEdit(cfg.get("api_key", ""))
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setPlaceholderText("sk-or-…")
        lyt.addWidget(self._key_edit)

        # Model + load-free-models
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Model:"))
        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        models = list(dict.fromkeys(FREE_MODELS_FALLBACK + [cfg.get("model", "")]))
        self._model_combo.addItems([m for m in models if m])
        self._model_combo.setCurrentText(cfg.get("model", FREE_MODELS_FALLBACK[0]))
        mrow.addWidget(self._model_combo, stretch=1)
        self._load_btn = QPushButton("Load models")
        self._load_btn.clicked.connect(self._load_models)
        mrow.addWidget(self._load_btn)
        lyt.addLayout(mrow)

        # Context / seed
        crow = QHBoxLayout()
        crow.addWidget(QLabel("Context:"))
        seed = seed_title or (DANCE_NAMES.get(dance, dance) if dance else "") or (theme or "")
        self._ctx_edit = QLineEdit(seed)
        self._ctx_edit.setPlaceholderText("e.g. a song title, mood, or leave blank")
        crow.addWidget(self._ctx_edit, stretch=1)
        crow.addWidget(QLabel("Count:"))
        self._count = QSpinBox()
        self._count.setRange(3, 40)
        self._count.setValue(12)
        crow.addWidget(self._count)
        lyt.addLayout(crow)

        # Get button + status
        grow = QHBoxLayout()
        self._get_btn = QPushButton("🤖  Get Suggestions")
        self._get_btn.clicked.connect(self._get)
        grow.addWidget(self._get_btn)
        self._status = QLabel("")
        self._status.setStyleSheet("color:#666; font-size:11px;")
        grow.addWidget(self._status, stretch=1)
        lyt.addLayout(grow)

        # Results table
        self._table = _DragTable(self._row_paths)
        self._table.setColumnCount(len(self._COLS))
        self._table.setHorizontalHeaderLabels(self._COLS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False)
        self._table.setDragEnabled(True)
        self._table.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        lyt.addWidget(self._table, stretch=1)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lyt.addWidget(close)

    # ── Free model list ────────────────────────────────────────────────────────
    def _load_models(self):
        self._load_btn.setEnabled(False)
        self._status.setText("Fetching the model list…")
        self._models = OpenRouterModelsWorker(self._key_edit.text().strip(), self,
                                              base_url=self._base_url())
        self._models.done.connect(self._on_models)
        self._models.error.connect(self._on_models_error)
        self._models.start()

    def _on_models(self, models):
        cur = self._model_combo.currentText()
        self._model_combo.clear()
        self._model_combo.addItems(models or FREE_MODELS_FALLBACK)
        if cur:
            self._model_combo.setCurrentText(cur)
        self._status.setText(i18n.t("%d models loaded.") % len(models))
        self._load_btn.setEnabled(True)

    def _on_models_error(self, msg):
        self._status.setText("Could not fetch models (using fallback list).")
        self._load_btn.setEnabled(True)

    def _base_url(self) -> str:
        return self._base_edit.currentText().strip() or DEFAULT_API_BASE

    # ── Get suggestions ──────────────────────────────────────────────────────────
    def _get(self):
        key   = self._key_edit.text().strip()
        model = self._model_combo.currentText().strip()
        if not key:
            QMessageBox.warning(self, "API key needed",
                                "Enter a free OpenRouter API key (openrouter.ai/keys).")
            return
        save_openrouter_config(key, model, self._base_url())
        ctx = self._ctx_edit.text().strip()
        system, user = build_track_prompt(
            dance=self._dance, seed_title=ctx or None,
            theme=self._theme, n=self._count.value(),
        )
        self._get_btn.setEnabled(False)
        self._status.setText("Asking the model…")
        self._chat = OpenRouterChatWorker(key, model, system, user, self,
                                          base_url=self._base_url())
        self._chat.done.connect(self._on_reply)
        self._chat.error.connect(self._on_reply_error)
        self._chat.start()

    def _on_reply_error(self, msg):
        self._get_btn.setEnabled(True)
        self._status.setText("Failed.")
        QMessageBox.critical(self, "AI Error", msg)

    def _on_reply(self, text: str):
        self._get_btn.setEnabled(True)
        suggestions = parse_ai_suggestions(text)
        if not suggestions:
            self._status.setText("No parseable suggestions returned.")
            return
        matched = match_suggestions_to_library(self._lib, suggestions)
        owned = sum(1 for m in matched if m["entry"])
        self._status.setText(i18n.t("%d suggestions — %d in your library.") % (len(matched), owned))
        self._populate(matched)

    def _populate(self, matched):
        self._row_paths = []
        self._table.setRowCount(len(matched))
        ctr = Qt.AlignmentFlag.AlignCenter
        for r, m in enumerate(matched):
            s     = m["suggestion"]
            entry = m["entry"]
            self._row_paths.append(entry.path if entry else None)

            play_btn = QPushButton("▶")
            play_btn.setFixedSize(26, 20)
            play_btn.setStyleSheet("padding: 0;")
            if entry and self._play_cb:
                play_btn.clicked.connect(lambda _, rr=r: self._toggle_play(rr))
            else:
                play_btn.setEnabled(False)
            self._table.setCellWidget(r, 0, play_btn)

            lib_it = QTableWidgetItem("✓" if entry else "–")
            lib_it.setTextAlignment(ctr)
            lib_it.setForeground(_C_SIM_FG if entry else _C_DEFAULT)
            self._table.setItem(r, 1, lib_it)
            self._table.setItem(r, 2, QTableWidgetItem(s.get("artist", "")[:30]))
            self._table.setItem(r, 3, QTableWidgetItem(s.get("title", "")[:50]))
            match_txt = entry.title[:40] if entry else ""
            mi = QTableWidgetItem(match_txt)
            mi.setForeground(_C_SIM_FG if entry else _C_DEFAULT)
            self._table.setItem(r, 4, mi)
        self._table._paths = self._row_paths
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for c in (0, 1, 2, 4):
            self._table.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.ResizeToContents)

    def _toggle_play(self, row: int):
        if not self._play_cb:
            return
        path = self._row_paths[row] if 0 <= row < len(self._row_paths) else None
        if path is None:
            return
        if row == self._cur_row:
            self._set_btn(row, "▶")
            self._cur_row = -1
            self._play_cb(None)
            return
        if self._cur_row >= 0:
            self._set_btn(self._cur_row, "▶")
        self._cur_row = row
        self._set_btn(row, "■")
        self._play_cb(path)

    def _set_btn(self, row, text):
        w = self._table.cellWidget(row, 0)
        if isinstance(w, QPushButton):
            w.setText(text)

    def closeEvent(self, event):
        if self._cur_row >= 0 and self._play_cb:
            self._play_cb(None)
        super().closeEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# 🏆 Event: a whole day of competitions, planned from its history
# ─────────────────────────────────────────────────────────────────────────────
_EVENT_CLASSES = ("S", "A", "B", "C", "D")
# The variants offered before "Last year, renewed" came: a choice saved then
# did not leave that one out on purpose.
_VARIANTS_BEFORE_RENEWED = ("like_last_year", "proven_fresh", "variety")
_STD_CODES = set(DEFAULT_DANCES['Standard']['S'])
_LAT_CODES = set(DEFAULT_DANCES['Latin']['S'])


def _edited_spec(base: CompetitionSpec, label: str, cls: str, dances: str,
                 heats: str) -> CompetitionSpec:
    """`base` with what the user corrected in its table row. A cell that reads
    as nothing sensible keeps what the schedule said."""
    label = label.strip() or base.label
    cls = cls.strip().upper()
    if cls not in _EVENT_CLASSES:
        cls = base.dance_class
    codes = list(dict.fromkeys(t.upper() for t in re.split(r'[\s;,/]+', dances) if t))
    if not codes or not set(codes) <= _STD_CODES | _LAT_CODES:
        codes = list(base.dances)
    style = ('Standard' if set(codes) <= _STD_CODES else
             'Latin' if set(codes) <= _LAT_CODES else None)
    counts = [int(n) for n in re.findall(r'\d+', heats)]
    if not counts or 0 in counts:
        counts = list(base.heats)
    per_round = base.couples_per_round if counts == base.heats else None
    return replace(base, label=label, style=style, dance_class=cls,
                   dances=codes, heats=counts, couples_per_round=per_round)


class _EventPanel(QWidget):
    """The 🏆 Event mode's own controls: the schedule, what was read from it,
    where the titles may come from and which variants to plan."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._specs: list[CompetitionSpec] = []
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(18, 0, 0, 0)

        self._schedule = QPlainTextEdit()
        self._schedule.setPlaceholderText(i18n.t(
            "Paste the event's schedule, one competition per line:\n"
            "\n"
            "Sa: 10:00 HGR S STD 3-2-1\n"
            "So: 14:00 SEN I S STD (24) 2-1\n"
            "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6"))
        self._schedule.setMaximumHeight(90)
        lyt.addWidget(self._schedule)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Competition", "Class", "Dances", "Heats per round"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3):
            self._table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setMaximumHeight(150)
        self._table.setToolTip(
            "What was read from the schedule. Double-click a cell to correct\n"
            "it — the class (S, A … D), the dance codes, the heats per round.")
        lyt.addWidget(self._table)
        self._schedule.textChanged.connect(self._reparse)
        self._schedule.setPlainText(settings.get("ai_event_schedule", ""))

        row = QHBoxLayout()
        row.addWidget(_lbl("Event:"))
        self._series = QComboBox()
        self._series.setEditable(True)
        for _key, name, editions in event_plan.event_series_list():
            self._series.addItem(name)
            self._series.setItemData(self._series.count() - 1,
                                     i18n.t("%d editions") % editions,
                                     Qt.ItemDataRole.ToolTipRole)
        self._series.setCurrentText(settings.get("ai_event_series", ""))
        self._series.setToolTip(
            "The event whose earlier editions are its history — the folders\n"
            "of that name in the playlist folder, whatever the year.")
        row.addWidget(self._series, stretch=1)
        row.addWidget(_lbl("Year planned:"))
        self._year = QSpinBox()
        self._year.setRange(2000, 2100)
        self._year.setValue(datetime.date.today().year)
        self._year.setToolTip(
            "Editions of this year and later are not used as history.")
        row.addWidget(self._year)
        lyt.addLayout(row)

        self._use_event = QCheckBox("Earlier editions of the event")
        self._use_event.setChecked(settings.get("ai_event_use_event", True))
        self._use_class = QCheckBox("Lists of the same class from other events")
        self._use_class.setChecked(settings.get("ai_event_use_class", True))
        src = QHBoxLayout()
        src.addWidget(self._use_event)
        src.addWidget(self._use_class)
        src.addStretch(1)
        lyt.addLayout(src)

        row = QHBoxLayout()
        row.addWidget(_lbl("New titles:"))
        self._new_share = QSlider(Qt.Orientation.Horizontal)
        self._new_share.setRange(0, 50)
        self._new_share.setSingleStep(5)
        self._new_share.setPageStep(10)
        self._new_share.setValue(int(settings.get("ai_event_new_share", 20)))
        self._new_share.setToolTip(
            "How much of a variant may be titles that came into the archive in\n"
            "the last 18 months and were never played at the class. \"Like last\n"
            "year\" takes none — it offers them as replacements instead.")
        self._new_share_box = QSpinBox()
        self._new_share_box.setRange(0, 50)
        self._new_share_box.setSuffix(" %")
        self._new_share_box.setValue(self._new_share.value())
        self._new_share.valueChanged.connect(self._new_share_box.setValue)
        self._new_share_box.valueChanged.connect(self._new_share.setValue)
        row.addWidget(self._new_share, stretch=1)
        row.addWidget(self._new_share_box)
        lyt.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(_lbl("Rarely played:"))
        self._rare_share = QSlider(Qt.Orientation.Horizontal)
        self._rare_share.setRange(0, 50)
        self._rare_share.setSingleStep(5)
        self._rare_share.setPageStep(10)
        self._rare_share.setValue(int(settings.get("ai_event_rare_share", 15)))
        self._rare_share.setToolTip(
            "How much of a variant may be titles played at most twice at the\n"
            "class so far, new ones included, the ones that sound like the\n"
            "played ones first. \"Like last year\" takes none.")
        self._rare_share_box = QSpinBox()
        self._rare_share_box.setRange(0, 50)
        self._rare_share_box.setSuffix(" %")
        self._rare_share_box.setValue(self._rare_share.value())
        self._rare_share.valueChanged.connect(self._rare_share_box.setValue)
        self._rare_share_box.valueChanged.connect(self._rare_share.setValue)
        row.addWidget(self._rare_share, stretch=1)
        row.addWidget(self._rare_share_box)
        lyt.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(_lbl("Variants:"))
        wanted = settings.get("ai_event_variants", list(event_plan.PROFILE_ORDER))
        # A variant the saved choice never offered starts on.
        offered = settings.get("ai_event_variants_offered", _VARIANTS_BEFORE_RENEWED)
        self._variants = {}
        for profile in event_plan.PROFILE_ORDER:
            cb = QCheckBox(event_plan.PROFILE_NAMES[profile])
            cb.setChecked(profile in wanted or profile not in offered)
            self._variants[profile] = cb
            row.addWidget(cb)
        row.addStretch(1)
        lyt.addLayout(row)

        self._ai_check = QCheckBox("🤖  Let the AI check the drafts")
        self._ai_check.setChecked(settings.get("ai_event_ai_check", True))
        self._ai_check.setToolTip(
            "The model reads every draft and proposes swaps; each one is\n"
            "checked against the day before it goes in. Without it the\n"
            "computed plan is shown as it is.")
        lyt.addWidget(self._ai_check)

    def _reparse(self):
        self._specs = parse_competition_schedule(self._schedule.toPlainText())
        self._table.setRowCount(len(self._specs))
        for r, spec in enumerate(self._specs):
            cells = (spec.label, spec.dance_class, " ".join(spec.dances),
                     "-".join(str(h) for h in spec.heats))
            for c, text in enumerate(cells):
                self._table.setItem(r, c, QTableWidgetItem(text))

    def specs(self) -> list[CompetitionSpec]:
        return [_edited_spec(base, *(self._table.item(r, c).text()
                                     for c in range(4)))
                for r, base in enumerate(self._specs)]

    def values(self) -> dict:
        name = self._series.currentText().strip()
        return dict(
            schedule=self._schedule.toPlainText().strip(),
            specs=self.specs(),
            series=event_plan.event_series(name),
            series_name=name,
            year=self._year.value(),
            use_event=self._use_event.isChecked(),
            use_class=self._use_class.isChecked(),
            new_share=self._new_share.value() / 100,
            rare_share=self._rare_share.value() / 100,
            variants=[p for p, cb in self._variants.items() if cb.isChecked()],
            ai_check=self._ai_check.isChecked(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# AI Playlist Dialog (claude -p, OpenRouter as fallback)
# ─────────────────────────────────────────────────────────────────────────────
class AiPlaylistDialog(QDialog):
    """Ask an LLM to assemble the playlist instead of the scoring algorithm.

    The user owns the RULES — the editable block that says what a good playlist
    is — while the output contract, the tempo table and the candidate catalog
    are appended by llm. Rules and model are remembered in the settings
    dict handed in; the caller persists it."""

    REOPEN_PLAN = 2    # exec() result: show the kept 🏆 event plan again

    def __init__(self, settings: dict, parent=None, *, event_plan_kept=False):
        super().__init__(parent)
        self.setWindowTitle("🤖  AI playlist")
        self.resize(660, 720)
        self._settings = settings

        lyt = QVBoxLayout(self)

        # ── What to build ──────────────────────────────────────────────────
        mode_box = QGroupBox("What to build")
        mode_lyt = QVBoxLayout(mode_box)
        self._rb_comp = QRadioButton(
            "🏆  Competition playlist — rounds and heats from the left panel")
        self._rb_comp.setToolTip(
            "Style, age, start class, dances and the round pattern come from\n"
            "the panel on the left. The model only picks and orders the music.")
        self._rb_flat = QRadioButton("🎵  One flat list of")
        self._rb_comp.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self._rb_comp, 0)
        grp.addButton(self._rb_flat, 1)
        mode_lyt.addWidget(self._rb_comp)
        flat_row = QHBoxLayout()
        flat_row.addWidget(self._rb_flat)
        self._count_spin = QSpinBox()
        self._count_spin.setRange(5, 500)
        self._count_spin.setValue(int(settings.get("ai_flat_count", 60)))
        self._count_spin.setSuffix(" tracks")
        flat_row.addWidget(self._count_spin)
        flat_row.addStretch(1)
        mode_lyt.addLayout(flat_row)

        self._rb_wish = QRadioButton(
            "📝  Wish list — the titles below, in that order")
        self._rb_wish.setToolTip(
            "Name the tracks yourself. The model does the looking up: it finds\n"
            "the library title behind every shortened or mistyped wish.")
        grp.addButton(self._rb_wish, 2)
        mode_lyt.addWidget(self._rb_wish)
        self._wishes = QPlainTextEdit(settings.get("ai_wishes", ""))
        self._wishes.setPlaceholderText(
            "Write the wishes however you like — one per line, a sentence, or "
            "a whole sheet pasted in with a column per dance:\n"
            "\n"
            "lw            t               ww        qs\n"
            "White wings   a new life      Willow    quit playing games !!\n"
            "melancolia !  Dance of love   Kiss me   youre so fine\n"
            "\n"
            "Short names and typos are fine. A two-letter code beside a title "
            "names its dance, ! or !! marks the ones you really want, and "
            "anything else you write here is read as an instruction.")
        self._wishes.setMinimumHeight(96)
        # Into the layout first, hidden second — a widget made visible while
        # it still hangs off nothing flashes as a window of its own.
        mode_lyt.addWidget(self._wishes)
        self._wishes.setVisible(False)

        self._rb_event = QRadioButton(
            "🏆  Event — a whole day of competitions, planned from its history")
        self._rb_event.setToolTip(
            "Paste the event's schedule. Every competition gets up to three\n"
            "variants, drawn from the event's earlier editions, the class's\n"
            "lists at other events and titles that sound like those.")
        grp.addButton(self._rb_event, 3)
        mode_lyt.addWidget(self._rb_event)
        self._event = _EventPanel(settings)
        mode_lyt.addWidget(self._event)
        self._event.setVisible(False)
        lyt.addWidget(mode_box)

        # ── The brief ──────────────────────────────────────────────────────
        self._brief_lbl = _lbl(
            "In your own words — what this list is for (optional):")
        lyt.addWidget(self._brief_lbl)
        self._brief = QPlainTextEdit(settings.get("ai_brief", ""))
        self._brief.setPlaceholderText(
            "e.g. 'club evening, keep it modern', 'no covers in the final',\n"
            "'the wishes are for a show — put the two marked ones last'")
        self._brief.setMaximumHeight(76)
        lyt.addWidget(self._brief)

        def sync_mode():
            self._count_spin.setEnabled(self._rb_flat.isChecked())
            # Only the mode that uses it gets to take up the room.
            self._wishes.setVisible(self._rb_wish.isChecked())
            event = self._rb_event.isChecked()
            self._event.setVisible(event)
            # The event's variants say what they are for; there is no brief.
            self._brief_lbl.setVisible(not event)
            self._brief.setVisible(not event)
        grp.idToggled.connect(lambda *_: sync_mode())
        sync_mode()

        # ── The rules ──────────────────────────────────────────────────────
        rules_row = QHBoxLayout()
        rules_row.addWidget(_lbl("Rules the model has to follow:"), stretch=1)
        reset_btn = QPushButton("↺  Default rules")
        reset_btn.setToolTip("Put the shipped rule set back.")
        reset_btn.clicked.connect(
            lambda: self._rules.setPlainText(llm.DEFAULT_RULES))
        rules_row.addWidget(reset_btn)
        lyt.addLayout(rules_row)
        self._rules = QPlainTextEdit(
            settings.get("ai_rules") or llm.DEFAULT_RULES)
        self._rules.setToolTip(
            "Free text. The tempo table, the track catalog and the answer\n"
            "format are added automatically — describe only what makes a\n"
            "playlist good in your eyes.")
        lyt.addWidget(self._rules, stretch=1)

        # ── Model ──────────────────────────────────────────────────────────
        mrow = QHBoxLayout()
        mrow.addWidget(_lbl("Model:"))
        # The CLI's aliases for the latest of each; a full model id can be typed.
        self._model = QComboBox()
        self._model.setEditable(True)
        self._model.addItems(["opus", "sonnet"])
        self._model.setCurrentText(settings.get("ai_model") or llm.CLAUDE_MODEL)
        mrow.addWidget(self._model, stretch=1)
        lyt.addLayout(mrow)

        # ── Which login ────────────────────────────────────────────────────
        # A shell exports CLAUDE_CONFIG_DIR; a GUI started from the desktop has
        # no such variable, so `claude -p` would take ~/.claude — which is not
        # necessarily the profile that is logged in.
        lrow = QHBoxLayout()
        lrow.addWidget(_lbl("Claude login:"))
        self._config_dir = QComboBox()
        self._config_dir.setEditable(True)
        self._config_dir.addItem("")                     # = the CLI's own default
        for path in llm.claude_config_dirs():
            self._config_dir.addItem(path)
        chosen = (settings.get("ai_claude_config_dir")
                  or llm.default_claude_config_dir())
        if chosen and self._config_dir.findText(chosen) < 0:
            self._config_dir.addItem(chosen)
        self._config_dir.setCurrentText(chosen)
        self._config_dir.setToolTip(
            "CLAUDE_CONFIG_DIR — which claude login the CLI uses.\n"
            "Empty leaves it to the CLI (~/.claude).")
        lrow.addWidget(self._config_dir, stretch=1)
        lyt.addLayout(lrow)

        if llm.claude_available():
            hint = ("Runs through the claude CLI on your Claude subscription — "
                    "no API key. Falls back to OpenRouter if that fails.")
        else:
            hint = ("⚠ claude CLI not found — OpenRouter will be used. Set the "
                    "CLAUDE_BIN environment variable to use your subscription.")
        note = _lbl(hint)
        note.setWordWrap(True)
        lyt.addWidget(note)

        # ── Buttons ────────────────────────────────────────────────────────
        bb = QHBoxLayout()
        self._reopen_btn = QPushButton("🏆  Open the last plan")
        self._reopen_btn.setToolTip(
            "Show the last event plan side by side again, as you left it —\n"
            "nothing is planned or asked anew.")
        self._reopen_btn.clicked.connect(lambda: self.done(self.REOPEN_PLAN))
        bb.addWidget(self._reopen_btn)
        self._reopen_btn.setVisible(False)
        if event_plan_kept:
            self._rb_event.toggled.connect(self._reopen_btn.setVisible)
            self._reopen_btn.setVisible(self._rb_event.isChecked())
        bb.addStretch(1)
        cancel = QPushButton("Cancel")
        ok = QPushButton("🤖  Build")
        ok.setDefault(True)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        bb.addWidget(cancel)
        bb.addWidget(ok)
        lyt.addLayout(bb)

    def values(self) -> dict:
        if self._rb_comp.isChecked():
            mode = "competition"
        elif self._rb_wish.isChecked():
            mode = "wishes"
        elif self._rb_event.isChecked():
            mode = "event"
        else:
            mode = "flat"
        return dict(
            mode=mode,
            event=self._event.values(),
            count=self._count_spin.value(),
            wishes=self._wishes.toPlainText().strip(),
            brief=self._brief.toPlainText().strip(),
            rules=self._rules.toPlainText().strip() or llm.DEFAULT_RULES,
            model=self._model.currentText().strip() or llm.CLAUDE_MODEL,
            config_dir=self._config_dir.currentText().strip(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# AI Playlist Transcript (what actually went over the wire)
# ─────────────────────────────────────────────────────────────────────────────
class _Bubble(QFrame):
    """One chat bubble: who said it, and what they said.

    Long turns — the catalog of rows is hundreds of lines — open with a preview
    and a link that unfolds the rest, so the shape of the conversation stays
    readable while every word is still one click away. The same link folds it
    back up: an unfolded catalog buries the turns after it."""

    _PREVIEW_LINES = 14

    _SKIN = {
        # role: (background, border, header colour)
        "sent":     ("#dce9fb", "#b6d0ee", "#1d4f86"),
        "received": ("#ffffff", "#d7dbe2", "#3a3f47"),
    }

    def __init__(self, role: str, speaker: str, title: str, text: str,
                 parent=None):
        super().__init__(parent)
        bg, border, head = self._SKIN.get(role, self._SKIN["received"])
        self.setStyleSheet(
            f"_Bubble {{ background:{bg}; border:1px solid {border};"
            f" border-radius:10px; }}")
        self.setSizePolicy(QSizePolicy.Policy.Maximum,
                           QSizePolicy.Policy.Preferred)

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(12, 8, 12, 10)
        lyt.setSpacing(4)

        hdr = QLabel(f"{speaker}  ·  {title}")
        hdr.setTextFormat(Qt.TextFormat.PlainText)
        hdr.setStyleSheet(f"color:{head}; font-weight:bold; border:none;")
        lyt.addWidget(hdr)

        # Only the blank edges go: a leading space is column alignment in
        # a catalog row, not padding.
        self._full = text.replace("\r\n", "\n").strip("\n").rstrip()
        lines = self._full.split("\n")
        self._hidden = max(0, len(lines) - self._PREVIEW_LINES)

        self._body = QLabel()
        # Verbatim: a prompt or a reply may hold anything, and none of it is markup.
        self._body.setTextFormat(Qt.TextFormat.PlainText)
        self._body.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self._body.setWordWrap(True)
        self._body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self._body.setStyleSheet("border:none;")
        self._body.setText("\n".join(lines[:self._PREVIEW_LINES])
                           if self._hidden else self._full)
        lyt.addWidget(self._body)

        self._folded = bool(self._hidden)
        self._more = None
        if self._hidden:
            self._more = QPushButton()
            self._more.setFlat(True)
            self._more.setCursor(Qt.CursorShape.PointingHandCursor)
            self._more.setStyleSheet("text-align:left; color:#1d4f86;"
                                     " border:none; padding:0;")
            self._more.clicked.connect(self.toggle_fold)
            lyt.addWidget(self._more)
            self._apply_fold()

    def toggle_fold(self):
        """Unfold the rest of the turn, or fold it back to the preview."""
        self._folded = not self._folded
        self._apply_fold()

    def _apply_fold(self):
        lines = self._full.split("\n")
        self._body.setText("\n".join(lines[:self._PREVIEW_LINES])
                           if self._folded else self._full)
        self._more.setText(i18n.t("▾  %d more lines") % self._hidden if self._folded
                           else "▴  fold back")


class _ThinkingBubble(QFrame):
    """The model's side of the thread while it is still typing.

    A turn takes minutes, and a still window with a finished prompt in it looks
    exactly like a window that has died. The dots move and the clock counts, so
    the wait is visibly a wait."""

    _FRAMES = ("●··", "·●·", "··●")
    _INTERVAL_MS = 400

    def __init__(self, speaker: str, what: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "_ThinkingBubble { background:#ffffff; border:1px solid #d7dbe2;"
            " border-radius:10px; }")
        self.setSizePolicy(QSizePolicy.Policy.Maximum,
                           QSizePolicy.Policy.Preferred)
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(12, 8, 12, 10)
        lyt.setSpacing(4)

        hdr = QLabel(f"{speaker}  ·  {what}")
        hdr.setTextFormat(Qt.TextFormat.PlainText)
        hdr.setStyleSheet("color:#3a3f47; font-weight:bold; border:none;")
        lyt.addWidget(hdr)

        self._label = QLabel()
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setStyleSheet("color:#6b727c; border:none;")
        lyt.addWidget(self._label)

        self._frame = 0
        self._secs = 0
        self._paint()
        self._timer = QTimer(self)
        self._timer.setInterval(self._INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._frame += 1
        # The clock is counted in ticks, not read off a wall clock: it stays in
        # step with the dots and needs no second timer.
        self._secs = self._frame * self._INTERVAL_MS // 1000
        self._paint()

    def _paint(self):
        self._label.setText(f"{self._FRAMES[self._frame % len(self._FRAMES)]}   "
                            + i18n.t("thinking…") + f"  {self.elapsed_text()}")

    def elapsed_text(self) -> str:
        return f"{self._secs // 60}:{self._secs % 60:02d}"

    def stop(self):
        self._timer.stop()

    def restart(self):
        """The clock from zero — a retry is a new attempt."""
        self._frame = 0
        self._secs = 0
        self._paint()


class AiTranscriptDialog(QDialog):
    """The whole exchange with the model, written down as it happens.

    A run is two questions and two answers with a query pass in between, and
    all of it used to be invisible — the grid simply filled itself. This window
    lays it out the way a chat client does: what the planner sends on the
    right, what the model answers on the left, the program's own steps as a
    thin line between them.

    Not modal: the run is on a worker thread, and the window stays open with
    the finished transcript once the playlist has landed. It is also a window
    in its own right — minimise + maximise buttons and a taskbar button of its
    own — because a run takes minutes and a dialog that is merely owned by the
    main window has nowhere to be minimised TO: it just disappears."""

    _SPEAKER = {"sent": "📋  Planner", "received": "🤖  Model"}

    stopRequested = Signal()   # ⏹ — the worker is asked to cancel the run

    # No tokenizer ships with the app and the backends (claude -p --output-format
    # text, the OpenAI-compatible endpoint as it is called here) hand back no
    # usage numbers, so the size is counted in characters and divided. Four
    # characters per token is the usual rule of thumb for English prose and
    # holds well enough for these catalog rows; everything shown is marked ≈.
    _CHARS_PER_TOKEN = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window
                            | Qt.WindowType.WindowMinMaxButtonsHint
                            | Qt.WindowType.WindowCloseButtonHint)
        self.setWindowTitle("🤖  Conversation with the model")
        self.resize(860, 660)
        self._steps: list[tuple[str, str, str]] = []
        # How much text this run has moved, for the readout below the thread.
        self._sent_chars = 0
        self._recv_chars = 0
        self._turn_max = 0
        # The questions still out, oldest first, as [label, row, prompt size]:
        # the event planner asks every competition at once, so several can
        # wait side by side and their answers land in any order.
        self._open: list[list] = []

        lyt = QVBoxLayout(self)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background:#f2f4f7; }")
        inner = QWidget()
        inner.setStyleSheet("background:#f2f4f7;")
        self._thread = QVBoxLayout(inner)
        self._thread.setContentsMargins(14, 12, 14, 12)
        self._thread.setSpacing(10)
        self._thread.addStretch(1)        # bubbles are inserted above this
        self._scroll.setWidget(inner)
        lyt.addWidget(self._scroll, stretch=1)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)          # indeterminate while the model thinks
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        lyt.addWidget(self._bar)

        row = QHBoxLayout()
        self._status = _lbl("Asking the model…")
        row.addWidget(self._status, stretch=1)
        self._usage = _lbl("")
        self._usage.setStyleSheet("color:#6b727c; font-size:11px;")
        self._usage.setToolTip(
            "How much text this run moves.\n\n"
            "Sent is everything the model was given (the rules, the library "
            "summary, the catalog rows), back is what it answered. The biggest "
            "turn is the one that has to fit the model's context window: one "
            "prompt plus its reply.\n\n"
            "Token counts are estimated at ~4 characters each — no backend "
            "here reports its real usage.")
        row.addWidget(self._usage)
        self._stop_btn = QPushButton("⏹  Stop")
        self._stop_btn.setToolTip(
            "Stop the run. A model that is still thinking is cut off and "
            "nothing is changed.")
        self._stop_btn.clicked.connect(self._request_stop)
        row.addWidget(self._stop_btn)
        copy_btn = QPushButton("📋  Copy")
        copy_btn.setToolTip("Put the whole transcript on the clipboard.")
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.transcript()))
        row.addWidget(copy_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        row.addWidget(close_btn)
        lyt.addLayout(row)

    def showEvent(self, ev):
        """The taskbar button is created with the native window — this is the
        first moment it can be handed the app icon instead of a generic one."""
        super().showEvent(ev)
        apply_taskbar_icon(self)

    # ── The conversation ──────────────────────────────────────────────────────
    def add_step(self, role: str, title: str, text: str):
        """Append one prompt / reply / note and scroll to it."""
        self._steps.append((role, title, text))
        # Above the waiting bubbles, which stay at the end of the thread.
        self._thread.insertWidget(self._waiting_index(),
                                  self._row_for(role, title, text))
        asked = 0
        if role == "sent":
            # The question is out; whatever comes next is the model's turn.
            self._start_waiting(title, len(text or ""))
        else:
            turn = self._turn_for(title)
            if turn is not None:
                # Its answer — or, for a note, the question failed for good.
                asked = turn[2]
                self._stop_waiting(turn)
            elif role == "note" and len(self._open) == 1:
                # A note DURING a turn — a retry after a server-side wobble,
                # say. The question is still out, so the waiting goes on; the
                # clock starts over because the attempt did.
                self._open[0][1].findChild(_ThinkingBubble).restart()
            elif role == "received" and self._open:
                turn = self._open[0]
                asked = turn[2]
                self._stop_waiting(turn)
        # The scrollbar only knows its new range after the layout has run.
        QTimer.singleShot(0, self._to_bottom)
        self._status.setText(self._status_text())
        self._count(role, text, asked)

    @staticmethod
    def _turn_label(title: str) -> str:
        """What a question and its answer share: the event planner titles both
        after the competition, "HGR S STD — the drafts to check" and
        "HGR S STD — its swaps — <backend>"."""
        return title.split(" — ")[0]

    def _turn_for(self, title: str):
        label = self._turn_label(title)
        return next((t for t in self._open if t[0] == label), None)

    def _status_text(self) -> str:
        if not self._open:
            return i18n.t("Working…")
        text = i18n.t("Waiting for the model…")
        return f"{text} ({len(self._open)})" if len(self._open) > 1 else text

    def _waiting_index(self) -> int:
        """Where a new row goes: above the first waiting bubble, else at the
        end (before the stretch)."""
        if self._open:
            return self._thread.indexOf(self._open[0][1])
        return self._thread.count() - 1

    def _start_waiting(self, what: str, size: int):
        """Put a live "the model is typing" bubble at the end of the thread."""
        bubble = _ThinkingBubble(self._SPEAKER["received"], what)
        bubble.setMaximumWidth(self._bubble_width())
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(bubble)      # the model answers on the left
        box.addStretch(1)
        self._thread.insertWidget(self._thread.count() - 1, row)
        self._open.append([self._turn_label(what), row, size])

    def _stop_waiting(self, turn=None):
        """Take an indicator away — its answer landed — or, without a turn,
        all of them: the run is over."""
        for label, row, size in [turn] if turn is not None else list(self._open):
            self._open.remove([label, row, size])
            for bubble in row.findChildren(_ThinkingBubble):
                bubble.stop()
            self._thread.removeWidget(row)
            row.setParent(None)
            row.deleteLater()

    # ── How much text the run moves ───────────────────────────────────────────
    def _count(self, role: str, text: str, asked: int = 0):
        """Add one turn to the size readout. Notes are the planner talking to
        itself — they never reach the model, so they do not count. `asked` is
        the size of the question a reply answers."""
        size = len(text or "")
        if role == "sent":
            self._sent_chars += size
        elif role == "received":
            self._recv_chars += size
            self._turn_max = max(self._turn_max, asked + size)
        else:
            return
        self._usage.setText(self.usage_text())

    @classmethod
    def _tokens(cls, chars: int) -> int:
        return round(chars / cls._CHARS_PER_TOKEN)

    @staticmethod
    def _short(n: int) -> str:
        return f"{n / 1000:.1f}k" if n >= 1000 else str(n)

    def usage_text(self) -> str:
        """The one-line context readout: what went out, what came back, and the
        biggest single turn — the one that has to fit the context window."""
        parts = [f"📤 {self._short(self._sent_chars)} chars "
                 f"(≈{self._short(self._tokens(self._sent_chars))} tok)",
                 f"📥 {self._short(self._recv_chars)} chars "
                 f"(≈{self._short(self._tokens(self._recv_chars))} tok)"]
        if self._turn_max:
            parts.append(f"biggest turn ≈{self._short(self._tokens(self._turn_max))} tok")
        return "   ·   ".join(parts)

    def _row_for(self, role: str, title: str, text: str) -> QWidget:
        """A note is a thin line across the thread; anything else is a bubble,
        pushed to its speaker's side."""
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        if role == "note":
            note = QLabel(f"{title} — {text.strip()}" if text.strip() else title)
            note.setTextFormat(Qt.TextFormat.PlainText)
            note.setWordWrap(True)
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note.setStyleSheet("color:#6b727c; font-size:11px;")
            box.addWidget(note, stretch=1)
            return row
        bubble = _Bubble(role, self._SPEAKER.get(role, "•"), title, text)
        bubble.setMaximumWidth(self._bubble_width())
        if role == "sent":                # the planner speaks on the right
            box.addStretch(1)
            box.addWidget(bubble)
        else:                             # the model answers on the left
            box.addWidget(bubble)
            box.addStretch(1)
        return row

    def _bubble_width(self) -> int:
        """How wide a bubble may grow — a chat bubble stops well short of the
        far edge, and that is also what makes long lines wrap."""
        return max(320, int(self._scroll.viewport().width() * 0.80))

    def resizeEvent(self, ev):
        """Bubbles follow the window: the wrap width is a width, not a constant."""
        super().resizeEvent(ev)
        width = self._bubble_width()
        for bubble in self.findChildren(_Bubble):
            bubble.setMaximumWidth(width)

    def _to_bottom(self):
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def transcript(self) -> str:
        """The whole exchange as plain text — what 📋 Copy puts on the clipboard."""
        return "\n\n".join(
            f"{'─' * 70}\n{self._SPEAKER.get(role, '·')}  {title}\n{'─' * 70}\n"
            f"{text.strip()}"
            for role, title, text in self._steps)

    def _request_stop(self):
        self._stop_btn.setEnabled(False)
        self._status.setText("Stopping…")
        self.stopRequested.emit()

    def finish(self, message: str):
        """The run is over — stop the bar and say how it ended."""
        self._stop_btn.hide()
        self._stop_waiting()
        self._bar.setRange(0, 1)
        self._bar.setValue(1)
        self._status.setText(message)
