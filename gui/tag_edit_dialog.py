"""🏷 The tag editor, laid out like Mp3tag: the MP3's own fields, the app's.

Opened from a row's context menu, for one track or every selected one. The
dialog only says what each track should become; the window writes and stores.

"In the MP3 file" is Mp3tag's form — title, artist, album, year, …, the cover
— for every selected MP3 on disk, written into the files themselves
(planner.id3_frames). "In the app" holds stars, classes, instrumental,
markers and the free Custom field, stored as an in-app tag edit
(planner.tag_edits — the DB) and, if the user says yes when saving, written
into the MP3 too — Custom only while it is mapped to a frame
(planner.custom_field).

With several tracks, a field they disagree on starts as "keep": a form field
on "< keep >", a class box half-ticked, the stars on "keep", the marker line
empty. Only what is actually changed reaches the tracks — ticking B on three
tracks with different class tags adds B to each and leaves their other
classes alone; a typed album goes into all of them.

The second tab, "Extended tags", lists every ID3 frame of ONE track —
UltraMixer's TXXX frames, MediaMonkey's comments, WMP's rating. The frames the
form shows, and the one Custom is mapped to, are read-only there; the rest is
edited there and written along.
"""
import re
from pathlib import Path

from mutagen import MutagenError

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from planner import i18n, id3_frames

CLASSES = ("D", "C", "B", "A", "S")
_KEEP = -1          # the stars combo's "keep each track's own"
_MAX_SUGGESTIONS = 12
_CHIP_COLUMNS = 4
_RAW_FRAME, _RAW_DESC, _RAW_VALUE = range(3)
_KEY_ROLE = Qt.ItemDataRole.UserRole
_FIXED_ROLE = Qt.ItemDataRole.UserRole + 1   # shown as text to copy, not changed
_FRAME_ROLE = Qt.ItemDataRole.UserRole + 2   # the frame id of a row
_EDITABLE_ROLE = Qt.ItemDataRole.UserRole + 3   # a text the frame can hold
_WITH_DESC = ("TXXX", "COMM")    # added frames told apart by a description
# The MP3 form's rows as Mp3tag lays them out; several fields share a row.
_FORM_ROWS = (
    (("title", "Title:"),),
    (("artist", "Artist:"),),
    (("album", "Album:"),),
    (("year", "Year:"), ("track", "Track:"), ("genre", "Genre:")),
    (("comment", "Comment:"),),
    (("albumartist", "Album artist:"),),
    (("composer", "Composer:"),),
    (("disc", "Disc number:"), ("replaygain", "Replay Gain:")),
)
_FORM_COLUMNS = 6           # label + field, three times
_MAX_FORM_VALUES = 25       # a differing field's dropdown offers this many
_COVER = 150


def parse_markers(text: str) -> list[str]:
    """'Classic, vocal_f;  remix' → ['classic', 'vocal_f', 'remix']: lower-case
    like the file's markers are read, in typed order, each once."""
    out: list[str] = []
    for part in re.split(r"[,;]", text):
        m = part.strip().lower()
        if m and m not in out:
            out.append(m)
    return out


def marker_suggestions(entries, limit: int = _MAX_SUGGESTIONS) -> list[str]:
    """The markers the library uses most, most-used first. One-off notes (a
    store's song id, a pasted album credit) are not offered."""
    counts: dict[str, int] = {}
    for e in entries:
        for m in getattr(e, "comment_tags", None) or ():
            counts[m] = counts.get(m, 0) + 1
    usable = [m for m, n in counts.items()
              if n >= 3 and len(m) <= 20 and "\n" not in m and "\r" not in m]
    return sorted(usable, key=lambda m: (-counts[m], m))[:limit]


def _tristate(values) -> Qt.CheckState:
    values = set(values)
    if values == {True}:
        return Qt.CheckState.Checked
    if values == {False}:
        return Qt.CheckState.Unchecked
    return Qt.CheckState.PartiallyChecked


