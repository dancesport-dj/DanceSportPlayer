"""🔊 The Settings dialog's Sound & player tab: the audio engine, the
outputs, and the player's own rows.

Split off gui/dialogs/settings_dialog.py: building the tab, the voice
test, and reading its settings back for SettingsDialog.values().
"""
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from planner import i18n
from shared.audio.playback import (
    _AUDIO_IDLE_S,
    SYSTEM_DEFAULT,
    duck_db_text,
    match_output,
)
from shared.stores import player_layout_of
from shared.widgets import _hsep
from gui.dialogs import (
    MEDIA_BACKEND_CHOICES,
    PLAYER_LAYOUT_CHOICES,
    audio_output_choices,
    media_backend_of,
)
from gui.dialogs.settings_look import _DialogHost


class SoundTabMixin(_DialogHost):
    """The 🔊 Sound & player tab of SettingsDialog."""

    _announce_test_cb: Callable[[str, bool], None] | None

    def _setup_sound_tab(self, settings, tabs):
        """🔊 Sound & player: the audio engine, what reaches the PA and the
        player's own rows."""
        sound_tab = QWidget()
        plyt = QVBoxLayout(sound_tab)
        plyt.setSpacing(10)

        # ── Audio backend ──
        plyt.addWidget(QLabel(
            "<b>🔊 Audio backend</b> — the engine every title is played "
            "through:"))
        self._backend_combo = QComboBox()
        for key, caption in MEDIA_BACKEND_CHOICES:
            self._backend_combo.addItem(caption, key)
        self._backend_combo.setCurrentIndex(
            max(0, self._backend_combo.findData(media_backend_of(settings))))
        self._backend_combo.setToolTip(
            "Only change this if the sound gives you trouble: a title that\n"
            "won't play, or the short gap a pitch change costs — the two\n"
            "engines handle that differently. Takes effect on the next start.")
        plyt.addWidget(self._backend_combo)
        backend_note = QLabel(
            "Takes effect after restarting the app. If the sound stays away "
            "afterwards, switch back here — the setting is only read at start, "
            "so nothing else in the app depends on it.")
        backend_note.setWordWrap(True)
        backend_note.setStyleSheet("color:#666; font-size:11px;")
        plyt.addWidget(backend_note)

        # ── Give the sound card back between titles ──
        self._release_audio_chk = QCheckBox(
            "🔇  Release the sound card between titles — takes away the hiss an "
            "onboard output puts on the PA while the app holds it open")
        self._release_audio_chk.setChecked(
            bool(settings.get("release_audio_idle", False)))
        self._release_audio_chk.setToolTip(
            i18n.t("An onboard sound card un-mutes its output stage the moment an app\n"
                   "opens it, and the amplifier carries that hiss across the hall — you\n"
                   "hear it start with the app and stop when it closes, whether or not\n"
                   "anything is playing.\n\n"
                   "Handing the device back after %.0f s of silence takes it "
                   "away. The cost is the soft click the card makes re-opening it\n"
                   "for the next title, so only switch this on if you hear the hiss.")
            % _AUDIO_IDLE_S)
        plyt.addWidget(self._release_audio_chk)

        # ── Keep the operating system's own sounds off the PA ──
        self._mute_sys_chk = QCheckBox(
            "🔕  Mute system sounds while the evening runs — no error ding or "
            "notification chime over the speakers")
        self._mute_sys_chk.setChecked(
            bool(settings.get("mute_system_sounds", True)))
        self._mute_sys_chk.setToolTip(
            i18n.t("The music and the computer share the one sound card, so every\n"
                   "sound the system makes goes out over the PA too.\n\n"
                   "Muted all through Playing mode and whenever something plays,\n"
                   "put back when you return to planning or close the app.\n"
                   "Windows: the System Sounds slider of the volume mixer.\n"
                   "macOS: the alert volume. Linux (GNOME): event sounds."))
        plyt.addWidget(self._mute_sys_chk)

        plyt.addWidget(_hsep())
        self._add_output_rows(settings, plyt)

        plyt.addWidget(_hsep())
        self._add_player_rows(settings, plyt)

        plyt.addWidget(_hsep())
        self._add_dblclick_rows(settings, plyt)

        plyt.addStretch()
        return tabs.addTab(sound_tab, "🔊 Sound && player")

    def _add_output_rows(self, settings, plyt):
        """🔈 One output per source — see shared.audio.playback.OUTPUT_SOURCES."""
        plyt.addWidget(QLabel(
            "<b>🔈 Outputs</b> — where each part of the evening is heard:"))
        outputs = audio_output_choices()
        saved = settings.get("audio_outputs") or {}
        # Names to save with a choice: what the OS calls it, or what it was
        # called when it was chosen, for a card that is not plugged in now.
        self._output_names = {i: c.get("name") for c in saved.values()
                              if isinstance(c, dict) and (i := c.get("id"))}
        self._output_names.update(outputs)
        captions = {"music": "🎵  Music:", "filler": "⏸  Filler music:",
                    "cartwall": "🎛  Cartwall:", "announcer": "🔈  Announcements:",
                    "cue": "🎧  Pre-listen:"}
        tip = (
            "Every output the operating system lists can be chosen. On a sound card\n"
            "with several outputs, each pair that shows up as a device of its own\n"
            "(\"Out 3/4\" next to \"Out 1/2\") can take a source of its own; channels\n"
            "3/4 of ONE multichannel device cannot be picked separately.\n"
            "\n"
            "A card that is not plugged in plays on the system default until it is back.")
        cue_tip = (
            "▶ in the library pane, the 🏆 pane, the Similar window and the\n"
            "event plan plays here, with a mini player of its own, and the\n"
            "music keeps running. Refused while it is the output the music\n"
            "plays on, unless it is the only output. \"Same as the music\": they\n"
            "play on the music's player.")
        grid = QGridLayout()
        self._output_combos = {}
        # 🎧 Pre-listen right below the music: the two the desk is set up by.
        # Filler and announcements rarely need an output of their own — they
        # come last, below a line. None is that line.
        order = ("music", "cue", "cartwall", None, "filler", "announcer")
        for row, source in enumerate(order):
            if source is None:
                grid.addWidget(_hsep(), row, 0, 1, 2)
                continue
            combo = QComboBox()
            if source == "music":
                combo.addItem("System default (follows the OS)", None)
            else:
                combo.addItem("Same as the music", None)
                combo.addItem("System default (follows the OS)", SYSTEM_DEFAULT)
            for dev_id, name in outputs:
                combo.addItem(name, dev_id)
            choice = saved.get(source)
            want = choice.get("id") if isinstance(choice, dict) else None
            if want and isinstance(choice, dict):
                # A card Windows numbered anew is that card, under its new id.
                want = match_output(outputs, want, choice.get("name")) or want
            if want and combo.findData(want) < 0:
                combo.addItem(i18n.t("⚠  %s (not connected)")
                              % (self._output_names.get(want) or want), want)
            combo.setCurrentIndex(max(0, combo.findData(want)) if want else 0)
            combo.setToolTip(cue_tip if source == "cue" else tip)
            grid.addWidget(QLabel(captions[source]), row, 0)
            grid.addWidget(combo, row, 1)
            self._output_combos[source] = combo
        grid.setColumnStretch(1, 1)
        plyt.addLayout(grid)

    def _output_values(self) -> dict:
        """The pickers as the "audio_outputs" setting: a source left on
        follow is left out."""
        chosen = {}
        for source, combo in self._output_combos.items():
            dev_id = combo.currentData()
            if not dev_id:
                continue
            chosen[source] = ({"id": dev_id} if dev_id == SYSTEM_DEFAULT
                              else {"id": dev_id, "name": self._output_names.get(dev_id)})
        return chosen

    def _add_player_rows(self, settings, plyt):
        """The player's own rows, on the 🔊 Sound & player tab: the mini
        player, where the master player stands and the announcement voice."""
        self._add_card_rows(settings, plyt)
        self._add_duck_rows(settings, plyt)
        self._add_start_rows(settings, plyt)
        self._add_voice_rows(settings, plyt)
        self._add_position_rows(settings, plyt)

    def _add_card_rows(self, settings, plyt):
        """🎧 The mini player, 🖼 the cover and 〰 the waveform."""
        # ── Preview player overlay ──
        self._preview_chk = QCheckBox(
            "🎧  Preview player — float a mini player (seek / skip / volume) over "
            "the deck when a ▶ button is clicked")
        self._preview_chk.setChecked(bool(settings.get("preview_player", True)))
        plyt.addWidget(self._preview_chk)

        # ── 🖼 Cover art on the player card ──
        self._artwork_chk = QCheckBox(
            "🖼  Show artwork — a cover next to the title on the player card")
        self._artwork_chk.setToolTip(
            "Show a cover picture next to the title on the player.\n"
            "The playlist's own image is used when it has one (an #EXTIMG line\n"
            "in the .m3u or a cover file beside it), otherwise the track's\n"
            "embedded artwork, otherwise a plain ♪ tile.")
        self._artwork_chk.setChecked(bool(settings.get("show_artwork", True)))
        plyt.addWidget(self._artwork_chk)

        # ── 〰 The title's waveform in place of the seek bar ──
        self._waveform_chk = QCheckBox(
            "〰  Show waveform — the title's waveform in place of the player "
            "card's seek bar")
        self._waveform_chk.setToolTip(
            "Draw the playing title's waveform in place of the seek bar: quiet\n"
            "passages, the skipped silence, the Paso Doble highlights and\n"
            "where the fade-out of a timed cut begins. Click it to jump.")
        self._waveform_chk.setChecked(bool(settings.get("show_waveform", True)))
        plyt.addWidget(self._waveform_chk)

    def _add_duck_rows(self, settings, plyt):
        """🔉 How far the duck pulls the music down, and what that means in dB."""
        # ── 🔉 How far the duck button pulls the music down ──
        # 20 and 90 are player.audio.mix's DESK_DUCK_PCT and its cap: a duck
        # to full would be no duck at all.
        duck_row = QHBoxLayout()
        duck_row.addWidget(QLabel("🔉  Duck to:"))
        self._duck_spin = QSpinBox()
        self._duck_spin.setRange(0, 90)
        self._duck_spin.setSingleStep(5)
        self._duck_spin.setSuffix(" %")
        self._duck_spin.setToolTip(
            "How loud everything stays while 🔉 Duck is pressed on the player\n"
            "card, the mini player or the presenter screen: low enough to talk\n"
            "over, loud enough to keep the floor moving. 0 % is silence.")
        try:
            duck_pct = int(settings.get("duck_pct", 20))
        except (TypeError, ValueError):
            duck_pct = 20
        self._duck_db = QLabel()
        self._duck_spin.valueChanged.connect(
            lambda pct: self._duck_db.setText(duck_db_text(pct)))
        self._duck_spin.setValue(duck_pct)
        self._duck_db.setText(duck_db_text(self._duck_spin.value()))
        duck_row.addWidget(self._duck_spin)
        duck_row.addWidget(self._duck_db)
        duck_row.addStretch(1)
        plyt.addLayout(duck_row)

        # A duck is linear volume, and 10 % reads like "barely there" when it
        # is a clear −20 dB; the figures match duck_db_text.
        self._duck_note = QLabel(
            "A duck, here or a pad's on the 🎛 Cartwall tab, is a percentage "
            "of the music's volume, not of its loudness: 50 % ≈ −6 dB, "
            "30 % ≈ −10 dB (sounds about half as loud), 20 % ≈ −14 dB, "
            "10 % ≈ −20 dB.")
        self._duck_note.setWordWrap(True)
        self._duck_note.setStyleSheet("color:#666; font-size:11px;")
        plyt.addWidget(self._duck_note)

    def _add_start_rows(self, settings, plyt):
        """🌅 The fade-in and ⏩ the pre-roll every title starts with."""
        # ── 🌅 Every title fades in from silence ──
        # An edge case, so it lives here and not on the ▶ Playing panel. 10 s
        # is player.audio.mix's FADE_IN_MAX_SECS.
        fade_in_row = QHBoxLayout()
        fade_in_row.addWidget(QLabel("🌅  Fade each title in over:"))
        self._fade_in_spin = QDoubleSpinBox()
        self._fade_in_spin.setRange(0.0, 10.0)
        self._fade_in_spin.setSingleStep(0.5)
        self._fade_in_spin.setDecimals(1)
        self._fade_in_spin.setSuffix(" s")
        self._fade_in_spin.setSpecialValueText("off")
        self._fade_in_spin.setToolTip(
            "The big player starts every title at silence and brings it up\n"
            "over these seconds of music. Not a title a 🔀 crossfade brings in,\n"
            "which has its own ramp. Couples start on the first downbeat, so\n"
            "leave it off for a competition. 0 = off.")
        try:
            self._fade_in_spin.setValue(float(settings.get("fade_in_secs", 0) or 0))
        except (TypeError, ValueError):
            self._fade_in_spin.setValue(0.0)
        fade_in_row.addWidget(self._fade_in_spin)
        fade_in_row.addStretch(1)
        plyt.addLayout(fade_in_row)

        # ── ⏩ Every title starts a few seconds in ──
        # The same edge case; 30 s is shared.audio.playback's PRE_ROLL_MAX_SECS.
        pre_roll_row = QHBoxLayout()
        pre_roll_row.addWidget(QLabel("⏩  Start each title this far in:"))
        self._pre_roll_spin = QSpinBox()
        self._pre_roll_spin.setRange(0, 30)
        self._pre_roll_spin.setSuffix(" s")
        self._pre_roll_spin.setSpecialValueText("off")
        self._pre_roll_spin.setToolTip(
            "The big player skips the first seconds of every title. They do\n"
            "not count against the play length. A title picked up where it\n"
            "was left starts there instead, and a silent intro is still\n"
            "skipped on top. Cuts the same seconds from every title. 0 = off.")
        try:
            self._pre_roll_spin.setValue(int(settings.get("pre_roll_secs", 0) or 0))
        except (TypeError, ValueError):
            self._pre_roll_spin.setValue(0)
        pre_roll_row.addWidget(self._pre_roll_spin)
        pre_roll_row.addStretch(1)
        plyt.addLayout(pre_roll_row)

    def _add_voice_rows(self, settings, plyt):
        """🎙 The announcement voice and 🗣 where the call sits."""
        # ── 🎙 How 🔈 Announce next dance sounds ──
        # Set once per venue, not on the night: the ▶ Playing panel only
        # names the choice under its 🔈 switch.
        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("🎙  Announcement voice:"))
        self._voice_combo = QComboBox()
        self._voice_combo.setToolTip(
            "Which recorded voice announces the dance. “Mixed” alternates them\n"
            "— she, he, she, he — so an evening doesn't run on a single voice.\n\n"
            "A dance that was never recorded is not announced.")
        for label, key in (("Female", "female"), ("Male", "male"),
                           ("Mixed", "random")):
            self._voice_combo.addItem(label, key)
        self._voice_combo.setCurrentIndex(max(0, self._voice_combo.findData(
            str(settings.get("announce_voice", "random")))))
        voice_row.addWidget(self._voice_combo)
        self._heat_chk = QCheckBox("…with heat")
        self._heat_chk.setToolTip(
            "Append the heat number (\"…, Heat 3\") — the couples hear which\n"
            "heat they are about to dance.\n\n"
            "Only a round grid has heats: a theme list, the warm-up and a free\n"
            "running order are announced without one. Recorded for heats 1-8;\n"
            "beyond that the number is left out.")
        self._heat_chk.setChecked(bool(settings.get("announce_heat", False)))
        voice_row.addWidget(self._heat_chk)
        self._voice_test_btn = QPushButton("🔈  Test")
        self._voice_test_btn.setToolTip(
            "Speak a sample announcement now — check voice and level\n"
            "before the round, not during it.")
        # The unsaved pick: trying a voice before OK is what the button is for.
        self._voice_test_btn.setEnabled(self._announce_test_cb is not None)
        self._voice_test_btn.clicked.connect(self._test_voice)
        voice_row.addWidget(self._voice_test_btn)
        voice_row.addStretch(1)
        plyt.addLayout(voice_row)

        # Where the spoken dance sits against the first bar, when a title
        # names its dance as it starts. The panel names the choice in short.
        lead_row = QHBoxLayout()
        lead_row.addWidget(QLabel("🗣  Dance is named:"))
        self._lead_over_radio = QRadioButton("over the first bars")
        self._lead_wait_radio = QRadioButton("before the music starts")
        self._lead_over_radio.setToolTip(
            "The dance is named while the music is already running, ducked\n"
            "under the voice — the hall hears both at once and the title\n"
            "loses none of its first bars.\n\n"
            "Applies where a title names its dance as it starts: 🔈 Announce\n"
            "next dance on, and no pause between songs (a pause has a gap of\n"
            "its own for the call).")
        self._lead_wait_radio.setToolTip(
            "The dance is called into silence and the music follows when the\n"
            "voice is done — the hall hears WHICH dance before it starts, at\n"
            "the cost of a second or two of quiet.\n\n"
            "Applies where a title names its dance as it starts: 🔈 Announce\n"
            "next dance on, and no pause between songs (a pause has a gap of\n"
            "its own for the call).")
        lead_group = QButtonGroup(self)
        for r in (self._lead_over_radio, self._lead_wait_radio):
            lead_group.addButton(r)
            lead_row.addWidget(r)
        wait = bool(settings.get("announce_wait", False))
        self._lead_wait_radio.setChecked(wait)
        self._lead_over_radio.setChecked(not wait)
        lead_row.addStretch(1)
        plyt.addLayout(lead_row)

    def _add_position_rows(self, settings, plyt):
        """▶ Where the master player stands in Playing mode."""
        # ── Where the master player is docked ──
        plyt.addWidget(QLabel(
            "<b>▶ Player position</b> — where the master player stands in "
            "▶ Playing mode:"))
        self._player_layout_combo = QComboBox()
        for key, caption, blurb in PLAYER_LAYOUT_CHOICES:
            self._player_layout_combo.addItem(caption, key)
            self._player_layout_combo.setItemData(
                self._player_layout_combo.count() - 1, i18n.t(blurb),
                Qt.ItemDataRole.ToolTipRole)
        self._player_layout_combo.setCurrentIndex(
            max(0, self._player_layout_combo.findData(
                player_layout_of(settings))))
        plyt.addWidget(self._player_layout_combo)

    def _add_dblclick_rows(self, settings, plyt):
        """📂 What a double-click on a title does while planning: last on the
        tab, since it is about 📚 the library, not the player."""
        self._dblclick_head = QLabel("<b>📚 Library</b>")
        plyt.addWidget(self._dblclick_head)
        # The keys are gui.common.DBLCLICK_ACTIONS.
        dbl_row = QHBoxLayout()
        dbl_row.addWidget(QLabel("📂  Double-click on a title in 📚 the library:"))
        self._dblclick_combo = QComboBox()
        self._dblclick_combo.setToolTip(
            "What a double-click on a title does in 📚 the library and the 🏆\n"
            "tournament lists.\n\n"
            "Nothing: the title stays as it is; ▶ plays it.\n"
            "Open external player: the program your system plays music with\n"
            "(on a Mac, Music) — in the decks and the dialogs too.\n"
            "Edit tags: the 🏷 Tags editor, where you choose what Save\n"
            "writes into the file and what stays in the app.\n\n"
            "Right-click still offers all of it, and in Playing mode a\n"
            "double-click always plays or cues the title.")
        for label, key in (("Nothing", "nothing"),
                           ("Open external player", "external"),
                           ("Edit tags", "tags")):
            self._dblclick_combo.addItem(label, key)
        self._dblclick_combo.setCurrentIndex(
            max(0, self._dblclick_combo.findData(settings.get("dblclick_action"))))
        dbl_row.addWidget(self._dblclick_combo)
        dbl_row.addStretch(1)
        plyt.addLayout(dbl_row)
        self._dblclick_note = QLabel(
            "Only for 📚 the library and the 🏆 lists while planning. In ▶ "
            "Playing mode a double-click always plays or cues the title.")
        self._dblclick_note.setWordWrap(True)
        self._dblclick_note.setStyleSheet("color:#666; font-size:11px;")
        plyt.addWidget(self._dblclick_note)

    def _test_voice(self):
        """🔈 Test: speak a sample in the voice the dialog shows."""
        if self._announce_test_cb is not None:
            self._announce_test_cb(self._voice_combo.currentData(),
                                   self._heat_chk.isChecked())

    def _sound_values(self) -> dict:
        """The tab's settings, for values()."""
        return {
            "audio_outputs": self._output_values(),
            "preview_player": self._preview_chk.isChecked(),
            "duck_pct": self._duck_spin.value(),
            "fade_in_secs": self._fade_in_spin.value(),
            "pre_roll_secs": self._pre_roll_spin.value(),
            "dblclick_action": self._dblclick_combo.currentData(),
            "show_artwork": self._artwork_chk.isChecked(),
            "show_waveform": self._waveform_chk.isChecked(),
            "player_layout": self._player_layout_combo.currentData(),
            "announce_voice": self._voice_combo.currentData(),
            "announce_heat": self._heat_chk.isChecked(),
            "announce_wait": self._lead_wait_radio.isChecked(),
            "media_backend": self._backend_combo.currentData(),
            "release_audio_idle": self._release_audio_chk.isChecked(),
            "mute_system_sounds": self._mute_sys_chk.isChecked(),
        }
