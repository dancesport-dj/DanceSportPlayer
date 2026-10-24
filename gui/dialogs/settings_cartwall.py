"""🎛 The Settings dialog's Cartwall tab: how a pad ducks the music, what a
starting title does to a 🎶 background pad, and the wall's own fade-out and
colour.

The first two are settings like any other. The fade-out and the colour
belong to the wall and are kept in cartwall.json, so a wall carried to
another machine brings them along: the window hands them in under
CART_WALL_KEYS and takes them back out of values() before it saves.
"""
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from planner.playing import cartwall as pc
from shared.audio.playback import duck_db_text
from shared.widgets import _hsep
from gui.dialogs.settings_look import _DialogHost

# The wall's own two, which ride through the dialog but not into the settings.
CART_WALL_KEYS = ("cart_fade_ms", "cart_wall_colour")


def _swatch(colour: str) -> QIcon:
    """A filled square for the colour combo, with a grey edge so white shows."""
    pix = QPixmap(14, 14)
    pix.fill(QColor("#b9c0cc"))
    painter = QPainter(pix)
    painter.fillRect(1, 1, 12, 12, QColor(colour))
    painter.end()
    return QIcon(pix)


class CartwallTabMixin(_DialogHost):
    """The 🎛 Cartwall tab of SettingsDialog."""

    def _setup_cartwall_tab(self, settings, tabs):
        cart_tab = QWidget()
        clyt = QVBoxLayout(cart_tab)
        clyt.setSpacing(10)
        self._cart_intro = QLabel(
            "<b>🎛 Cartwall</b> — what the pads do to the music, and what "
            "every pad follows unless it was given its own.")
        self._cart_intro.setWordWrap(True)
        clyt.addWidget(self._cart_intro)

        # ── 🎛 How far a cartwall pad pulls the music down ──
        # 10 and 90 are player.audio.mix's CART_DUCK_PCT and its cap.
        cart_duck_row = QHBoxLayout()
        cart_duck_row.addWidget(QLabel("🎛  A pad ducks the music to:"))
        self._cart_duck_spin = QSpinBox()
        self._cart_duck_spin.setRange(0, 90)
        self._cart_duck_spin.setSingleStep(5)
        self._cart_duck_spin.setSuffix(" %")
        self._cart_duck_spin.setToolTip(
            "How loud the music stays while a 🎛 cartwall pad set to 🔈 pull\n"
            "the music down plays, in percent of its volume like 🔉 Duck to.\n"
            "10 % is about −20 dB: a fanfare cuts through. 30 % (about −10 dB)\n"
            "only sits the music back. 0 % is silence.")
        try:
            cart_duck_pct = int(settings.get("cart_duck_pct", 10))
        except (TypeError, ValueError):
            cart_duck_pct = 10
        self._cart_duck_db = QLabel()
        self._cart_duck_spin.valueChanged.connect(
            lambda pct: self._cart_duck_db.setText(duck_db_text(pct)))
        self._cart_duck_spin.setValue(cart_duck_pct)
        self._cart_duck_db.setText(duck_db_text(self._cart_duck_spin.value()))
        cart_duck_row.addWidget(self._cart_duck_spin)
        cart_duck_row.addWidget(self._cart_duck_db)
        cart_duck_row.addStretch(1)
        clyt.addLayout(cart_duck_row)

        # ── 🎶 What a starting title does to a cartwall background pad ──
        # The keys are planner.playing.cartwall.BG_MODES.
        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("🎶  Background pads when a title starts:"))
        self._cart_bg_combo = QComboBox()
        self._cart_bg_combo.setToolTip(
            "What a 🎛 cartwall pad set to 🎶 Background does once the music\n"
            "starts.\n\n"
            "Mute and keep playing: it runs on silently under the title and\n"
            "fades back in when the music stops.\n"
            "Pause: it holds where it was and carries on from there when\n"
            "the music stops.")
        for label, key in (("Mute and keep playing", "mute"), ("Pause", "pause")):
            self._cart_bg_combo.addItem(label, key)
        self._cart_bg_combo.setCurrentIndex(
            1 if pc.background_pauses(settings) else 0)
        bg_row.addWidget(self._cart_bg_combo)
        bg_row.addStretch(1)
        clyt.addLayout(bg_row)
        clyt.addWidget(_hsep())
        self._add_wall_rows(settings, clyt)

        clyt.addStretch()
        return tabs.addTab(cart_tab, "🎛 Cartwall")

    def _add_wall_rows(self, settings, clyt):
        """⏱ The fade-out and 🖌 the colour every pad follows by default —
        once in the pad's right-click menu."""
        fade_row = QHBoxLayout()
        self._cart_fade_lbl = QLabel("⏱  Pads fade out over:")
        fade_row.addWidget(self._cart_fade_lbl)
        self._cart_fade_spin = QDoubleSpinBox()
        self._cart_fade_spin.setRange(0.0, pc.MAX_FADE_MS / 1000)
        self._cart_fade_spin.setDecimals(1)
        self._cart_fade_spin.setSingleStep(0.1)
        self._cart_fade_spin.setSuffix(" s")
        self._cart_fade_spin.setSpecialValueText("cut")
        self._cart_fade_spin.setToolTip(
            "How long a pad takes to let go when it is tapped again or ⏹\n"
            "stops the wall. A pad can override this in its own settings.")
        try:
            fade_ms = int(settings.get("cart_fade_ms", pc.DEFAULT_FADE_MS))
        except (TypeError, ValueError):
            fade_ms = pc.DEFAULT_FADE_MS
        self._cart_fade_spin.setValue(max(0, min(pc.MAX_FADE_MS, fade_ms)) / 1000)
        fade_row.addWidget(self._cart_fade_spin)
        fade_row.addStretch(1)
        clyt.addLayout(fade_row)

        colour_row = QHBoxLayout()
        self._cart_colour_lbl = QLabel("🖌  Default wall colour:")
        colour_row.addWidget(self._cart_colour_lbl)
        self._cart_colour_combo = QComboBox()
        self._cart_colour_combo.setToolTip(
            "The wall's default colour: every pad without a colour of its own\n"
            "(🎨 Colour ▸ Wall default) shows it. A pad given its own keeps it.")
        # White is not a pad colour — it is what "Wall default" already means —
        # but it has to be here, or a wall painted green can never go back.
        for name, value in {"White": pc.DEFAULT_PAD_COLOUR,
                            **{n: v for n, v in pc.PAD_COLOURS.items() if v}}.items():
            self._cart_colour_combo.addItem(_swatch(value), name, value)
        colour = str(settings.get("cart_wall_colour") or pc.DEFAULT_PAD_COLOUR)
        self._cart_colour_combo.setCurrentIndex(
            max(0, self._cart_colour_combo.findData(colour)))
        colour_row.addWidget(self._cart_colour_combo)
        colour_row.addStretch(1)
        clyt.addLayout(colour_row)

    def _cartwall_values(self) -> dict:
        """The tab's settings, for values() — CART_WALL_KEYS among them."""
        return {
            "cart_duck_pct": self._cart_duck_spin.value(),
            "cart_bg_mode": self._cart_bg_combo.currentData(),
            "cart_fade_ms": int(round(self._cart_fade_spin.value() * 1000)),
            "cart_wall_colour": self._cart_colour_combo.currentData(),
        }
