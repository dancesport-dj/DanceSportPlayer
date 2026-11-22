"""🎚 One source's equalizer as controls: the 🎚 EQ card (player) and
⚙ Settings → 🔊 Sound & player (gui) both show it, one per source.

On / Bypass, a preset (💾 / 🗑 the operator's own), the four gains as vertical sliders (a double-click
sets one back to 0 dB; each readout a double-click-to-type field), the low cut on or off, and behind "Advanced"
every band's frequency, width and on/off. The model is
planner.playing.equalizer; the panel holds a working copy (`cfg()`) and says
`changed` on every edit. What it is written into, and when it is heard, is
the caller's.

Switching the MUSIC's EQ on asks first (`confirm_on`, see
shared.audio.eq_question); a No puts the box back without a second ask.
"""
from collections.abc import Callable

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QSlider,
    QStyle,
    QStyleOptionButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from planner import i18n
from planner.playing import equalizer as eqs
from shared.widgets import TypedValue

# What each of the five bands is called, in their fixed order.
BAND_CAPTIONS = ("Low cut", "Bass", "Low mid", "Presence", "Treble")
# One tab per source, in this order; the UI calls the announcer the voice.
EQ_TABS = (("music", "🎵 Music"), ("announcer", "🔈 Voice"), ("cue", "🎧 Cue"))
_STEPS_PER_DB = 2      # the sliders move in 0.5 dB


class _GainSlider(QSlider):
    """A band's gain: a double-click sets it back to 0 dB."""

    def mouseDoubleClickEvent(self, event):
        self.setValue(0)
        event.accept()


class _BandSwitch(QCheckBox):
    """A band's on/off box with no text: only as wide as its indicator, with
    the same margin either side. A plain QCheckBox draws the box at its left
    and leaves room for text, so centred over the slider it sat a few pixels
    left of the groove (most on the player card's 12 px box)."""

    def sizeHint(self) -> QSize:
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        box = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, opt, self)
        return QSize(2 * box.left() + box.width(), super().sizeHint().height())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


def freq_text(freq: float) -> str:
    return f"{freq / 1000:g} kHz" if freq >= 1000 else f"{freq:g} Hz"


def _whole(freq: float) -> float | int:
    """80.0 as 80: one key for a list item, whether stored as int or float."""
    return int(freq) if float(freq).is_integer() else freq


def _fade(label: QWidget, off: bool) -> None:
    """Greyed and faded. The theme's disabled colour alone is no help: on a
    light look it is darker than the frequencies' own grey."""
    label.setEnabled(not off)
    if off and label.graphicsEffect() is None:
        effect = QGraphicsOpacityEffect(label)
        effect.setOpacity(0.35)
        label.setGraphicsEffect(effect)
    elif not off and label.graphicsEffect() is not None:
        label.setGraphicsEffect(None)  # pyright: ignore[reportArgumentType]  # None removes it (Qt docs)


