"""🎨 The look editor: every colour and shape of a look of your own, beside a
live preview of the app's controls dressed in it.

A built-in look comes with a picture of the real main window
(assets/themes/). A look of your own has none: rendering one means starting a
second app. `LookPreview` stands in, both here and in ⚙ Settings: a small set
of real widgets — a deck strip, tabs, a table with its round and dance bands,
buttons, fields — styled with the look's own sheet and palette, so it shows
what the app will, just not all of it.

The editor works on the look's dict form (shared/user_looks.py) and builds the
look from it on every change, through the same check a file goes through: what
it previews is exactly what will be saved.
"""
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox,
    QDialog, QDialogButtonBox, QFontComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSlider,
    QSpinBox, QTabBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from planner import i18n
from shared import looks, theme, user_looks

# The colour tokens in the editor's groups: (token, caption, what it colours).
TOKEN_GROUPS = (
    ("Grounds", (
        ("window", "Window", "The ground of the main window and the dialogs."),
        ("base", "Lists and fields", "Tables, lists and text fields."),
        ("alt_base", "Every other row", "The second row colour of a table."),
        ("header", "Headers", "Table headers and the menu bar."),
        ("tooltip", "Tooltips", "The ground of a tooltip."),
    )),
    ("Buttons", (
        ("surface", "Button face", "A button at rest."),
        ("surface_hover", "Under the mouse", "A button the mouse is over."),
        ("surface_pressed", "Pressed", "A button held down."),
        ("surface_top", "Light from above",
         "Set, a button fades from this colour down to its face, like a key "
         "on a mixing desk. Off, the face is flat."),
        ("header_top", "Header light from above",
         "The same fade for the table headers and the deck title strips."),
    )),
    ("Lines", (
        ("border", "Hairlines", "Frames, the table grid and separators."),
        ("border_strong", "Outlines", "A control's frame and the scrollbar handle."),
    )),
    ("Text", (
        ("text", "Text", "All ordinary text."),
        ("text_dim", "Dim text", "Disabled text, placeholders and side notes."),
    )),
    ("Accent", (
        ("accent", "Accent", "The default button and a switched-on toggle."),
        ("on_accent", "Text on the accent", "The caption on an accent fill."),
        ("accent_ink", "Accent as text", "Links, focus rings and the round bands' lettering."),
    )),
    ("Selection", (
        ("selection", "Selected row", "The band of the selected row."),
        ("on_selection", "Text on the selection", "The text in that band."),
    )),
)

BUTTON_CHOICES = (
    ("outline", "Outlined"),
    ("flat", "Flat, no frame"),
    ("key", "Desk key, lit from above"),
    ("glow", "Dark, glowing rim when on"),
    ("tonal", "Soft filled"),
    ("pill", "Pill, fully rounded"),
    ("bold", "2 px frame, high contrast"),
)
TAB_CHOICES = (
    ("underline", "Underlined"),
    ("segment", "Segmented"),
    ("key", "Desk keys"),
    ("pill", "Pills"),
)
FOCUS_CHOICES = (
    ("ring", "Ring around the field"),
    ("underline", "Line under the field"),
)

# What the editor warns about: (ink, ground, floor, what). WCAG AA for text,
# its large-text floor for what is bold or an accent. A warning, not a refusal:
# a look of your own may be as daring as you like.
CONTRAST_CHECKS = (
    ("text", "base", 4.5, "Text on lists"),
    ("text", "alt_base", 4.5, "Text on every other row"),
    ("text", "window", 4.5, "Text on the window"),
    ("text", "surface", 4.5, "Text on buttons"),
    ("text_dim", "base", 3.0, "Dim text on lists"),
    ("on_accent", "accent", 3.0, "Text on the accent"),
    ("accent_ink", "base", 3.0, "Accent as text"),
    ("on_selection", "selection", 4.5, "Text on the selection"),
)


