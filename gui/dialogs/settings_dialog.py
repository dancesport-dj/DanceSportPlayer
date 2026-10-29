"""The settings dialog: library paths and global search, the analyses and
index builds, playback, the look and the app mode, one tab each.

Split out of gui/dialogs/__init__.py, which keeps the settings persistence
(load_settings, the path fallbacks, the choice tables) this dialog reads.
The 🎨 Look tab is a mixin of its own, in gui/dialogs/settings_look.py,
and so are 🔊 Sound & player and 🎛 Play sets, in settings_sound.py and
settings_play_sets.py.
"""
import logging
import os

from PySide6.QtCore import (
    Qt,
    QTime,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

import planner.config
from gui.dialogs import (
    APP_MODE_CHOICES,
    M3U_FORMAT_CHOICES,
    app_mode_of,
)
from gui.dialogs.settings_cartwall import CartwallTabMixin
from gui.dialogs.settings_look import LookTabMixin
from gui.dialogs.settings_play_sets import PlaySetsTabMixin
from gui.dialogs.settings_sound import SoundTabMixin
from planner import i18n
from planner.models import ceremony_words_of
from planner.music.analysis import HAS_LIBROSA
from planner.music.paths import parse_remap_paths
from shared import error_reports, update_check
from shared.audio.audio_files import (
    music_browse_dir,
)
from shared.widgets import (
    hsep,
)

log = logging.getLogger("dancesport.gui")


class SettingsDialog(LookTabMixin, SoundTabMixin, CartwallTabMixin,
                     PlaySetsTabMixin, QDialog):
    """Configure the library paths + global search (tab 1) and run every
    analysis / index build, grouped light vs heavy (tab 2)."""

    # The tab the last Settings closed on, for this run of the app only.
    _last_tab: int | None = None

    def __init__(self, settings: dict, parent=None, build_cb=None, embed_cb=None,
                 index_summary=None, all_cb=None, maintenance_cb=None, relearn_cb=None,
                 rescan_cb=None,
                 analyze_cb=None, loudness_cb=None, silence_cb=None, pd_cb=None,
                 vocals_cb=None, gaps_cb=None, n_unanalyzed: int = 0,
                 pd_export_cb=None, pd_import_cb=None, backup_restore_cb=None,
                 venue_export_cb=None, venue_import_cb=None, remote_cb=None,
                 remote_running=None, remote_stop_cb=None, remote_changed=None,
                 guests_cb=None, controller_cb=None, desk_keys_cb=None,
                 announce_test_cb=None, open_sound=False, reset_cb=None,
                 open_cartwall=False):
        super().__init__(parent)
        self.setWindowTitle("⚙  Settings")
        self.setMinimumWidth(560)
        self._settings_in = dict(settings)
        self._gaps_cb = gaps_cb
        self._build_cb = build_cb
        self._embed_cb = embed_cb
        self._all_cb = all_cb
        self._maintenance_cb = maintenance_cb
        self._reset_cb = reset_cb
        self._relearn_cb = relearn_cb
        self._rescan_cb = rescan_cb
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
        cart_idx = self._setup_cartwall_tab(settings, tabs)
        self._setup_analysis_tab(
            all_cb, analyze_cb, backup_restore_cb, build_cb, embed_cb, loudness_cb,
            maintenance_cb, n_unanalyzed, pd_cb, pd_export_cb, pd_import_cb, silence_cb,
            summ, tabs, vocals_cb)
        sets_idx = self._setup_play_sets_tab(settings, tabs)
        chk_idx = self._setup_checks_tab(gaps_cb, settings, tabs)
        self._setup_venue_tab(tabs)
        self._setup_tab_visibility(chk_idx, lyt, sets_idx, cart_idx, tabs)
        self._scroll_the_pages(tabs)
        self._tabs = tabs
        last = SettingsDialog._last_tab
        # The tab the last Settings closed on — unless the app mode hides it.
        if last is not None and tabs.isTabVisible(last):
            tabs.setCurrentIndex(last)
        if open_sound:      # 🚦 Check → choose outputs: they are picked here
            tabs.setCurrentIndex(sound_idx)
        if open_cartwall:   # 🎛 the pad's right-click → the wall's settings
            tabs.setCurrentIndex(cart_idx)

    def done(self, result):
        """OK, Cancel or ✕: the next Settings of this session opens on the
        tab this one closes on."""
        SettingsDialog._last_tab = self._tabs.currentIndex()
        super().done(result)

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
        mode_sep = hsep()
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
        self._add_library_path_rows(relearn_cb, settings, plyt)
        self._add_fix_path_rows(settings, plyt)
        plyt.addStretch()
        tabs.addTab(paths_tab, "📁 Paths")

    def _add_library_path_rows(self, relearn_cb, settings, plyt):
        """The folders the app reads and writes, and the playlist file format."""
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
        self._rescan_btn = QPushButton("🔄  Scan repository for new titles")
        self._rescan_btn.setToolTip(
            "Walk the whole music repository folder and read the tags of new and\n"
            "changed files, so 🌐 Whole library in the library pane and the global\n"
            "search know every title. No audio analysis; the scan runs in the\n"
            "background, its progress in the status bar.")
        self._rescan_btn.clicked.connect(self._on_rescan_clicked)
        self._rescan_btn.setEnabled(self._rescan_cb is not None)
        plyt.addWidget(self._rescan_btn)

        # ── Save-as default folder ──
        plyt.addWidget(QLabel(
            "<b>Save-as folder</b> — where 'Save as M3U…' starts (e.g. D:\\Playlists):"))
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

    def _add_fix_path_rows(self, settings, plyt):
        """Where 🧭 Fix paths looks for a moved track, and the excluded folders."""
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

        # ── Excluded folders (both libraries) ──
        plyt.addWidget(QLabel(
            "<b>Excluded folders</b> — titles in these folders and below stay out "
            "of the library, one folder per line:"))
        self._hidden_edit = QPlainTextEdit(
            "\n".join(parse_remap_paths(settings.get("hidden_folders"))))
        self._hidden_edit.setPlaceholderText("F:\\my music\\Party\nF:\\my music\\Hörbücher")  # i18n: data
        self._hidden_edit.setFixedHeight(66)
        self._hidden_edit.setToolTip(
            "Left out of ⭐ Favorites and 🌐 Whole library alike: not shown, not\n"
            "searched, never suggested. Nothing on disk changes, and the tags\n"
            "read so far stay cached, so a folder taken off the list is back\n"
            "after a restart.")
        hidden_row = QHBoxLayout()
        hidden_row.addWidget(self._hidden_edit, stretch=1)
        hidden_add = QPushButton("Add…")
        hidden_add.clicked.connect(self._add_hidden_folder)
        hidden_col = QVBoxLayout()
        hidden_col.addWidget(hidden_add)
        hidden_col.addStretch(1)
        hidden_row.addLayout(hidden_col)
        plyt.addLayout(hidden_row)

        # ── 🏅 Entrance and award music (a library category) ──
        plyt.addWidget(QLabel(
            "<b>🏅 Background: entrance & awards</b> — a title with one of these "
            "words in its file or folder name, title or comment, comma-separated:"))
        self._ceremony_words_edit = QLineEdit(", ".join(ceremony_words_of(settings)))
        self._ceremony_words_edit.setToolTip(
            "Upper or lower case does not matter, and a part of a word is\n"
            "enough: 'Award' also finds '(Background Award)'. Shown under\n"
            "🏅 in the library's category filter and kept out of generated\n"
            "playlists. Leave it empty to go by the folders below only.")
        plyt.addWidget(self._ceremony_words_edit)
        plyt.addWidget(QLabel(
            "…and every title in these folders and below, one folder per line:"))
        self._ceremony_edit = QPlainTextEdit(
            "\n".join(parse_remap_paths(settings.get("ceremony_folders"))))
        self._ceremony_edit.setPlaceholderText("F:\\my music\\Einmarsch")  # i18n: data
        self._ceremony_edit.setFixedHeight(66)
        ceremony_row = QHBoxLayout()
        ceremony_row.addWidget(self._ceremony_edit, stretch=1)
        ceremony_add = QPushButton("Add…")
        ceremony_add.clicked.connect(self._add_ceremony_folder)
        ceremony_col = QVBoxLayout()
        ceremony_col.addWidget(ceremony_add)
        ceremony_col.addStretch(1)
        ceremony_row.addLayout(ceremony_col)
        plyt.addLayout(ceremony_row)

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

        self._reset_btn = QPushButton("🗑  Reset database…")
        self._reset_btn.setToolTip(
            "Empty chosen parts of the database: the tags read from the files,\n"
            "the audio analysis, your own data. A dialog asks which; your own\n"
            "data is backed up first, and the app restarts afterwards.")
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        self._reset_btn.setEnabled(self._reset_cb is not None)
        alyt.addWidget(self._reset_btn)

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
        # every first start of a day: backups/ next to the database, or the
        # folder set here (one subfolder per PC, so a shared Dropbox folder
        # keeps every PC's own).
        llyt.addWidget(QLabel(
            "<b>Backup folder</b> — where the daily backup of your own data goes"
            " (e.g. a Dropbox folder). Empty: next to the database."))
        self._backup_edit = QLineEdit(self._settings_in.get("backup_dir", ""))
        llyt.addLayout(self._path_row(self._backup_edit))
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

        klyt.addWidget(hsep())
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

    def _setup_tab_visibility(self, chk_idx, lyt, sets_idx, cart_idx, tabs):
        """Tabs that follow the app mode, and the OK/Cancel buttons."""
        # A player-only install never runs the planning checks — and the tab
        # follows the combo above right away, so the dialog stays consistent
        # with what the user just picked.
        # …and the mirror image: a planner-only install has no Playing panel, so
        # the two buttons the play sets configure are nowhere to be pressed, and
        # there is no 🎛 cartwall either.
        def _sync_checks_tab():
            mode = self._app_mode_combo.currentData()
            tabs.setTabVisible(chk_idx, mode != "player")
            tabs.setTabVisible(sets_idx, mode != "planner")
            tabs.setTabVisible(cart_idx, mode != "planner")
        _sync_checks_tab()
        self._app_mode_combo.currentIndexChanged.connect(_sync_checks_tab)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lyt.addWidget(bb)

    def _scroll_the_pages(self, tabs):
        """Each page in a scroll area of its own: on a screen shorter than the
        tallest page the page scrolls, and OK / Cancel below stay on screen.
        The dialog still opens at its full size where the screen has room."""
        full = self.sizeHint()
        for i in range(tabs.count()):
            text, visible = tabs.tabText(i), tabs.isTabVisible(i)
            page = tabs.widget(i)
            tabs.removeTab(i)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(page)
            tabs.insertTab(i, scroll, text)
            tabs.setTabVisible(i, visible)
        tabs.setCurrentIndex(0)
        tabs.updateGeometry()     # the layout still holds the unwrapped pages' sizes
        # 90 %: the title bar sits outside the dialog's own size.
        avail = self.screen().availableGeometry().size() * 0.9
        self.resize(full.boundedTo(avail))

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
            # Qt answers with forward slashes; stored that way, the same folder
            # picked again would compare as a change (a restart, a relearn).
            edit.setText(os.path.normpath(chosen))

    def _add_remap_folder(self):
        """Append a browsed folder to the search-folder list (they are a list —
        picking one must not replace the one already there)."""
        chosen = QFileDialog.getExistingDirectory(
            self, "Add a folder to search for tracks", music_browse_dir())
        if not chosen:
            return
        lines = parse_remap_paths(self._remap_edit.toPlainText())
        lines.append(os.path.normpath(chosen))
        self._remap_edit.setPlainText("\n".join(parse_remap_paths(lines)))

    def _add_hidden_folder(self):
        """Append a browsed folder to the excluded folders."""
        chosen = QFileDialog.getExistingDirectory(
            self, "Hide a folder from the library", music_browse_dir())
        if not chosen:
            return
        lines = parse_remap_paths(self._hidden_edit.toPlainText())
        lines.append(os.path.normpath(chosen))
        self._hidden_edit.setPlainText("\n".join(parse_remap_paths(lines)))

    def _add_ceremony_folder(self):
        """Append a browsed folder to the 🏅 entrance and award folders."""
        chosen = QFileDialog.getExistingDirectory(
            self, "Entrance and award music folder", music_browse_dir())
        if not chosen:
            return
        lines = parse_remap_paths(self._ceremony_edit.toPlainText())
        lines.append(os.path.normpath(chosen))
        self._ceremony_edit.setPlainText("\n".join(parse_remap_paths(lines)))

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

    def _on_reset_clicked(self):
        if self._reset_cb:
            self.accept()
            self._reset_cb()

    def _on_relearn_clicked(self):
        if self._relearn_cb:
            self.accept()
            self._relearn_cb()

    def _on_rescan_clicked(self):
        if self._rescan_cb:
            vals = self.values()
            self.accept()
            self._rescan_cb(vals)

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
            "app_mode": self._app_mode_combo.currentData(),
            "library_dir": self._lib_edit.text().strip(),
            "global_dir": self._glob_edit.text().strip(),
            "save_dir": self._save_edit.text().strip(),
            "backup_dir": self._backup_edit.text().strip(),
            "m3u_format": self._m3u_format_combo.currentData(),
            "playlist_dir": self._pl_edit.text().strip(),
            "reference_path": self._ref_edit.text().strip(),
            "remap_paths": parse_remap_paths(self._remap_edit.toPlainText()),
            "hidden_folders": parse_remap_paths(self._hidden_edit.toPlainText()),
            "ceremony_words": [w.strip() for w in self._ceremony_words_edit.text().split(",")
                               if w.strip()],
            "ceremony_folders": parse_remap_paths(self._ceremony_edit.toPlainText()),
            "global_search": self._global_chk.isChecked(),
            "exclude_no_class": self._exclude_no_class_chk.isChecked(),
            "clock_time_only": self._clock_time_only_chk.isChecked(),
            "theme": self.selected_theme(),
            "presenter_theme": self.presenter_theme(),
            "accent_color": self._accent,
            "font_scale": self._font_scale_combo.currentData(),
            "language": self._language_combo.currentData(),
            "german_dance_terms": self._german_terms_chk.isChecked(),
            **({"error_reports": self._error_reports_chk.isChecked()}
               if self._error_reports_chk is not None else {}),
            update_check.SETTING: self._update_check_chk.isChecked(),
            "check_min_play_secs": self._mmss_secs(self._min_time),
            "check_max_play_secs": self._mmss_secs(self._max_time),
            "check_tempo_dev_pct": self._dev_spin.value(),
            "check_noise_floor_db": self._noise_spin.value(),
        })
        vals.update(self._sound_values())
        vals.update(self._cartwall_values())
        vals.update(self._play_sets_values())
        return vals
