"""Building the big player card: its skin, head, time, seek bar, transport,
volume and tempo controls.

Mixin of BigPlayerWidget, split off player/widgets/player.py, which keeps the
card's layout and everything MainWindow feeds it while it plays.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout

from planner import i18n
from planner.terms import rules_name
from player.dialogs.cart_pad_dialog import TypedValue
from player.widgets.player_parts import (
    ART_PX,
    CARD_CUE,
    CARD_DIM,
    CARD_EXTEND,
    CARD_FADE,
    CARD_GAIN,
    CARD_INK,
    CARD_PANIC,
    CARD_PAUSE,
    COUNTDOWN_CSS,
    TEMPO_STEP,
    VOL_STEP,
    ClickSlider,
    TempoSlider,
    block,
)
from player.widgets.waveform import WaveformLoader, WaveformStrip
from shared.appearance.icons import button as icon_button
from shared.appearance.icons import pixmap as icon_pixmap

if TYPE_CHECKING:
    from gui.window.hosts import BigPlayerHost
else:
    BigPlayerHost = object


# 🎚 The fader knob from the canvas boards: a dark cap crossed by a light line.
_CAP_H = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b4252,"
          " stop:0.42 #3b4252, stop:0.43 #e8eef8, stop:0.57 #e8eef8,"
          " stop:0.58 #3b4252, stop:1 #3b4252)")


class BigPlayerSetupMixin(BigPlayerHost):
    """Builds BigPlayerWidget's parts once, when the card is made."""

    def _build_skin(self):
        """The card's skins (normal / end-of-track / fade) and the flash beat."""
        self.setObjectName("BigPlayer")
        _common_qss = (
            "QLabel { background:transparent; }"
            "QToolButton { color:#cfe0f5; background:#2a3346; border:none;"
            " font-size:14px; padding:3px 5px; border-radius:5px; }"
            "QToolButton:hover { background:#3a4a68; }"
            "QToolButton:pressed { background:#1565c0; }"
            "QSlider::groove:horizontal { height:6px; border-radius:3px;"
            " background:#2a3346; }"
            "QSlider::sub-page:horizontal { background:#4a82d2; border-radius:3px; }"
            # 🎚 DJ-cap knobs (dark cap, light line) on volume, pitch and seek.
            "QSlider::handle:horizontal { width:14px; margin:-6px 0;"
            f" border-radius:3px; border:1px solid #0d1017; background:{_CAP_H}; }}"
            "QSlider#seek { min-height:20px; }")
        # Normal vs end-of-track warning skins (the card flashes red while a
        # song is in its last seconds — see _flash_step / _update_time).
        # Both skins use the SAME 2px border width so toggling them never
        # reflows the card's content (only the colour changes when flashing).
        # A deliberate fade (🔉↓ / 🛑) blinks the same beat in ORANGE: the song
        # is on its way out because the operator said so, which reads
        # differently from a song running into its own end.
        # One sheet for all three, picked by the `flash` property: the beat
        # flips the property instead of setting a new sheet, which re-polished
        # every child of the card twice a second.
        self.setProperty("flash", "")
        card_qss = (
            "#BigPlayer { background:#1d2330; border:2px solid #10141d;"
            " border-radius:8px; }"
            '#BigPlayer[flash="end"] { background:#3a1d22; border-color:#e53935; }'
            '#BigPlayer[flash="fade"] { background:#3a2a17; border-color:#fb8c00; }'
            + _common_qss)
        # The seek bar joins the warning but does NOT blink with the card: it
        # stays steadily red for the whole final stretch, so the played portion
        # keeps reading as a progress bar. Set on the slider itself (its own
        # sheet outranks the card's), which also keeps _flash_step from
        # toggling it and leaves the volume slider blue.
        self._seek_end_qss = (
            "QSlider::sub-page:horizontal { background:#e53935;"
            " border-radius:3px; }"
            "QSlider::handle:horizontal { width:12px; margin:-4px 0;"
            " border-radius:6px; background:#ff8a80; }")
        self.setStyleSheet(card_qss)
        # End-of-track flash: blinks the card red over the last seconds.
        self._END_FLASH_MS = 10_000   # warn over the final 10 s of playback
        self._flash_on = False
        self._fading = False          # a fade-out is ramping the song down
        self._flash = QTimer(self)
        self._flash.setInterval(450)
        self._flash.timeout.connect(self._flash_step)

    def _build_head(self):
        """Cover, title, subtitle row and the what-comes-next line."""
        # 🖼 Cover next to the title block — off unless the operator asks for it
        # (see set_artwork_enabled); the text column keeps the rest of the width.
        head_row = QHBoxLayout()
        head_row.setSpacing(8)
        self._art_on = False
        self._art_track: Path | None = None
        self._art_list: Path | None = None
        self._art = QLabel()
        self._art.setFixedSize(ART_PX, ART_PX)
        self._art.setVisible(False)
        head_row.addWidget(self._art, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        head_row.addLayout(text_col, 1)
        self._head_box = block(head_row)

        self._title = QLabel("")
        # Track metadata is foreign input — never let Qt read markup in it (see
        # the preview overlay's title above).
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setStyleSheet("font-size:13px; font-weight:bold; color:#eef3fb;")
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text_col.addWidget(self._title)

        sub_row = QHBoxLayout()
        self._sub_row = sub_row      # set_wait pulls the seconds up to the words
        # Tight: every pixel between the bpm and the dB is one the bpm needs
        # before it has to walk.
        sub_row.setSpacing(5)
        self._sub = QLabel("")
        self._sub.setTextFormat(Qt.TextFormat.PlainText)
        self._sub.setStyleSheet("font-size:11px; color:#8fa3c4;")
        # Ignored width: a plain QLabel won't shrink below its text width, so a
        # long subtitle (dance · takt · 🥁 bpm) used to spill under the fade-out
        # / aux buttons. Let it yield space and elide instead (see _elide_sub).
        self._sub.setSizePolicy(QSizePolicy.Policy.Ignored,
                                QSizePolicy.Policy.Preferred)
        self._full_sub = ""
        # 🐂 A wait before the music stands in the subtitle row; the title's
        # stats are kept here meanwhile (see set_wait).
        self._waiting = False
        self._stats_sub = ""
        # State glyph in front of the subtitle (the auto-advance pause). It has
        # to be its own label: _elide_sub pushes the subtitle through plain-text
        # elision, which would chew up an inline <img>.
        self._sub_icon = QLabel()
        self._sub_icon.setVisible(False)
        sub_row.addWidget(self._sub_icon)
        sub_row.addWidget(self._sub, stretch=1)
        # Pause-only countdown mirror (⏸ N s) — shown on the card ONLY while the
        # between-songs pause runs. During normal play the panel already shows
        # the sand clock and the card shows the adjusted time, so mirroring it
        # here too would just double the ⏳.
        self._countdown_lbl = QLabel("")
        self._countdown_lbl.setStyleSheet(COUNTDOWN_CSS)
        # Hidden while empty: an empty label still takes its font's width and
        # a spacing on both sides, right between the bpm and the dB.
        self._countdown_lbl.setVisible(False)
        sub_row.addWidget(self._countdown_lbl)
        # R128 equalization feedback: how far this track's volume was pulled —
        # back at the right end of the subtitle row.
        self._gain_icon = QLabel()
        self._gain_icon.setPixmap(icon_pixmap("volume", 11, CARD_GAIN))
        self._gain_icon.setVisible(False)
        sub_row.addWidget(self._gain_icon)
        self._gain_lbl = QLabel("")
        self._gain_lbl.setStyleSheet(f"font-size:11px; color:{CARD_GAIN};")
        self._gain_lbl.setToolTip(
            "Volume adjustment of this track by Equalize volume (R128)")
        sub_row.addWidget(self._gain_lbl)
        text_col.addLayout(sub_row)

        # What comes after this title — the operator's cue to get ready, and the
        # early warning that this is the round's last song. Elided like the
        # subtitle so a long title can't widen the card.
        self._next_lbl = QLabel("")
        self._next_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self._next_lbl.setStyleSheet("font-size:11px; color:#6e87ad;")
        self._next_lbl.setSizePolicy(QSizePolicy.Policy.Ignored,
                                     QSizePolicy.Policy.Preferred)
        self._full_next = ""
        text_col.addWidget(self._next_lbl)

    def _build_aux_buttons(self):
        """Fade-out / jump-to-pause / extend-pause; placed by _build_aux_row."""
        # Context aux buttons — fade-out / jump-to-pause / extend-pause. Created
        # here but placed in their OWN row BELOW the transport buttons (see
        # _build_aux_row); shown only while a song plays / a pause runs.
        self._fade_btn = QToolButton()
        icon_button(self._fade_btn, "fade_out", 16, CARD_FADE)
        self._fade_btn.setFixedHeight(28)
        self._fade_btn.setMinimumWidth(52)
        self._fade_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._fade_btn.setToolTip(
            "Fade this song out now (over the configured fade time), then end "
            "it\n— for a quick, clean finish on the floor.")
        self._fade_btn.clicked.connect(self.fadeOutRequested.emit)
        self._fade_btn.setVisible(False)
        self._topause_btn = QToolButton()
        icon_button(self._topause_btn, "break_music", 16, CARD_PAUSE)
        self._topause_btn.setFixedHeight(28)
        self._topause_btn.setMinimumWidth(52)
        self._topause_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._topause_btn.setToolTip(
            "Go to the pause music — fade this song out (over the configured\n"
            "fade time), then start the between-songs pause (e.g. the dancers\n"
            "are already leaving).")
        self._topause_btn.clicked.connect(self.toPauseRequested.emit)
        self._topause_btn.setVisible(False)
        self._extend_btn = QToolButton()
        icon_button(self._extend_btn, "extend", 16, CARD_EXTEND)
        self._extend_btn.setFixedHeight(28)
        self._extend_btn.setMinimumWidth(52)
        self._extend_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._extend_btn.setToolTip(
            "Extend the auto-advance pause (add another pause length) —\n"
            "use it when the heat change is taking longer than planned.")
        self._extend_btn.clicked.connect(self.extendPauseRequested.emit)
        self._extend_btn.setVisible(False)
        # The pause's own way out, in words: ⏭ does the same, but the hall
        # waiting on the next dance should not hinge on knowing that.
        self._skip_pause_btn = QToolButton()
        icon_button(self._skip_pause_btn, "next", 16, CARD_EXTEND)
        self._skip_pause_btn.setText("Next dance")
        self._skip_pause_btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._skip_pause_btn.setFixedHeight(28)
        self._skip_pause_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._skip_pause_btn.setToolTip(
            "Cut the pause short and go to the next dance. Its announcement\n"
            "still plays first; the pause music fades out, like ⏭.")
        self._skip_pause_btn.clicked.connect(self.nextRequested.emit)
        self._skip_pause_btn.setVisible(False)
        # Card state for the context-dependent aux buttons (play vs. pause).
        self._is_paused = False
        self._has_song = False
        self._pause_avail = True         # ☕ shows only with a pause to jump to

    def _build_time(self):
        """Elapsed time, remaining time and the adjusted-length readout."""
        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        self._elapsed = QLabel("00:00")
        self._elapsed.setStyleSheet(
            "font-size:32px; font-weight:bold; color:#7fd4a0;"
            "font-family:Consolas,monospace;")
        time_row.addWidget(self._elapsed)
        time_row.addStretch(1)
        right_col = QVBoxLayout()
        right_col.setSpacing(0)
        self._remaining = QLabel("-00:00")
        self._remaining.setStyleSheet(
            "font-size:20px; color:#6e87ad; font-family:Consolas,monospace;")
        self._remaining.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        right_col.addWidget(self._remaining)
        # Where playback will ACTUALLY end (⏳ timed cut / 🐂 PD highlight
        # stop) next to the track's full length.
        self._limit_ms: int | None = None
        self._limit_glyph = "hourglass"
        self._limit_then: str | None = None   # 🥇 drawn after the limit
        # True when a stop is armed but resolves to the track's natural end (a PD
        # whose finale highlight sits at the end) — the card still shows a 🐂
        # marker so the operator sees the highlight-stop is on and the song plays
        # through, instead of the sand clock just vanishing.
        self._limit_to_end = False
        self._limit_lbl = QLabel("")
        self._limit_lbl.setStyleSheet(
            "font-size:11px; color:#d8b35c; font-family:Consolas,monospace;")
        self._limit_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._limit_lbl.setToolTip(
            "Adjusted play length (timed play / Paso Doble highlight stop)\n"
            "next to the track's full length")
        right_col.addWidget(self._limit_lbl)
        time_row.addLayout(right_col)
        self._time_box = block(time_row)

    def _build_seek(self, cache_of):
        """The seek bar and the waveform strip above it."""
        self._slider = ClickSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("seek")
        self._slider.setRange(0, 0)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderMoved.connect(self._on_slider_moved)
        self._slider.sliderReleased.connect(self._on_slider_released)
        # Late-bound: the card can be retargeted to the pause-music player.
        self._slider.clickJumped.connect(self._seek_by_hand)
        # 〰 The title's waveform above the seek bar — the same span, the same
        # late-bound seek.
        self._wave = WaveformStrip()
        self._wave.scrubbed.connect(self._on_wave_scrubbed)
        self._wave.seekRequested.connect(self._on_wave_released)
        self._wave_on = True
        self._wave_path: str | None = None
        self._moved_by_hand = False     # an operator seek hid the start line
        self._wave_loader = WaveformLoader(self, cache_of=cache_of)
        self._wave_loader.ready.connect(self._on_wave_ready)

    def _build_transport(self):
        """Cue, prev / rewind / play-pause / forward / next and the loop toggle."""
        btns = QHBoxLayout()
        btns.setSpacing(4)
        btns.addStretch(1)
        self._cue_btn = QToolButton()
        icon_button(self._cue_btn, "cue_start", 16, CARD_CUE)
        self._cue_btn.setToolTip("Jump back to the start (0:00) of this track")
        self._cue_btn.clicked.connect(self._seek_to_start)
        btns.addWidget(self._cue_btn)
        self._pause_btn = None
        self._primary_btns = []     # 🔘 what the button size in ⚙ Settings grows
        # The primary controls (prev / play-pause / next) are enlarged so the
        # operator can hit them at a glance; the fine controls stay smaller.
        primary = {"prev", "play_circle", "next"}
        for name, tip, cb in (
                ("prev", "Previous title", self.prevRequested.emit),
                ("rewind", "Back 10 s", lambda: self._skip(-10_000)),
                ("play_circle", "Pause / resume", self._toggle_pause),
                ("forward", "Forward 10 s", lambda: self._skip(+10_000)),
                ("next", "Next title", self.nextRequested.emit)):
            b = QToolButton()
            big = name in primary
            icon_button(b, name, 24 if big else 16, CARD_INK)
            b.setToolTip(tip)
            b.clicked.connect(cb)
            if big:
                b.setStyleSheet("QToolButton { padding:5px 7px; }")
                self._primary_btns.append(b)
            btns.addWidget(b)
            if name == "play_circle":
                self._pause_btn = b
        # 🔁 Hold the evening on THIS title: it starts over every time it ends.
        # A state, not an action, so it stays pressed and lights up — next to ⏭
        # because it is the answer to the same question, "what comes now".
        self._loop_btn = QToolButton()
        icon_button(self._loop_btn, "regen", 16, CARD_INK)
        self._loop_btn.setCheckable(True)
        self._loop_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._loop_btn.setToolTip(
            "Endless repeat of THIS title (toggle):\n"
            "while on, the running title starts again every time it ends —\n"
            "for the moment the floor is still full or the speech runs long.\n\n"
            "It holds the evening on one title, so it beats the 🏁 end of a\n"
            "round and works with ⏭ auto-advance off too. Switch it off and\n"
            "the list carries on where it stands.")
        self._loop_btn.setStyleSheet(
            "QToolButton:checked { background:#1565c0; }")
        btns.addWidget(self._loop_btn)
        btns.addStretch(1)
        self._btn_box = block(btns)

    def _build_aux_row(self):
        """The row under the transport that holds the aux buttons."""
        # Aux controls row — fade-out / jump-to-pause / extend-pause — sitting
        # in their own row right BELOW the transport buttons (the operator's
        # "end this song" / "manage the pause" actions, kept clear of the main
        # play controls). Visibility is toggled per play / pause state.
        aux_row = QHBoxLayout()
        aux_row.setSpacing(6)
        aux_row.addStretch(1)
        aux_row.addWidget(self._fade_btn)
        aux_row.addWidget(self._topause_btn)
        aux_row.addWidget(self._extend_btn)
        aux_row.addWidget(self._skip_pause_btn)
        aux_row.addStretch(1)
        self._aux_box = block(aux_row)
        # Hidden, it still holds its row: a title ending (a 🔉↓ fade-out, the
        # last of a list) must not make the whole card jump shorter.
        keep = self._aux_box.sizePolicy()
        keep.setRetainSizeWhenHidden(True)
        self._aux_box.setSizePolicy(keep)

    def _build_volume(self):
        """Panic, duck, the master volume slider and its readout."""
        # ── Master volume — the ONLY volume control in Playing mode (the
        # preview overlay, which owns the other one, is hidden here). Full width
        # on purpose: it has to be hittable at a glance from a standing desk.
        vol_row = QHBoxLayout()
        vol_row.setSpacing(6)
        self._panic_btn = QToolButton()
        icon_button(self._panic_btn, "panic", 16, CARD_PANIC)
        self._panic_btn.setFixedHeight(28)
        self._panic_btn.setMinimumWidth(40)
        self._panic_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._panic_btn.setToolTip(
            "Fade the music out and HOLD it there (over the fade time).\n"
            "Nothing ends and nothing advances — ⏯ resumes at exactly the\n"
            "spot it went quiet. For an announcement or an incident on the floor.")
        self._panic_btn.clicked.connect(self.panicRequested.emit)
        # Here until set_vol_buttons_shown moves it up beside 🔉↓.
        self._panic_up = False
        vol_row.addWidget(self._panic_btn)
        self._duck_btn = QToolButton()
        icon_button(self._duck_btn, "volume", 16, CARD_INK)
        self._duck_btn.setFixedHeight(28)
        self._duck_btn.setMinimumWidth(40)
        self._duck_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._duck_btn.setCheckable(True)   # stays pressed while ducked
        # Orange while ducked, red while muted: the colours of the % readout.
        self._duck_btn.setStyleSheet(
            "QToolButton:checked { background:#d98f3a; border:1px solid #b06f20;"
            " border-radius:4px; }"
            "QToolButton[muted=\"true\"]:checked { background:#d9534f;"
            " border:1px solid #b52b27; }")
        self._duck_btn.clicked.connect(self.toggle_duck)
        vol_row.addWidget(self._duck_btn)
        self._vol = ClickSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(round(self._get_vol() * 100))
        self._vol.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._vol.setToolTip("Master volume")
        self._vol.valueChanged.connect(self._on_vol_changed)
        # − / + around it, like the tempo fader's; ⚙ Sound & player hides them.
        self._vol_down_btn = self._vol_step_btn("−", -VOL_STEP, i18n.t("quieter"))
        self._vol_up_btn = self._vol_step_btn("+", +VOL_STEP, i18n.t("louder"))
        vol_row.addWidget(self._vol_down_btn)
        vol_row.addWidget(self._vol, stretch=1)
        vol_row.addWidget(self._vol_up_btn)
        # Double-click it to type a level the sound check already gave.
        self._vol_lbl = TypedValue(self._vol)
        self._vol_lbl.setFixedWidth(34)
        self._vol_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                                   | Qt.AlignmentFlag.AlignVCenter)
        self._vol_lbl.setStyleSheet(
            "font-size:11px; color:#8fa3c4; font-family:Consolas,monospace;")
        vol_row.addWidget(self._vol_lbl)
        self._vol_box = block(vol_row)
        self._refresh_vol_lbl()

    def _vol_step_btn(self, text: str, delta: int, word: str) -> QToolButton:
        """One of the − / + buttons beside the volume slider."""
        b = QToolButton()
        b.setText(text)
        b.setFixedHeight(28)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setToolTip(i18n.t("Volume %s %s — hold to glide")
                     % (f"{VOL_STEP} %", word))
        b.setAutoRepeat(True)
        b.setAutoRepeatDelay(400)
        b.setAutoRepeatInterval(110)
        b.setStyleSheet(
            "QToolButton { font-size:14px; font-weight:bold; padding:0 5px; }")
        b.clicked.connect(
            lambda _checked=False, d=delta: self._vol.setValue(self._vol.value() + d))
        return b

    def _build_tempo(self):
        """The tempo fader with its step buttons, TSO, reset, pin and takt meter."""
        # ── Tempo fader: ±16% time-stretch, pitch preserved (the Qt ffmpeg
        # backend keeps the key — verified with a 440 Hz sine at rate 1.16).
        self._takt: int | None = None
        self._current_dance: str | None = None
        self._takt_overlay = None   # lazy: player.widgets.takt_meter.TaktMeterOverlay
        tempo_box = QVBoxLayout()
        tempo_box.setSpacing(2)
        # Top row: just the icon + the slider, so the fader spans the whole
        # card width and is easy to nudge precisely.
        slider_row = QHBoxLayout()
        slider_row.setSpacing(6)
        tempo_icon = QLabel()
        tempo_icon.setPixmap(icon_pixmap("sliders", 12, CARD_DIM))
        slider_row.addWidget(tempo_icon)
        self._tempo = TempoSlider(Qt.Orientation.Horizontal)
        self._tempo.setRange(-160, 160)   # 0.1 % steps
        self._tempo.setValue(0)
        self._tempo.setToolTip(
            "Tempo −16 % … +16 % without changing the pitch (time stretch) —\n"
            "e.g. to pull a track onto the takt the tournament needs.\n"
            "Stays set across tracks; a double-click on the fader (or the\n"
            "button below) resets it.")
        self._tempo.resetRequested.connect(self.reset_tempo)
        # Every setPlaybackRate makes the backend re-init its resampler, which
        # is the short audible gap. So while the user is dragging we only move
        # the label and apply the rate ONCE, when the handle is released.
        # Wheel / keyboard changes (no drag) fall back to a debounce timer.
        self._tempo_apply = QTimer(self)
        self._tempo_apply.setSingleShot(True)
        self._tempo_apply.setInterval(220)
        self._tempo_apply.timeout.connect(self.apply_tempo)
        self._tempo.valueChanged.connect(self._on_tempo)
        self._tempo.sliderReleased.connect(self._on_tempo_released)
        # − / + around the fader: walk the tempo instead of hunting for it with
        # the handle, which on a 32 %-wide fader is a coarse instrument. Held,
        # they glide — the one control in this app where auto-repeat is the
        # point, not the hazard. The rate still lands once, when the stepping
        # stops: a programmatic setValue is no drag, so _on_tempo debounces it
        # exactly like a wheel notch and a glide costs one gap, not thirty.
        minus = self._tempo_step_btn("−", -TEMPO_STEP, i18n.t("slower"))
        plus = self._tempo_step_btn("+", +TEMPO_STEP, i18n.t("faster"))
        slider_row.addWidget(minus)
        slider_row.addWidget(self._tempo, stretch=1)
        slider_row.addWidget(plus)
        tempo_box.addLayout(slider_row)
        info_row = self._build_tempo_info()
        tempo_box.addLayout(info_row)
        self._tempo_box = block(tempo_box)

    def _build_tempo_info(self):
        """The row under the fader: readout, TSO, reset, 📌 pin and ♪ meter."""
        # Bottom row: the percentage / takt readout on the left, the reset and
        # the per-title auto-reset toggle on the right.
        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        self._tempo_lbl = QLabel("±0.0%")
        self._tempo_lbl.setStyleSheet(
            "font-size:11px; color:#8fa3c4; font-family:Consolas,monospace;")
        info_row.addWidget(self._tempo_lbl)
        info_row.addStretch(1)
        self._tso_btn = QToolButton()
        # TSO on the German terms, CR (the WDSF Competition Rules) otherwise.
        self._tso_btn.setText(rules_name("TSO", short=True))
        self._tso_btn.setCheckable(True)
        self._tso_btn.setStyleSheet(
            "QToolButton { font-size:11px; font-weight:bold; color:#7fd4a0; }"
            "QToolButton:checked { background:#1565c0; color:#ffffff; }")
        self._tso_btn.setToolTip(rules_name(i18n.t(
            "Auto-equalize the heat tempo (toggle):\n"
            "while on, every title is pitched to the average tempo of its\n"
            "dance in this round, kept inside the TSO range (e.g. a Rumba\n"
            "at 23 → T24, a Paso Doble at 57 → T58)."), short=True))
        self._tso_btn.toggled.connect(self.tsoModeChanged.emit)
        self._tso_btn.toggled.connect(self._sync_tempo_pin)
        info_row.addWidget(self._tso_btn)
        tempo_reset = QToolButton()
        tempo_reset.setText("0")
        tempo_reset.setToolTip(
            "Reset the tempo to ±0 % (or double-click the fader)")
        tempo_reset.clicked.connect(self.reset_tempo)
        info_row.addWidget(tempo_reset)
        # A checkable button (not a QCheckBox — its white indicator clashed with
        # the dark card); it lights up in the accent colour while armed. Pinned
        # is the exception, so the signal carries the reset flag, not the pin.
        self._tempo_pin = QToolButton()
        icon_button(self._tempo_pin, "pin", 12, CARD_INK)
        self._tempo_pin.setCheckable(True)
        self._tempo_pin.setToolTip(rules_name(i18n.t(
            "📌 Pin the tempo: the fader stays where you left it when the next\n"
            "title starts.\n"
            "Off: every new title begins at ±0 %.\n"
            "Switching TSO on takes the pin off — TSO pitches each title itself."),
            short=True))
        self._tempo_pin.setStyleSheet(
            "QToolButton:checked { background:#1565c0; color:#ffffff; }")
        self._tempo_pin.toggled.connect(
            lambda on: self.tempoResetModeChanged.emit(not on))
        info_row.addWidget(self._tempo_pin)
        self._takt_btn = QToolButton()
        self._takt_btn.setText("♪")
        self._takt_btn.setCheckable(True)
        self._takt_btn.setStyleSheet(
            "QToolButton:checked { background:#1565c0; color:#ffffff; }")
        self._takt_btn.setToolTip(
            "Tap along to the beat to measure this track's live tempo by hand,\n"
            "against a target for its dance (Sollwert) — display only, does not\n"
            "touch the fader.")
        self._takt_btn.toggled.connect(self._toggle_takt_overlay)
        info_row.addWidget(self._takt_btn)
        return info_row

    def _tempo_step_btn(self, text: str, delta: int, word: str) -> QToolButton:
        """One of the − / + buttons beside the tempo fader."""
        b = QToolButton()
        b.setText(text)
        # The step and its percent sign travel together as one value: a literal
        # %% in a catalog key would be the only one in the catalog, and the
        # number is a number in every language anyway.
        b.setToolTip(i18n.t("Tempo %s %s — hold to glide")
                     % (f"{TEMPO_STEP / 10:.1f} %", word))
        b.setAutoRepeat(True)
        b.setAutoRepeatDelay(400)
        b.setAutoRepeatInterval(110)
        b.setStyleSheet(
            "QToolButton { font-size:14px; font-weight:bold; padding:0 5px; }")
        b.clicked.connect(lambda _checked=False, d=delta: self._nudge_tempo(d))
        return b
