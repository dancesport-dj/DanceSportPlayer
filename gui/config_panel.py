"""The left-side configuration panel (style/age/class, dances, rounds, strategy).

Extracted from dancesport_gui.py (view split).
"""
import html
import logging
import re

from PySide6.QtCore import (
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from planner.competition import CompetitionSpec, parse_competition_schedule
from planner.models import (
    DANCE_STYLES,
    DEFAULT_DANCES,
    RoundConfig,
    best_style_for_dances,
    rounds_from_pattern,
    style_covers_dances,
)
from planner import terms
from planner.terms import dance_name
from planner.scoring import STRATEGIES, STRATEGY_HELP, STRATEGY_LABELS
from planner.themes import all_themes
from planner import i18n
from planner.scoring import _resolve_strategy
from gui.common import (
    DropZone,
    _lbl,
)
from shared.widgets import (
    _hsep,
)

log = logging.getLogger("dancesport.gui.config_panel")

# "1,234/3,638" — an "analyzed / total" count in the status block.
_COUNT_PAIR = re.compile(r"(\d[\d,]*)/(\d[\d,]*)")


def mark_index_gaps(msg: str) -> str:
    """The library status as rich text, with every short count marked amber.

    The block prints six index lines of 'analyzed/total' pairs in one flat
    grey — so the only number that asks for an action, an index that is not
    finished yet, reads exactly like the five that are. Only that number is
    coloured: a finished index stays grey, and the total it is measured
    against never changes colour either.
    """
    def paint(m):
        done, total = (int(g.replace(",", "")) for g in m.groups())
        if done >= total:
            return m.group(0)
        return f'<span style="color:#c77700">{m.group(1)}</span>/{m.group(2)}'

    return _COUNT_PAIR.sub(paint, html.escape(msg)).replace("\n", "<br>")


# ─────────────────────────────────────────────────────────────────────────────
# Config Panel (left side)
# ─────────────────────────────────────────────────────────────────────────────
class ConfigPanel(QWidget):
    generate_requested = Signal()
    import_requested   = Signal()
    ai_requested       = Signal()
    ai_playlist_requested = Signal()
    ai_log_requested   = Signal()
    settings_requested = Signal()
    build_all_requested = Signal()       # 🧱 next to the status counts
    m3u_source_requested = Signal()      # 'Browse…' next to the .m3u source
    round_strategy_changed = Signal(str, str)   # (round_name, strategy_key)
    replay_competition_changed = Signal(int)    # selected competition index
    schedule_parsed            = Signal()        # a fresh schedule was parsed

    def __init__(self, parent=None):
        super().__init__(parent)
        # Resizable via the main splitter (was a hard setFixedWidth, which froze the
        # handle). Keep a sensible min so the controls stay usable and a max so it
        # can't swallow the playlist area; initial width set by splitter.setSizes.
        self.setMinimumWidth(250)
        self.setMaximumWidth(640)
        self._round_cfgs: list[RoundConfig] = []
        self._strategy_combos: dict[str, QComboBox] = {}
        self._scope_checks: dict[str, QCheckBox] = {}   # per-round 🎯 same-comp toggle
        self._last_parsed_rounds: str = ""   # guard against redundant re-parse
        # Will be populated in _update_dances
        self.dance_checks: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # ── Mode switch ──
        layout.addWidget(_lbl("Mode:"))
        self.mode_combo = QComboBox()
        # (caption, value) pairs, never addItems: the caption is translated and
        # the value is not. These three strings ARE the mode — fourteen sites
        # compare against them and an autosaved deck carries one in its "mode"
        # field — so everything reads currentData(), never currentText().
        for _mode in ("Favorites", "Theme", "Past Competitions"):
            self.mode_combo.addItem(_mode, _mode)
        layout.addWidget(self.mode_combo)
        layout.addWidget(_hsep())

        # ── Favorites config (hidden in Theme mode) ──
        self._comp = QWidget()
        clyt = QVBoxLayout(self._comp)
        clyt.setContentsMargins(0, 0, 0, 0)
        clyt.setSpacing(5)
        layout.addWidget(self._comp)

        # ── Where the titles come from ──
        # Default: the scored Favorites library. The other two draw from a
        # hand-picked pool instead — what is parked in the open ⭐ wishlists, or
        # one .m3u file — and then only from it: a dance the pool has no track
        # for stays blank rather than being filled from the whole library.
        clyt.addWidget(_lbl("Draw tracks from:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("⭐  Favorites library", "library")
        self.source_combo.addItem("⭐  Open wishlists", "wishlists")
        self.source_combo.addItem("📂  An .m3u playlist file", "m3u")
        self.source_combo.setToolTip(
            "Which titles ⚡ Generate may pick from.\n"
            "Favorites library — everything scanned from your library folder.\n"
            "Open wishlists — only what you parked in the ⭐ wishlists.\n"
            "An .m3u file — only the tracks in that one playlist.\n"
            "With the last two, a dance the pool cannot cover stays blank.")
        clyt.addWidget(self.source_combo)
        self._source_m3u_row = QWidget()
        m3u_hl = QHBoxLayout(self._source_m3u_row)
        m3u_hl.setContentsMargins(0, 0, 0, 0)
        self.source_m3u_edit = QLineEdit()
        self.source_m3u_edit.setPlaceholderText("Choose an .m3u file…")
        m3u_hl.addWidget(self.source_m3u_edit, stretch=1)
        source_m3u_btn = QPushButton("Browse…")
        source_m3u_btn.setFixedWidth(70)
        source_m3u_btn.clicked.connect(self.m3u_source_requested)
        m3u_hl.addWidget(source_m3u_btn)
        self._source_m3u_row.setVisible(False)
        clyt.addWidget(self._source_m3u_row)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)

        # ── Dance style ──
        clyt.addWidget(_lbl("Dance Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(list(DANCE_STYLES))
        self.style_combo.setCurrentText("Latin")
        clyt.addWidget(self.style_combo)

        # ── Age class ──
        clyt.addWidget(_lbl("Age Class:"))
        self.age_combo = QComboBox()
        self.age_combo.addItems([
            "Kinder", "Junioren", "Jugend",
            "Hauptgruppe", "Senioren I", "Senioren II", "Senioren III",
            "Senioren IV", "Senioren V",
        ])
        self.age_combo.setCurrentText("Hauptgruppe")
        clyt.addWidget(self.age_combo)

        # ── Start class ──
        clyt.addWidget(_lbl("Start Class:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(["D", "C", "B", "A", "S"])
        self.class_combo.setCurrentText("S")
        clyt.addWidget(self.class_combo)

        clyt.addWidget(_hsep())

        # ── Dances ──
        clyt.addWidget(_lbl("Dances:"))
        self.dances_box = QWidget()
        self.dances_layout = QVBoxLayout(self.dances_box)
        self.dances_layout.setContentsMargins(4, 0, 4, 0)
        self.dances_layout.setSpacing(1)
        clyt.addWidget(self.dances_box)
        clyt.addWidget(_hsep())

        # ── Rounds + strategy + options (shared by Favorites & Past Competitions) ──
        self._rounds_box = QWidget()
        rlyt = QVBoxLayout(self._rounds_box)
        rlyt.setContentsMargins(0, 0, 0, 0)
        rlyt.setSpacing(5)

        # ── Rounds ──
        rlyt.addWidget(_lbl("Rounds  (e.g. 6-3-2-1):"))
        row_w = QWidget()
        row_hl = QHBoxLayout(row_w)
        row_hl.setContentsMargins(0, 0, 0, 0)
        self.rounds_edit = QLineEdit("6-3-2-1")
        row_hl.addWidget(self.rounds_edit)
        parse_btn = QPushButton("Parse")
        parse_btn.setFixedWidth(55)
        parse_btn.clicked.connect(self._parse_rounds)
        row_hl.addWidget(parse_btn)
        rlyt.addWidget(row_w)
        self.rounds_edit.editingFinished.connect(self._parse_rounds)

        # ── Round strategy ──
        self.strategy_group = QGroupBox("Round Strategy")
        self.strategy_lyt = QVBoxLayout(self.strategy_group)
        self.strategy_lyt.setContentsMargins(6, 4, 6, 4)
        self.strategy_lyt.setSpacing(10)
        rlyt.addWidget(self.strategy_group)

        # Contextual explanation of what "Proven"/"New" mean here, updated per mode.
        self.strategy_note = QLabel()
        self.strategy_note.setWordWrap(True)
        self.strategy_note.setStyleSheet("color:#888; font-size:10px;")
        rlyt.addWidget(self.strategy_note)

        # When ticked, changing a strategy combo immediately re-rolls that whole
        # round (live). Untick to only store the new strategy: the generated grid
        # stays as-is and you fix individual slots with the per-song / per-dance ↺
        # buttons (which then draw from the new strategy's pool).
        self.auto_reroll_check = QCheckBox("Auto re-roll round on strategy change")
        self.auto_reroll_check.setChecked(False)
        self.auto_reroll_check.setToolTip(
            "On: changing a round's strategy re-rolls that whole round.\n"
            "Off: keep the current grid and change only the songs you want\n"
            "via the ↺ buttons (they use the newly selected strategy)."
        )
        rlyt.addWidget(self.auto_reroll_check)

        rlyt.addWidget(_hsep())

        # ── Options ──
        self.timbre_check = QCheckBox("Use Timbre Similarity")
        self.timbre_check.setChecked(True)
        self.timbre_check.setToolTip(
            "When enabled, songs within a round are scored for\n"
            "timbral similarity to the round's first song.\n"
            "Disable for more varied song choices."
        )
        rlyt.addWidget(self.timbre_check)

        # ── Past Competitions config (above the rounds box; hidden in Favorites mode) ──
        self._replay_box = QWidget()
        plyt = QVBoxLayout(self._replay_box)
        plyt.setContentsMargins(0, 0, 0, 0)
        plyt.setSpacing(5)
        plyt.addWidget(_lbl("Paste competition schedule:"))
        self.replay_text = QPlainTextEdit()
        # i18n: data — an example of the schedule the parser reads
        self.replay_text.setPlaceholderText(
            "Fr: U21 STD (50) 4 - 4 - 3 - 2 - 1\n"
            "    SEN I LAT (38) 4 - 3 - 2 - 1\n"
            "So: Youth STD (21) 2 - 2 - 1"
        )
        self.replay_text.setFixedHeight(90)
        plyt.addWidget(self.replay_text)
        replay_parse_btn = QPushButton("Parse schedule")
        replay_parse_btn.clicked.connect(self._parse_schedule)
        plyt.addWidget(replay_parse_btn)
        plyt.addWidget(_lbl("Competition:"))
        self.replay_combo = QComboBox()
        self.replay_combo.currentIndexChanged.connect(self._on_replay_selected)
        plyt.addWidget(self.replay_combo)
        plyt.addWidget(_lbl(
            "Seeds the grid from songs you played at this\n"
            "class before (matching per-class M3U files)."
        ))
        plyt.addWidget(_hsep())
        self._replay_specs: list[CompetitionSpec] = []
        self._replay_box.setVisible(False)
        # Order: replay box sits ABOVE the shared rounds/strategy box
        layout.addWidget(self._replay_box)
        layout.addWidget(self._rounds_box)

        # ── Theme config (hidden in Favorites mode) ──
        self._theme_box = QWidget()
        tlyt = QVBoxLayout(self._theme_box)
        tlyt.setContentsMargins(0, 0, 0, 0)
        tlyt.setSpacing(5)
        tlyt.addWidget(_lbl("Theme:"))
        self.theme_combo = QComboBox()
        self._theme_keys: list[str] = []
        for key, spec in all_themes().items():
            self._theme_keys.append(key)
            self.theme_combo.addItem(spec.get("label", key))
        tlyt.addWidget(self.theme_combo)
        tlyt.addWidget(_lbl("Number of tracks:"))
        self.theme_count = QSpinBox()
        self.theme_count.setRange(5, 200)
        self.theme_count.setValue(30)
        tlyt.addWidget(self.theme_count)
        tlyt.addWidget(_lbl(
            "Themes use ID3 year tags + themes.json overrides.\n"
            "Decade themes need year data in your MP3s."
        ))
        self._theme_box.setVisible(False)
        layout.addWidget(self._theme_box)

        layout.addWidget(_hsep())

        # ── Action buttons ──
        self.generate_btn = QPushButton("⚡  Generate Playlist")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setMinimumHeight(32)
        self.generate_btn.clicked.connect(self.generate_requested)
        layout.addWidget(self.generate_btn)

        self.save_btn = QPushButton("💾  Save M3U")
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)

        self.import_btn = QPushButton("📂  Import M3U…")
        self.import_btn.setEnabled(False)
        self.import_btn.setToolTip(
            "Load an existing .m3u into the focused deck or wishlist.\n"
            "Decks detect rounds, dances and heats automatically — a final\n"
            "with extra backup variants (e.g. two Sambas) is handled too.\n"
            "A focused wishlist appends the tracks flat."
        )
        self.import_btn.clicked.connect(self.import_requested)
        layout.addWidget(self.import_btn)

        self.ai_playlist_btn = QPushButton("🤖  AI Playlist…")
        self.ai_playlist_btn.setEnabled(False)
        self.ai_playlist_btn.setToolTip(
            "Let a model build the playlist instead of the scoring algorithm.\n"
            "You give it the rules (a default set is filled in), it picks and\n"
            "orders the music — either into the rounds/heats configured above\n"
            "or as one flat list.\n"
            "Runs on your Claude subscription via the claude CLI, with\n"
            "OpenRouter as fallback."
        )
        self.ai_playlist_btn.clicked.connect(self.ai_playlist_requested)

        # The last conversation is kept until the next run replaces it, so it
        # needs a way back once its window has been closed. Hidden until there
        # is something to reopen.
        self.ai_log_btn = QPushButton("💬")
        self.ai_log_btn.setToolTip(
            "Open the last conversation with the model again.\n"
            "It is kept until the next AI run starts."
        )
        self.ai_log_btn.setFixedWidth(36)
        self.ai_log_btn.setVisible(False)
        self.ai_log_btn.clicked.connect(self.ai_log_requested)
        ai_row = QHBoxLayout()
        ai_row.setContentsMargins(0, 0, 0, 0)
        ai_row.setSpacing(4)
        ai_row.addWidget(self.ai_playlist_btn, stretch=1)
        ai_row.addWidget(self.ai_log_btn)
        layout.addLayout(ai_row)

        # self.ai_btn = QPushButton("🤖  AI Suggestions…")
        # self.ai_btn.setToolTip(
        #     "Ask a free OpenRouter model for song ideas for the selected dance,\n"
        #     "cross-referenced with your library."
        # )
        # self.ai_btn.clicked.connect(self.ai_requested)
        # layout.addWidget(self.ai_btn)

        # ── Drop zone: find similar from an external file ──
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        layout.addStretch()
        layout.addWidget(_hsep())

        # ── Library status (+ settings gear) ──
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        self.status_lbl = QLabel("Library: loading…")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setTextFormat(Qt.TextFormat.RichText)   # coloured count pairs
        self.status_lbl.setStyleSheet("color: #555; font-size: 11px;")
        status_row.addWidget(self.status_lbl, stretch=1)
        # Straight from the amber counts to the job that fixes them — the same
        # build the ⚙ Settings dialog offers, three clicks deeper.
        self.build_all_btn = QPushButton("🧱")
        self.build_all_btn.setFixedSize(26, 26)
        self.build_all_btn.setVisible(False)
        self.build_all_btn.clicked.connect(self.build_all_requested)
        status_row.addWidget(self.build_all_btn, alignment=Qt.AlignmentFlag.AlignTop)
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(26, 26)
        self.settings_btn.setToolTip("Settings — library paths, global search & analysis")
        self.settings_btn.clicked.connect(self.settings_requested)
        status_row.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(status_row)

        # Connect signals after all widgets exist
        self.style_combo.currentTextChanged.connect(self._update_dances)
        self.class_combo.currentTextChanged.connect(self._update_dances)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        # Populate dances + parse default rounds
        self._update_dances()
        self._parse_rounds()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _on_mode_changed(self, _index=None):
        mode = self.mode_combo.currentData()
        is_theme  = (mode == "Theme")
        is_replay = (mode == "Past Competitions")
        # style/age/class/dances only make sense in Favorites mode
        self._comp.setVisible(not is_theme and not is_replay)
        # rounds + strategy combos shared by Favorites & Past Competitions
        self._rounds_box.setVisible(not is_theme)
        self._replay_box.setVisible(is_replay)
        self._theme_box.setVisible(is_theme)
        if is_theme:
            text = "⚡  Generate Theme Playlist"
        elif is_replay:
            text = "⚡  Generate from History"
        else:
            text = "⚡  Generate Playlist"
        self.generate_btn.setText(text)
        # Strategy defaults differ per mode (replay → all 'proven'); force a rebuild
        if not is_theme:
            self._last_parsed_rounds = ""
            self._parse_rounds()
        self._update_strategy_note()

    def _parse_schedule(self):
        """Parse the pasted schedule into CompetitionSpecs and fill the dropdown."""
        text = self.replay_text.toPlainText()
        specs = parse_competition_schedule(text)
        self._replay_specs = specs
        # New schedule → drop any per-competition work stashes (they no longer match).
        self.schedule_parsed.emit()
        self.replay_combo.blockSignals(True)
        self.replay_combo.clear()
        for spec in specs:
            self.replay_combo.addItem(f"{spec.label}  ({'-'.join(map(str, spec.heats))})")
        self.replay_combo.blockSignals(False)
        if specs:
            self.replay_combo.setCurrentIndex(0)
            self._on_replay_selected(0)
        else:
            QMessageBox.warning(
                self, "No competitions parsed",
                "Could not parse any competition lines from the pasted text.\n"
                "Each line needs a class label, a style (STD/LAT) and the\n"
                "heat counts, e.g.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'."
            )

    def _on_replay_selected(self, idx: int):
        if not (0 <= idx < len(self._replay_specs)):
            return
        spec = self._replay_specs[idx]
        self.rounds_edit.setText("-".join(str(h) for h in spec.heats))
        self._last_parsed_rounds = ""   # force rebuild so 'proven' defaults apply
        self._parse_rounds()
        # Let the main window swap the visible grid to this competition's saved work.
        self.replay_competition_changed.emit(idx)


    def _update_dances(self):
        """Rebuild the dance boxes for the style/class on screen and tick that
        class's default set: all five dances from C upwards, four in D (no Wiener
        Walzer in Standard, no Paso Doble in Latin). Switching either combo
        starts from those defaults again -- a hand-picked subset belongs to the
        style it was picked in, not to the one being switched to."""
        style    = self.style_combo.currentText()
        cls      = self.class_combo.currentText()
        defaults = DEFAULT_DANCES.get(style, {}).get(cls, [])
        all_d    = list(DEFAULT_DANCES.get(style, {}).get("S", []))

        # Clear existing checkboxes
        while self.dances_layout.count():
            item = self.dances_layout.takeAt(0)
            w    = item.widget()
            if w:
                w.setParent(None)
        self.dance_checks.clear()

        for d in all_d:
            cb = QCheckBox(dance_name(d, d))
            cb.setChecked(d in defaults)
            self.dance_checks[d] = cb
            self.dances_layout.addWidget(cb)

    def _parse_rounds(self):
        raw = self.rounds_edit.text().strip()
        if raw == self._last_parsed_rounds:
            return   # text unchanged – keep existing combo selections
        self._last_parsed_rounds = raw
        cfgs = rounds_from_pattern(raw)
        if not cfgs:
            return
        self._round_cfgs = cfgs

        # Rebuild strategy UI
        while self.strategy_lyt.count():
            item = self.strategy_lyt.takeAt(0)
            w    = item.widget()
            if w:
                w.setParent(None)
        self._strategy_combos.clear()
        self._scope_checks.clear()

        # Past Competitions seeds per-round from the matching history (final↔final,
        # semi↔semi). Final + semi reuse the perennial finalist songs (top_proven);
        # every earlier round stays 'proven'. Changing a combo live re-rolls that
        # round from its history pool (timbre-matched, library fallback). The 🎯
        # checkbox restricts a round's "proven" pool to THIS competition; unticked,
        # it draws from all your playlists.
        is_replay = (self.mode_combo.currentData() == "Past Competitions")

        def _replay_default(i: int, tier: str) -> str:
            return "top_proven" if tier in ("final", "semi") else "proven"

        for i, rc in enumerate(cfgs):
            rw  = QWidget()
            rhl = QHBoxLayout(rw)
            rhl.setContentsMargins(0, 0, 0, 0)
            rhl.setSpacing(4)
            lbl = QLabel(terms.round_name(rc.name)[:20])
            # Fixed (not just minimum) width so long names like "2. Zwischenrunde"
            # don't shove their combo further right than short rows ("Finale") —
            # every round's combo then lines up in one clean column.
            lbl.setFixedWidth(135)
            rhl.addWidget(lbl)
            combo = QComboBox()
            for j, key in enumerate(STRATEGIES):
                combo.addItem(STRATEGY_LABELS[key], key)
                # addItem's caption goes through the hook; setItemData does
                # not — it carries arbitrary data for arbitrary roles, so it
                # cannot be patched without translating data too. The one
                # tooltip that IS chrome therefore asks for itself.
                combo.setItemData(j, i18n.t(STRATEGY_HELP[key]),
                                  Qt.ItemDataRole.ToolTipRole)
            if is_replay:
                default = _replay_default(i, rc.tier)
            elif rc.strategy:
                # An explicit (restored / user-picked) strategy always wins.
                default = _resolve_strategy(rc.tier, rc.prefer_fresh, rc.strategy)
            elif i == 0:
                default = "all"      # 1st round → Even Mix (maximum variety)
            elif i == 1:
                default = "mixed"    # 2nd round → Mostly Proven
            else:
                default = _resolve_strategy(rc.tier, rc.prefer_fresh, None)
            combo.setCurrentIndex(STRATEGIES.index(default))
            combo.setToolTip(STRATEGY_HELP[default])
            # Connect AFTER setCurrentIndex so the initial build doesn't fire a
            # spurious live re-roll; only genuine user changes emit.
            combo.currentIndexChanged.connect(
                lambda _i, c=combo: c.setToolTip(STRATEGY_HELP[c.currentData()]))
            combo.currentIndexChanged.connect(
                lambda _i, rn=rc.name, c=combo:
                    self.round_strategy_changed.emit(rn, c.currentData() or ""))
            # Uniform native sizing: a CSS stylesheet (padding) drops Windows combos off
            # native rendering and makes their heights inconsistent — use a fixed size
            # instead so every round's combo is identical.
            combo.setFixedSize(110 if is_replay else 130, 26)
            self._strategy_combos[rc.name] = combo
            rhl.addWidget(combo)

            if is_replay:
                scope = QCheckBox("🎯")
                scope.setChecked(True)   # default: this competition only
                scope.setToolTip(
                    "🎯 ticked: draw this round's songs from THIS competition's "
                    "past lists only.\nUnticked: draw from ALL your playlists."
                )
                # Connect after setChecked so the initial build doesn't re-roll.
                scope.toggled.connect(
                    lambda _on, rn=rc.name, c=combo:
                        self.round_strategy_changed.emit(rn, c.currentData() or ""))
                self._scope_checks[rc.name] = scope
                rhl.addWidget(scope)

            self.strategy_lyt.addWidget(rw)

        self._update_strategy_note()

    def _update_strategy_note(self):
        mode = self.mode_combo.currentData()
        if mode == "Past Competitions":
            self.strategy_note.setText(
                "“Proven” = songs you played in THIS competition's past lists · "
                "“New” = never played.  🎯 keeps a round to this competition; "
                "untick it to draw that round from ALL your playlists."
            )
            self.strategy_note.setVisible(True)
        elif mode == "Theme":
            self.strategy_note.setVisible(False)
        else:
            self.strategy_note.setText(
                "“Proven” = songs in any of your playlists · “New” = in none."
            )
            self.strategy_note.setVisible(True)

    def round_scope(self, round_name: str) -> bool:
        """True if this round should pull 'proven' from THIS competition only
        (🎯 ticked); False to draw from all playlists. Defaults to True."""
        cb = self._scope_checks.get(round_name)
        return cb.isChecked() if cb else True

    # ── Public API ────────────────────────────────────────────────────────────

    def get_config(self) -> tuple[str, str, str, list[str], list[RoundConfig], bool]:
        self._parse_rounds()   # ensure rounds reflect any unsaved edits
        style  = self.style_combo.currentText()
        age    = self.age_combo.currentText()
        cls    = self.class_combo.currentText()
        dances = [d for d, cb in self.dance_checks.items() if cb.isChecked()]
        # Apply user-chosen strategies
        for rc in self._round_cfgs:
            combo = self._strategy_combos.get(rc.name)
            if combo:
                rc.strategy     = combo.currentData()
                rc.prefer_fresh = (rc.strategy == "fresh")   # keep legacy flag in sync
        use_timbre = self.timbre_check.isChecked()
        return style, age, cls, dances, self._round_cfgs, use_timbre

    def apply_config(self, mode=None, style=None, age=None, cls=None, dances=None,
                     replay_idx=None):
        """Push a deck's stored generation settings back into the visible combos.

        Used when switching the active deck so the controls follow the focused
        playlist (e.g. flip back to an 'HGR S Latin' deck and the class combo
        returns to S instead of keeping the other deck's A). Each combo is set
        via findText/setCurrentIndex so the natural signals still fire and the
        dependent dance checkboxes / strategy rows rebuild for the deck.
        """
        if mode:
            i = self.mode_combo.findData(mode)
            if i >= 0:
                self.mode_combo.setCurrentIndex(i)   # → _on_mode_changed (panel toggle)
        # Restore which past-competition this deck was working on. Block signals so
        # we don't re-run the grid-swap (_on_replay_competition_changed) — the deck's
        # rows are already in its own table; we only need the combo to match.
        if (replay_idx is not None and self._replay_specs
                and 0 <= replay_idx < self.replay_combo.count()):
            self.replay_combo.blockSignals(True)
            self.replay_combo.setCurrentIndex(replay_idx)
            self.replay_combo.blockSignals(False)
            spec = self._replay_specs[replay_idx]
            self.rounds_edit.setText("-".join(str(h) for h in spec.heats))
            self._last_parsed_rounds = ""
            self._parse_rounds()
        # When an explicit dance set is given, the style must be one whose checkbox
        # list can actually hold those dances — otherwise a mismatch (e.g. a Latin
        # deck whose `_dances` slipped to Standard codes) would silently drop dances
        # from the panel. Override a non-covering style with the best-fitting one.
        if dances and style and not style_covers_dances(style, dances):
            style = best_style_for_dances(dances) or style
        if style:
            i = self.style_combo.findText(style)
            if i >= 0:
                self.style_combo.setCurrentIndex(i)  # → _update_dances
        if age:
            i = self.age_combo.findText(age)
            if i >= 0:
                self.age_combo.setCurrentIndex(i)
        if cls:
            i = self.class_combo.findText(cls)
            if i >= 0:
                self.class_combo.setCurrentIndex(i)  # → _update_dances
        # Reconcile the dance checkboxes with the deck's actual dance set (the
        # style/class change above already rebuilt them to that style's defaults).
        # An EMPTY list means "this deck has no dance set of its own" — a Theme
        # or player deck never fills `_dances` — and must NOT untick everything:
        # those modes hide the dance box, so the empty panel could not be seen,
        # let alone fixed, and the next Generate / 🤖 AI run refused to start.
        if dances:
            for d, cb in self.dance_checks.items():
                cb.setChecked(d in dances)
            if not any(cb.isChecked() for cb in self.dance_checks.values()):
                # Not one of them fits the style on screen (a stored set of codes
                # no style covers, so the override above found nothing better).
                # Fall back to this class's defaults rather than show an empty
                # box: Generate would refuse to start and nothing would say why.
                self._update_dances()

    def reset_to_defaults(self):
        """Restore the combos/toggles to their initial state (used when a deck is
        cleared): Favorites · Latin · Hauptgruppe · S · 6-3-2-1, style-default dances."""
        # dances=None → the style/class rebuild leaves that style's default checks.
        self.apply_config(mode="Favorites", style="Latin", age="Hauptgruppe", cls="S")
        self.reset_source()
        self.rounds_edit.setText("6-3-2-1")
        self._parse_rounds()

    def _on_source_changed(self, _idx: int = 0):
        """Only the .m3u source needs a path, so its row shows with it."""
        self._source_m3u_row.setVisible(self.get_source()[0] == "m3u")

    def get_source(self) -> tuple[str, str]:
        """(kind, m3u_path) for ⚡ Generate: kind is 'library' (the default),
        'wishlists' or 'm3u'; the path is empty unless kind is 'm3u'."""
        kind = self.source_combo.currentData() or "library"
        path = self.source_m3u_edit.text().strip() if kind == "m3u" else ""
        return kind, path

    def set_source_m3u(self, path: str):
        """Fill in a browsed/dropped .m3u and select that source."""
        self.source_m3u_edit.setText(path)
        i = self.source_combo.findData("m3u")
        if i >= 0:
            self.source_combo.setCurrentIndex(i)

    def reset_source(self):
        """Back to the Favorites library — a fresh start never plans from a
        pool the user picked in some earlier session."""
        self.source_combo.setCurrentIndex(0)
        self.source_m3u_edit.clear()

    def get_mode(self) -> str:
        return self.mode_combo.currentData()

    def get_theme_config(self) -> tuple[str, str, int]:
        """Return (theme_key, theme_label, count) for the selected theme."""
        idx = self.theme_combo.currentIndex()
        key = self._theme_keys[idx] if 0 <= idx < len(self._theme_keys) else ""
        return key, self.theme_combo.currentText(), self.theme_count.value()

    def get_replay_config(self) -> tuple[CompetitionSpec, list[RoundConfig], bool] | None:
        """Return (spec, rounds, use_timbre) for the selected past competition.

        Rounds reflect the strategy-combo choices, so the user can tune how each
        round draws from the matched history pool.
        """
        idx = self.replay_combo.currentIndex()
        if not (0 <= idx < len(self._replay_specs)):
            return None
        spec = self._replay_specs[idx]
        self._parse_rounds()
        for rc in self._round_cfgs:
            combo = self._strategy_combos.get(rc.name)
            if combo:
                rc.strategy     = combo.currentData()
                rc.prefer_fresh = (rc.strategy == "fresh")
        return spec, self._round_cfgs, self.timbre_check.isChecked()

    def set_library_status(self, msg: str, enable_generate: bool = False,
                           n_unanalyzed: int = 0, needs_build: bool = False):
        """`needs_build`: any index of the FAVORITES library is still short (see
        `_index_summary`) — the 🧱 shortcut only offers to fix that scope, so a
        half-built repository index must not put a button on screen."""
        self.status_lbl.setText(mark_index_gaps(msg))
        show_build = needs_build or n_unanalyzed > 0
        self.build_all_btn.setVisible(show_build)
        if show_build:
            missing = (i18n.t("%s file(s) in the favorites library have no\n"
                              "analysis yet") % f"{n_unanalyzed:,}"
                       if n_unanalyzed > 0 else
                       i18n.t("an index of the favorites library is not complete yet"))
            self.build_all_btn.setToolTip(
                i18n.t("🧱 Build ALL caches — %s. Asks for the scope\n"
                       "first; reuses everything already cached and can be "
                       "cancelled.") % missing)
        if enable_generate:
            self.generate_btn.setEnabled(True)
            self.import_btn.setEnabled(True)
            self.ai_playlist_btn.setEnabled(True)
