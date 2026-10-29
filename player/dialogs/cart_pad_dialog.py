"""🎛 The cartwall's pad settings: the per-pad dialog.

CartPadDialog edits one pad (label, colour, volume, endless repeat, ducking,
its own fade); the fade the whole wall uses is in ⚙ Settings ▸ 🎛 Cartwall.
The click-to-type labels live here too.
The wall and its pads are in player.widgets.cartwall.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QSlider,
    QToolButton,
    QVBoxLayout,
)

from planner import i18n
from planner.playing import cartwall as pc

PAD_COLOURS = pc.PAD_COLOURS    # kept with the model, for ⚙ Settings too


# ─────────────────────────────────────────────────────────────────────────────
# Per-pad settings
# ─────────────────────────────────────────────────────────────────────────────
class CartPadDialog(QDialog):
    """Label, colour, volume, endless repeat, and whether this pad ducks the
    deck music. A looping background bed wants 25 % and no ducking; a fanfare
    wants full level and the music out of its way."""

    previewVolume = Signal(float)   # the slider, while it is being dragged
    previewFire = Signal(bool)      # ▶ / ⏹ inside the dialog

    def __init__(self, pad: pc.CartPad, parent=None, slot_key: str = "",
                 pad_count: int = 1, wall_fade_ms: int = pc.DEFAULT_FADE_MS,
                 background_pauses: bool = False,
                 background_volume: float = pc.DEFAULT_BG_VOLUME_PCT / 100):
        super().__init__(parent)
        self.setWindowTitle("Pad settings")
        self._pad = pad
        self._bg_volume = background_volume
        lyt = QVBoxLayout(self)

        lyt.addWidget(QLabel(f"🎵  {Path(pad.path).name}"))
        if pad_count > 1:
            # Which of these fields reach the other pads is not guessable, so it
            # is stated rather than discovered after the fact.
            note = QLabel(i18n.t("✏  %d pads selected — what you change here "
                                 "(colour, volume, fade, 🔁, 🔈, 🎶, S) "
                                 "applies to all of them.\n"
                                 "Label and shortcut stay with this pad.") % pad_count)
            note.setWordWrap(True)
            lyt.addWidget(note)
        self._label = QLineEdit(pad.label)
        self._label.setPlaceholderText(pc.default_label(pad.path))
        row = QHBoxLayout()
        row.addWidget(QLabel("Label"))
        row.addWidget(self._label, 1)
        lyt.addLayout(row)

        self._colour = QComboBox()
        for name, value in PAD_COLOURS.items():
            self._colour.addItem(name, value)
        idx = self._colour.findData(pad.colour)
        self._colour.setCurrentIndex(idx if idx >= 0 else 0)
        row = QHBoxLayout()
        row.addWidget(QLabel("Colour"))
        row.addWidget(self._colour, 1)
        lyt.addLayout(row)

        self._build_volume_row(lyt, pad)

        # The wall's fade unless this pad says otherwise: most walls want one
        # answer, but a sting should be gone the moment it is tapped again while
        # a bed wants seconds.
        self._wall_fade = max(0, min(pc.MAX_FADE_MS, int(wall_fade_ms)))
        self._fade_own = QCheckBox("Own fade-out")
        self._fade_own.setChecked(pad.fade_ms is not None)
        self._fade = QSlider(Qt.Orientation.Horizontal)
        self._fade.setRange(0, pc.MAX_FADE_MS)
        self._fade.setSingleStep(100)
        self._fade.setPageStep(500)
        self._fade.setValue(int(pad.fade_ms if pad.fade_ms is not None
                                else self._wall_fade))
        self._fade_lbl = TypedValue(self._fade, 1000)
        self._fade_lbl.setMinimumWidth(56)
        self._fade.valueChanged.connect(self._show_fade)
        self._fade_own.toggled.connect(self._on_fade_own)
        self._on_fade_own(self._fade_own.isChecked())
        row = QHBoxLayout()
        row.addWidget(self._fade_own)
        row.addWidget(self._fade, 1)
        row.addWidget(self._fade_lbl)
        lyt.addLayout(row)

        # A key of its own travels WITH the pad, unlike the slot default, which
        # belongs to the position on the wall.
        self._key = QKeySequenceEdit()
        self._key.setKeySequence(QKeySequence(pad.shortcut))
        clear_key = QToolButton()
        clear_key.setText("✕")
        clear_key.setAutoRaise(True)
        clear_key.setToolTip("Back to this slot's default key")
        clear_key.clicked.connect(self._key.clear)
        row = QHBoxLayout()
        row.addWidget(QLabel("Shortcut"))
        row.addWidget(self._key, 1)
        row.addWidget(clear_key)
        lyt.addLayout(row)
        lyt.addWidget(QLabel(
            i18n.t("Empty = this slot's default (%s)") % slot_key if slot_key
            else "Empty = no key (this slot has no default)"))

        self._loop = QCheckBox("🔁  Endless repeat")
        self._loop.setChecked(pad.loop)
        self._loop.setToolTip("Play this pad over and over until it is stopped —\n"
                              "for a background bed under a ceremony.")
        lyt.addWidget(self._loop)

        self._duck = QCheckBox("🔈  Pull the music down while this pad plays")
        self._duck.setChecked(pad.duck)
        lyt.addWidget(self._duck)
        # A bed that ducks the deck music for twenty minutes is never what
        # anyone wants, so turning on the loop turns the duck off with it.
        self._loop.toggled.connect(
            lambda on: self._duck.setChecked(False) if on else None)

        # ⚙ Settings ▸ 🎛 Cartwall decides what a title does to the pad
        # (planner.playing.cartwall.background_pauses); the box says which.
        if background_pauses:
            self._background = QCheckBox("🎶  Background: pause while a title plays")
            self._background.setToolTip(
                "The other way round from 🔈: a title starting on the main\n"
                "player pauses this pad, and it carries on from where it was\n"
                "when the music stops.\n"
                "(⚙ Settings → 🎛 Cartwall → 🎶 Background pads)")
        else:
            self._background = QCheckBox(
                "🎶  Background: dip under the music while a title plays")
            self._background.setToolTip(
                "The other way round from 🔈: this pad goes silent while the\n"
                "main player plays and comes back up in the pauses.")
        self._background.setChecked(pad.background)
        lyt.addWidget(self._background)
        self._background.toggled.connect(self._on_background)
        self._on_background(pad.background)
        # Only a tick sets the bed volume: a bed opened again keeps its own.
        self._background.toggled.connect(self._on_background_ticked)

        self._stops_others = QCheckBox("S  Stop the other pads when this one starts")
        self._stops_others.setChecked(pad.stops_others)
        self._stops_others.setToolTip(
            "Every other running pad fades out as this one starts —\n"
            "for an anthem or a winners' fanfare that needs the room.")
        lyt.addWidget(self._stops_others)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lyt.addWidget(buttons)

    def _on_background(self, on: bool) -> None:
        """A pad that dips under the music cannot pull the music down as well —
        the two would hold each other at the bottom."""
        if on:
            self._duck.setChecked(False)
        self._duck.setEnabled(not on)

    def _on_background_ticked(self, on: bool) -> None:
        """🎶 Made a bed: down to the bed volume (⚙ Settings → 🎛 Cartwall)."""
        if on:
            self._vol.setValue(int(round(self._bg_volume * 100)))

    def _build_volume_row(self, lyt, pad):
        """The pad's volume slider with its value and ▶ to listen."""
        # The slider is heard while it moves — a per-pad trim is a judgement you
        # make with your ears, and 25 % means nothing until the bed is running
        # under the deck music. ▶ starts the pad so there is something to judge;
        # a pad that is already playing needs no button at all.
        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(int(round(pad.volume * 100)))
        self._vol_lbl = TypedValue(self._vol)
        self._vol_lbl.setText(f"{self._vol.value()} %")
        self._vol_lbl.setMinimumWidth(44)
        self._vol.valueChanged.connect(self._on_volume)
        self._play_btn = QToolButton()
        self._play_btn.setText("▶")
        self._play_btn.setCheckable(True)
        self._play_btn.setAutoRaise(True)
        self._play_btn.setToolTip("Listen to this pad while you set its level")
        self._play_btn.toggled.connect(self._on_preview)
        row = QHBoxLayout()
        row.addWidget(QLabel("Volume"))
        row.addWidget(self._vol, 1)
        row.addWidget(self._vol_lbl)
        row.addWidget(self._play_btn)
        lyt.addLayout(row)

    def _on_volume(self, value: int) -> None:
        self._vol_lbl.setText(f"{value} %")
        self.previewVolume.emit(value / 100.0)

    def _on_preview(self, on: bool) -> None:
        self._play_btn.setText("⏹" if on else "▶")
        self.previewFire.emit(on)

    def done(self, result: int) -> None:
        """However the dialog is left — Ok, Cancel, Esc, the ✕ — the preview must
        not keep playing behind it."""
        if self._play_btn.isChecked():
            self._play_btn.setChecked(False)
        super().done(result)

    def _show_fade(self, ms: int) -> None:
        text = f"{ms / 1000:.1f} s"
        self._fade_lbl.setText(text if self._fade_own.isChecked()
                               else i18n.t("%s (wall)") % text)

    def _on_fade_own(self, own: bool) -> None:
        """Unticked, the slider still SHOWS the wall's fade — greyed out, so the
        value this pad is actually going to use is never a mystery."""
        self._fade.setEnabled(own)
        if not own:
            self._fade.blockSignals(True)
            self._fade.setValue(self._wall_fade)
            self._fade.blockSignals(False)
        self._show_fade(self._fade.value())

    def pad(self) -> pc.CartPad:
        return pc.CartPad(
            path=self._pad.path,
            label=self._label.text().strip(),
            colour=self._colour.currentData() or "",
            volume=self._vol.value() / 100.0,
            loop=self._loop.isChecked(),
            duck=self._duck.isChecked(),
            background=self._background.isChecked(),
            stops_others=self._stops_others.isChecked(),
            shortcut=self._key.keySequence().toString(),
            fade_ms=self._fade.value() if self._fade_own.isChecked() else None)


