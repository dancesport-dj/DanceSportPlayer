"""🎛 The Settings dialog's Cartwall tab: how a pad ducks the music, what a
starting title does to a 🎶 background pad and how fast it dips and comes
back, and the wall's own fade-out and colour.

All but those last two are settings like any other. The fade-out and the colour
belong to the wall and are kept in cartwall.json, so a wall carried to
another machine brings them along: the window hands them in under
CART_WALL_KEYS and takes them back out of values() before it saves.
"""
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from planner.playing import cartwall as pc
from shared.audio.playback import duck_db_text
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

        # Two boxes, so it is clear which rows touch every pad and which
        # only the 🎶 Background ones — the latter in the order they happen.
        all_box = QGroupBox("🎛  All pads")
        alyt = QVBoxLayout(all_box)

        # ── 🔈 How far a cartwall pad pulls the music down ──
        # 10 and 90 are player.audio.mix's CART_DUCK_PCT and its cap.
        cart_duck_row = QHBoxLayout()
        cart_duck_row.addWidget(QLabel("🔈  While a 🔈 pad plays, the music ducks to:"))
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
        alyt.addLayout(cart_duck_row)
        self._add_wall_rows(settings, alyt)
        clyt.addWidget(all_box)

        bg_box = QGroupBox("🎶  Pads set to 🎶 Background")
        blyt = QVBoxLayout(bg_box)
        self._cart_bg_hint = QLabel(
            "Tapped again or ⏹, a background pad fades out like every other "
            "pad (⏱ above).")
        self._cart_bg_hint.setWordWrap(True)
        self._cart_bg_hint.setStyleSheet("color:#777; font-size:11px;")
        blyt.addWidget(self._cart_bg_hint)

        # ── ▶ How fast a background pad comes up when it is fired ──
        bg_fire_row = QHBoxLayout()
        self._cart_bg_fire_lbl = QLabel("▶  When fired — fade in over:")
        bg_fire_row.addWidget(self._cart_bg_fire_lbl)
        self._cart_bg_fire_spin = QDoubleSpinBox()
        self._cart_bg_fire_spin.setRange(0.0, pc.MAX_FADE_MS / 1000)
        self._cart_bg_fire_spin.setDecimals(1)
        self._cart_bg_fire_spin.setSingleStep(0.1)
        self._cart_bg_fire_spin.setSuffix(" s")
        self._cart_bg_fire_spin.setToolTip(
            "How long a 🎛 cartwall pad set to 🎶 Background takes to come\n"
            "up from silence when it is fired. 0 s starts it at full volume.")
        self._cart_bg_fire_spin.setValue(pc.background_fire_fade_ms(settings) / 1000)
        bg_fire_row.addWidget(self._cart_bg_fire_spin)
        bg_fire_row.addStretch(1)
        blyt.addLayout(bg_fire_row)

        # ── 🎶 What a starting title does to a cartwall background pad ──
        # The keys are planner.playing.cartwall.BG_MODES.
        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("🎵  When a title starts:"))
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
        blyt.addLayout(bg_row)

        # ── 🌙 How fast a background pad dips when a title starts ──
        bg_out_row = QHBoxLayout()
        self._cart_bg_out_lbl = QLabel("🌙  …fading out over:")
        bg_out_row.addWidget(self._cart_bg_out_lbl)
        self._cart_bg_out_spin = QDoubleSpinBox()
        self._cart_bg_out_spin.setRange(0.0, pc.MAX_FADE_MS / 1000)
        self._cart_bg_out_spin.setDecimals(1)
        self._cart_bg_out_spin.setSingleStep(0.1)
        self._cart_bg_out_spin.setSuffix(" s")
        self._cart_bg_out_spin.setToolTip(
            "How long a 🎛 cartwall pad set to 🎶 Background takes to go\n"
            "silent once a title starts.")
        self._cart_bg_out_spin.setValue(pc.background_fade_out_ms(settings) / 1000)
        bg_out_row.addWidget(self._cart_bg_out_spin)
        bg_out_row.addStretch(1)
        blyt.addLayout(bg_out_row)

        # ── ⏳ How long the music has to stay stopped before it comes back ──
        bg_hold_row = QHBoxLayout()
        self._cart_bg_hold_lbl = QLabel("⏳  When the music stops — wait:")
        bg_hold_row.addWidget(self._cart_bg_hold_lbl)
        self._cart_bg_hold_spin = QDoubleSpinBox()
        self._cart_bg_hold_spin.setRange(0.0, pc.MAX_FADE_MS / 1000)
        self._cart_bg_hold_spin.setDecimals(1)
        self._cart_bg_hold_spin.setSingleStep(0.1)
        self._cart_bg_hold_spin.setSuffix(" s")
        self._cart_bg_hold_spin.setToolTip(
            "How long the main player has to stay stopped before a 🎛 cartwall\n"
            "pad set to 🎶 Background fades back in.\n"
            "\n"
            "Between two titles the deck stops for a moment. Without a wait,\n"
            "the bed would swell up in every such gap and dip again as soon as\n"
            "the next title starts. A title starting during the wait keeps the\n"
            "bed down.\n"
            "\n"
            "There is no wait when a title starts: the bed gets out of the way\n"
            "at once, so it never plays over the first notes.\n"
            "\n"
            "0 s brings it back the moment the music stops, gaps included.\n"
            "Standard 0.3 s; much longer feels as if the bed lags behind.")
        self._cart_bg_hold_spin.setValue(pc.background_hold_ms(settings) / 1000)
        bg_hold_row.addWidget(self._cart_bg_hold_spin)
        bg_hold_row.addStretch(1)
        blyt.addLayout(bg_hold_row)

        # ── 🌅 How fast a background pad comes back once the music stops ──
        bg_fade_row = QHBoxLayout()
        self._cart_bg_fade_lbl = QLabel("🌅  …then fade back in over:")
        bg_fade_row.addWidget(self._cart_bg_fade_lbl)
        self._cart_bg_fade_spin = QDoubleSpinBox()
        self._cart_bg_fade_spin.setRange(0.0, pc.MAX_FADE_MS / 1000)
        self._cart_bg_fade_spin.setDecimals(1)
        self._cart_bg_fade_spin.setSingleStep(0.1)
        self._cart_bg_fade_spin.setSuffix(" s")
        self._cart_bg_fade_spin.setToolTip(
            "How long a 🎛 cartwall pad set to 🎶 Background takes to come\n"
            "back up to its full volume once the music stops.")
        self._cart_bg_fade_spin.setValue(pc.background_fade_in_ms(settings) / 1000)
        bg_fade_row.addWidget(self._cart_bg_fade_spin)
        bg_fade_row.addStretch(1)
        blyt.addLayout(bg_fade_row)
        clyt.addWidget(bg_box)

        clyt.addStretch()
        return tabs.addTab(cart_tab, "🎛 Cartwall")

    def _add_wall_rows(self, settings, clyt):
        """⏱ The fade-out and 🖌 the colour every pad follows by default —
        once in the pad's right-click menu."""
        fade_row = QHBoxLayout()
        self._cart_fade_lbl = QLabel("⏱  Tapped again or ⏹ — fade out over:")
        fade_row.addWidget(self._cart_fade_lbl)
        self._cart_fade_spin = QDoubleSpinBox()
        self._cart_fade_spin.setRange(0.0, pc.MAX_FADE_MS / 1000)
        self._cart_fade_spin.setDecimals(1)
        self._cart_fade_spin.setSingleStep(0.1)
        self._cart_fade_spin.setSuffix(" s")
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
            "cart_bg_fire_fade_ms": int(round(self._cart_bg_fire_spin.value() * 1000)),
            "cart_bg_fade_out_ms": int(round(self._cart_bg_out_spin.value() * 1000)),
            "cart_bg_hold_ms": int(round(self._cart_bg_hold_spin.value() * 1000)),
            "cart_bg_fade_in_ms": int(round(self._cart_bg_fade_spin.value() * 1000)),
            "cart_fade_ms": int(round(self._cart_fade_spin.value() * 1000)),
            "cart_wall_colour": self._cart_colour_combo.currentData(),
        }
