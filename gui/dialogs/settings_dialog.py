"""The settings dialog: library paths and global search, the analyses and
index builds, playback, the look and the app mode, one tab each.

Split out of gui/dialogs/__init__.py, which keeps the settings persistence
(load_settings, the path fallbacks, the choice tables) this dialog reads.
The 🎨 Look tab is a mixin of its own, in gui/dialogs/settings_look.py.
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel,
    QComboBox, QCheckBox, QLineEdit, QGroupBox, QRadioButton, QButtonGroup,
    QDialog, QSpinBox, QDoubleSpinBox, QTimeEdit,
    QFileDialog, QDialogButtonBox, QTabWidget, QPlainTextEdit,
)
from PySide6.QtCore import (
    Qt, QTime,
)
import planner.config
from planner.music.analysis import HAS_LIBROSA
from planner.models import TEMPO_RANGES
from planner.terms import dance_name
from planner.playing.play_sets import (
    _LEN_MAX, _LEN_STEP, DANCE_SECS_KEY, XFADE_MAX_SECS, XFADE_MIN_SECS,
    dance_secs_of, parse_play_length, pd_of, play_set_of, tso_of)
from shared.audio.audio_files import (
    music_browse_dir,
)
from shared.audio.playback import (
    _AUDIO_IDLE_S,
    SYSTEM_DEFAULT,
    match_output,
)
from shared.widgets import (
    _hsep,
)
from shared import error_reports, update_check
from planner import i18n
from planner.music.paths import parse_remap_paths
from shared.stores import player_layout_of
from shared.xfade_view import CrossfadeCurveButton, CrossfadeView
from gui.dialogs import (
    APP_MODE_CHOICES,
    M3U_FORMAT_CHOICES,
    MEDIA_BACKEND_CHOICES,
    PLAYER_LAYOUT_CHOICES,
    app_mode_of,
    audio_output_choices,
    media_backend_of,
)
from gui.dialogs.settings_look import LookTabMixin

log = logging.getLogger("dancesport.gui")


class SettingsDialog(LookTabMixin, QDialog):
    """Configure the library paths + global search (tab 1) and run every
    analysis / index build, grouped light vs heavy (tab 2)."""

    def __init__(self, settings: dict, parent=None, build_cb=None, embed_cb=None,
                 index_summary=None, all_cb=None, maintenance_cb=None, relearn_cb=None,
                 analyze_cb=None, loudness_cb=None, silence_cb=None, pd_cb=None,
                 vocals_cb=None, gaps_cb=None, n_unanalyzed: int = 0,
                 pd_export_cb=None, pd_import_cb=None, backup_restore_cb=None,
                 venue_export_cb=None, venue_import_cb=None, remote_cb=None,
                 remote_running=None, remote_stop_cb=None, remote_changed=None,
                 guests_cb=None, controller_cb=None, desk_keys_cb=None,
                 announce_test_cb=None, open_sound=False):
        super().__init__(parent)
        self.setWindowTitle("⚙  Settings")
        self.setMinimumWidth(560)
        self._settings_in = dict(settings)
        self._gaps_cb = gaps_cb
        self._build_cb = build_cb
        self._embed_cb = embed_cb
        self._all_cb = all_cb
        self._maintenance_cb = maintenance_cb
        self._relearn_cb = relearn_cb
        self._analyze_cb = analyze_cb
        self._loudness_cb = loudness_cb
        self._silence_cb = silence_cb
        self._pd_cb = pd_cb
        self._vocals_cb = vocals_cb
        self._venue_export_cb = venue_export_cb
        self._venue_import_cb = venue_import_cb
        self._remote_cb = remote_cb
        self._remote_running = remote_running or (lambda: False)
        self._remote_stop_cb = remote_stop_cb
        self._remote_changed = remote_changed
        self._guests_cb = guests_cb
        self._controller_cb = controller_cb
        self._desk_keys_cb = desk_keys_cb
        self._announce_test_cb = announce_test_cb
        summ = index_summary or {}
        lyt = QVBoxLayout(self)
        tabs = QTabWidget()
        lyt.addWidget(tabs)
        self._setup_general_tab(settings, tabs)
        self._setup_paths_tab(relearn_cb, settings, tabs)
        self._setup_look_tab(settings, tabs)
        sound_idx = self._setup_sound_tab(settings, tabs)
        self._setup_analysis_tab(
            all_cb, analyze_cb, backup_restore_cb, build_cb, embed_cb, loudness_cb,
            maintenance_cb, n_unanalyzed, pd_cb, pd_export_cb, pd_import_cb, silence_cb,
            summ, tabs, vocals_cb)
        sets_idx = self._setup_play_sets_tab(settings, tabs)
        chk_idx = self._setup_checks_tab(gaps_cb, settings, tabs)
        self._setup_venue_tab(tabs)
        self._setup_tab_visibility(chk_idx, lyt, sets_idx, tabs)
        if open_sound:      # 🚦 Check → choose outputs: they are picked here
            tabs.setCurrentIndex(sound_idx)

    def _setup_general_tab(self, settings, tabs):
        """⚙ General: app mode, the 📱 phone remote, global search and error
        reports."""
        gen_tab = QWidget()
        plyt = QVBoxLayout(gen_tab)
        plyt.setSpacing(10)

        self._add_app_mode_row(plyt, settings)

        self._add_remote_box(plyt)

        self._add_controller_box(plyt)

        # ── Global search opt-in ──
        self._global_chk = QCheckBox(
            "🌐  Global search — match dropped files against the whole repository "
            "(default: favorites library only)")
        self._global_chk.setChecked(bool(settings.get("global_search", False)))
        plyt.addWidget(self._global_chk)

        note = QLabel(
            "Global search needs the repo's audio analyzed once (⚗ Analysis tab). "
            "Analysis only <i>reads</i> your files — it never modifies them. "
            "Results are cached, so repeat searches are fast.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#666; font-size:11px;")
        plyt.addWidget(note)

        # ── 🏷 Untagged titles out of generation, opt-in ──
        self._exclude_no_class_chk = QCheckBox(
            "🏷  Leave titles without a class out of generated playlists")
        self._exclude_no_class_chk.setToolTip(
            "Competition titles whose comment carries no class tag are listed\n"
            "under the '🏷 No class' library category either way. Ticked, they\n"
            "also stay out of the generated playlists, the warm-up and the AI search.")
        self._exclude_no_class_chk.setChecked(
            bool(settings.get("exclude_no_class", False)))
        plyt.addWidget(self._exclude_no_class_chk)

        # ── 🐞 Opt-in error reports, only where the build can send them ──
        self._error_reports_chk = None
        if error_reports.available():
            self._error_reports_chk = QCheckBox(
                "🐞  Send error reports — when the app hits an error, send its "
                "technical details to the developer")
            self._error_reports_chk.setChecked(
                bool(settings.get("error_reports", False)))
            self._error_reports_chk.setToolTip(
                "Goes to the developer's GlitchTip project (app.glitchtip.com),\n"
                "which also sees the IP address a report comes from.\n\n"
                "Sent: the error and where in the program it happened, the last\n"
                "log lines before it (they can name the title that was playing),\n"
                "the operating system and the app version.\n\n"
                "Not sent: your music, your playlists, your computer's name.\n"
                "Your user folder is cut out of every path.\n\n"
                "Off by default. Applies as soon as you save.")
            plyt.addWidget(self._error_reports_chk)

        # ── 🔔 Opt-in update check ──
        self._update_check_chk = QCheckBox(
            "🔔  Check for new versions — once per start, ask GitHub whether a "
            "newer release is out")
        self._update_check_chk.setChecked(
            bool(settings.get(update_check.SETTING, False)))
        self._update_check_chk.setToolTip(
            "Asks api.github.com for the latest release. The request carries\n"
            "nothing about you or your music; GitHub sees the IP address it\n"
            "comes from. A newer version is announced once, with a link to\n"
            "its download page. Nothing is downloaded or installed.\n\n"
            "Off by default. Applies from the next start.")
        plyt.addWidget(self._update_check_chk)

        plyt.addStretch()
        tabs.addTab(gen_tab, "⚙ General")

    def _add_app_mode_row(self, plyt, settings):
        """Planner, player or both — hidden where the build fixes it."""
        # ── App mode ──
        # A player-only build fixes the mode, so the row would be a control
        # with one usable entry. It is built either way — values() reads it —
        # and only kept off the screen.
        mode_locked = planner.config.player_build()
        mode_lbl = QLabel("<b>App mode</b> — which side of the app is shown:")
        plyt.addWidget(mode_lbl)
        mode_lbl.setVisible(not mode_locked)
        self._app_mode_combo = QComboBox()
        for key, caption, blurb in APP_MODE_CHOICES:
            self._app_mode_combo.addItem(caption, key)
            # addItem is hooked, setItemData is not — see gui/config_panel.py's
            # strategy combo for why it should stay that way.
            self._app_mode_combo.setItemData(
                self._app_mode_combo.count() - 1, i18n.t(blurb),
                Qt.ItemDataRole.ToolTipRole)
        self._app_mode_combo.setCurrentIndex(
            max(0, self._app_mode_combo.findData(app_mode_of(settings))))
        self._app_mode_combo.setToolTip(
            "Planner only hides the tournament floor's playing panel;\n"
            "Player only hides everything that generates or checks a playlist.\n"
            "Nothing is removed — switching back brings it all straight back.")
        plyt.addWidget(self._app_mode_combo)
        self._app_mode_combo.setVisible(not mode_locked)
        mode_sep = _hsep()
        plyt.addWidget(mode_sep)
        mode_sep.setVisible(not mode_locked)

    def _add_remote_box(self, plyt):
        """📱 The phone remote's pane and its server button."""
        # ── 📱 Phone remote: its own pane, switched in its own window ──
        # Starting the server here leaves ⚙ Settings open: the window that
        # shows the address, the QR code and the PIN opens on top of it.
        self._remote_box = QGroupBox("📱  Phone remote")
        rlyt = QHBoxLayout(self._remote_box)
        self._remote_info = QLabel(
            "Play, skip, fade and fire pads from a phone's browser on this "
            "network — no app to install. The server's window shows the "
            "address, a QR code that logs the phone in, and the PIN.")
        self._remote_info.setWordWrap(True)
        self._remote_info.setStyleSheet("color:#666; font-size:11px;")
        rlyt.addWidget(self._remote_info, stretch=1)
        self._remote_window_btn = QPushButton()
        self._remote_window_btn.clicked.connect(self._on_remote_btn)
        rlyt.addWidget(self._remote_window_btn)
        # 📨 Guests' song requests: a page of their own, no PIN, nothing it moves.
        guests_btn = QPushButton("📨  Guest requests…")
        guests_btn.setToolTip(
            "Guests search the library on their phones and ask for a title, or\n"
            "leave a few words — it lands in an inbox, and you put it on the\n"
            "wishlist or dismiss it. Nothing a guest sends is played on its own.")
        guests_cb = self._guests_cb
        if guests_cb is not None:
            guests_btn.clicked.connect(lambda: guests_cb(self))
        # Into the layout first, then visible: a widget shown while it has
        # no parent yet flashes up as a window of its own.
        rlyt.addWidget(guests_btn)
        guests_btn.setVisible(guests_cb is not None)
        plyt.addWidget(self._remote_box)
        self._remote_box.setVisible(self._remote_cb is not None)
        self._sync_remote_btn()
        # Stopped or started from the server's own window: follow it.
        if self._remote_changed is not None:
            self._remote_changed.connect(self._sync_remote_btn)

    def _add_controller_box(self, plyt):
        """🎛 The controller and ⌨ keys windows, where the app offers them."""
        # ── 🎛 Hardware controller: its own window, applied as it is set ──
        ctl_box = QGroupBox("🎛  Controller")
        clyt = QHBoxLayout(ctl_box)
        ctl_info = QLabel(
            "Play, skip, fade, set the volume and fire cartwall pads from a USB "
            "MIDI or HID controller — a profile for the Korg nanoKONTROL2 is "
            "built in, any other is learned by pressing its buttons.")
        ctl_info.setWordWrap(True)
        ctl_info.setStyleSheet("color:#666; font-size:11px;")
        clyt.addWidget(ctl_info, stretch=1)
        ctl_btn = QPushButton("🎛  Set up…")
        controller_cb = self._controller_cb
        if controller_cb is not None:
            ctl_btn.clicked.connect(lambda: controller_cb(self))
        clyt.addWidget(ctl_btn)
        ctl_btn.setVisible(controller_cb is not None)
        # ⌨ The same actions on keys — also a Stream Deck's or a keypad's —
        # and the 🎛 wall's keys, in one window.
        keys_btn = QPushButton("⌨  Keys…")
        desk_keys_cb = self._desk_keys_cb
        if desk_keys_cb is not None:
            keys_btn.clicked.connect(lambda: desk_keys_cb(self))
        clyt.addWidget(keys_btn)
        keys_btn.setVisible(desk_keys_cb is not None)
        plyt.addWidget(ctl_box)
        ctl_box.setVisible(self._controller_cb is not None
                           or self._desk_keys_cb is not None)

    def _on_remote_btn(self):
        if self._remote_running():
            if self._remote_stop_cb is not None:
                self._remote_stop_cb()
        elif self._remote_cb is not None:
            self._remote_cb(self)
        self._sync_remote_btn()

    def _sync_remote_btn(self):
        """The button names what a click does: start the server, or stop the
        one that is running."""
        btn = self._remote_window_btn
        if self._remote_running():
            btn.setText("📱  Stop Server")
            btn.setToolTip("Stops the phone remote's server — "
                           "connected phones lose the remote.")
        else:
            btn.setText("📱  Start Server")
            btn.setToolTip(
                "Starts the server and opens its window — stop it there again.\n\n"
                "Only phones on the same network get in, and only with the PIN;\n"
                "wrong PINs lock the phone out for a while.\n"
                "Windows may ask once whether the app may use the network —\n"
                "allow it for private networks.")

    def _setup_paths_tab(self, relearn_cb, settings, tabs):
        """📁 Paths: the folders, the playlist file format and 🧭 Fix paths."""
        paths_tab = QWidget()
        plyt = QVBoxLayout(paths_tab)
        plyt.setSpacing(10)

        # ── Favorites library path ──
        plyt.addWidget(QLabel(
            "<b>Favorites library</b> — scanned on start (your tanzcds folder):"))
        self._lib_edit = QLineEdit(settings.get("library_dir", ""))
        plyt.addLayout(self._path_row(self._lib_edit))

        # ── Whole-repo path ──
        plyt.addWidget(QLabel(
            "<b>Whole music repository</b> — used by global search (e.g. F:\\my music):"))
        self._glob_edit = QLineEdit(settings.get("global_dir", ""))
        plyt.addLayout(self._path_row(self._glob_edit))

        # ── Save-as default folder ──
        plyt.addWidget(QLabel(
            "<b>Save-as folder</b> — where 'Save as M3U…' starts (e.g. D:\\Dropbox\\Turniere):"))
        self._save_edit = QLineEdit(settings.get("save_dir", ""))
        plyt.addLayout(self._path_row(self._save_edit))

        # ── Playlist file format (every M3U export) ──
        plyt.addWidget(QLabel(
            "<b>Playlist file format</b> — what 'Save as M3U' and the exports write:"))
        self._m3u_format_combo = QComboBox()
        for key, caption in M3U_FORMAT_CHOICES:
            self._m3u_format_combo.addItem(caption, key)
        self._m3u_format_combo.setCurrentIndex(
            max(0, self._m3u_format_combo.findData(settings.get("m3u_format", "utf-8"))))
        self._m3u_format_combo.setToolTip(
            "UTF-8 keeps every umlaut and is what current players read.\n"
            "Pick the BOM variant only if an older Windows tool shows 'Ã¼' instead\n"
            "of 'ü'; .m3u8 is the same UTF-8 under the extension some players expect.")
        plyt.addWidget(self._m3u_format_combo)

        # ── Tournament playlists folder (popularity learning) ──
        plyt.addWidget(QLabel(
            "<b>Tournament playlists</b> — learned for popularity: .m3u files "
            "and/or tournament folders with copied music (e.g. "
            "H:\\DM Latein 2026):"))
        self._pl_edit = QLineEdit(settings.get("playlist_dir", ""))
        plyt.addLayout(self._path_row(self._pl_edit))

        self._relearn_btn = QPushButton("📜  Re-learn playlist popularity…")
        self._relearn_btn.setToolTip(
            "Re-read every M3U and tournament music folder in the tournament\n"
            "playlist folder and rebuild the popularity / co-occurrence index from\n"
            "it — WITHOUT rescanning files or audio. Use after exporting a played\n"
            "tournament so it counts right away.")
        self._relearn_btn.clicked.connect(self._on_relearn_clicked)
        self._relearn_btn.setEnabled(relearn_cb is not None)
        plyt.addWidget(self._relearn_btn)

        # ── Reference path (Fix paths) ──
        plyt.addWidget(QLabel(
            "<b>Reference path</b> — base folder the playlist files live in on THIS PC; "
            "🧭 Fix paths re-roots broken references here (e.g. "
            "C:\\Users\\…\\my music\\tanzcds):"))
        self._ref_edit = QLineEdit(settings.get("reference_path", ""))
        plyt.addLayout(self._path_row(self._ref_edit))

        # ── Extra search folders (Fix paths) ──
        plyt.addWidget(QLabel(
            "<b>Search folders</b> — where else to look for a track when a playlist "
            "was written on another PC, one folder per line (e.g. F:\\my music and "
            "C:\\Users\\…\\Documents\\datein\\my music):"))
        self._remap_edit = QPlainTextEdit(
            "\n".join(parse_remap_paths(settings.get("remap_paths"))))
        self._remap_edit.setPlaceholderText("F:\\my music\nC:\\Users\\…\\my music")  # i18n: data
        self._remap_edit.setFixedHeight(66)
        self._remap_edit.setToolTip(
            "🧭 Fix paths tries the Reference path first and then these folders,\n"
            "in order, cutting the foreign path down until what is left lands on a\n"
            "real file underneath one of them. A path is only ever rewritten to a\n"
            "file that is actually there.")
        remap_row = QHBoxLayout()
        remap_row.addWidget(self._remap_edit, stretch=1)
        remap_add = QPushButton("Add…")
        remap_add.clicked.connect(self._add_remap_folder)
        remap_col = QVBoxLayout()
        remap_col.addWidget(remap_add)
        remap_col.addStretch(1)
        remap_row.addLayout(remap_col)
        plyt.addLayout(remap_row)

        plyt.addStretch()
        tabs.addTab(paths_tab, "📁 Paths")

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
            "plays on. \"Same as the music\": they play on the music's player.")
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

    def _test_voice(self):
        """🔈 Test: speak a sample in the voice the dialog shows."""
        if self._announce_test_cb is not None:
            self._announce_test_cb(self._voice_combo.currentData(),
                                   self._heat_chk.isChecked())

    def _setup_analysis_tab(self, all_cb, analyze_cb, backup_restore_cb, build_cb,
                            embed_cb, loudness_cb, maintenance_cb, n_unanalyzed, pd_cb,
                            pd_export_cb, pd_import_cb, silence_cb, summ, tabs, vocals_cb):
        """⚗ Analysis: every analyze/index action, light vs heavy."""
        # ═══ Tab 3: Analysis — every analyze/index action, light vs heavy ═══
        ana_tab = QWidget()
        alyt = QVBoxLayout(ana_tab)
        alyt.setSpacing(8)

        self._add_light_box(alyt, summ, n_unanalyzed, analyze_cb, build_cb,
                            embed_cb, loudness_cb, pd_cb, silence_cb,
                            pd_export_cb, pd_import_cb, backup_restore_cb)

        self._add_heavy_box(alyt, summ, embed_cb, vocals_cb)

        # ── One-click: build every cache on this tab ──
        self._all_btn = QPushButton("🧱  Build ALL caches…")
        self._all_btn.setToolTip(
            "Build everything on this tab in one go for a chosen library, in turn:\n"
            "🎚 librosa → 📊 loudness → 🔇 silences → 🐂 PD highlights → 🧠 MERT →\n"
            "🎼 Chroma. Reuses anything already cached and can be cancelled\n"
            "between/within steps. Read-only; your audio files are never modified.\n"
            "Skips models that aren't installed — and 🎙 Demucs vocals, which are far\n"
            "slower than the rest and stay a deliberate choice.")
        self._all_btn.clicked.connect(self._on_all_clicked)
        self._all_btn.setEnabled(all_cb is not None)
        alyt.addWidget(self._all_btn)

        self._maint_btn = QPushButton("🧹  Clean up database…")
        self._maint_btn.setToolTip(
            "Remove cached rows for music files that no longer exist (features,\n"
            "embeddings, loudness, …) and compact the database file (VACUUM).\n"
            "Slow on a big library; refuses to run when the music drive looks\n"
            "unmounted so cached analysis can't be wiped by accident.")
        self._maint_btn.clicked.connect(self._on_maintenance_clicked)
        self._maint_btn.setEnabled(maintenance_cb is not None)
        alyt.addWidget(self._maint_btn)

        alyt.addStretch()
        tabs.addTab(ana_tab, "⚗ Analysis")

    def _add_light_box(self, alyt, summ, n_unanalyzed, analyze_cb, build_cb,
                       embed_cb, loudness_cb, pd_cb, silence_cb,
                       pd_export_cb, pd_import_cb, backup_restore_cb):
        """⚡ The light analyses: librosa where the build has it, and ffmpeg."""
        from planner.music import embeddings as ae
        # ── Light: librosa/ffmpeg only, available in the LITE build/exe ──
        # A player build ships no librosa at all, so the three librosa entries
        # below are hidden rather than shown disabled — nothing in that .exe
        # can ever enable them. The ffmpeg trio (loudness / PD / silences) is
        # exactly what a venue prepares with and stays.
        no_librosa = planner.config.player_build()
        light_box = QGroupBox(
            "⚡ Light — ffmpeg, works in every install (player build)" if no_librosa
            else "⚡ Light — librosa/ffmpeg, works in every install (lite build)")
        llyt = QVBoxLayout(light_box)

        atxt = (i18n.t("🔬  Analyze audio (timbre) — %d files to do")
                % n_unanalyzed if n_unanalyzed
                else i18n.t("🔬  Re-analyze audio (timbre)  ✓ all cached"))
        self._analyze_btn = QPushButton(atxt)
        self._analyze_btn.setToolTip(
            "Run librosa on the favorites library's MP3 files not yet cached.\n"
            "Required for timbral similarity scoring; when everything is cached\n"
            "a click offers a full re-analysis (e.g. after a tempo-method change).")
        self._analyze_btn.clicked.connect(self._on_analyze_clicked)
        self._analyze_btn.setEnabled(analyze_cb is not None and HAS_LIBROSA)
        llyt.addWidget(self._analyze_btn)
        self._analyze_btn.setVisible(not no_librosa)

        self._build_btn = QPushButton("🌐  Build / refresh librosa audio index (whole repo)…")
        self._build_btn.setToolTip(
            "Scan the whole repository and analyze any files not yet cached, using the\n"
            "fast librosa timbre+rhythm features (the default similarity method).\n"
            "Read-only; runs in the background and can be left to finish.")
        self._build_btn.clicked.connect(self._on_build_clicked)
        self._build_btn.setEnabled(build_cb is not None and HAS_LIBROSA)
        if not HAS_LIBROSA:
            self._build_btn.setText("🌐  Build librosa index (needs librosa)")
        llyt.addWidget(self._build_btn)
        self._build_btn.setVisible(not no_librosa)
        lib_lbl = self._index_label("🎚️  librosa indexed", summ.get("librosa"))
        llyt.addWidget(lib_lbl)
        lib_lbl.setVisible(not no_librosa)

        self._chroma_btn = QPushButton("🎼  Build chroma cover / remix index…")
        self._chroma_btn.setToolTip(
            "Chroma vectors match melody/harmony instead of sound, so the\n"
            "Similar-Tracks window can find remixes & covers of the same tune.\n"
            "librosa-only; reuses anything already cached.")
        self._chroma_btn.clicked.connect(
            lambda: self._on_embed_model_clicked(ae.MODEL_CHROMA))
        self._chroma_btn.setEnabled(embed_cb is not None and ae.chroma_available())
        llyt.addWidget(self._chroma_btn)
        self._chroma_btn.setVisible(not no_librosa)
        chroma_lbl = self._index_label("🎼  Chroma indexed", summ.get("chroma"))
        llyt.addWidget(chroma_lbl)
        chroma_lbl.setVisible(not no_librosa)

        self._add_ffmpeg_rows(llyt, summ, loudness_cb, pd_cb, silence_cb,
                              pd_export_cb, pd_import_cb, backup_restore_cb)
        alyt.addWidget(light_box)

    def _add_ffmpeg_rows(self, llyt, summ, loudness_cb, pd_cb, silence_cb,
                         pd_export_cb, pd_import_cb, backup_restore_cb):
        """📊 The ffmpeg trio, the 🎯 PD marks and the backup, with their coverage."""
        lrow = QHBoxLayout()
        self._loudness_btn = QPushButton("📊  Analyze loudness (R128)…")
        self._loudness_btn.setToolTip(
            "Measure the EBU R128 loudness of every track of the music\n"
            "library (via ffmpeg; already-measured tracks are skipped,\n"
            "results are cached). Enables 🔊 Equalize volume in Playing mode.")
        self._loudness_btn.clicked.connect(self._on_loudness_clicked)
        self._loudness_btn.setEnabled(loudness_cb is not None)
        lrow.addWidget(self._loudness_btn)
        self._pd_btn = QPushButton("🐂  Analyze PD highlights…")
        self._pd_btn.setToolTip(
            "Detect the highlights of every Paso Doble in the music library\n"
            "and store them in the local database, so the highlight stop is\n"
            "armed instantly on playback (already-analyzed tracks are skipped).")
        self._pd_btn.clicked.connect(self._on_pd_clicked)
        self._pd_btn.setEnabled(pd_cb is not None)
        lrow.addWidget(self._pd_btn)
        self._silence_btn = QPushButton("🔇  Probe silences…")
        self._silence_btn.setToolTip(
            "Find the silent stretches of every track of the music library\n"
            "(via ffmpeg; already-probed tracks are skipped, results are\n"
            "cached). Playback probes each new title itself — doing it up\n"
            "front keeps that decode off the disk during a tournament.")
        self._silence_btn.clicked.connect(self._on_silence_clicked)
        self._silence_btn.setEnabled(silence_cb is not None)
        lrow.addWidget(self._silence_btn)
        llyt.addLayout(lrow)
        # 🎯 hand-set highlights are the one thing here no detection gets back —
        # carried to another PC as a file.
        mrow = QHBoxLayout()
        self._pd_export_btn = QPushButton("📤  Export manual PD marks…")
        self._pd_export_btn.setToolTip(
            "Save the Paso Doble highlights you set by hand (🎯) to a file,\n"
            "to take them to another PC. Detected highlights are not included —\n"
            "🐂 finds those again by itself.")
        self._pd_export_btn.clicked.connect(lambda: self._run_and_close(pd_export_cb))
        self._pd_export_btn.setEnabled(pd_export_cb is not None)
        mrow.addWidget(self._pd_export_btn)
        self._pd_import_btn = QPushButton("📥  Import manual PD marks…")
        self._pd_import_btn.setToolTip(
            "Load hand-set Paso Doble highlights exported on another PC.\n"
            "They are matched by the music itself, not by the file path, and\n"
            "replace what this PC has for those tracks.")
        self._pd_import_btn.clicked.connect(lambda: self._run_and_close(pd_import_cb))
        self._pd_import_btn.setEnabled(pd_import_cb is not None)
        mrow.addWidget(self._pd_import_btn)
        llyt.addLayout(mrow)
        # The same marks and the in-app tag edits go into a dated backup at
        # every first start of a day (backups/ next to the database).
        brow = QHBoxLayout()
        self._backup_restore_btn = QPushButton("♻  Restore user data backup…")
        self._backup_restore_btn.setToolTip(
            "Merge a daily backup of your tag edits, hand-set Paso Doble\n"
            "highlights and play log back in. The app keeps one per day for the last 7 days.\n"
            "Everything else in the database is left as it is.")
        self._backup_restore_btn.clicked.connect(lambda: self._run_and_close(backup_restore_cb))
        self._backup_restore_btn.setEnabled(backup_restore_cb is not None)
        brow.addWidget(self._backup_restore_btn)
        brow.addStretch(1)
        llyt.addLayout(brow)
        # …and what each of the three has actually done so far. Without these the
        # tab showed a coverage line for every librosa/AI index and none at all
        # for the ffmpeg ones, so "is my loudness done?" had no answer here.
        llyt.addWidget(self._index_label("📊  Loudness measured", summ.get("loudness")))
        llyt.addWidget(self._index_label("🐂  PD highlights detected", summ.get("pd")))
        llyt.addWidget(self._index_label("🔇  Silences probed", summ.get("silences")))

    def _add_heavy_box(self, alyt, summ, embed_cb, vocals_cb):
        """🐘 The AI analyses, where the build or a dev install has them."""
        from planner.music import embeddings as ae
        from planner.music.vocals import demucs_available
        # ── Heavy: torch AI stack, needs the FULL build / optional installs ──
        # In a frozen .exe (planner.build_flavor() != "dev") a missing backend
        # can't be pip-installed, so its controls are hidden entirely; a dev
        # install keeps them visible with the "– not installed" hint instead.
        dev = planner.config.build_flavor() == "dev"
        have_mert = ae.mert_available()
        have_demucs = demucs_available()
        self._embed_combo = None
        self._embed_btn = None
        self._vocals_btn = None
        if dev or have_mert or have_demucs:
            heavy_box = QGroupBox("🐘 Heavy — AI models, needs the FULL build (or the "
                                  "requirements-full.txt extras)")
            hlyt = QVBoxLayout(heavy_box)

            if dev or have_mert:
                erow = QHBoxLayout()
                self._embed_combo = QComboBox()
                if dev or have_mert:
                    mert = i18n.t("🧠  MERT 'sounds-alike' index")
                    if not have_mert:
                        mert += i18n.t("  – not installed")
                    self._embed_combo.addItem(mert, ae.MODEL_MERT)
                erow.addWidget(self._embed_combo, 1)
                self._embed_btn = QPushButton("Build / refresh…")
                self._embed_btn.setToolTip(
                    "Compute the selected similarity index over the library (global repo\n"
                    "when global search is on, else the favorites library). Reuses anything\n"
                    "already cached; only missing vectors are added.")
                self._embed_btn.clicked.connect(self._on_embed_clicked)
                self._embed_btn.setEnabled(embed_cb is not None)
                erow.addWidget(self._embed_btn)
                hlyt.addLayout(erow)
                if dev or have_mert:
                    hlyt.addWidget(self._index_label("🧠  MERT indexed", summ.get("mert")))

            if dev or have_demucs:
                vtxt = i18n.t("🎙️  Analyze vocals (Demucs)…")
                if not have_demucs:
                    vtxt += i18n.t("  – not installed")
                self._vocals_btn = QPushButton(vtxt)
                self._vocals_btn.setToolTip(
                    "Measure each track's vocal share by actually separating the vocals\n"
                    "from the music (Demucs source separation) — far more reliable than\n"
                    "the tag/filename heuristics for the Vocal/Instrumental filter.\n"
                    "~7 s per track, cached; already-measured tracks are skipped.")
                self._vocals_btn.clicked.connect(self._on_vocals_clicked)
                self._vocals_btn.setEnabled(vocals_cb is not None)
                hlyt.addWidget(self._vocals_btn)
            alyt.addWidget(heavy_box)

    def _setup_play_sets_tab(self, settings, tabs):
        """🎛 Play sets: what the two buttons on the ▶ panel apply."""
        # ═══ Tab 4: Play sets — what the two buttons on the ▶ panel apply ═══
        sets_tab = QWidget()
        tlyt = QVBoxLayout(sets_tab)
        tlyt.setSpacing(8)
        tlyt.addWidget(QLabel(
            "<b>🎛 Play sets</b> — the two buttons on the ▶ Playing panel put "
            "the controls on these values in one press:"))

        self._set_widgets = {}
        for which, caption, blurb in (
                ("tournament", "🏆  Tournament set",
                 "The values a heat is run with — pressed to get back to them "
                 "after a party list has pulled the panel somewhere else."),
                ("party", "🎉  Party set",
                 "Applied by itself as soon as you play from the 🤸 Practice / "
                 "party list, and switched back when a tournament deck takes over.")):
            self._add_play_set_box(tlyt, settings, which, caption, blurb)

        pd_note = QLabel(
            "🐂 Each set carries its own Paso Doble values. Under 🏆 the "
            "highlight stop is <i>off</i> by default: the detection is not good "
            "enough yet to cut a competition Paso Doble on, and a heat stopped "
            "in the wrong bar is danced twice. Under 🎉 it stops after the 2nd "
            "highlight and waits 3 s, so the couples can take their position.")
        pd_note.setWordWrap(True)
        pd_note.setStyleSheet("color:#666; font-size:11px;")
        tlyt.addWidget(pd_note)

        self._add_tso_band_grid(tlyt, settings)

        tlyt.addStretch()
        sets_idx = tabs.addTab(sets_tab, "🎛 Play sets")
        return sets_idx

    def _add_play_set_box(self, tlyt, settings, which, caption, blurb):
        """🏆/🎉 One play set's box: length, fades, crossfade and switches."""
        cur = dict(play_set_of(settings, which), tso=tso_of(settings, which))
        box = QGroupBox(caption)
        blyt = QVBoxLayout(box)
        hint = QLabel(blurb)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#777; font-size:11px;")
        blyt.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("Play length:"))
        length = QComboBox()
        length.addItem("full — to each title's own end", 0)
        for s in range(_LEN_STEP, _LEN_MAX + 1, _LEN_STEP):
            length.addItem(f"{s // 60}:{s % 60:02d}", s)
        # Typable as well as pickable — the rungs are 15 s apart and a heat
        # that wants 1:37 has to be able to say so here too, not only on the
        # panel. NoInsert: a typed length is read back from the text, it
        # must not grow the list.
        length.setEditable(True)
        length.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        length.setToolTip("Pick a length or type one: m:ss, seconds, "
                          "or 'full'")
        idx = length.findData(cur["secs"])
        if idx >= 0:
            length.setCurrentIndex(idx)
        else:
            # An off-ladder length typed in earlier: show it as it is, or
            # reopening the dialog would silently snap it to a rung.
            length.setEditText(
                f"{cur['secs'] // 60}:{cur['secs'] % 60:02d}")
        row.addWidget(length)
        row.addSpacing(12)
        row.addWidget(QLabel("Fade-out:"))
        fade = QDoubleSpinBox()
        fade.setRange(0, 10)
        fade.setDecimals(1)
        fade.setSingleStep(0.5)
        fade.setSuffix(" s")
        fade.setValue(float(cur["fade"]))
        fade.setToolTip("How long the volume takes to ramp down to 0 when\n"
                        "the play length cuts a title — half-second steps")
        row.addWidget(fade)
        fade_inside = QCheckBox("within the length")
        fade_inside.setChecked(bool(cur["fade_inside"]))
        fade_inside.setToolTip(
            "Ticked: the fade-out ends at the play length.\n"
            "Unticked: the title plays its full length, then fades out.")
        row.addWidget(fade_inside)
        row.addSpacing(12)
        xfade_on, xfade, curves = self._add_crossfade_controls(row, cur)
        row.addStretch(1)
        blyt.addLayout(row)

        boxes = self._add_play_set_checks(blyt, cur)
        boxes["fade_inside"] = fade_inside
        self._set_widgets[which] = {"length": length, "fade": fade,
                                    "xfade": xfade, "xfade_on": xfade_on,
                                    "xfade_curve": curves,
                                    "boxes": boxes, "secs": cur["secs"]}
        self._set_widgets[which]["pd"] = self._add_pd_row(blyt, settings, which)
        if which == "tournament":
            self._add_dance_len_grid(blyt, settings)
        tlyt.addWidget(box)

    def _add_pd_row(self, blyt, settings, which):
        """🐂 One set's Paso Doble: the highlight stop, which highlight, and
        the wait after the call."""
        pd = pd_of(settings, which)
        row = QHBoxLayout()
        stop = QCheckBox("🐂  Paso Doble: stop after highlight")
        stop.setChecked(pd["pd_stop"])
        if which == "tournament":
            stop.setToolTip("Shut the music off at the chosen highlight instead of\n"
                            "the play length. Off by default: a highlight detected\n"
                            "in the wrong bar cuts the heat short.")
        else:
            stop.setToolTip("Shut the music off at the chosen highlight instead of\n"
                            "the play length. On by default: at a party the\n"
                            "Paso Doble ends on its 2nd highlight.")
        row.addWidget(stop)
        n = QSpinBox()
        n.setRange(1, 3)
        n.setValue(pd["pd_n"])
        n.setToolTip("Which highlight ends the Paso Doble — usually the 2nd,\n"
                     "in rare cases the 3rd.")
        row.addWidget(n)
        row.addSpacing(12)
        row.addWidget(QLabel("Start after:"))
        delay = QSpinBox()
        delay.setRange(0, 60)
        delay.setSuffix(" s")
        delay.setValue(pd["pd_delay"])
        if which == "tournament":
            delay.setToolTip("Hold a Paso Doble back this long before the music\n"
                             "starts. 0 s = at once: at a competition the couples\n"
                             "stand before the music, the chairman's call is the wait.")
        else:
            delay.setToolTip("Hold a Paso Doble back this long before the music\n"
                             "starts, so the couples can take their position.")
        row.addWidget(delay)
        stop.toggled.connect(n.setEnabled)
        n.setEnabled(stop.isChecked())
        row.addStretch(1)
        blyt.addLayout(row)
        return stop, n, delay

    def _add_crossfade_controls(self, row, cur):
        """🔀 A play set's crossfade switch, seconds, curve and preview."""
        # 🔀 Its own switch, as on the panel: off keeps the seconds.
        xfade_on = QCheckBox("🔀  Crossfade:")
        xfade_on.setChecked(bool(cur["xfade_on"]))
        xfade_on.setToolTip("The next title comes in under the end of the\n"
                            "last one — only where the list walks on with\n"
                            "no pause. Off: one ends, the next starts.")
        row.addWidget(xfade_on)
        xfade = QDoubleSpinBox()
        xfade.setRange(XFADE_MIN_SECS, XFADE_MAX_SECS)
        xfade.setDecimals(1)
        xfade.setSingleStep(0.5)
        xfade.setSuffix(" s")
        xfade.setValue(float(cur["xfade"]))
        xfade.setToolTip(
            "How long the two titles play together — half-second steps")
        row.addWidget(xfade)
        curves = CrossfadeCurveButton()
        curves.set_curve(str(cur["xfade_curve"]))
        row.addWidget(curves)
        xfade_view = CrossfadeView()
        row.addWidget(xfade_view)

        def sync_xfade(*_, on=xfade_on, spin=xfade, curves=curves,
                       view=xfade_view):
            spin.setEnabled(on.isChecked())
            curves.setEnabled(on.isChecked())
            view.set_curve(curves.curve())
            view.set_secs(spin.value() if on.isChecked() else 0.0)
        xfade_on.toggled.connect(sync_xfade)
        xfade.valueChanged.connect(sync_xfade)
        curves.curveChanged.connect(sync_xfade)
        sync_xfade()
        return xfade_on, xfade, curves

    def _add_play_set_checks(self, blyt, cur):
        """A play set's switches (⏭ ⏸ 🔈 🔊 ▶️ 🎚), keyed by setting."""
        boxes = {}
        for key, label, tip in (
                ("advance", "⏭  Auto-advance to next song", ""),
                ("pause_off", "⏸  No pause between songs", ""),
                ("announce", "🔈  Announce next dance", ""),
                ("loudness", "🔊  Equalize volume (R128)", ""),
                ("dblclick", "▶️  Double-click starts the title",
                 "On: a double-click in a deck plays the title at once.\n"
                 "Off: it is only cued on the player (loaded, shown,\n"
                 "silent) and ⏯ starts it — the heat begins when the\n"
                 "couples stand."),
                ("tso", "🎚  TSO pitch to the heat tempo",
                 "Pitch every title to the mean tempo of its dance in the\n"
                 "current round, kept inside the TSO range — what a heat is\n"
                 "danced to. Wrong for a party, where the next song is a\n"
                 "different dance at whatever tempo it was recorded at.")):
            chk = QCheckBox(label)
            chk.setChecked(bool(cur[key]))
            if tip:
                chk.setToolTip(tip)
            blyt.addWidget(chk)
            boxes[key] = chk
        return boxes

    def _add_dance_len_grid(self, blyt, settings):
        """⏱ The 🏆 set's own play length per dance — a heat is timed per
        dance, a Viennese Waltz shorter than a Waltz."""
        lbl = QLabel(
            "<b>⏱ Per dance</b> — a dance given a length of its own is cut "
            "there instead, as long as a list stands on this set. The ▶ "
            "Playing panel names the dance under its length.")
        lbl.setWordWrap(True)
        blyt.addWidget(lbl)
        stored = dance_secs_of(settings)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        self._dance_len_combos: dict[str, tuple[QComboBox, int | None]] = {}
        dances = [d for d in ("LW", "TG", "WW", "SF", "QS",
                              "SA", "CC", "RB", "PD", "JI")
                  if d in TEMPO_RANGES]
        for i, dance in enumerate(dances):
            combo = QComboBox()
            combo.addItem("— the set's length", None)
            combo.addItem("full", 0)
            for s in range(_LEN_STEP, _LEN_MAX + 1, _LEN_STEP):
                combo.addItem(f"{s // 60}:{s % 60:02d}", s)
            # Typable like the set's own length: 1:37 is not a rung.
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            combo.setToolTip("Pick a length or type one: m:ss, seconds, "
                             "or 'full'")
            secs = stored.get(dance)
            idx = combo.findData(secs) if secs is not None else 0
            if idx >= 0:
                combo.setCurrentIndex(idx)
            elif secs is not None:
                combo.setEditText(f"{secs // 60}:{secs % 60:02d}")
            self._dance_len_combos[dance] = (combo, secs)
            row, col = i % 5, (i // 5) * 2
            grid.addWidget(QLabel(f"{dance_name(dance, dance)}:"), row, col)
            grid.addWidget(combo, row, col + 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        blyt.addLayout(grid)

    @staticmethod
    def _dance_len_secs(combo: QComboBox, opened: int | None) -> int | None:
        """One dance's length in the grid: None = the set's, 0 = full. An item
        picked or its caption typed comes first — "— the set's length" is
        not something the parser takes — then a typed length; anything else
        keeps the value the dialog opened on."""
        idx = combo.findText(combo.currentText().strip())
        if idx >= 0:
            return combo.itemData(idx)
        secs = parse_play_length(combo.currentText())
        return secs if secs is not None else opened

    def _add_tso_band_grid(self, tlyt, settings):
        """🎚 Which takt of its TSO band each dance is pitched to."""
        # ── 🎚 Where in its TSO band each dance is pitched ──
        tlyt.addWidget(_hsep())
        band_lbl = QLabel(
            "<b>🎚 TSO pitch target</b> — which takt the 🎚 button pitches a "
            "heat to. <i>Middle of the round</i> puts the round on one takt: "
            "the takt most of its titles are on where a step of one gets the "
            "rest there cheaply (T30+T31+T31 Cha-Chas → 31), the middle of "
            "its takte where it does not (T24+T25+T25 Rumbas → 24.5, "
            "T50+T52+T52 Quicksteps → 51). Nothing moves more than a takt. A fixed takt "
            "puts every title of that dance on the same tempo instead — worth "
            "setting on the slow dances, where one takt out of 24 is twice "
            "the pitch shift one takt out of 50 is.")
        band_lbl.setWordWrap(True)
        tlyt.addWidget(band_lbl)

        stored_bands = settings.get("tso_band") or {}
        band_grid = QGridLayout()
        band_grid.setHorizontalSpacing(14)
        self._band_combos: dict[str, QComboBox] = {}
        dances = [d for d in ("LW", "TG", "WW", "SF", "QS",
                              "SA", "CC", "RB", "PD", "JI")
                  if d in TEMPO_RANGES]
        for i, dance in enumerate(dances):
            lo, hi = TEMPO_RANGES[dance]["S"]
            combo = QComboBox()
            combo.addItem("Middle of the round", "mean")
            combo.addItem(i18n.t("Lower — T%s") % f"{lo:g}", "lower")
            combo.addItem(i18n.t("Middle — T%s") % f"{(lo + hi) / 2:g}",
                          "middle")
            combo.addItem(i18n.t("Upper — T%s") % f"{hi:g}", "upper")
            idx = combo.findData(str(stored_bands.get(dance, "mean")))
            combo.setCurrentIndex(max(0, idx))
            self._band_combos[dance] = combo
            row, col = i % 5, (i // 5) * 2
            band_grid.addWidget(
                QLabel(f"{dance_name(dance, dance)}:"), row, col)
            band_grid.addWidget(combo, row, col + 1)
        band_grid.setColumnStretch(1, 1)
        band_grid.setColumnStretch(3, 1)
        tlyt.addLayout(band_grid)

    def _setup_checks_tab(self, gaps_cb, settings, tabs):
        """🎵 Checks: the Check-music thresholds."""
        # ═══ Tab 5: Checks — 🎵 Check-music thresholds ═══
        chk_tab = QWidget()
        klyt = QVBoxLayout(chk_tab)
        klyt.setSpacing(6)
        klyt.addWidget(QLabel(
            "<b>🎵 Check music</b> — thresholds used by the tournament checks "
            "(open decks and dragged-in files):"))

        def spin_row(label: str, edit, hint: str):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(edit)
            row.addStretch(1)
            klyt.addLayout(row)
            h = QLabel(hint)
            h.setWordWrap(True)
            h.setStyleSheet("color:#777; font-size:11px; margin-left:2px;")
            klyt.addWidget(h)

        def mmss_edit(secs: int, lo: int, hi: int) -> QTimeEdit:
            e = QTimeEdit()
            e.setDisplayFormat("m:ss")
            e.setTimeRange(QTime(0, lo // 60, lo % 60), QTime(0, hi // 60, hi % 60))
            e.setTime(QTime(0, secs // 60, secs % 60))
            return e

        self._min_time = mmss_edit(
            int(settings.get("check_min_play_secs", 105)), 30, 600)
        spin_row("⏱  Too short — at or below:", self._min_time,
                 "The cut must cover the 1:30–1:45 TSO play time; default 1:45.")

        self._max_time = mmss_edit(
            int(settings.get("check_max_play_secs", 240)), 60, 900)
        spin_row("⏳  Too long — above:", self._max_time,
                 "Only flagged when the ⏳ checkbox in the Music-check window is "
                 "on (Practice playlists); default 4:00.")

        self._dev_spin = QSpinBox()
        self._dev_spin.setRange(1, 50)
        self._dev_spin.setSuffix(" %")
        self._dev_spin.setValue(int(settings.get("check_tempo_dev_pct", 10)))
        spin_row("⚡  Tempo mismatch — deviation above:", self._dev_spin,
                 "Measured tempo vs the filename label (detector ×2, ×3, ×1.5 … "
                 "slips are excused first); default 10 %.")

        self._noise_spin = QSpinBox()
        self._noise_spin.setRange(-90, -20)
        self._noise_spin.setSuffix(" dB")
        self._noise_spin.setValue(int(settings.get("check_noise_floor_db", -50)))
        spin_row("🔇  Hiss — noise floor above:", self._noise_spin,
                 "How quiet a track must get somewhere. A clean file reaches its "
                 "lead-in silence, a tape rip never gets below its own hiss; "
                 "default −50 dB. Only flagged when the 🔇 checkbox in the "
                 "Music-check window is on.")

        klyt.addWidget(_hsep())
        self._gaps_btn = QPushButton("📊  Library gaps…")
        self._gaps_btn.setToolTip(
            "Library gap dashboard: per dance × class — pool size, tournament-\n"
            "tempo compliance, proven/fresh split and staleness. Thin pools\n"
            "are marked red.")
        self._gaps_btn.setEnabled(gaps_cb is not None)
        self._gaps_btn.clicked.connect(lambda: self._gaps_cb and self._gaps_cb())
        klyt.addWidget(self._gaps_btn)

        klyt.addStretch()
        chk_idx = tabs.addTab(chk_tab, "🎵 Checks")
        return chk_idx

    def _setup_venue_tab(self, tabs):
        """📦 Venue pack: the whole desk — settings, decks, cartwall and keys,
        the music if wanted — home PC to venue laptop in one file."""
        venue_tab = QWidget()
        vlyt = QVBoxLayout(venue_tab)
        intro = QLabel(
            "Take this desk to another PC in one file: the settings, every deck "
            "and wishlist, the 🎛 cartwall with its pads and keys — and, if you "
            "want, the music they use. Folder settings stay with each PC.")
        intro.setWordWrap(True)
        vlyt.addWidget(intro)
        vrow = QHBoxLayout()
        self._venue_export_btn = QPushButton("📦  Export venue pack…")
        self._venue_export_btn.setToolTip(
            "Save this desk to one file to take to another PC: the settings,\n"
            "every deck and wishlist, the 🎛 cartwall with its pads and keys —\n"
            "and, if you want, the music they use. Folder settings stay with\n"
            "each PC.")
        self._venue_export_btn.clicked.connect(
            lambda: self._run_and_close(self._venue_export_cb))
        self._venue_export_btn.setEnabled(self._venue_export_cb is not None)
        vrow.addWidget(self._venue_export_btn)
        self._venue_import_btn = QPushButton("📥  Import venue pack…")
        self._venue_import_btn.setToolTip(
            "Load a venue pack made on another PC. It replaces this PC's\n"
            "settings, decks and cartwall at the next start; what it replaces\n"
            "is kept in a before-venue-import folder next to them.")
        self._venue_import_btn.clicked.connect(
            lambda: self._run_and_close(self._venue_import_cb))
        self._venue_import_btn.setEnabled(self._venue_import_cb is not None)
        vrow.addWidget(self._venue_import_btn)
        vrow.addStretch(1)
        vlyt.addLayout(vrow)
        vlyt.addStretch()
        return tabs.addTab(venue_tab, "📦 Venue pack")

    def _setup_tab_visibility(self, chk_idx, lyt, sets_idx, tabs):
        """Tabs that follow the app mode, and the OK/Cancel buttons."""
        # A player-only install never runs the planning checks — and the tab
        # follows the combo above right away, so the dialog stays consistent
        # with what the user just picked.
        # …and the mirror image: a planner-only install has no Playing panel, so
        # the two buttons the play sets configure are nowhere to be pressed.
        def _sync_checks_tab():
            mode = self._app_mode_combo.currentData()
            tabs.setTabVisible(chk_idx, mode != "player")
            tabs.setTabVisible(sets_idx, mode != "planner")
        _sync_checks_tab()
        self._app_mode_combo.currentIndexChanged.connect(_sync_checks_tab)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lyt.addWidget(bb)

    @staticmethod
    def _mmss_secs(edit: QTimeEdit) -> int:
        """Total seconds of an m:ss QTimeEdit."""
        t = edit.time()
        return t.minute() * 60 + t.second()

    @staticmethod
    def _index_label(prefix: str, coverage) -> QLabel:
        """Small grey caption stating which library is indexed for this model."""
        text = coverage if coverage else "—"
        lbl = QLabel(f"{i18n.t(prefix)}:  {text}")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#777; font-size:11px; margin-left:2px;")
        return lbl

    def _path_row(self, edit: QLineEdit) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(edit, stretch=1)
        btn = QPushButton("Browse…")
        btn.clicked.connect(lambda: self._browse(edit))
        row.addWidget(btn)
        return row

    def _browse(self, edit: QLineEdit):
        start = edit.text().strip() or music_browse_dir()
        chosen = QFileDialog.getExistingDirectory(self, "Select folder", start)
        if chosen:
            edit.setText(chosen)

    def _add_remap_folder(self):
        """Append a browsed folder to the search-folder list (they are a list —
        picking one must not replace the one already there)."""
        chosen = QFileDialog.getExistingDirectory(
            self, "Add a folder to search for tracks", music_browse_dir())
        if not chosen:
            return
        lines = parse_remap_paths(self._remap_edit.toPlainText())
        lines.append(chosen)
        self._remap_edit.setPlainText("\n".join(parse_remap_paths(lines)))

    def _on_build_clicked(self):
        if self._build_cb:
            # Close the (modal) dialog first so the build's progress prompts aren't
            # blocked, then kick off the background scan/analyze with current values.
            vals = self.values()
            self.accept()
            self._build_cb(vals)

    def _on_embed_clicked(self):
        if self._embed_cb and self._embed_combo is not None:
            vals = self.values()
            model = self._embed_combo.currentData()
            self.accept()
            self._embed_cb(vals, model)

    def _on_all_clicked(self):
        if self._all_cb:
            vals = self.values()
            self.accept()
            self._all_cb(vals)

    def _on_maintenance_clicked(self):
        if self._maintenance_cb:
            self.accept()
            self._maintenance_cb()

    def _on_relearn_clicked(self):
        if self._relearn_cb:
            self.accept()
            self._relearn_cb()

    def _on_embed_model_clicked(self, model: str):
        if self._embed_cb:
            vals = self.values()
            self.accept()
            self._embed_cb(vals, model)

    def _on_analyze_clicked(self):
        if self._analyze_cb:
            self.accept()
            self._analyze_cb()

    def _on_loudness_clicked(self):
        if self._loudness_cb:
            self.accept()
            self._loudness_cb()

    def _on_silence_clicked(self):
        if self._silence_cb:
            self.accept()
            self._silence_cb()

    def _on_pd_clicked(self):
        if self._pd_cb:
            self.accept()
            self._pd_cb()

    def _run_and_close(self, cb):
        if cb:
            self.accept()
            cb()

    def _on_vocals_clicked(self):
        if self._vocals_cb:
            self.accept()
            self._vocals_cb()

    def values(self) -> dict:
        # Start from the settings handed in: _open_settings saves this dict as a
        # WHOLE, so keys persisted by other panels (play settings, loudness
        # toggle, …) must ride along instead of being dropped.
        vals = dict(self._settings_in)
        vals.update({
            "app_mode":      self._app_mode_combo.currentData(),
            "library_dir":   self._lib_edit.text().strip(),
            "global_dir":    self._glob_edit.text().strip(),
            "save_dir":      self._save_edit.text().strip(),
            "m3u_format": self._m3u_format_combo.currentData(),
            "playlist_dir":  self._pl_edit.text().strip(),
            "reference_path": self._ref_edit.text().strip(),
            "remap_paths": parse_remap_paths(self._remap_edit.toPlainText()),
            "global_search": self._global_chk.isChecked(),
            "exclude_no_class": self._exclude_no_class_chk.isChecked(),
            "audio_outputs": self._output_values(),
            "clock_time_only": self._clock_time_only_chk.isChecked(),
            "preview_player": self._preview_chk.isChecked(),
            "show_artwork": self._artwork_chk.isChecked(),
            "show_waveform": self._waveform_chk.isChecked(),
            "player_layout": self._player_layout_combo.currentData(),
            "announce_voice": self._voice_combo.currentData(),
            "announce_heat": self._heat_chk.isChecked(),
            "announce_wait": self._lead_wait_radio.isChecked(),
            "media_backend": self._backend_combo.currentData(),
            "theme": self.selected_theme(),
            "presenter_theme": self.presenter_theme(),
            "accent_color": self._accent,
            "language": self._language_combo.currentData(),
            "german_dance_terms": self._german_terms_chk.isChecked(),
            "release_audio_idle": self._release_audio_chk.isChecked(),
            "mute_system_sounds": self._mute_sys_chk.isChecked(),
            **({"error_reports": self._error_reports_chk.isChecked()}
               if self._error_reports_chk is not None else {}),
            update_check.SETTING: self._update_check_chk.isChecked(),
            "check_min_play_secs": self._mmss_secs(self._min_time),
            "check_max_play_secs": self._mmss_secs(self._max_time),
            "check_tempo_dev_pct": self._dev_spin.value(),
            "check_noise_floor_db": self._noise_spin.value(),
        })
        # Only the dances that are NOT on the heat mean: the default is what
        # the button does without the setting, and writing ten "mean" entries
        # would freeze today's default into the settings file.
        vals["tso_band"] = {d: c.currentData()
                            for d, c in self._band_combos.items()
                            if c.currentData() != "mean"}
        # Only the dances given a length of their own: the rest run on the set's.
        lens = {d: self._dance_len_secs(c, opened)
                for d, (c, opened) in self._dance_len_combos.items()}
        vals[DANCE_SECS_KEY] = {d: s for d, s in lens.items() if s is not None}
        for which, w in self._set_widgets.items():
            vals[f"{which}_set"] = dict(
                {k: chk.isChecked() for k, chk in w["boxes"].items()},
                secs=self._play_set_secs(w),
                fade=w["fade"].value(),
                xfade=w["xfade"].value(),
                xfade_on=w["xfade_on"].isChecked(),
                xfade_curve=w["xfade_curve"].curve())
            if "pd" in w:
                stop, n, delay = w["pd"]
                vals[f"{which}_set"].update(pd_stop=stop.isChecked(),
                                            pd_n=n.value(), pd_delay=delay.value())
        return vals

    @staticmethod
    def _play_set_secs(w) -> int:
        """The play length of one set: a rung picked, or a length typed in.

        The text is asked first because a typed one leaves the combo on no
        index at all; the picked item's data covers "full", whose caption
        spells out more than the parser will take."""
        secs = parse_play_length(w["length"].currentText())
        if secs is not None:
            return secs
        data = w["length"].currentData()
        # Neither parseable nor a rung: something was typed that is not a
        # length, and the value the dialog opened on stands.
        return int(data) if data is not None else int(w["secs"])