def contrast_warnings(look: looks.Look) -> list[str]:
    """One line per pair that reads too faintly, in the order checked."""
    t = look.tokens
    out = []
    for ink, ground, floor, what in CONTRAST_CHECKS:
        ratio = theme.contrast_ratio(getattr(t, ink), getattr(t, ground))
        if ratio < floor:
            out.append(i18n.t("%s: %.1f : 1, should be at least %.1f")
                       % (i18n.t(what), ratio, floor))
    return out


def paint_swatch(button: QPushButton, color: str) -> None:
    """A button showing exactly `color`, with its hex readable on it. Past the
    theme hook: the swatch is the content, not the styling."""
    if not color:
        theme.set_stylesheet_unthemed(button, "padding:3px 10px;")
        button.setText(i18n.t("off"))
        return
    ink = "#ffffff" if theme.contrast_ratio(color, "#ffffff") >= 3.0 else "#141414"
    theme.set_stylesheet_unthemed(
        button, f"background:{color}; color:{ink}; border:1px solid #888;"
                f" border-radius:3px; padding:3px 10px; font-family:monospace;")
    button.setText(color)


class LookPreview(QFrame):
    """The app's controls in one look: what a look of your own shows instead of
    a picture of the main window."""

    # Invented on purpose: a preview must not advertise real songs.
    _SONGS = ((1, "Orchestra Nova", "Evening Waltz", "29"),
              (2, "The Ballroom Set", "Silver Lights", "28"),
              (1, "Café Quartet", "Midnight Tango", "32"))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("lookPreview")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        strips = QHBoxLayout()
        self._strip_on = QLabel("A  ·  Playlist 1")
        self._strip_off = QLabel("B  ·  Playlist 2")
        strips.addWidget(self._strip_on)
        strips.addWidget(self._strip_off)
        strips.addStretch()
        lay.addLayout(strips)

        tabs = QTabBar()
        # QTabBar and QTableWidgetItem are not among the hooked setters.
        tabs.addTab(i18n.t("Planning"))
        tabs.addTab(i18n.t("Playing"))
        tabs.setExpanding(False)
        lay.addWidget(tabs)

        self._table = QTableWidget(2 + len(self._SONGS), 4)
        self._table.setHorizontalHeaderLabels(["Group", "Artist", "Title", "BPM"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSpan(0, 0, 1, 4)
        self._table.setSpan(1, 0, 1, 4)
        self._table.setItem(0, 0, QTableWidgetItem(
            i18n.t("▼  PRELIMINARY ROUND  (2 heats)")))
        self._table.setItem(1, 0, QTableWidgetItem(i18n.t("▼  Slow Waltz")))
        for row, (heat, *cells) in enumerate(self._SONGS, start=2):
            self._table.setItem(row, 0, QTableWidgetItem(i18n.t("Heat %d") % heat))
            for col, text in enumerate(cells, start=1):
                self._table.setItem(row, col, QTableWidgetItem(text))
        self._table.resizeColumnsToContents()
        self._table.selectRow(3)
        self._fit_table()
        lay.addWidget(self._table)

        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton("Button"))
        toggle = QPushButton("Switched on")
        toggle.setCheckable(True)
        toggle.setChecked(True)
        buttons.addWidget(toggle)
        off = QPushButton("Disabled")
        off.setEnabled(False)
        buttons.addWidget(off)
        default = QPushButton("OK")
        default.setDefault(True)
        buttons.addWidget(default)
        buttons.addStretch()
        lay.addLayout(buttons)

        fields = QHBoxLayout()
        combo = QComboBox()
        combo.addItem("Standard")
        fields.addWidget(combo)
        search = QLineEdit()
        search.setPlaceholderText("Search…")
        fields.addWidget(search, stretch=1)
        check = QCheckBox("Ticked")
        check.setChecked(True)
        fields.addWidget(check)
        lay.addLayout(fields)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setValue(60)
        lay.addWidget(slider)
        self._dim = QLabel("Dim text: a hint, a placeholder.")
        lay.addWidget(self._dim)
        lay.addStretch()

    def set_look(self, look: looks.Look) -> None:
        t = look.tokens
        self.setPalette(theme.look_palette(look))
        self.setFont(looks.font(look, QApplication.font()))
        # The app takes its text colours from the application palette, which
        # here is the running theme's: a widget with a stylesheet falls back
        # to that one, not to its own. So the text colour leads the sheet,
        # where every rule of the look that names one still wins.
        theme.set_stylesheet_unthemed(
            self, f"QWidget {{ color: {t.text}; }}\n"
            + looks.stylesheet(look)
            + f"\n#lookPreview {{ background: {t.window};"
              f" border: 1px solid {t.border}; border-radius: {t.radius}px; }}"
              f"\n#lookPreview QLabel {{ background: transparent; }}")
        parts = looks.parts(look)
        theme.set_stylesheet_unthemed(self._strip_on, parts["deck_active"])
        theme.set_stylesheet_unthemed(self._strip_off, parts["deck_idle"])
        theme.set_stylesheet_unthemed(self._dim, f"color:{t.text_dim};")
        colors = looks.shared_colors(look)
        for row, (ground, ink) in ((0, ("_C_ROUND_BG", "_C_ROUND_FG")),
                                   (1, ("_C_DANCE_BG", "_C_DANCE_FG"))):
            item = self._table.item(row, 0)
            item.setBackground(QColor(colors[ground]))
            item.setForeground(QColor(colors[ink]))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        self._table.resizeColumnsToContents()
        self._fit_table()

    def _fit_table(self) -> None:
        """Every row shown, no scrollbar: a look's padding changes the heights."""
        table = self._table
        table.resizeRowsToContents()
        table.setFixedHeight(table.horizontalHeader().sizeHint().height()
                             + sum(table.rowHeight(r) for r in range(table.rowCount()))
                             + 2 * table.frameWidth() + 2)


class LookEditor(QDialog):
    """Edit one look of your own. `look()` is the result once accepted."""

    def __init__(self, look: looks.Look, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨  Edit look")
        self._data = user_looks.to_dict(look)
        self._swatches: dict[str, QPushButton] = {}
        self._gradients: dict[str, QCheckBox] = {}
        self._captions: dict[str, str] = {}

        outer = QHBoxLayout(self)
        form_host = QWidget()
        form = QVBoxLayout(form_host)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self._name = QLineEdit(look.caption)
        self._name.textChanged.connect(self._on_name)
        name_row.addWidget(self._name, stretch=1)
        form.addLayout(name_row)
        family = dict(looks.GROUPS).get(looks.family(look), "")
        family_note = QLabel(i18n.t(
            "Family: %s. The details it shares with the built-in looks of "
            "that group stay: faders, checkboxes, headers.") % i18n.t(family))
        family_note.setWordWrap(True)
        form.addWidget(family_note)

        # One grid for every group, so the swatches line up down the page.
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        row = 0
        for title, entries in TOKEN_GROUPS:
            grid.addWidget(self._heading(title), row, 0, 1, 3)
            row += 1
            for token, caption, tip in entries:
                label = QLabel(caption)
                label.setToolTip(tip)
                grid.addWidget(label, row, 0)
                swatch = QPushButton()
                swatch.setToolTip(tip)
                swatch.setMinimumWidth(96)
                swatch.clicked.connect(partial(self._pick, token))
                grid.addWidget(swatch, row, 1)
                self._swatches[token] = swatch
                self._captions[token] = caption
                if token in user_looks.OPTIONAL_COLORS:
                    fade = QCheckBox("Fade")
                    fade.setToolTip(tip)
                    fade.setChecked(bool(self._data["tokens"][token]))
                    fade.toggled.connect(partial(self._on_fade, token))
                    grid.addWidget(fade, row, 2)
                    self._gradients[token] = fade
                row += 1
        form.addLayout(grid)

        form.addWidget(self._heading("Shape and lettering"))
        shape = QGridLayout()
        shape.setColumnStretch(1, 1)
        shape.addWidget(QLabel("Corners:"), 0, 0)
        self._radius = QSpinBox()
        self._radius.setRange(0, user_looks.RADIUS_MAX)
        self._radius.setSuffix(" px")
        self._radius.setValue(self._data["tokens"]["radius"])
        self._radius.valueChanged.connect(self._on_radius)
        shape.addWidget(self._radius, 0, 1)
        self._buttons = self._choice(shape, 1, "Buttons:", BUTTON_CHOICES, "buttons")
        self._tabs = self._choice(shape, 2, "Tabs:", TAB_CHOICES, "tabs")
        self._focus = self._choice(shape, 3, "Focus:", FOCUS_CHOICES, "focus")
        shape.addWidget(QLabel("Font:"), 4, 0)
        self._font = QFontComboBox()
        self._font.setCurrentFont(QFont(self._data["fonts"][0]))
        self._font.currentFontChanged.connect(self._on_font)
        shape.addWidget(self._font, 4, 1)
        form.addLayout(shape)
        form.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(form_host)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(form_host.sizeHint().width() + 24)
        outer.addWidget(scroll)

        right = QVBoxLayout()
        self._preview = LookPreview()
        right.addWidget(self._preview)
        self._warnings = QLabel()
        self._warnings.setWordWrap(True)
        right.addWidget(self._warnings)
        note = QLabel("Saved looks are kept on this computer. The app takes a "
                      "changed look on its next start.")
        note.setWordWrap(True)
        right.addWidget(note)
        right.addStretch()
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                               | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        self._save = box.button(QDialogButtonBox.StandardButton.Save)
        right.addWidget(box)
        outer.addLayout(right, stretch=1)

        for token in self._swatches:
            paint_swatch(self._swatches[token], self._data["tokens"][token])
        self._refresh()
        self.resize(1040, 760)

    # ── Building ──────────────────────────────────────────────────────────────
    @staticmethod
    def _heading(text: str) -> QLabel:
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    def _choice(self, grid, row, caption, choices, field) -> QComboBox:
        grid.addWidget(QLabel(caption), row, 0)
        combo = QComboBox()
        for key, text in choices:
            combo.addItem(text, key)
        combo.setCurrentIndex(max(0, combo.findData(self._data[field])))
        combo.currentIndexChanged.connect(
            lambda _i: self._set(field, combo.currentData()))
        grid.addWidget(combo, row, 1)
        return combo

    # ── Changes ───────────────────────────────────────────────────────────────
    def _set(self, field, value) -> None:
        self._data[field] = value
        self._refresh()

    def _on_name(self, text: str) -> None:
        self._set("name", text.strip())

    def _on_radius(self, value: int) -> None:
        self._data["tokens"]["radius"] = value
        self._refresh()

    def _on_font(self, chosen: QFont) -> None:
        family = chosen.family()
        rest = [f for f in self._data["fonts"] if f != family]
        self._set("fonts", [family] + rest[:3])

    def _on_fade(self, token: str, on: bool) -> None:
        tokens = self._data["tokens"]
        face = tokens["surface" if token == "surface_top" else "header"]
        tokens[token] = looks.mix("#ffffff", face, 0.14) if on else ""
        paint_swatch(self._swatches[token], tokens[token])
        self._refresh()

    def _pick(self, token: str) -> None:
        current = self._data["tokens"][token] or self._data["tokens"]["surface"]
        # Not a patched static: the title is translated here.
        chosen = QColorDialog.getColor(QColor(current), self,
                                       i18n.t(self._captions[token]))
        if not chosen.isValid():
            return
        self._data["tokens"][token] = chosen.name()
        if token in self._gradients:
            self._gradients[token].blockSignals(True)
            self._gradients[token].setChecked(True)
            self._gradients[token].blockSignals(False)
        paint_swatch(self._swatches[token], chosen.name())
        self._refresh()

    def _refresh(self) -> None:
        try:
            look = user_looks.from_dict(self._data)
        except ValueError:
            # Only the name can be wrong here — every other field is picked
            # from what is valid. No name, nothing to save.
            self._save.setEnabled(False)
            return
        self._save.setEnabled(True)
        self._preview.set_look(look)
        warnings = contrast_warnings(look)
        self._warnings.setText(
            i18n.t("⚠ Hard to read:") + "\n" + "\n".join(warnings) if warnings
            else i18n.t("✓ Every text reads clearly against its ground."))

    def look(self) -> looks.Look:
        return user_looks.from_dict(self._data)