class ClickableLabel(QLabel):
    """A QLabel that reports a double-click — Qt's does not."""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()


class TypedValue(ClickableLabel):
    """A slider's readout that a double-click turns into a field.

    A slider is the right control for a level judged by ear and the wrong one
    for a number that is already known: 25 % and 1.5 s are quicker typed than
    aimed at, and a pad that has to match another one has to hit the figure
    exactly, not nearly."""

    def __init__(self, slider: QSlider, per_unit: int = 1, parent=None):
        super().__init__("", parent)
        self._slider = slider
        # Slider steps per typed unit: 1000 for a fade typed in seconds, 1 for
        # a volume typed in per cent.
        self._per_unit = per_unit
        self._edit = None       # built on first use
        self.setToolTip("Double-click to type a value")
        self.double_clicked.connect(self._open)

    def _open(self) -> None:
        """Put the field over the readout. Made once and then reused."""
        if not self._slider.isEnabled():
            return          # a pad following the wall's fade: nothing to set
        if self._edit is None:
            self._edit = QLineEdit(self)
            self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._edit.installEventFilter(self)
            self._edit.editingFinished.connect(self._commit)
        self._edit.setGeometry(self.rect())
        # The bare number, not the caption: "1.5 s (wall)" is what the reader
        # wants and "1.5" is what the typist wants to start from.
        self._edit.setText(f"{self._slider.value() / self._per_unit:g}")
        self._edit.show()
        self._edit.selectAll()
        self._edit.setFocus()

    def eventFilter(self, obj, event):
        """Both keys have to be caught here.

        Esc, because a QLineEdit swallows it without telling anyone. Enter,
        because a QLineEdit does the opposite — it commits and then hands the
        key on, and the next thing in line is the dialog's Ok button: typing a
        value and pressing Enter would shut the whole settings window."""
        edit = self._edit
        if edit is not None and obj is edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                edit.hide()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._commit()
                return True
        return super().eventFilter(obj, event)

    def _commit(self) -> None:
        """Enter, or the focus moving on. Nonsense is refused rather than
        guessed at, so a half-typed value leaves the slider where it was."""
        edit = self._edit
        if edit is None or edit.isHidden():
            return          # editingFinished comes again on the focus-out
        # The unit may be typed along with the number, and a German keyboard
        # puts a comma where float() wants a point.
        text = edit.text().strip().rstrip("s% ").replace(",", ".")
        edit.hide()
        try:
            typed = float(text)
        except ValueError:
            return
        # setValue clamps: 999 s of fade is not a fade, it is a stuck pad.
        self._slider.setValue(int(round(typed * self._per_unit)))