class EqPanel(QWidget):

    changed = Signal()
    # 💾 / 🗑 an own preset: (name, four gains) or (name, None) to delete. The
    # owner stores it (eqs.with_user_preset) and calls refill_presets() on
    # every panel; the presets are shared by all sources.
    presetSaved = Signal(str, object)

    def __init__(self, source: str, cfg: dict,
                 settings: Callable[[], dict] = dict,
                 headroom: Callable[[dict], float] | None = None,
                 confirm_on: Callable[[], bool] | None = None, parent=None):
        super().__init__(parent)
        self.source = source
        self._settings = settings       # for the operator's own presets
        self._headroom = headroom
        self._confirm_on = confirm_on
        self._cfg = cfg
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.addLayout(self._build_head())
        lyt.addLayout(self._build_bands())
        self._advanced = QCheckBox(i18n.t("⚙ Advanced: frequencies and widths"))
        self._advanced.toggled.connect(self._on_advanced)
        lyt.addWidget(self._advanced)
        self._headroom_lbl = QLabel("")
        self._headroom_lbl.setStyleSheet("color:#888; font-size:11px;")
        lyt.addWidget(self._headroom_lbl)
        self.set_cfg(cfg)

    # ── Building ──

    def _build_head(self):
        row = QHBoxLayout()
        self._on = QCheckBox(i18n.t("On"))
        self._on.setToolTip(i18n.t(
            "Off: the player plays as without an EQ. On and off are heard at\n"
            "once, after a short gap; Bypass compares without one."))
        self._on.toggled.connect(self._on_switched)
        row.addWidget(self._on)
        self._bypass = QCheckBox(i18n.t("Bypass"))
        self._bypass.setToolTip(i18n.t("Hear it without the EQ for a moment, at once."))
        self._bypass.toggled.connect(self._on_bypass)
        row.addWidget(self._bypass)
        row.addStretch(1)
        self._preset = QComboBox()
        self._preset.setToolTip(i18n.t("A starting point for a room; the sliders fine-tune it."))
        self._preset.activated.connect(self._on_preset)
        row.addWidget(self._preset)
        self._save_btn = QToolButton()
        self._save_btn.setText("💾")
        self._save_btn.setToolTip(i18n.t(
            "Keep these four gains as a preset of your own, for every tab."))
        self._save_btn.clicked.connect(self._on_save_preset)
        row.addWidget(self._save_btn)
        self._delete_btn = QToolButton()
        self._delete_btn.setText("🗑")
        self._delete_btn.setToolTip(i18n.t("Delete this preset of your own."))
        self._delete_btn.clicked.connect(self._on_delete_preset)
        row.addWidget(self._delete_btn)
        return row

    def _build_bands(self):
        grid = QGridLayout()
        self._sliders: list[QSlider | None] = []
        self._readouts: list[TypedValue | None] = []
        self._freq_lbls, self._freq_spins, self._q_spins, self._band_on = [], [], [], []
        self._heads: list[QLabel] = []
        for col, caption in enumerate(BAND_CAPTIONS):
            head = QLabel(i18n.t(caption))
            head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(head, 0, col)
            self._heads.append(head)
            freq = QLabel("")
            freq.setAlignment(Qt.AlignmentFlag.AlignCenter)
            freq.setStyleSheet("color:#888; font-size:11px;")
            grid.addWidget(freq, 1, col)
            self._freq_lbls.append(freq)
            on = _BandSwitch()
            on.setToolTip(i18n.t("This band on or off"))
            on.toggled.connect(lambda checked, i=col: self._on_band_on(i, checked))
            grid.addWidget(on, 2, col, Qt.AlignmentFlag.AlignHCenter)
            self._band_on.append(on)
            if col == 0:
                # The low cut has no gain: it is off or on at a cut-off, picked
                # here without "Advanced" (there: the switch and the field).
                self._low_cut = QComboBox()
                self._low_cut.setToolTip(i18n.t(
                    "Takes away everything below this frequency: rumble, stage\n"
                    "thumps, hum. Off lets the deepest bass through."))
                self._low_cut.currentIndexChanged.connect(self._on_low_cut)
                grid.addWidget(self._low_cut, 1, col, 2, 1, Qt.AlignmentFlag.AlignTop)
                self._sliders.append(None)
                self._readouts.append(None)
            else:
                slider = _GainSlider(Qt.Orientation.Vertical)
                slider.setToolTip(i18n.t("Double-click: back to 0 dB"))
                slider.setRange(-int(eqs.MAX_GAIN_DB * _STEPS_PER_DB),
                                int(eqs.MAX_GAIN_DB * _STEPS_PER_DB))
                slider.setMinimumHeight(110)
                slider.valueChanged.connect(lambda v, i=col: self._on_gain(i, v))
                grid.addWidget(slider, 3, col, Qt.AlignmentFlag.AlignHCenter)
                readout = TypedValue(slider, _STEPS_PER_DB)
                readout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                readout.setMinimumWidth(56)
                grid.addWidget(readout, 4, col)
                self._sliders.append(slider)
                self._readouts.append(readout)
            fspin = QDoubleSpinBox()
            fspin.setRange(20.0, 20000.0)
            fspin.setDecimals(0)
            fspin.setSuffix(" Hz")
            fspin.valueChanged.connect(lambda v, i=col: self._on_freq(i, v))
            grid.addWidget(fspin, 5, col)
            self._freq_spins.append(fspin)
            qspin = QDoubleSpinBox()
            qspin.setRange(0.3, 6.0)
            qspin.setSingleStep(0.1)
            qspin.setDecimals(2)
            qspin.setPrefix("Q ")
            qspin.valueChanged.connect(lambda v, i=col: self._on_q(i, v))
            grid.addWidget(qspin, 6, col)
            self._q_spins.append(qspin)
        return grid

    # ── The working copy ──

    def cfg(self) -> dict:
        return {**self._cfg, "bands": [dict(b) for b in self._cfg["bands"]]}

    def set_cfg(self, cfg: dict) -> None:
        """Show `cfg` (eq_of's shape), without saying `changed`."""
        self._cfg = {**cfg, "bands": [dict(b) for b in cfg["bands"]]}
        for w in self._all_inputs():
            w.blockSignals(True)
        self._on.setChecked(self._cfg["on"])
        self._bypass.setChecked(self._cfg["bypass"])
        self._advanced.setChecked(self._cfg["advanced"])
        self._fill_presets()
        self._fill_low_cut()
        for i, band in enumerate(self._cfg["bands"]):
            self._band_on[i].setChecked(band["on"])
            self._freq_spins[i].setValue(band["freq"])
            self._q_spins[i].setValue(band["q"])
            slider = self._sliders[i]
            if slider is not None:
                slider.setValue(round(band["gain"] * _STEPS_PER_DB))
        for w in self._all_inputs():
            w.blockSignals(False)
        self._refresh()

    def _all_inputs(self):
        return [self._on, self._bypass, self._advanced, self._preset, self._low_cut,
                *self._band_on,
                *self._freq_spins, *self._q_spins, *(s for s in self._sliders if s)]

    def _fill_presets(self):
        self._preset.clear()
        for key in eqs.PRESETS:
            self._preset.addItem(i18n.t(eqs.PRESET_CAPTIONS[key]), key)
        for name in eqs.user_presets(self._settings() or {}):
            self._preset.addItem(name, name)
        found = self._preset.findData(self._cfg["preset"]) if self._cfg["preset"] else -1
        if found < 0:
            self._preset.addItem(i18n.t("Custom"), "")
            found = self._preset.count() - 1
        self._preset.setCurrentIndex(found)
        self._delete_btn.setEnabled(self._own_preset() is not None)

    def _fill_low_cut(self):
        """Off and LOW_CUT_CHOICES, plus a cut-off typed under "Advanced"."""
        cut = self._cfg["bands"][0]
        freq = _whole(cut["freq"])
        choices = list(eqs.LOW_CUT_CHOICES)
        if freq not in choices:
            choices = sorted([*choices, freq])
        self._low_cut.clear()
        self._low_cut.addItem(i18n.t("Off"), 0)
        for choice in choices:
            self._low_cut.addItem(freq_text(choice), choice)
        self._low_cut.setCurrentIndex(self._low_cut.findData(freq) if cut["on"] else 0)

    def refill_presets(self) -> None:
        """The preset list again, after an own preset was saved or deleted
        (on any tab: they are shared)."""
        self._preset.blockSignals(True)
        self._fill_presets()
        self._preset.blockSignals(False)

    def _own_preset(self) -> str | None:
        name = self._cfg["preset"]
        return name if name and name in eqs.user_presets(self._settings() or {}) else None

    def _refresh(self):
        """What follows from the copy: readouts, what can be touched, headroom."""
        advanced = self._cfg["advanced"]
        self._bypass.setEnabled(self._cfg["on"])
        for i, band in enumerate(self._cfg["bands"]):
            self._freq_lbls[i].setText(freq_text(band["freq"]))
            # The low cut's list says its cut-off; "Advanced" has switch and field.
            self._freq_lbls[i].setVisible(not advanced and i > 0)
            self._band_on[i].setVisible(advanced)
            self._freq_spins[i].setVisible(advanced)
            # A shelf's slope is fixed; the low cut and the peaks have a width.
            self._q_spins[i].setVisible(advanced and band["kind"] in ("lowcut", "peak"))
            # A band switched off fades its whole column, not just the slider.
            slider, readout = self._sliders[i], self._readouts[i]
            for label in (self._heads[i], self._freq_lbls[i], readout):
                if label is not None:
                    _fade(label, not band["on"])
            if slider is not None:
                slider.setEnabled(band["on"])
                if readout is not None:
                    readout.setText(f"{band['gain']:+.1f} dB")
        self._low_cut.setVisible(not advanced)
        if self._headroom is not None:
            db = self._headroom(self._cfg)
            self._headroom_lbl.setText(
                i18n.t("Turned down %.1f dB so no boost can clip.") % db if db >= 0.05 else "")

    def _edited(self):
        self._refresh()
        self.changed.emit()

    # ── Edits ──

    def _on_switched(self, on: bool):
        if on and self._confirm_on is not None and not self._confirm_on():
            self._on.blockSignals(True)
            self._on.setChecked(False)
            self._on.blockSignals(False)
            return
        self._cfg["on"] = on
        self._edited()

    def _on_bypass(self, on: bool):
        self._cfg["bypass"] = on
        self._edited()

    def _on_advanced(self, on: bool):
        self._cfg["advanced"] = on
        if not on:
            # What the model does without it: back to the default frequencies,
            # widths and switches, so the panel shows what is heard.
            self.set_cfg(eqs.eq_of({"equalizer": {self.source: self._cfg}}, self.source))
        self._edited()

    def _on_preset(self, index: int):
        key = self._preset.itemData(index)
        if not key:
            return
        self.set_cfg(eqs.apply_preset(self._cfg, key, self._settings() or {}))
        self.changed.emit()

    def _on_gain(self, i: int, value: int):
        self._cfg["bands"][i]["gain"] = value / _STEPS_PER_DB
        if self._cfg["preset"]:
            # The gains are the operator's own now: the combo says so.
            self._cfg["preset"] = ""
            self.refill_presets()
        self._edited()

    def _on_save_preset(self):
        """💾 The four gains under a name: refused for a built-in preset's
        name, asked before an own one is replaced."""
        # The window, not the panel: in the 🎚 card a child takes its dark style.
        name, ok = QInputDialog.getText(
            self.window(), i18n.t("Save preset"), i18n.t("Name of the preset:"),
            text=self._own_preset() or "")
        name = name.strip()
        if not ok or not name:
            return
        built_in = {k.casefold() for k in eqs.PRESETS}
        for caption in eqs.PRESET_CAPTIONS.values():
            built_in |= {caption.casefold(), i18n.t(caption).casefold()}
        if name.casefold() in built_in:
            QMessageBox.warning(self.window(), i18n.t("Save preset"), i18n.t(
                "A built-in preset has that name. Please choose another one."))
            return
        if name in eqs.user_presets(self._settings() or {}) and QMessageBox.question(
                self.window(), i18n.t("Save preset"),
                i18n.t("Replace your preset \"%s\"?") % name) != QMessageBox.StandardButton.Yes:
            return
        self.presetSaved.emit(name, tuple(b["gain"] for b in self._cfg["bands"][1:]))
        self._cfg["preset"] = name
        self.refill_presets()
        self.changed.emit()

    def _on_delete_preset(self):
        name = self._own_preset()
        if name is None or QMessageBox.question(
                self.window(), i18n.t("Delete preset"),
                i18n.t("Delete your preset \"%s\"?") % name) != QMessageBox.StandardButton.Yes:
            return
        self.presetSaved.emit(name, None)
        self._cfg["preset"] = ""
        self.refill_presets()
        self.changed.emit()

    def _on_low_cut(self, index: int):
        freq = self._low_cut.itemData(index)
        if freq is None:
            return
        cut = self._cfg["bands"][0]
        cut["on"] = bool(freq)
        if freq:
            cut["freq"] = freq
        self._edited()

    def _on_band_on(self, i: int, on: bool):
        self._cfg["bands"][i]["on"] = on
        self._edited()

    def _on_freq(self, i: int, value: float):
        self._cfg["bands"][i]["freq"] = value
        self._edited()

    def _on_q(self, i: int, value: float):
        self._cfg["bands"][i]["q"] = value
        self._edited()