def _frame_label(frame_id: str) -> str:
    name = id3_frames.FRAME_NAMES.get(frame_id)
    return f"{i18n.t(name)} ({frame_id})" if name else frame_id


def _source_label(source) -> str:
    """'Custom text (TXXX) "ultramixer_last_played"' — a mapping as the
    Extended tab shows the frame."""
    frame_id, desc = source
    return f'{_frame_label(frame_id)} "{desc}"' if desc else _frame_label(frame_id)


class _CopyOnlyDelegate(QStyledItemDelegate):
    """A frame's description is part of its identity, so it can't be changed
    here; a double-click still opens it as text to mark and copy."""

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if index.data(_FIXED_ROLE) and isinstance(editor, QLineEdit):
            editor.setReadOnly(True)
        return editor

    def setModelData(self, editor, model, index):
        if not index.data(_FIXED_ROLE):
            super().setModelData(editor, model, index)


class TagEditDialog(QDialog):
    """Edit the tags of `entries`; read the result with `changes_for(entry)`,
    `raw_edits()` for the MP3 itself, or `reset_requested` for "back to what
    the files say". `custom_source` is the (frame id, description) the Custom
    field is mapped to (planner.custom_field.source()), None for none.
    `map_custom(frame id, description)` maps it anew from a row of the
    Extended tab and says whether it took; without it that isn't offered."""

    def __init__(self, entries, suggestions=(), parent=None, custom_source=None,
                 map_custom=None):
        super().__init__(parent)
        self._entries = list(entries)
        self._custom_source = custom_source
        self._map_custom = map_custom
        self.reset_requested = False
        n = len(self._entries)
        self.setWindowTitle(
            i18n.t("🏷  Edit tags") if n == 1
            else i18n.t("🏷  Edit tags of %d tracks") % n)
        outer = QVBoxLayout(self)
        self._tabs = QTabWidget()
        outer.addWidget(self._tabs)
        page = QWidget()
        lyt = QVBoxLayout(page)
        self._tabs.addTab(page, i18n.t("Tags"))

        head = QLabel(self._entries[0].title or "" if n == 1
                      else i18n.t("%d tracks — a field they differ in is kept "
                                  "per track until you change it.") % n)
        head.setWordWrap(True)
        lyt.addWidget(head)
        self._build_file_box(lyt)

        app_box = QGroupBox(i18n.t("In the app"))
        lyt.addWidget(app_box)
        form = QFormLayout(app_box)

        # ★ Stars
        self._stars = QComboBox()
        ratings = {int(e.rating or 0) for e in self._entries}
        if len(ratings) > 1:
            self._stars.addItem(i18n.t("keep (differs per track)"), _KEEP)
        self._stars.addItem(i18n.t("no stars"), 0)
        for s in range(1, 6):
            self._stars.addItem("★" * s, s)
        self._stars.setCurrentIndex(
            self._stars.findData(ratings.pop() if len(ratings) == 1 else _KEEP))
        self._stars_start = self._stars.currentData()
        form.addRow(i18n.t("Stars:"), self._stars)

        # Classes
        cls_row = QWidget()
        cls_lyt = QHBoxLayout(cls_row)
        cls_lyt.setContentsMargins(0, 0, 0, 0)
        self._cls: dict[str, QCheckBox] = {}
        self._cls_start: dict[str, Qt.CheckState] = {}
        for c in CLASSES:
            box = QCheckBox(c)
            state = _tristate(c in (e.classes_ok or ()) for e in self._entries)
            box.setTristate(state == Qt.CheckState.PartiallyChecked)
            box.setCheckState(state)
            self._cls[c] = box
            self._cls_start[c] = state
            cls_lyt.addWidget(box)
        cls_lyt.addStretch(1)
        form.addRow(i18n.t("Classes:"), cls_row)
        hint = QLabel(i18n.t("None ticked = suits every class."))
        hint.setStyleSheet("color: #777;")
        form.addRow("", hint)

        # Instrumental
        self._instr = QCheckBox(i18n.t("Instrumental (no vocals)"))
        state = _tristate(bool(e.is_instrumental) for e in self._entries)
        self._instr.setTristate(state == Qt.CheckState.PartiallyChecked)
        self._instr.setCheckState(state)
        self._instr_start = state
        form.addRow("", self._instr)

        # Markers
        marks = {tuple(e.comment_tags or ()) for e in self._entries}
        self._markers = QLineEdit(", ".join(marks.pop()) if len(marks) == 1 else "")
        if self._markers.text() == "" and n > 1 and any(e.comment_tags for e in self._entries):
            self._markers.setPlaceholderText(
                i18n.t("differs per track — typing here replaces them all"))
        else:
            self._markers.setPlaceholderText(i18n.t("e.g. classic, vocal_f"))
        self._markers_start = self._markers.text()
        form.addRow(i18n.t("Markers:"), self._markers)
        # The library's most-used markers as chips, lit while set. A fixed grid,
        # not a flow layout: a dialog sizes itself from its size hint and never
        # asks a wrapping row how tall it gets at the real width.
        self._chips: dict[str, QPushButton] = {}
        if suggestions:
            chips = QWidget()
            chips.setStyleSheet(
                "QPushButton { border: 1px solid palette(mid); border-radius: 9px;"
                " padding: 2px 10px; background: transparent; }"
                "QPushButton:checked { background: palette(highlight);"
                " color: palette(highlighted-text); border-color: palette(highlight); }")
            grid = QGridLayout(chips)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(4)
            for i, m in enumerate(suggestions):
                b = QPushButton(m)
                b.setCheckable(True)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setToolTip(i18n.t("Add this marker, or take it out again"))
                b.clicked.connect(lambda _=False, m=m: self.toggle_marker(m))
                grid.addWidget(b, i // _CHIP_COLUMNS, i % _CHIP_COLUMNS)
                self._chips[m] = b
            form.addRow("", chips)
            self._markers.textChanged.connect(self._sync_chips)
            self._sync_chips()

        # Custom — free text, or what the mapped frame says
        values = {e.custom or "" for e in self._entries}
        self._custom = QLineEdit(values.pop() if len(values) == 1 else "")
        if values:
            self._custom.setPlaceholderText(
                i18n.t("differs per track — typing here replaces them all"))
        self._custom_start = self._custom.text()
        self._custom_tip()
        form.addRow(i18n.t("Custom:"), self._custom)
        lyt.addStretch(1)
        self._build_raw_tab()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self._reset_btn = buttons.addButton(
            i18n.t("↺  Back to the file's tags"), QDialogButtonBox.ButtonRole.ResetRole)
        self._reset_btn.setToolTip(i18n.t(
            "Forget every change made here in the app — stars, classes,\n"
            "instrumental, markers and Custom read from the MP3 again."))
        self._reset_btn.setEnabled(any(e.tag_edits for e in self._entries))
        self._reset_btn.clicked.connect(self._on_reset)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    # ── The MP3's own fields, like Mp3tag ───────────────────────────────────
    def _build_file_box(self, lyt):
        """Title, artist, … of every selected MP3 on disk: a value they share,
        or "< keep >" where they differ — written into the files on Save."""
        self._keep = i18n.t("< keep >")
        self._blank = i18n.t("< blank >")
        self._file_box = QGroupBox(i18n.t("In the MP3 file"))
        lyt.addWidget(self._file_box)
        row = QHBoxLayout(self._file_box)
        grid = QGridLayout()
        row.addLayout(grid, 1)
        self._cover = QLabel()
        self._cover.setFixedSize(_COVER, _COVER)
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover.setStyleSheet("border: 1px solid palette(mid); color: #777;")
        row.addWidget(self._cover, 0, Qt.AlignmentFlag.AlignTop)

        self._mp3s = [e for e in self._entries
                      if Path(e.path).suffix.lower() == ".mp3" and Path(e.path).is_file()]
        self._form_read: list[dict] = []
        covers = []
        reason = None if self._mp3s else i18n.t("Only for MP3 files on disk")
        try:
            for e in self._mp3s:
                self._form_read.append(id3_frames.read_form(e.path))
                covers.append(id3_frames.read_cover(e.path))
        except (OSError, ValueError, MutagenError) as exc:
            reason = i18n.t("Couldn't read the MP3 tags: %s") % exc
        if reason:
            self._mp3s, self._form_read, covers = [], [], []
            self._file_box.setEnabled(False)
            self._file_box.setToolTip(reason)

        self._form: dict[str, QComboBox] = {}
        self._form_start: dict[str, str] = {}
        for r, fields in enumerate(_FORM_ROWS):
            for i, (field, label) in enumerate(fields):
                combo = self._form_combo(
                    [f[field].value if f[field] else "" for f in self._form_read] or [""])
                last = i == len(fields) - 1
                grid.addWidget(QLabel(i18n.t(label)), r, 2 * i)
                grid.addWidget(combo, r, 2 * i + 1, 1,
                               _FORM_COLUMNS - 2 * i - 1 if last else 1)
                self._form[field] = combo
                self._form_start[field] = combo.currentText()
        for c in range(1, _FORM_COLUMNS, 2):
            grid.setColumnStretch(c, 1)

        if len(set(covers)) > 1:
            self._cover.setText(i18n.t("Covers differ"))
        elif covers and covers[0] is not None:
            pm = QPixmap()
            if pm.loadFromData(covers[0]):
                self._cover.setPixmap(pm.scaled(
                    _COVER - 2, _COVER - 2, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
            else:
                self._cover.setText(i18n.t("Cover can't be shown"))
        else:
            self._cover.setText(i18n.t("No cover"))

    def _form_combo(self, values: list) -> QComboBox:
        """An editable field: the shared value, or "< keep >" when the tracks
        differ, with "< blank >" and their values to pick from."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(6)
        distinct = list(dict.fromkeys(values))
        combo.addItem(self._keep)
        combo.addItem(self._blank)
        for v in [v for v in distinct if v][:_MAX_FORM_VALUES]:
            combo.addItem(v)
        combo.setEditText(distinct[0] if len(distinct) == 1 else self._keep)
        return combo

    def form_mp3s(self) -> list:
        """The entries the form is written into: the selection's MP3s on disk."""
        return list(self._mp3s)

    def form_changes(self) -> dict:
        """{form field: new value} for every field changed — '' removes it from
        the files; a field left on "< keep >" or as it was isn't there."""
        if not self._mp3s:
            return {}
        out = {}
        for field, combo in self._form.items():
            text = combo.currentText()
            if text not in (self._keep, self._form_start[field]):
                out[field] = "" if text == self._blank else text
        return out

    # ── "Extended tags" ─────────────────────────────────────────────────────
    def _build_raw_tab(self):
        page = QWidget()
        lyt = QVBoxLayout(page)
        idx = self._tabs.addTab(page, i18n.t("Extended tags"))
        hint = QLabel(i18n.t(
            "Every frame of the MP3, written straight into the file on Save. "
            "The fields of the form on the first tab are changed there."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #777;")
        lyt.addWidget(hint)

        self._raw = QTableWidget(0, 3)
        self._raw.setHorizontalHeaderLabels(
            [i18n.t("Frame"), i18n.t("Description"), i18n.t("Value")])
        self._raw.verticalHeader().hide()
        self._raw.horizontalHeader().setStretchLastSection(True)
        self._raw.setColumnWidth(_RAW_FRAME, 170)
        self._raw.setColumnWidth(_RAW_DESC, 170)
        self._raw.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._raw.setMinimumSize(620, 280)
        self._raw.setItemDelegateForColumn(_RAW_DESC, _CopyOnlyDelegate(self._raw))
        self._raw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._raw.customContextMenuRequested.connect(self._raw_context_menu)
        lyt.addWidget(self._raw)

        row = QHBoxLayout()
        self._raw_add_btn = QPushButton(i18n.t("➕  Add field"))
        self._raw_add_btn.clicked.connect(self._raw_add)
        self._raw_remove_btn = QPushButton(i18n.t("➖  Remove selected"))
        self._raw_remove_btn.clicked.connect(self._raw_remove)
        row.addWidget(self._raw_add_btn)
        row.addWidget(self._raw_remove_btn)
        row.addStretch(1)
        lyt.addLayout(row)

        self._raw_start: dict[str, str] = {}
        self._raw_deleted: list[str] = []
        self._raw_version = 3
        self._raw_ok = False
        self._raw_form: dict[str, str] = {}
        self._raw_custom: str | None = None   # key of the frame Custom is mapped to
        reason = None
        path = Path(self._entries[0].path)
        if len(self._entries) != 1:
            reason = i18n.t("Only for one track at a time")
        elif path.suffix.lower() != ".mp3" or not path.is_file():
            reason = i18n.t("Only for an MP3 file on disk")
        else:
            try:
                fields = id3_frames.read_fields(path)
                self._raw_version = id3_frames.tag_version(path)
            except (OSError, ValueError, MutagenError) as exc:
                reason = i18n.t("Couldn't read the MP3 tags: %s") % exc
        if reason:
            self._tabs.setTabEnabled(idx, False)
            self._tabs.setTabToolTip(idx, reason)
            return
        self._raw_ok = True
        # The form's fields: shown here as the form has them, changed there.
        self._raw_form = {f.key: field for field, f in self._form_read[0].items() if f}
        if self._custom_source:
            frame_id, desc = self._custom_source
            self._raw_custom = next(
                (f.key for f in fields if f.frame == frame_id
                 and (f.frame not in _WITH_DESC or f.desc.lower() == desc.lower())), None)
        for f in fields:
            self._raw_fill(f)
        for key, field in self._raw_form.items():
            self._form[field].editTextChanged.connect(
                lambda text, key=key: self._raw_mirror(key, text))

    def _raw_fill(self, f):
        r = self._raw.rowCount()
        self._raw.insertRow(r)
        fixed = ~Qt.ItemFlag.ItemIsEditable
        frame = QTableWidgetItem(_frame_label(f.frame))
        frame.setData(_KEY_ROLE, f.key)
        frame.setData(_FRAME_ROLE, f.frame)
        frame.setFlags(frame.flags() & fixed)
        desc = QTableWidgetItem(f.desc)
        desc.setData(_FIXED_ROLE, True)
        value = QTableWidgetItem(f.value)
        value.setData(_EDITABLE_ROLE, f.editable)
        self._raw_lock(value, f.key)
        self._raw.setItem(r, _RAW_FRAME, frame)
        self._raw.setItem(r, _RAW_DESC, desc)
        self._raw.setItem(r, _RAW_VALUE, value)
        self._raw_start[f.key] = f.value

    def _raw_lock(self, value: QTableWidgetItem, key: str):
        """A value is typed here unless the form or the Custom field owns its
        frame, or the frame holds no text."""
        locked = True
        if key in self._raw_form:
            tip = i18n.t("Changed in the form on the first tab")
        elif key == self._raw_custom:
            tip = i18n.t("Changed in the Custom field on the first tab")
        elif not value.data(_EDITABLE_ROLE):
            value.setForeground(Qt.GlobalColor.gray)
            tip = i18n.t("Can only be removed, not edited here")
        else:
            locked, tip = False, value.text()
        editable = Qt.ItemFlag.ItemIsEditable
        value.setFlags(value.flags() & ~editable if locked else value.flags() | editable)
        value.setToolTip(tip)

    def _raw_mirror(self, key: str, text: str):
        if text == self._keep:
            text = self._raw_start[key]
        elif text == self._blank:
            text = ""
        for r in range(self._raw.rowCount()):
            if self._raw.item(r, _RAW_FRAME).data(_KEY_ROLE) == key:
                self._raw.item(r, _RAW_VALUE).setText(text)

    def _raw_context_menu(self, pos):
        index = self._raw.indexAt(pos)
        if index.isValid():
            self._raw_menu(index.row(), index.column()).exec(
                self._raw.viewport().mapToGlobal(pos))

    def _raw_menu(self, r: int, c: int) -> QMenu:
        """The right-click menu of a cell on the Extended tab."""
        menu = QMenu(self._raw)
        item = self._raw.item(r, c)
        text = item.text() if item is not None else ""
        copy = menu.addAction("📋  Copy")
        copy.setEnabled(bool(text))
        copy.triggered.connect(lambda: QGuiApplication.clipboard().setText(text))
        if self._map_custom is not None:
            source = self._raw_source(r)
            fill = menu.addAction("🏷  Fill Custom from this tag")
            fill.setEnabled(source is not None
                            and self._raw.item(r, _RAW_FRAME).data(_KEY_ROLE)
                            != self._raw_custom)
            fill.triggered.connect(lambda: self._map_custom_to_row(r))
        return menu

    def _raw_source(self, r: int):
        """(frame id, description) a mapping of Custom to row `r` would be,
        or None when that frame can't fill it: one the form shows, one that
        holds no text, a new row, or a comment without a description — that
        is the plain one the classes go into."""
        frame = self._raw.item(r, _RAW_FRAME)
        fid = frame.data(_FRAME_ROLE)
        desc = self._raw.item(r, _RAW_DESC).text()
        if (frame.data(_KEY_ROLE) is None or fid not in id3_frames.custom_frames()
                or (fid in _WITH_DESC and not desc.strip())):
            return None
        return fid, desc if fid in _WITH_DESC else ""

    def _map_custom_to_row(self, r: int):
        """🏷 Fill Custom from this tag: the window maps it (every track's
        Custom is read from that frame), then this dialog shows it so."""
        source = self._raw_source(r)
        if source is None or not self._map_custom(*source):
            return
        old = self._raw_custom
        self._custom_source = source
        self._raw_custom = key = self._raw.item(r, _RAW_FRAME).data(_KEY_ROLE)
        # The frame's value is the Custom field's now; an edit made to it here
        # would be left out of the write.
        self._raw.item(r, _RAW_VALUE).setText(self._raw_start[key])
        for row in range(self._raw.rowCount()):
            k = self._raw.item(row, _RAW_FRAME).data(_KEY_ROLE)
            if k is not None and k in (old, key):
                self._raw_lock(self._raw.item(row, _RAW_VALUE), k)
        # An untouched Custom field shows what the file says, unless a value
        # typed in the app before still wins.
        entry = self._entries[0]
        if (self._custom.text() == self._custom_start
                and "custom" not in (entry.tag_edits or {})):
            self._custom.setText(self._raw_start[key])
            self._custom_start = self._custom.text()
        self._custom_tip()

    def _custom_tip(self):
        self._custom.setToolTip(
            i18n.t("Filled from the MP3 tag %s. What is typed here wins over it.")
            % _source_label(self._custom_source) if self._custom_source
            else i18n.t("Kept in the app only. Right-click a column header to fill "
                        "it from an MP3 tag."))

    def _raw_keys(self) -> set:
        return {k for r in range(self._raw.rowCount())
                if (k := self._raw.item(r, _RAW_FRAME).data(_KEY_ROLE)) is not None}

    def _raw_add(self):
        """➕ A new row: the frame from a list, its description, its value."""
        combo = QComboBox()
        present = self._raw_keys() | id3_frames.form_frame_ids(self._raw_version)
        for fid in id3_frames.addable_frames(self._raw_version, present):
            combo.addItem(_frame_label(fid), fid)
        r = self._raw.rowCount()
        self._raw.insertRow(r)
        frame = QTableWidgetItem()
        frame.setFlags(frame.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._raw.setItem(r, _RAW_FRAME, frame)
        self._raw.setCellWidget(r, _RAW_FRAME, combo)
        self._raw.setItem(r, _RAW_DESC, QTableWidgetItem(""))
        self._raw.setItem(r, _RAW_VALUE, QTableWidgetItem(""))
        combo.currentIndexChanged.connect(lambda _i, c=combo: self._raw_frame_chosen(c))
        self._raw.setCurrentCell(r, _RAW_DESC)

    def _raw_frame_chosen(self, combo):
        """Only a custom text or comment has a description to type."""
        for r in range(self._raw.rowCount()):
            if self._raw.cellWidget(r, _RAW_FRAME) is combo:
                desc = self._raw.item(r, _RAW_DESC)
                if combo.currentData() in _WITH_DESC:
                    desc.setFlags(desc.flags() | Qt.ItemFlag.ItemIsEditable)
                else:
                    desc.setText("")
                    desc.setFlags(desc.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return

    def _raw_remove(self):
        rows = sorted({i.row() for i in self._raw.selectedIndexes()}, reverse=True)
        for r in rows:
            key = self._raw.item(r, _RAW_FRAME).data(_KEY_ROLE)
            if key in self._raw_form or (key is not None and key == self._raw_custom):
                continue
            if key is not None:
                self._raw_deleted.append(key)
            self._raw.removeRow(r)

    def raw_edits(self) -> dict | None:
        """What the "Extended tags" tab writes into the file — {"sets": {key:
        value}, "deletes": [key], "adds": [(frame id, description, value)]} —
        or None when nothing there was changed. A new row without a value is
        left out: an empty frame is never written."""
        if not self._raw_ok:
            return None
        sets, adds = {}, []
        for r in range(self._raw.rowCount()):
            key = self._raw.item(r, _RAW_FRAME).data(_KEY_ROLE)
            value = self._raw.item(r, _RAW_VALUE).text()
            if key is None:
                fid = self._raw.cellWidget(r, _RAW_FRAME).currentData()
                desc = self._raw.item(r, _RAW_DESC).text() if fid in _WITH_DESC else ""
                if value:
                    adds.append((fid, desc, value))
            elif (key not in self._raw_form and key != self._raw_custom
                  and value != self._raw_start[key]):
                sets[key] = value
        if not (sets or self._raw_deleted or adds):
            return None
        return {"sets": sets, "deletes": list(self._raw_deleted), "adds": adds}

    # ── what the tracks become ──────────────────────────────────────────────
    def toggle_marker(self, marker: str):
        marks = parse_markers(self._markers.text())
        if marker in marks:
            marks.remove(marker)
        else:
            marks.append(marker)
        self._markers.setText(", ".join(marks))

    def _sync_chips(self):
        marks = set(parse_markers(self._markers.text()))
        for m, b in self._chips.items():
            b.setChecked(m in marks)

    def _on_reset(self):
        self.reset_requested = True
        self.accept()

    def changes_for(self, entry) -> dict:
        """What `entry` should become: only the fields changed in the dialog,
        and for a half-ticked class the track's own say."""
        out = {}
        stars = self._stars.currentData()
        if stars != self._stars_start and stars != _KEEP:
            out["rating"] = stars
        if any(self._cls[c].checkState() != self._cls_start[c] for c in CLASSES):
            own = set(entry.classes_ok or ())
            keep = []
            for c in CLASSES:
                state = self._cls[c].checkState()
                if (state == Qt.CheckState.Checked
                        or (state == Qt.CheckState.PartiallyChecked and c in own)):
                    keep.append(c)
            out["classes_ok"] = keep
        state = self._instr.checkState()
        if state != self._instr_start and state != Qt.CheckState.PartiallyChecked:
            out["is_instrumental"] = state == Qt.CheckState.Checked
        if self._markers.text() != self._markers_start:
            out["comment_tags"] = parse_markers(self._markers.text())
        if self._custom.text() != self._custom_start:
            out["custom"] = self._custom.text()
        return out


class CustomSourceDialog(QDialog):
    """Which MP3 frame fills the Custom field: a custom text or comment by
    its description, or a standard text frame the form doesn't show — or
    none, and the field is kept in the app only. `source()` is the answer,
    (frame id or None, description). `samples` is what a look into some MP3s
    of the archive found (id3_frames.sample_custom): their descriptions are
    offered, and what the chosen one holds is shown."""

    def __init__(self, current=None, parent=None, samples=(0, {})):
        super().__init__(parent)
        self._read, self._samples = samples
        self.setWindowTitle(i18n.t("🏷  Custom field"))
        lyt = QVBoxLayout(self)
        hint = QLabel(i18n.t(
            "The Custom column shows this tag of each MP3. A value typed in the "
            "🏷 editor wins over it, and on Save it can be written into it."))
        hint.setWordWrap(True)
        lyt.addWidget(hint)
        form = QFormLayout()
        lyt.addLayout(form)
        self._frame = QComboBox()
        self._frame.addItem(i18n.t("In the app only"), None)
        for fid in id3_frames.custom_frames():
            self._frame.addItem(_frame_label(fid), fid)
        form.addRow(i18n.t("Frame:"), self._frame)
        self._desc = QComboBox()
        self._desc.setEditable(True)
        self._desc.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._desc.lineEdit().setPlaceholderText(i18n.t("e.g. ultramixer_last_played"))
        form.addRow(i18n.t("Description:"), self._desc)
        self._seen = QLabel()
        self._seen.setWordWrap(True)
        self._seen.setStyleSheet("color: #777;")
        lyt.addWidget(self._seen)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lyt.addWidget(buttons)
        if current:
            self._frame.setCurrentIndex(max(0, self._frame.findData(current[0])))
        self._offer_descs()
        if current:
            self._desc.setEditText(current[1])
        self._frame.currentIndexChanged.connect(self._offer_descs)
        self._frame.currentIndexChanged.connect(self._sync)
        self._desc.editTextChanged.connect(self._sync)
        self._sync()

    def _offer_descs(self):
        """The descriptions the sampled MP3s have for the chosen frame, the
        most common first; what is typed stays."""
        fid, typed = self._frame.currentData(), self._desc.currentText()
        found = sorted(((d, n) for (f, d), (n, _ex) in self._samples.items()
                        if f == fid and d), key=lambda dn: (-dn[1], dn[0].lower()))
        self._desc.blockSignals(True)
        self._desc.clear()
        for desc, _n in found:
            self._desc.addItem(desc)
        self._desc.setEditText(typed)
        self._desc.blockSignals(False)

    def _sync(self):
        """A custom text or comment is told apart only by its description —
        without one, a comment would be the plain one the classes go into."""
        with_desc = self._frame.currentData() in _WITH_DESC
        self._desc.setEnabled(with_desc)
        self._ok.setEnabled(not with_desc or bool(self._desc.currentText().strip()))
        self._show_seen()

    def _show_seen(self):
        """How many of the sampled MP3s hold the chosen tag, and one value."""
        fid, desc = self.source()
        if fid is None or not self._read or (fid in _WITH_DESC and not desc):
            self._seen.setText("")
            return
        hit = next(((n, ex) for (f, d), (n, ex) in self._samples.items()
                    if f == fid and d.lower() == desc.lower()), None)
        if hit is None:
            self._seen.setText(i18n.t("In none of the %d sampled MP3s") % self._read)
        else:
            self._seen.setText(i18n.t("In %d of %d sampled MP3s, e.g. “%s”")
                               % (hit[0], self._read, hit[1]))

    def source(self) -> tuple:
        fid = self._frame.currentData()
        return fid, self._desc.currentText().strip() if fid in _WITH_DESC else ""
