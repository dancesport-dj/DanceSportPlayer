"""Building the Playing-mode panel: each group of controls, and the wiring
between them.

Mixin of PlayModePanel, split off player/widgets/play_mode_panel.py, which
keeps the panel's layout, its state and the values the player reads.
"""
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from planner import i18n
from planner.playing.party_stop import PartyStop
from planner.playing.play_sets import (
    _LEN_MAX,
    _LEN_STEP,
    upgrade_xfade,
    XFADE_DEFAULT_SECS,
    XFADE_MAX_SECS,
    XFADE_MIN_SECS,
)
from shared.widgets import _hsep
from shared.xfade_view import CrossfadeCurveButton, CrossfadeView
from player.widgets.panel_parts import _InlineEdit, _row_box, _Rows, _Toggle

if TYPE_CHECKING:
    from gui.window.hosts import PlayModePanelHost
else:
    PlayModePanelHost = object


class PlayModeSetupMixin(PlayModePanelHost):
    """Builds PlayModePanel's control groups once, from the saved settings."""

    def _setup_length_row(self, lyt, settings):
        """⏱ Timed play: the length ladder, its readout and the fade."""
        # ── Timed play: − / + around a big readout, stepping the length in
        # 15 s rungs up to 2:30 and then to "full" (no cut at all). One control
        # instead of a slider plus an on/off box: "full" IS the off position.
        self._secs = self._load_secs(settings)
        len_row = QHBoxLayout()
        len_row.setSpacing(6)
        self.len_minus = QPushButton("−")
        self.len_plus = QPushButton("+")
        for b in (self.len_minus, self.len_plus):
            b.setFixedSize(46, 46)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            # Scoped by type: a bare style would size the tooltips too.
            b.setStyleSheet("QPushButton{font-size:22px; font-weight:bold;}")
        self.len_minus.setToolTip(i18n.t("Shorter by %s s") % _LEN_STEP)
        self.len_plus.setToolTip(
            i18n.t("Longer by %s s — past %s the title plays to its end")
            % (_LEN_STEP, f"{_LEN_MAX // 60}:{_LEN_MAX % 60:02d}"))
        self.len_minus.clicked.connect(lambda: self._step_len(-1))
        self.len_plus.clicked.connect(lambda: self._step_len(+1))
        len_row.addWidget(self.len_minus)
        # Big mm:ss display — readable from a standing position at the desk.
        # Styled by its name only: the tooltip is a QLabel too, and a bare
        # style would put the explanation on screen in 34 px bold.
        self.len_lbl = QLabel("")
        self.len_lbl.setObjectName("playLen")
        self.len_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.len_lbl.setStyleSheet(
            "QLabel#playLen{font-size:34px; font-weight:bold; color:#1565c0;"
            "font-family:Consolas,monospace;}")
        self.len_lbl.setToolTip(
            i18n.t("Play length per song: each song is stopped after this time,\n"
                   "ramping down over the fade time first. Steps of %s s\n"
                   "up to %s; one step further is\n"
                   "'full' — no cut, every title plays to its own end.\n\n"
                   "Double-click to type an exact length (e.g. 1:37).")
            % (_LEN_STEP, f"{_LEN_MAX // 60}:{_LEN_MAX % 60:02d}"))
        # The ladder covers the usual lengths in two taps; typing covers the
        # ones between its rungs, which −/+ can never reach.
        self.len_lbl.setCursor(Qt.CursorShape.IBeamCursor)
        self.len_lbl.mouseDoubleClickEvent = self._on_len_typed
        self._len_edit: _InlineEdit | None = None    # built on first use
        len_row.addWidget(self.len_lbl, stretch=1)
        len_row.addWidget(self.len_plus)
        # 🏆 Under the digits, the dance whose own length they show — so the
        # desk sees which length counts, and that −/+ moves that dance's.
        self._dance_len: tuple[str, str, int] | None = None   # code, name, secs
        self.len_dance_lbl = QLabel("")
        self.len_dance_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Wraps: "Langsamer Walzer, 2. Zwischenrunde — …" on a 250px panel
        # would otherwise widen the column and push −/+ aside (Mac).
        self.len_dance_lbl.setWordWrap(True)
        self.len_dance_lbl.setStyleSheet("color:#b8860b; font-weight:bold;")
        self.len_dance_lbl.setToolTip(
            i18n.t("This dance has its own play length in the 🏆 tournament set\n"
                   "(⚙ Settings → 🎛 Play sets). − / + and typing change it there."))
        self.len_dance_lbl.hide()
        len_col = QVBoxLayout()
        len_col.setSpacing(0)
        len_col.addLayout(len_row)
        len_col.addWidget(self.len_dance_lbl)
        lyt.addWidget(_row_box(len_col))

        fade_row = QHBoxLayout()
        fade_row.addWidget(QLabel("Fade-out:"))
        # Half seconds: at 3 s a fade is already gentle, and the difference
        # between 1.5 and 2 is audible on the floor — whole seconds are too
        # coarse a ladder down at the short end.
        self.fade_spin = QDoubleSpinBox()
        self.fade_spin.setRange(0, 10)
        self.fade_spin.setDecimals(1)
        self.fade_spin.setSingleStep(0.5)
        self.fade_spin.setSuffix(" s")
        self.fade_spin.setValue(float(settings.get("fade_secs", 3)))
        self.fade_spin.setToolTip("Volume ramps to 0 over the last N seconds,\n"
                                  "in steps of half a second")
        fade_row.addWidget(self.fade_spin)
        self.fade_inside_check = QCheckBox("within the length")
        self.fade_inside_check.setChecked(bool(settings.get("fade_inside", True)))
        self.fade_inside_check.setToolTip(
            "Ticked: the fade-out ends at the play length.\n"
            "Unticked: the title plays its full length, then fades out.")
        fade_row.addWidget(self.fade_inside_check)
        fade_row.addStretch(1)
        lyt.addWidget(_row_box(fade_row))

        lyt.addWidget(_hsep())

    def _setup_paso_doble(self, lyt, settings):
        """Paso Doble: stop after a highlight, manual marks and edit mode."""
        # ── Paso Doble: stop after a highlight instead of the fade ──
        self.pd_check = _Toggle("🐂  Stop Paso Doble after highlight")
        self.pd_check.setToolTip(
            "A Paso Doble under this switch is never faded out and ignores\n"
            "the play length — it is danced to its choreographed highlights.\n"
            "the highlights (crescendo → dramatic drop) are auto-detected\n"
            "in the background and the music shuts off at once when the\n"
            "chosen one (its closing gong) hits. A highlight detection\n"
            "can't pin down falls back to the standard phrasing\n"
            "(1st ≈ 0:45, 2nd ≈ 1:15).\n\n"
            "Off, a Paso Doble is an ordinary title: the play length cuts it\n"
            "and the fade takes it out, like every other dance.")
        self.pd_check.setChecked(bool(settings.get("pd_highlight_stop", True)))
        lyt.addWidget(self.pd_check)

        # Everything in this box belongs to the switch: which highlight stops
        # the dance and the marking tools. With the switch off none of it does
        # anything, and the desk column is the one place in the app where a
        # screenful of dead controls costs a scroll mid-round. The wait after
        # the call is NOT in here — it is about how a PD starts, not how it
        # ends, and it applies just as much with the stop switched off.
        self.pd_sub_box = _Rows()
        lyt.addWidget(self.pd_sub_box)

        pd_row = QHBoxLayout()
        pd_row.addWidget(QLabel("Stop after highlight:"))
        self.pd_spin = QSpinBox()
        self.pd_spin.setRange(1, 3)
        self.pd_spin.setValue(max(1, min(3, int(settings.get("pd_highlight_n", 2)))))
        self.pd_spin.setToolTip(
            "Which highlight ends the Paso Doble — usually the 2nd,\n"
            "in rare cases the 3rd.")
        self._pd_spin_tip = self.pd_spin.toolTip()
        # 🏆 The panel's own number while a round's pick shows in the spin
        # (`set_round_pd_n`), else None — the spin holds it itself.
        self._pd_own_n: int | None = None
        pd_row.addWidget(self.pd_spin)
        pd_row.addStretch(1)
        self.pd_sub_box.add(_row_box(pd_row))

        self._add_pd_mark_tools()

        # The couples walk on and take position when the dance is called — a
        # Paso Doble that starts on the word is danced from the wrong bar.
        pd_call_row = QHBoxLayout()
        pd_call_row.addWidget(QLabel("Start after:"))
        self.pd_delay_spin = QSpinBox()
        self.pd_delay_spin.setRange(0, 60)
        self.pd_delay_spin.setSuffix(" s")
        self.pd_delay_spin.setValue(
            max(0, min(60, int(settings.get("pd_start_delay", 0)))))
        self.pd_delay_spin.setToolTip(
            "Hold a Paso Doble back this long before the music starts, so the\n"
            "couples reach their position after the dance is called. Applies\n"
            "to every way a PD is started — ▶, a double-click, auto-advance.\n"
            "0 s = start at once, like every other dance.\n\n"
            "With 🔈 Announce next dance on, the app makes the call and the\n"
            "seconds run from it; off, the hall's announcer does and the wait\n"
            "runs silently — counted down on this panel either way.")
        pd_call_row.addWidget(self.pd_delay_spin)
        pd_call_row.addStretch(1)
        lyt.addWidget(_row_box(pd_call_row))

        lyt.addWidget(_hsep())

    def _add_pd_mark_tools(self):
        """🎯 Marking a highlight, ✖ forgetting them, ✏️ edit mode and its chips."""
        # Manual learning: click exactly when a highlight hits while the PD plays.
        pd_learn_row = QHBoxLayout()
        self.pd_learn_btn = QPushButton("🎯  Mark highlight now")
        self.pd_learn_btn.setFixedHeight(26)
        self.pd_learn_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pd_learn_btn.setToolTip(
            "While a Paso Doble plays, click exactly when a highlight (the\n"
            "dramatic gong / drop) hits to teach its position. Click again at\n"
            "the 2nd / 3rd highlight. Manually learned highlights are flagged\n"
            "in the database and are never overwritten by 🐂 auto-detection.")
        self.pd_learn_btn.clicked.connect(self.pdLearnRequested.emit)
        pd_learn_row.addWidget(self.pd_learn_btn, stretch=1)
        self.pd_clear_btn = QPushButton("✖")
        self.pd_clear_btn.setFixedHeight(26)
        self.pd_clear_btn.setFixedWidth(30)
        self.pd_clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pd_clear_btn.setToolTip(
            "Forget the current track's learned highlights\n"
            "(falls back to 🐂 auto-detection on the next play).")
        self.pd_clear_btn.clicked.connect(self.pdClearRequested.emit)
        pd_learn_row.addWidget(self.pd_clear_btn)
        self.pd_sub_box.add(_row_box(pd_learn_row))

        # ✏️ Edit mode: while it's on nothing cuts the Paso Doble, so a later
        # crash can actually be reached, heard and marked. Without it the very
        # mark you just set becomes the stop and the title ends on the spot.
        self.pd_edit_btn = QPushButton("✏️  Edit highlights")
        self.pd_edit_btn.setCheckable(True)
        self.pd_edit_btn.setFixedHeight(26)
        self.pd_edit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pd_edit_btn.setToolTip(
            "Pause the music and suspend the highlight stop, so the whole Paso\n"
            "Doble is reachable while you set its marks: scrub to a crash, ⏯ to\n"
            "listen, hit 🎯, delete a wrong mark with its ✕. Marking within 3 s\n"
            "of an existing mark moves that one instead of adding a fourth.\n\n"
            "Leaving edit mode arms the stop again and PAUSES at it the next\n"
            "time it's reached, so you can hear whether the mark sits right.")
        self.pd_edit_btn.setStyleSheet(
            "QPushButton:checked { background:#ff9800; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.pd_edit_btn.toggled.connect(self._on_pd_edit)
        self.pd_sub_box.add(self.pd_edit_btn)

        # Mark chips, only while editing: "0:44 ✕  1:15 ✕  2:01 ✕".
        self.pd_marks_box = QWidget()
        self.pd_marks_lyt = QHBoxLayout(self.pd_marks_box)
        self.pd_marks_lyt.setContentsMargins(0, 0, 0, 0)
        self.pd_marks_lyt.setSpacing(4)
        self.pd_marks_box.setVisible(False)
        self.pd_sub_box.add(self.pd_marks_box)

    def _setup_auto_advance(self, lyt, settings):
        """⏭ Auto-advance, repeat and the pause with its filler music."""
        # ── Auto-advance: heat flow without touching the mouse ──
        self.advance_check = _Toggle("⏭  Auto-advance to next song")
        self.advance_check.setToolTip(
            "When a song ends (fade-out or natural end), pause for the\n"
            "configured time, then play the next song row of the deck —\n"
            "so a whole round runs through hands-free. Stops at the end\n"
            "of the round (🏁) — the next round is started manually.\n\n"
            "Switching it off stops 🔈 Announce next dance too: nothing\n"
            "should call a dance that nothing then plays. Switching it\n"
            "back on restores the announcement you had.\n\n"
            "Every playlist keeps its own answer: this is the one of the\n"
            "list last clicked, the same as the ⏭/✋ under that deck.")
        self.advance_check.setChecked(bool(settings.get("auto_advance", True)))
        lyt.addWidget(self.advance_check)

        # Hangs off auto-advance: without it the last title is followed by
        # nothing anyway, so there is no end to run past.
        self.repeat_check = _Toggle("🔁  Start again at the end")
        self.repeat_check.setToolTip(
            "When the LAST title of the list has finished, carry on with its\n"
            "first one instead of stopping — so a party keeps its music going\n"
            "without anybody at the desk.\n\n"
            "The 🏁 end of a round is untouched: that one happens between\n"
            "rounds, and still waits for the operator.\n\n"
            "Needs ⏭ auto-advance.")
        self.repeat_check.setChecked(bool(settings.get("repeat_list", False)))
        lyt.addWidget(self.repeat_check)

        self._add_stop_row(lyt)

        pause_row = QHBoxLayout()
        # The caption IS the switch — unchecked, songs run back to back and the
        # configured time stays in the box for switching back.
        self.pause_check = _Toggle("Pause between songs:")
        self.pause_check.setToolTip(
            "Off: the next song starts the moment the current one ends, with\n"
            "no filler music and no announcement. The configured time is kept\n"
            "for switching back.\n\n"
            "Needs ⏭ auto-advance — without it the next song waits for the\n"
            "operator anyway, so there is no gap to fill.")
        self.pause_check.setChecked(bool(settings.get("pause_enabled", False)))
        self.pause_check.toggled.connect(self._on_pause_on)
        pause_row.addWidget(self.pause_check)
        self.pause_spin = QSpinBox()
        self.pause_spin.setRange(0, 120)
        self.pause_spin.setSuffix(" s")
        self.pause_spin.setValue(int(settings.get("pause_secs", 15)))
        self.pause_spin.setToolTip(
            "Time for the couples to change / catch breath before the next song")
        pause_row.addWidget(self.pause_spin)
        pause_row.addStretch(1)
        # Kept, because the whole row leaves the panel together with the 🔁
        # tick above it when there is no auto-advance to hang a pause on.
        self.pause_row_box = _row_box(pause_row)
        lyt.addWidget(self.pause_row_box)

        self._add_xfade_row(lyt, settings)

        self._add_pause_music_rows(lyt, settings)

    def _add_stop_row(self, lyt):
        """⏹ When the music stops by itself. Never read from the settings:
        it is set for one evening (see planner/playing/party_stop.py)."""
        self._party_stop = PartyStop()
        stop_row = QHBoxLayout()
        stop_row.setSpacing(4)
        stop_row.addWidget(QLabel("⏹  Stop:"))
        self.stop_combo = QComboBox()
        for text, key in (("Never", "never"), ("After this title", "this"),
                          ("After … titles", "count"), ("At …", "time")):
            self.stop_combo.addItem(text, key)
        self.stop_combo.setToolTip(
            "Let the music stop by itself: after the title playing now,\n"
            "after a number of titles (the one playing now is the first),\n"
            "or with the first title that ends at or after a time of day.\n\n"
            "A title is never cut: it plays to its end, then the next one\n"
            "waits on the player for ⏯. A ⏭ skip does not count as an end.\n\n"
            "Set for this evening only — it is not saved.\n\n"
            "Needs ⏭ auto-advance.")
        stop_row.addWidget(self.stop_combo)
        self.stop_count_spin = QSpinBox()
        self.stop_count_spin.setRange(2, 99)
        self.stop_count_spin.setValue(5)
        self.stop_count_spin.setToolTip(
            "Titles still to end, the one playing now included —\n"
            "it counts down as they do.")
        stop_row.addWidget(self.stop_count_spin)
        self.stop_time_edit = QTimeEdit(QTime(23, 0))
        self.stop_time_edit.setDisplayFormat("HH:mm")
        self.stop_time_edit.setToolTip(
            "The first title that ends at or after this time is the last.\n"
            "A time already past today means after midnight.")
        stop_row.addWidget(self.stop_time_edit)
        stop_row.addStretch(1)
        self.stop_row_box = _row_box(stop_row)
        lyt.addWidget(self.stop_row_box)

    def _add_pause_music_rows(self, lyt, settings):
        """🎵 The pause music: its titles and how loud they play."""
        # Optional filler music during the pause, faded in and out. Stored as
        # a list of titles (rotated pause after pause); legacy settings hold
        # a single path string.
        raw = settings.get("pause_music", "") or []
        if isinstance(raw, str):
            raw = [raw] if raw else []
        self._pause_music = [str(p) for p in raw]
        # In their own boxes so the whole row greys out with the pause, labels
        # and all — Qt disables children with their parent.
        # Both boxes live in one folder so the pair disappears together when
        # there is no pause to fill.
        self.pause_sub_box = _Rows()
        lyt.addWidget(self.pause_sub_box)

        self.pause_music_box = QWidget()
        pm_row = QHBoxLayout(self.pause_music_box)
        pm_row.setContentsMargins(0, 0, 0, 0)
        pm_row.setSpacing(4)
        pm_row.addWidget(QLabel("Pause music:"))
        self.pause_music_lbl = QLabel("")
        self.pause_music_lbl.setStyleSheet("color:#555; font-style:italic;")
        self.pause_music_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        pm_row.addWidget(self.pause_music_lbl, stretch=1)
        pm_pick = QToolButton()
        pm_pick.setText("📂")
        pm_pick.setToolTip(
            "Choose one or more titles — or an .m3u playlist — that play\n"
            "softly during the pause between songs, faded in at the start\n"
            "and out before the next song. Several titles rotate: a title\n"
            "keeps playing pause after pause until it ends, then the next\n"
            "one takes over.")
        pm_pick.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        pm_pick.clicked.connect(self._pick_pause_music)
        pm_row.addWidget(pm_pick)
        pm_clear = QToolButton()
        pm_clear.setText("✕")
        pm_clear.setToolTip("No pause music")
        pm_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        pm_clear.clicked.connect(lambda: self._set_pause_music([]))
        pm_row.addWidget(pm_clear)
        self.pause_sub_box.add(self.pause_music_box)
        self._refresh_pause_music_lbl()

        # Filler plays quieter than the dance music — it's background, not
        # program. Percentage of the normal playback volume.
        self.pause_vol_box = QWidget()
        pv_row = QHBoxLayout(self.pause_vol_box)
        pv_row.setContentsMargins(0, 0, 0, 0)
        pv_row.addWidget(QLabel("Pause music volume:"))
        self.pause_vol_spin = QSpinBox()
        self.pause_vol_spin.setRange(10, 100)
        self.pause_vol_spin.setSingleStep(5)
        self.pause_vol_spin.setSuffix(" %")
        self.pause_vol_spin.setValue(
            max(10, min(100, int(settings.get("pause_music_vol", 10)))))
        self.pause_vol_spin.setToolTip(
            "How loud the pause music plays, relative to the normal\n"
            "playback volume — kept lower so it stays in the background.")
        pv_row.addWidget(self.pause_vol_spin)
        pv_row.addStretch(1)
        self.pause_sub_box.add(self.pause_vol_box)

    def _add_xfade_row(self, lyt, settings):
        """🔀 The crossfade switch, its seconds, curve and picture."""
        # 🔀 Crossfade: the next title comes in under the end of this one.
        # Only between titles that follow with no gap, so the row comes and
        # goes with the pause row and greys out while there is a pause. The
        # caption IS the switch, as on the pause row: off, the seconds stay in
        # the box, so switching it on comes back on a length worth hearing.
        xf_row = QHBoxLayout()
        self.xfade_check = _Toggle("🔀  Crossfade:")
        self.xfade_check.setToolTip(
            "The last seconds of a title and the first of the next play\n"
            "together: the old one fades out while the new one fades in,\n"
            "so the floor never hears a gap. Only where the list walks on\n"
            "by itself with no pause — a heat keeps its gap. Not after a\n"
            "🏁 round, a 🔁 title or a 🐂 Paso Doble run to its highlight.\n\n"
            "Off: one title ends, then the next starts. Every playlist\n"
            "keeps its own answer.")
        xf_row.addWidget(self.xfade_check)
        stored = upgrade_xfade({key: settings[name] for key, name in (
            ("xfade", "xfade_secs"), ("xfade_on", "xfade_on")) if name in settings})
        self.xfade_check.setChecked(bool(stored.get("xfade_on", False)))
        self.xfade_spin = QDoubleSpinBox()
        self.xfade_spin.setRange(XFADE_MIN_SECS, XFADE_MAX_SECS)
        self.xfade_spin.setDecimals(1)
        self.xfade_spin.setSingleStep(0.5)
        self.xfade_spin.setSuffix(" s")
        self.xfade_spin.setValue(float(stored.get("xfade", XFADE_DEFAULT_SECS)))
        self.xfade_spin.setToolTip(
            "How long the two titles play together — half-second steps")
        xf_row.addWidget(self.xfade_spin)
        xf_row.addStretch(1)
        # The curve and its picture on a line of their own under the switch:
        # beside it they made this the panel's widest row.
        curve_row = QHBoxLayout()
        curve_row.addSpacing(24)
        self.xfade_curves = CrossfadeCurveButton()
        self.xfade_curves.set_curve(str(settings.get("xfade_curve", "equal")))
        curve_row.addWidget(self.xfade_curves)
        self.xfade_view = CrossfadeView()
        curve_row.addWidget(self.xfade_view)
        curve_row.addStretch(1)
        self.xfade_check.toggled.connect(self._sync_xfade_row)
        self.xfade_spin.valueChanged.connect(self._sync_xfade_row)
        self.xfade_curves.curveChanged.connect(self._sync_xfade_row)
        self._sync_xfade_row()
        xf_lines = QVBoxLayout()
        xf_lines.setSpacing(2)
        xf_lines.addLayout(xf_row)
        xf_lines.addLayout(curve_row)
        self.xfade_row_box = _row_box(xf_lines)
        lyt.addWidget(self.xfade_row_box)

    def _setup_announce(self, lyt, settings):
        """🗣 The spoken cue for the couples: the switch, its timing and the
        voice chosen in ⚙ Settings."""
        # Spoken cue for the couples, timed to land just before the pause ends.
        self.announce_check = _Toggle("🔈  Announce next dance")
        self.announce_check.setToolTip(
            "Say the next dance out loud shortly before the pause ends\n"
            "(\"Nächster Tanz: Langsamer Walzer\"). Without a pause the dance\n"
            "is named as the title starts instead (\"Langsamer Walzer\") —\n"
            "over the first bars or before them, as ⚙ Settings → 🔊 Sound &\n"
            "player has it.")
        self.announce_check.setChecked(bool(settings.get("announce_next", False)))
        # What ✋ Manual switched off, so ⏭ Auto can put it back. Deliberately
        # not persisted: a session that ends in Manual starts in Manual, and
        # there is nothing left to restore.
        self._announce_before_manual = False
        lyt.addWidget(self.announce_check)

        # What goes with the call: none of it is worth a line when nothing is
        # announced.
        self.announce_sub_box = _Rows()
        lyt.addWidget(self.announce_sub_box)

        # Voice, heat and where the call sits against the first bar are set
        # once per venue in ⚙ Settings; the panel only names them, the way
        # the play length names a dance's own length.
        self._announce_voice = str(settings.get("announce_voice", "random"))
        self._announce_heat = bool(settings.get("announce_heat", False))
        self._announce_wait = bool(settings.get("announce_wait", False))
        self.announce_style_lbl = QLabel("")
        # Under the first word of the switch's caption, past its 🔈 — not
        # centred across the column.
        self.announce_style_lbl.setContentsMargins(
            self.announce_check.word_left(), 0, 0, 0)
        self.announce_style_lbl.setWordWrap(True)   # the panel can be 250px
        self.announce_style_lbl.setStyleSheet("color:#b8860b; font-weight:bold;")
        self.announce_style_lbl.setToolTip(
            i18n.t("The voice, the heat number and whether the dance is\n"
                   "named over the music or before it are set in\n"
                   "⚙ Settings → 🔊 Sound & player."))
        self.announce_sub_box.add(self.announce_style_lbl)
        self._refresh_announce_style()

        lyt.addWidget(_hsep())

    def _setup_play_options(self, lyt, settings):
        """Loudness, cover art, double-click and pick-up-where-left."""
        # ── Loudness equalization (EBU R128) ──
        self.loudness_check = _Toggle("🔊  Equalize volume (R128)")
        self.loudness_check.setToolTip(
            "Compensate loudness differences between tracks on playback:\n"
            "each song's measured EBU R128 loudness is pulled towards a common\n"
            "target, so quiet old recordings and loud modern masters play at\n"
            "a similar level. Needs 📊 Analyze loudness (⚙ Settings) first.")
        self.loudness_check.setChecked(bool(settings.get("loudness_eq", True)))
        # The box stays clickable so the user can always toggle their intent; whether
        # equalization is ACTUALLY applied is gated separately on `_loudness_available`
        # (set once measured loudness exists). Disabling it would trap a checked box.
        self._loudness_available = False
        lyt.addWidget(self.loudness_check)

        # ── ▶️ What a double-click on a title in the deck does ──
        self.dblclick_check = _Toggle("▶️  Double-click starts the title")
        self.dblclick_check.setToolTip(
            "On: a double-click in a deck puts the title on the speakers at\n"
            "once — what a party wants.\n"
            "Off: it is only CUED on the player (loaded, shown, silent) and ⏯\n"
            "starts it — what a heat wants, where the music begins when the\n"
            "couples are on the floor and not a moment earlier.\n\n"
            "Part of the play sets: 🏆 tournament switches it off, 🎉 party on.")
        self.dblclick_check.setChecked(bool(settings.get("dblclick_plays", False)))
        lyt.addWidget(self.dblclick_check)

        # ── ↩ Pick a title up where it was left ──
        self.remember_check = _Toggle("↩  Remember where a title stopped")
        self.remember_check.setToolTip(
            "There is one player for every deck, so leaving a title to hear\n"
            "another one loses your place in it. On: the spot a title stopped\n"
            "at is kept and it starts there again — marked by a tick on the\n"
            "seek bar and by ↩ mm:ss on its row.\n\n"
            "A title played to its end keeps no mark, and the marks are\n"
            "forgotten when the app closes.")
        self.remember_check.setChecked(bool(settings.get("remember_pos", False)))
        lyt.addWidget(self.remember_check)

        lyt.addWidget(_hsep())

    def _setup_play_set_buttons(self, lyt):
        """🏆/🎉 The tournament and party play-set buttons."""
        # ── 🏆 Tournament play set: the competition values in one press ──
        # Above the party button on purpose: it is the one you reach for when a
        # party list has just left the panel somewhere else, and the pair reads
        # as what it is — tournament above, party below.
        self.tournament_btn = QPushButton("🏆  Tournament set")
        self.tournament_btn.setCheckable(True)   # lit while the panel is on it
        self.tournament_btn.setFixedHeight(26)
        self.tournament_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tournament_btn.setToolTip(
            "Put the panel back on the competition values in one go: the\n"
            "configured play length, no pause between songs, no auto-advance\n"
            "and no spoken announcement — the settings a heat is run with.\n\n"
            "Lit gold while the panel stands on those values, the way 🎉 is lit\n"
            "purple during a party. Switches the 🎉 party set off. What exactly\n"
            "it sets is yours to change: ⚙ Settings → 🎛 Play sets.\n"
            "\n"
            "Clicked while lit, it switches itself off: the list goes back to\n"
            "the values it had before the set was pressed.")
        self.tournament_btn.setStyleSheet(
            "QPushButton:checked { background:#b8860b; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.tournament_btn.clicked.connect(self.tournamentSetRequested.emit)
        lyt.addWidget(self.tournament_btn)

        # ── 🎉 Party play set: the settings a party needs at once ──
        self.party_btn = QPushButton("🎉  Party set")
        self.party_btn.setCheckable(True)
        self.party_btn.setFixedHeight(26)
        self.party_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.party_btn.setToolTip(
            "Switch the tournament settings over to party playing in one go:\n"
            "every title to its full length, auto-advance to the next one, no\n"
            "pause (so no break music) in between and no spoken announcement.\n\n"
            "Applied by itself as soon as you play from the 🤸 Practice /\n"
            "party list, and switched back when a tournament deck takes over —\n"
            "a toast says what changed either way. What exactly it sets is\n"
            "yours to change: ⚙ Settings → 🎛 Play sets.\n"
            "\n"
            "Clicked while lit, it switches itself off: the list goes back to\n"
            "the values it had before the set was pressed.")
        self.party_btn.setStyleSheet(
            "QPushButton:checked { background:#7b1fa2; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.party_btn.toggled.connect(self.partySetToggled.emit)
        lyt.addWidget(self.party_btn)

    def _setup_presenter(self, lyt, settings):
        """🖥 The presenter screen: switch, palette and monitor."""
        # ── 🖥 Presenter screen: what's playing + what's next, hall-sized ──
        pres_row = QHBoxLayout()
        pres_row.setSpacing(4)
        self.presenter_btn = QPushButton("🖥  Presenter")
        self.presenter_btn.setCheckable(True)
        self.presenter_btn.setFixedHeight(26)
        self.presenter_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.presenter_btn.setToolTip(
            "Open a second, full-screen window showing only the running title\n"
            "with its dance and the next three songs — big and plain, for a\n"
            "beamer or a monitor turned towards the floor. Pick the screen\n"
            "next to it; Esc (or this button) closes it again.")
        self.presenter_btn.setStyleSheet(
            "QPushButton:checked { background:#1565c0; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.presenter_btn.toggled.connect(self.presenterToggled.emit)
        pres_row.addWidget(self.presenter_btn, stretch=1)
        self.presenter_screen_combo = QComboBox()
        self.presenter_screen_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.presenter_screen_combo.setToolTip(
            "Which monitor the presenter screen fills. Same screen as the app\n"
            "is fine too — double-click the presenter window to shrink it back\n"
            "out of full screen.")
        pres_row.addWidget(self.presenter_screen_combo)
        # The palette it wears is set once per venue: ⚙ Settings → 🎨 Look.
        self.timetable_btn = QPushButton("🕒")
        self.timetable_btn.setFixedSize(30, 26)
        self.timetable_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.timetable_btn.setToolTip(
            "The evening's running order — when dinner is, when the opening\n"
            "dance is — as a second page on the presenter screen.\n\n"
            "Type it here; on the screen itself, T (or its 🕒 button) switches\n"
            "to it, and it can fade between the two pages by itself.")
        self.timetable_btn.clicked.connect(self.timetableRequested.emit)
        pres_row.addWidget(self.timetable_btn)
        lyt.addWidget(_row_box(pres_row))

        # 📱 The phone remote: its server, its QR code, its log.
        self.remote_btn = QPushButton("📱  Phone remote…")
        self.remote_btn.setFixedHeight(26)
        self.remote_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.remote_btn.setToolTip(
            "Play, skip, fade and fire pads from a phone's browser on this\n"
            "network — no app to install. Opens the window to start the\n"
            "server, with a QR code that logs the phone in and a log of what\n"
            "reached it.")
        self.remote_btn.clicked.connect(self.remoteRequested.emit)
        lyt.addWidget(self.remote_btn)

        # The monitor the presenter is wanted on, by name. It outlives an
        # unplug: the combo falls back to what is there, and goes back to
        # this one as soon as it is connected again.
        self._screen_name = str(settings.get("presenter_screen_name", ""))
        self._fill_screens(int(settings.get("presenter_screen", 0)))
        self.presenter_screen_combo.currentIndexChanged.connect(
            self._on_screen_picked)
        self.presenter_screen_combo.currentIndexChanged.connect(
            self.presenterScreenChanged.emit)
        # A beamer usually gets plugged in AFTER the app is started — keep the
        # list in step with what's actually connected.
        app = QGuiApplication.instance()
        if isinstance(app, QGuiApplication):
            app.screenAdded.connect(lambda _s: self._fill_screens())
            app.screenRemoved.connect(lambda _s: self._fill_screens())

    def _setup_awake_and_countdown(self, lyt, settings):
        """☀ The screensaver hold and the live countdown."""
        # ── ☀ Hold the screensaver off while the desk is working ──
        self.awake_check = _Toggle("☀  Keep the screen awake")
        self.awake_check.setToolTip(
            "Keep the screensaver and the display timeout off while music is\n"
            "playing or the presenter screen is open.\n\n"
            "The system counts idle time from the mouse and the keyboard,\n"
            "never from the speakers — so an hour of music with nobody touching\n"
            "the desk blanks the screen mid-heat, the beamer included. It goes\n"
            "back to its normal timeouts as soon as neither is running.")
        self.awake_check.setChecked(bool(settings.get("keep_awake", True)))
        lyt.addWidget(self.awake_check)

        lyt.addWidget(_hsep())

        # ── Live countdown of the current song ──
        self.countdown_lbl = QLabel("")
        self.countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_lbl.setStyleSheet(
            "font-size:22px; font-family:Consolas,monospace; color:#444;")
        self._countdown_text: str | None = None   # last set_countdown text
        lyt.addWidget(self.countdown_lbl)

        lyt.addStretch(1)

    def _setup_gear(self, lyt):
        """⚙ The settings gear, for a player-only install."""
        # ── ⚙ Settings, in the corner the ConfigPanel keeps it ──
        # A player-only install never shows the planning panel, so its gear is
        # out of reach and the app mode could not be changed back. This one sits
        # in the same spot of the same left panel — the hand goes to the same
        # place. Hidden in every other mode: there the planning gear is the one.
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(26, 26)
        self.settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings_btn.setToolTip(
            "Settings — app mode, library paths & analysis")
        self.settings_btn.clicked.connect(self.settingsRequested)
        self._gear_box = QWidget()
        glyt = QVBoxLayout(self._gear_box)
        glyt.setContentsMargins(0, 0, 0, 0)
        glyt.setSpacing(4)
        gear_row = QHBoxLayout()
        gear_row.setContentsMargins(0, 0, 0, 0)
        gear_row.addStretch(1)
        gear_row.addWidget(self.settings_btn)
        glyt.addLayout(gear_row)
        self._gear_box.setVisible(False)
        lyt.addWidget(self._gear_box)

    def _connect_signals(self, settings):
        """Every control's change reaches settingsChanged; initial sync."""
        self.fade_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.fade_inside_check.toggled.connect(
            lambda _: self.settingsChanged.emit())
        self.xfade_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.xfade_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.xfade_curves.curveChanged.connect(lambda _: self.settingsChanged.emit())
        self.pd_check.toggled.connect(self._on_pd_on)
        self.pd_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.pd_spin.valueChanged.connect(self._on_pd_spin)
        self.pd_delay_spin.valueChanged.connect(
            lambda _: self.settingsChanged.emit())
        self.advance_check.toggled.connect(lambda _: self._sync_pause_row())
        self.advance_check.toggled.connect(lambda _: self.settingsChanged.emit())
        # `clicked`, not `toggled`: only a person switching to Manual means
        # "stop everything automatic". A play set or a restored setting sets
        # this box too, and those carry their own announce value.
        self.advance_check.clicked.connect(self._follow_advance_with_announce)
        self.repeat_check.toggled.connect(lambda _: self.settingsChanged.emit())
        # Not settingsChanged: the stop rule is never saved.
        self.stop_combo.currentIndexChanged.connect(lambda _: self._on_stop_rule())
        self.stop_count_spin.valueChanged.connect(lambda _: self._on_stop_rule())
        self.stop_time_edit.timeChanged.connect(lambda _: self._on_stop_rule())
        self.pause_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.pause_vol_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.announce_check.toggled.connect(self.announce_sub_box.setVisible)
        self.announce_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.loudness_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.awake_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.dblclick_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.remember_check.toggled.connect(self.rememberToggled.emit)
        self.remember_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self._refresh_len_lbl()
        self._sync_pause_row()
        self._show_stop_rule()
        self.pd_sub_box.setVisible(self.pd_check.isChecked())
        self.announce_sub_box.setVisible(self.announce_check.isChecked())
