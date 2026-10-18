#!/usr/bin/env python3
"""
dancesport_gui.py  –  PySide6 GUI for the Dancesport Playlist Planner

Run:  py dancesport_gui.py
CLI:  py dancesport_planner.py
"""
import io
import os
import sys
import time
import logging
from pathlib import Path
from collections.abc import Callable

# The log goes to stdout with emoji in it. A Windows console is cp1252, so switch
# it to UTF-8; a windowed build has no stdout at all (sys.stdout is None).
if (isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding
        and sys.stdout.encoding.lower() not in ('utf-8', 'utf-8-sig')):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QPushButton, QLabel,
        QLineEdit, QPlainTextEdit, QMessageBox, QSizePolicy,
        QSpinBox,
        QToolButton,
        QStackedWidget,
        QScrollArea, QFrame, QMenu,
    )
    from PySide6.QtCore import (
        Qt, QTimer, QEvent, QThread, QtMsgType, qInstallMessageHandler,
    )
    from PySide6.QtGui import QShortcut, QKeySequence
except ImportError as e:
    print(f"PySide6 not found: {e}")
    print("Install with:  pip install PySide6")
    sys.exit(1)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

# FFmpeg — Qt's own default on Windows since 6.5, and the one that has never
# misbehaved here. Windows Media Foundation worked too on Qt 6.10.2, and it is
# what the app ran on for months; on 6.11.1 its plugin cuts the first play of a
# freshly loaded track after about a second and resets it, which is why
# requirements.txt pins the version rather than trusting the backend choice
# alone (6.11.2 there now, its WMF not yet heard). Even working, WMF re-emits LoadedMedia mid-playback,
# never reports EndOfMedia for a clip that runs to its own end (see
# player/audio/announce.py), reports position 0 at a pause, and is the backend the ⏭
# access violation was seen on. So the default is ffmpeg on merit, not as a
# workaround — WMF stays reachable in ⚙ Settings → 🔊 Audio backend.
#
# Naming a backend on any other platform asks Qt for one that does not exist
# there and leaves the app with no audio at all, so everywhere else Qt picks its
# own — AVFoundation on macOS, gstreamer on Linux. The default set here; the
# Settings choice overrides it in run_gui(), still long before anything plays.
if sys.platform == "win32":
    os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"   # alt. windows (WMF)

import planner.config
import planner.playlist.m3u
from planner.models import set_no_class_exclusion
# Before anything can start a child process (ffmpeg, gsettings, xdg-open).
planner.config.restore_system_library_path()
from planner.version import app_version
from planner.dances import BEATS_PER_BAR
from planner.music.db_upkeep import backup_safely
from planner.generate.suggester import PlaylistSuggester

log = logging.getLogger("dancesport.gui")

def _without_gutter(menu: QMenu) -> QMenu:
    """Entries start at the left edge: Fusion keeps a check/icon column even
    when no entry has either. A look's own stylesheet already lays its menus
    out, so it is left alone."""
    app = QApplication.instance()
    if isinstance(app, QApplication) and not app.styleSheet():
        menu.setStyleSheet(
            "QMenu::item { padding: 4px 24px 4px 8px; }"
            "QMenu::item:selected { background: palette(highlight);"
            " color: palette(highlighted-text); }")
    return menu

def exit_app(code: int):
    """Leave the process once the event loop has returned.

    Without tearing anything down: every save already ran in `closeEvent`, and
    the interpreter taking every Python and Qt object apart one by one cost
    1.0-1.2 s of each quit (~0.2 s this way). It would also destroy the workers
    `adopt_running` holds, and destroying a running QThread aborts the process
    (0xC0000409). A worker's open SQLite transaction rolls back as it would
    after a power cut."""
    logging.shutdown()
    # A windowed build has no console: both streams are None there.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.flush()
    os._exit(code)


# ── Shared GUI modules (light split) ─────────────────────────────────────────
# Background workers and all dialogs/shared widgets live in their own modules;
# the names are re-imported here so the rest of this file keeps using them
# unchanged.
from gui.workers import (
    LibraryLoader, AudioAnalyzer,
    SimilarFromFileWorker,
    LoudnessAnalyzer, PdHighlightAnalyzer,
    SilenceAnalyzer, VocalShareAnalyzer,
    adopt_running,
)
from shared.audio.audio_probes import LoudnessWorker, PdHighlightWorker, SilenceWorker
from shared.appearance.icons import counted_emoji
from shared.audio.playback import (plain_output_name, prime_disconnect_notify,
                                   quiet_ffmpeg_log)
from shared import error_reports
from shared.appearance import look_icons, theme, user_looks
from planner import i18n, terms
from planner.event import venue_pack
from planner.store import state_dir
from gui.decks.deck import DeckContext, DeckField
from gui.window.undo_timeline import UndoTimeline
from gui.dialogs.shortcuts import show_shortcuts
from gui.dialogs.about import manual_pdf, open_manual, show_about
from gui.dialogs.update_notice import UpdateNotice
from gui.common import (
    BusyDialog,
    LoadingDialog,
    install_plain_title_hook,
)
from shared.audio.audio_files import (
    set_browse_dir,
)
from shared.widgets import (
    _app_icon,
    _show_toast,
)
from gui.dialogs import (  # auto-resolved
    load_settings,
    app_mode_of,
    app_title,
    ensure_app_mode,
    ensure_error_reports_choice,
    ensure_update_check_choice,
    warmup_name,
    PLAYER_FIRST_START,
    apply_media_backend,
)
from shared.stores import (
    save_settings,
)

# ── View widgets (light split) ───────────────────────────────────────────────
# Each standalone widget class lives in its own gui_* module; the names are
# re-imported here so MainWindow and the smoke scripts keep using them unchanged.
# === split re-exports ===

from gui.table.playlist_table import (  # facade re-export
    PlaylistTable,
)

from gui.config_panel import (  # facade re-export
    ConfigPanel,
)

from player.widgets.play_mode_panel import (  # facade re-export
    PlayModePanel,
)

from player.presenter.presenter import (  # facade re-export
    PresenterWindow,
)

from player.widgets.taskbar import (  # facade re-export
    TaskbarPlayer,
)

from player.audio.announce import (  # noqa: F401  (facade re-export)
    DanceAnnouncer,
    announce_text,
)

from gui.library_browser import (  # noqa: F401  (facade re-export)
    _LibSortItem,
    _LibPlayItem,
    _LibTable,
    LibraryBrowser,
)

from gui.tournament_tree import (  # noqa: F401  (facade re-export)
    TournamentTree,
    load_tree,
    normalize_nodes,
    save_tree,
)

from player.audio.mix import OutputMix
from player.audio.audio_device import AudioDevice
from player.audio.cue_player import CuePlayer
from player.audio.playback_state import PlaybackState
from player.audio.fade_now import FadeNow
from player.audio.resume_marks import ResumeMarks
from gui.decks.deck_grid import DeckGrid
from gui.decks.deck_set import DeckSet
from gui.window.library_service import LibraryService
from player.audio.between_dances import BetweenDances
from player.audio.pause_filler import PauseFiller
from player.dialogs.play_log_dialog import PlayLogDialog
from player.audio.system_sounds import SystemSoundGuard

from player.widgets.player_parts import (  # noqa: F401  (facade re-export)
    _fmt_ms,
    _round_half_up,
    _ClickSlider,
)
from player.widgets.player import (  # noqa: F401  (facade re-export)
    PreviewOverlay,
    BigPlayerWidget,
)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────
# MainWindow is assembled from concern mixins (see gui_main_*):
from gui.window.main_decks import DeckLayoutMixin
from gui.window.main_generate import GenerateMixin
from gui.window.main_import import ImportMixin
from gui.window.main_persist import PersistenceMixin
from player.window.main_player import PlayerControlMixin
from gui.window.main_global import GlobalIndexMixin
from player.window.main_cartwall import CartwallMixin
from player.window.main_controller import ControllerMixin
from player.window.main_remote import RemoteMixin
from player.window.main_guest import GuestMixin
from gui.window.main_fullscreen import FullscreenMixin
from gui.window.main_deck_setup import DeckSetupMixin


class MainWindow(DeckSetupMixin, DeckLayoutMixin, GenerateMixin, ImportMixin, PersistenceMixin, PlayerControlMixin, GlobalIndexMixin, CartwallMixin, RemoteMixin, GuestMixin, ControllerMixin, FullscreenMixin, QMainWindow):
    _space_at = 0.0   # when Space last toggled the big player — see eventFilter

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DanceSport Planner & Player")
        self.resize(1500, 900)
        # A 🎨 look draws the deck title strips and the mode switch its own way.
        self._look_parts = theme.look_parts()
        if self._look_parts:
            self._DECK_HDR_IDLE = self._look_parts["deck_idle"]
            self._DECK_HDR_ACTIVE = self._look_parts["deck_active"]

        # Undo/redo: snapshot-based timeline of full-UI env dicts (see _build_env).
        self._undo_timeline = UndoTimeline(limit=50)
        self._restoring     = False             # guards edit hooks during _apply_env

        # 📚 The libraries and the threads loading them (gui.window.library_service).
        self._library = LibraryService()
        # 🗂 The boxes and splitters the decks sit in (gui.decks.deck_grid).
        self._grid = DeckGrid()
        # 🎛 The decks, day decks, wishlists and their Decks (gui.decks.deck_set).
        self._deckset = DeckSet()
        self._suggester:  PlaylistSuggester | None  = None
        # Deck A's generation context, read and written through the DeckFields
        # (_style, _playlist …) until the decks exist to hold it.
        self._boot_ctx = DeckContext()
        self._iteration   = 0
        # Per-competition worked playlists, so switching the competition combo keeps
        # each one's edits. Keyed by combo index; reset when a new schedule is parsed.
        self._replay_work: dict[int, dict]   = {}

        # Settings + lazily-built whole-repo library (for global search)
        self._settings = load_settings()
        # Point the popularity learning at the configured tournament-playlists
        # folder BEFORE the library scan learns from it.
        if self._settings.get("playlist_dir"):
            planner.config.set_playlist_dir(self._settings["playlist_dir"])
        planner.playlist.m3u.set_m3u_format(self._settings.get("m3u_format"))
        set_no_class_exclusion(self._settings.get("exclude_no_class"))
        # Every open/add picker starts where the last one ended.
        set_browse_dir(self._settings.get("open_dir", ""),
                       self._remember_open_dir)
        self._pending_drop:  str | None              = None
        self._pending_after_global: Callable[[], None] | None = None
        self._index_analyzer: AudioAnalyzer | None   = None
        self._emb_idx_worker = None
        self._allcache = None
        self._allcache_worker = None   # the probe step running inside it

        # The scan needs nothing the window builds, so it runs while the window
        # is built instead of after it.
        self._setup_library_load()
        self.setWindowIcon(_app_icon())
        self._setup_media_player()
        self._setup_timed_play()
        splitter = self._setup_left_panel()
        right, rl, saved_cols, saved_widths = self._setup_decks()
        self._setup_deck_toolbar(rl)
        self._setup_deck_grids()
        self._setup_lower_panes(rl, saved_cols, saved_widths)
        self._setup_shortcuts()
        self._setup_player_bar(right, rl, splitter)
        # 🎛 Last: a press arriving at once must find the player and the wall.
        self._init_controller()
        self._ctl_hub.changed.connect(self._sync_controller_badge)
        self._sync_controller_badge()
        self._sync_sound_badge()

    def _setup_media_player(self):
        """🎵 The media player, its voices and the volume around them."""
        # ── Media player ──
        # 🎵 The loaded title, its dance, the load token and the silence skipped
        # on it — read across the player, pause, Paso Doble and loudness parts.
        self._playback = PlaybackState()
        # ⏱ Start-up latency of the running play request: when the ▶ was handled
        # and whether the "media ready" line has already been logged for it.
        self._play_t0: float | None = None
        self._play_ready_logged = False
        # 🔊 Every output level, and the factors behind it — see player.audio.mix. Held
        # apart from each other so they never fight: the user's slider, the
        # per-track loudness gain, the fade-out ramp and the two ducks.
        self._mix = OutputMix(float(self._settings.get("master_volume", 0.9)))
        # The 🎛 cartwall's own voice pool, built later in _build_cartwall.
        # Assigned here because _apply_volume() below already reads it.
        self._cart_voices = None
        # 🔕 The OS's own sounds off the PA while the evening runs (see
        # player.audio.audio_device.watch_system_sounds). A run that crashed while
        # holding the mute left it on — lift it before anything else.
        _system_sounds = SystemSoundGuard()
        _leftover = self._settings.pop("system_sounds_muted", None)
        if _leftover is not None:
            _system_sounds.restore_leftover(_leftover)
            save_settings(self._settings)
        if HAS_MULTIMEDIA:
            quiet_ffmpeg_log()
            self._player     = QMediaPlayer(self)
            self._audio_out  = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_out)
            prime_disconnect_notify(self._player, self._audio_out)
            self._apply_volume()
            self._player.mediaStatusChanged.connect(self._on_media_status)
            self._player.errorOccurred.connect(self._on_player_error)
            # Second, independent player for the optional pause/filler music —
            # the MAIN player holds the preloaded next song during the pause
            # (latency!), so the filler needs its own pipeline. When a filler
            # title runs out, _on_pause_media_status rotates to the next one
            # (a single title simply restarts — the old Loops.Infinite).
            self._pause_player = QMediaPlayer(self)
            self._pause_out = QAudioOutput(self)
            self._pause_player.setAudioOutput(self._pause_out)
            prime_disconnect_notify(self._pause_player, self._pause_out)
            self._pause_player.mediaStatusChanged.connect(
                self._on_pause_media_status)
            self._pause_out.setVolume(0.0)
        else:
            self._player = None
            self._audio_out = None
            self._pause_player = None
            self._pause_out = None
        # 🎧 Pre-listen on an output of its own (_prehear), with a mini
        # player of its own: the shared one runs the hall's music.
        cue = CuePlayer(self) if self._player is not None else None
        if cue is not None:
            cue.view = PreviewOverlay(cue.media_player, cue.audio_output, duck=False)
            cue.view.closeRequested.connect(cue.stop)
            cue.view.disableRequested.connect(self._disable_preview)
            cue.view.prevRequested.connect(lambda: self._cue_skip(-1))
            cue.view.nextRequested.connect(lambda: self._cue_skip(+1))
            cue.stopped.connect(cue.view.hide)
            cue.stopped.connect(lambda: self._reset_aux_play_markers())
        # 🔊 The sound card: follows the Windows default, is handed back while
        # nothing plays, keeps the OS's own sounds off the PA.
        self._audio_device = AudioDevice(
            self._player, self._audio_out, self._pause_player, self._pause_out,
            mix=self._mix,
            settings=lambda: self._settings,
            cart_voices=lambda: self._cart_voices,
            is_playing_mode=self._is_playing_mode,
            apply_volume=self._apply_volume,
            system_sounds=_system_sounds,
            announcer=lambda: getattr(self, "_announcer", None),
            warn=lambda text: _show_toast(self, text, 4000),
            cue=cue)
        if self._player is not None:
            self._follow_audio_devices(self._player)
        self._filler = PauseFiller()   # 🎵 the pause's filler titles and fade

    def _follow_audio_devices(self, player):
        """🔊 Wire the sound card's watchers to both players and the OS."""
        # 🔇 Idle audio release (setting "release_audio_idle"): both
        # pipelines report back so the sound device is taken again before a
        # title is heard, whichever of the many play paths started it —
        # see player.audio.audio_device.ensure.
        player.playbackStateChanged.connect(
            self._audio_device.on_playback_state)
        if self._pause_player is not None:
            self._pause_player.playbackStateChanged.connect(
                self._audio_device.on_playback_state)
        # A default-constructed QAudioOutput binds to the system default device
        # at creation and does NOT follow when the user switches the Windows
        # audio device. Track QMediaDevices and re-point both outputs at the
        # new default so playback follows the active device live.
        self._media_devices = QMediaDevices(self)
        self._media_devices.audioOutputsChanged.connect(
            self._audio_device.on_outputs_changed)
        # …but that signal only fires when a device appears or disappears.
        # Switching the default between two headsets that are both plugged in
        # changes nothing about the list, so it has to be watched for.
        self._device_watch = QTimer(self)
        self._device_watch.setInterval(2000)
        self._device_watch.timeout.connect(self._audio_device.watch_default)
        self._device_watch.timeout.connect(self._audio_device.watch_idle)
        self._device_watch.timeout.connect(
            self._audio_device.watch_system_sounds)
        # 🔊 The badge follows the card on the same tick, which also picks up
        # a card chosen in ⚙ Settings.
        self._media_devices.audioOutputsChanged.connect(self._sync_sound_badge)
        self._device_watch.timeout.connect(self._sync_sound_badge)
        self._device_watch.start()

    def _sync_sound_badge(self):
        """🔊 A small indicator at the right of the status bar while the card
        chosen for the music is plugged in, so the desk sees the MAYA44USB is
        there to play on. Plain text in the look's colour, not a pill like
        the 🎛 controller's. A click opens ⚙ Settings ▸ 🔊 Sound."""
        # Found on the status bar by name, so the window stores nothing more.
        badge = self.statusBar().findChild(QPushButton, "soundBadge")
        if badge is None:
            badge = QPushButton()
            badge.setObjectName("soundBadge")
            badge.setStyleSheet("background:transparent; border:none; "
                                "padding:1px 4px; margin:2px 4px;")
            badge.setCursor(Qt.CursorShape.PointingHandCursor)
            badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            badge.clicked.connect(lambda: self._open_settings(open_sound=True))
            # First of the permanent widgets: the ⛶ clock keeps the far right.
            self.statusBar().insertPermanentWidget(0, badge)
        card = self._audio_device.music_card()
        if card:
            # i18n: data — the card's own name
            badge.setText(f"🔊 {plain_output_name(card)}")
            badge.setToolTip(i18n.t("The music plays on %s — click for the "
                                    "sound settings.") % card)
        badge.setVisible(bool(card))

    def _setup_timed_play(self):
        """▶ The timed-play engine's tick and the state of the running title."""
        # Timed-play engine (▶ Playing mode): a 200 ms tick drives the countdown,
        # the fade-out ramp and the end-of-play-length stop. Position-based, so
        # pausing/seeking behaves naturally.
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(200)
        self._fade_timer.timeout.connect(self._on_play_tick)
        # 🔉 Level changes that happen DURING a title ride their own fast timer:
        # the announcement duck and a loudness gain that only arrives once the
        # track is already running. How far each step moves is player.audio.mix's, so
        # the tick length is too.
        self._ramp_timer = QTimer(self)
        self._ramp_timer.setInterval(self._mix.step_ms)
        self._ramp_timer.timeout.connect(self._step_volume_ramp)
        # Skipping ⏭ ⏭ ⏭ as fast as the finger goes used to hand the backend a
        # full media-session teardown + rebuild per press. Windows Media
        # Foundation does not survive that reliably (the app's own reload
        # watchdog was written for it hanging mid-switch, and it can take the
        # process down with an access violation). So loads are coalesced: the
        # first press goes through at once, presses inside the gap only move the
        # target, and one load runs when the burst settles.
        self._last_load_at = 0.0            # monotonic time of the last real load
        self._pending_load: tuple[Path | None, bool] | None = None
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._flush_pending_load)
        # Volume is persisted, but a slider drag fires per 1 % step — debounce so
        # one drag is one settings write instead of a hundred.
        self._vol_save_timer = QTimer(self)
        self._vol_save_timer.setSingleShot(True)
        self._vol_save_timer.setInterval(600)
        self._vol_save_timer.timeout.connect(self._save_master_volume)
        # ⏸ Auto-advance: the pause after a song ends and the title it leads
        # into (or, after a 🏁 round-end stop, the next round's first song).
        self._between = BetweenDances()
        # Spoken "next dance" cue during that pause — the engine inside is built
        # on first use, so nothing is loaded unless the operator switches it on.
        self._announcer = DanceAnnouncer(
            self, self._on_announcer_speaking,
            voice=str(self._settings.get("announce_voice", "random")))
        # Manual "fade out now" (🔉↓ on the card) and the 🛑 panic fade.
        self._fade_now = FadeNow()
        # 🕘 (dance, title) of the title before the running one — the presenter
        # screen shows it when asked to; None until a second title starts.
        self._last_played: tuple[str, str] | None = None
        # A track counts as "played" (greyed) once it has actually been heard
        # for this many ms — robust against the operator skipping rows around.
        self._PLAYED_AFTER_MS = 10_000
        self._played_marked = False   # current track already marked played?
        # ↩ Where each title was left (player.audio.resume_marks), for this session.
        self._resume = ResumeMarks()
        # Where the title now loading has to be put once its media is open —
        # a seek issued before that is dropped by the backend.
        self._resume_seek_ms: int | None = None
        # Paso Doble highlight stop: detected highlight times per path
        # (in-memory, session-scoped) and the armed stop position (seconds) —
        # None = play to the natural end.
        self._pd_highlights: dict = {}
        self._pd_stop_at: float | None = None
        # Set when ✏️ edit mode is switched off: the next time the highlight stop
        # is reached, pause there so the fresh mark can be checked by ear.
        self._pd_verify_stop = False
        self._pd_worker: PdHighlightWorker | None = None
        # 🐂 The wait between the call and the first bar, while it runs:
        # (play token, path, deadline) plus its countdown ticker.
        self._pd_hold: tuple | None = None
        self._pd_hold_timer: QTimer | None = None
        # ⏯ Loaded but never started (start=False): the next ⏯ runs the full
        # start — call, pitch, hold — instead of a bare play().
        self._cued = False
        # 🔇 Stillness skip: silence spans of tracks seen this session, probed
        # in the background on first play (or read from the DB cache).
        self._silences: dict = {}
        self._silence_worker: SilenceWorker | None = None
        # …and the ⚙ Settings bulk pass that fills the same table up front.
        self._silence_analyzer: SilenceAnalyzer | None = None
        # 📊 Loudness of a track nobody measured yet: probed on first play, with
        # its start held back briefly so the floor never hears the wrong level.
        self._lufs_worker: LoudnessWorker | None = None
        self._lufs_pending: Path | None = None   # the title waiting to start
        self._lufs_token = 0    # the playback token that wait belongs to
        self._lufs_failed: set = set()   # ffmpeg said no — don't wait for these

        # Mini preview player floating over the deck (toggle in ⚙ Settings).
        self._preview: PreviewOverlay | None = None
        self._preview_src: PlaylistTable | None = None   # deck whose ▶ started playback
        if self._player and self._audio_out is not None:
            self._preview = PreviewOverlay(self._player, self._audio_out,
                                           get_vol=lambda: self._mix.base,
                                           set_vol=self._set_base_volume)
            self._preview.closeRequested.connect(self._on_stop_btn)
            self._preview.disableRequested.connect(self._disable_preview)
            self._preview.prevRequested.connect(lambda: self._preview_skip(-1))
            self._preview.nextRequested.connect(lambda: self._preview_skip(+1))
            self._preview.duckToggled.connect(self._set_desk_duck)

    def _setup_left_panel(self):
        """📝/▶ The left side: config panel, mode switch and the Playing panel."""
        # ── Central layout ──
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter = splitter
        outer.addWidget(splitter, stretch=1)

        self._setup_config_panel()
        self._analyzer: AudioAnalyzer | None = None
        self._sim_worker: SimilarFromFileWorker | None = None
        self._busy: BusyDialog | None = None

        # Mode switch above the panel: 📝 Planning (combos, generate, settings)
        # ⇄ ▶ Playing (timed-play controls for the tournament floor). The whole
        # left side flips via a QStackedWidget; playback keeps running across it.
        self._play_panel = PlayModePanel(self._settings)
        self._play_panel.settingsChanged.connect(self._save_play_settings)
        self._play_panel.settingsChanged.connect(self._refresh_set_lights)
        self._play_panel.settingsChanged.connect(self._sync_dance_len)
        self._play_panel.danceLenChanged.connect(self._on_dance_len_changed)
        self._wire_advance_switch()
        self._play_panel.settingsRequested.connect(self._open_settings)
        self._setup_big_player()
        self._loudness_worker: LoudnessAnalyzer | None = None
        self._vocals_worker: VocalShareAnalyzer | None = None
        self._play_panel.pdLearnRequested.connect(self._learn_pd_highlight)
        self._play_panel.pdClearRequested.connect(self._clear_pd_highlight)
        self._play_panel.pdEditToggled.connect(self._on_pd_edit_toggled)
        self._play_panel.pdMarkDeleteRequested.connect(self._delete_pd_mark)
        # 🖥 Presenter screen — created on first use, closed with the app.
        self._presenter: PresenterWindow | None = None
        # 🕒 How far the running order's clock is set from this machine's, when
        # the evening is behind. Deliberately not persisted — see
        # TimetableDialog.now_offset().
        self._now_offset = None
        # ☀ Whether the screensaver is currently held off (see _refresh_wake_lock).
        self._awake_held = False
        self._play_panel.presenterToggled.connect(self._toggle_presenter)
        self._play_panel.presenterScreenChanged.connect(self._move_presenter)
        # The monitor a presenter stands on can be unplugged mid-evening.
        self._presenter_lost: str | None = None
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.screenRemoved.connect(self._on_screen_removed)
            app.screenAdded.connect(self._on_screen_added)
        self._play_panel.timetableRequested.connect(self._edit_timetable)
        self._play_panel.remoteRequested.connect(self.open_remote_window)
        # 🪟 ⏮ ⏯ ⏭ under the taskbar thumbnail on hover.
        self._taskbar: TaskbarPlayer | None = None
        self._init_taskbar()
        # 📱 The phone remote: off at every launch, switched in its window.
        # An older build saved Start / Stop in the settings — drop that.
        self._settings.pop("phone_remote", None)
        self._remote_wanted = False
        self._remote = None
        self._remote_timer = None
        self._remote_bridge = None
        self._remote_pad_keys = []
        # 🏆/🎉 lights: read off the controls, which the settings restored
        # a moment ago — so they need no memory of their own.
        self._refresh_set_lights()
        self._play_panel.partySetToggled.connect(self._set_party_mode)
        self._play_panel.tournamentSetRequested.connect(self._apply_tournament_set)
        self._play_panel.rememberToggled.connect(self._set_remember_pos)
        # 🖼 〰 Cover art and waveform on the player card, as ⚙ Settings left them.
        self._set_artwork_shown(bool(self._settings.get("show_artwork", True)))
        self._set_waveform_shown(bool(self._settings.get("show_waveform", True)))
        self._pd_analyzer: PdHighlightAnalyzer | None = None
        splitter.addWidget(self._build_left_column())
        return splitter

    def _setup_config_panel(self):
        """📝 The Planning side's config panel and what its buttons ask for."""
        self._cfg = ConfigPanel()
        self._cfg.generate_requested.connect(self._generate)
        self._cfg.import_requested.connect(self._import_playlist)
        self._cfg.save_btn.clicked.connect(self._save_m3u)
        self._cfg.ai_requested.connect(self._open_ai_dialog)
        self._cfg.ai_playlist_requested.connect(self._generate_ai_playlist)
        self._cfg.ai_log_requested.connect(self._show_ai_log)
        self._cfg.settings_requested.connect(self._open_settings)
        self._cfg.build_all_requested.connect(
            lambda: self._build_all_caches(self._settings))
        self._cfg.m3u_source_requested.connect(self._browse_source_m3u)
        self._cfg.round_strategy_changed.connect(self._on_strategy_changed)
        self._cfg.replay_competition_changed.connect(self._on_replay_competition_changed)
        self._cfg.schedule_parsed.connect(self._on_schedule_parsed)
        self._cfg.timbre_check.toggled.connect(self._on_timbre_toggled)
        self._cfg.drop_zone.fileDropped.connect(self._on_file_dropped)

    def _setup_big_player(self):
        """▶ The big master player on the Playing panel, when there is a player."""
        # Big master player on top of the Playing-mode panel (UltraMixer-style).
        self._big_player: BigPlayerWidget | None = None
        if self._player:
            self._big_player = BigPlayerWidget(
                self._player, self._audio_out,
                get_vol=lambda: self._mix.base,
                set_vol=self._set_base_volume,
                cache_of=lambda: self._library.cache)
            self._player.playbackStateChanged.connect(self._on_playback_state)
            self._big_player.prevRequested.connect(lambda: self._preview_skip(-1))
            self._big_player.nextRequested.connect(self._on_player_next)
            self._big_player.extendPauseRequested.connect(self._extend_pause)
            self._big_player.toPauseRequested.connect(self._on_to_pause)
            self._big_player.fadeOutRequested.connect(self._fade_out_now)
            self._big_player.panicRequested.connect(self._fade_and_hold)
            self._big_player.duckToggled.connect(self._set_desk_duck)
            self._big_player.fileDropped.connect(self._on_player_drop)
            self._big_player.resume_cb = self._resume_tap
            self._big_player.set_pause_available(
                self._play_panel.pause_available())
            self._big_player.set_tempo_reset_on_track(
                bool(self._settings.get("tempo_reset_per_track", True)))
            self._big_player.tempoResetModeChanged.connect(
                self._on_tempo_reset_mode)
            self._big_player.set_tso_mode(
                bool(self._settings.get("tso_equalize", True)))
            self._big_player.tsoModeChanged.connect(self._on_tso_mode)
            self._big_player.tempoApplied.connect(self._sync_big_player_limit)
            self._play_panel.set_player_widget(self._big_player)

    def _build_left_column(self):
        """📝/▶ The left column: the mode switch over the two stacked panels."""
        left_box = QWidget()
        left_box.setMinimumWidth(250)
        left_box.setMaximumWidth(640)
        # …kept: with the wide strip the whole of Playing mode stands in the
        # strip, and this column steps aside (see _apply_player_layout).
        self._left_box = left_box
        self._left_col = ll = QVBoxLayout(left_box)
        ll.setContentsMargins(0, 4, 0, 0)
        ll.setSpacing(4)
        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(8, 0, 8, 0)
        mode_row.setSpacing(0)
        self._mode_plan_btn = QPushButton("📝  Planning")
        self._mode_play_btn = QPushButton("▶  Playing")
        for b in (self._mode_plan_btn, self._mode_play_btn):
            b.setCheckable(True)
            b.setFixedHeight(28)
            # Down the column they stretch to its width anyway; in the wide
            # strip they stand on their own and must not squeeze their labels.
            b.setMinimumWidth(112)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setStyleSheet(self._look_parts.get("mode_btn") or (
                "QPushButton{border:1px solid #b9d4f2; background:#f4f7fb;}"
                "QPushButton:checked{background:#1565c0; color:white;"
                " font-weight:bold;}"))
            mode_row.addWidget(b)
        self._mode_plan_btn.setChecked(True)
        self._mode_plan_btn.clicked.connect(lambda: self._set_play_mode(False))
        self._mode_play_btn.clicked.connect(lambda: self._set_play_mode(True))
        # In its own widget so a single-sided install can hide the switch whole
        # (see _apply_app_mode) — there is nothing to switch between there.
        self._mode_row_w = QWidget()
        self._mode_row_w.setLayout(mode_row)
        self._mode_switch_shown = True
        ll.addWidget(self._mode_row_w)
        self._left_stack = QStackedWidget()
        # Index 0 — planning, behind a scroll area for the same reason as the
        # playing panel below: it wants 873 px, and on a 650 px column the
        # layout took the difference out of its children — the style/age/class
        # combos came out 12 px tall, at 450 px 2 px, and the dance checkboxes
        # 2 px instead of 89.
        self._cfg_scroll = QScrollArea()
        self._cfg_scroll.setWidgetResizable(True)
        self._cfg_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cfg_scroll.setWidget(self._cfg)
        self._left_stack.addWidget(self._cfg_scroll)
        # Index 1 — playing, behind a scroll area rather than straight in the
        # stack. The panel wants ~900 px; on a screen with less than that the
        # layout took the difference out of its children, and the player card —
        # the one thing an operator needs whole — went from 247 px to 26: no
        # transport, no time, no fader. Scrolled, everything keeps its full size
        # and what doesn't fit moves under a scrollbar.
        self._play_scroll = QScrollArea()
        self._play_scroll.setWidgetResizable(True)   # …but still fill a tall screen
        self._play_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._play_scroll.setWidget(self._play_panel)
        self._left_stack.addWidget(self._play_scroll)
        ll.addWidget(self._left_stack, stretch=1)
        return left_box

    def _setup_shortcuts(self):
        """⌨ The window's keyboard shortcuts."""
        # Ctrl+S (STRG+S) — save the currently focused playlist/wishlist as M3U.
        self._save_sc = QShortcut(QKeySequence.StandardKey.Save, self)
        self._save_sc.activated.connect(self._save_focused)
        # Ctrl+Shift+S — 📌 save the whole working session (decks, wishlists, layout).
        self._save_state_sc = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._save_state_sc.activated.connect(self._save_state_now)
        # Ctrl+Shift+Del — empty the focused playlist / wishlist (confirmed),
        # from anywhere in the window; Del does it only with nothing selected.
        self._clear_sc = QShortcut(QKeySequence("Ctrl+Shift+Del"), self)
        self._clear_sc.activated.connect(self._clear_focused)
        self._update_wish_counts()   # seed the badges before the first edit

        # Ctrl+Z / Ctrl+Y (+ Ctrl+Shift+Z) — undo/redo editing steps.
        self._undo_sc = QShortcut(QKeySequence.StandardKey.Undo, self)
        self._undo_sc.activated.connect(self._undo)
        self._redo_sc = QShortcut(QKeySequence.StandardKey.Redo, self)
        self._redo_sc.activated.connect(self._redo)
        self._redo_sc2 = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self._redo_sc2.activated.connect(self._redo)

        # ⌨ Desk keys — every Playing-side action on a key of its own
        # (player.window.main_controller). Ctrl+Shift+→ / ← are ⏭ / ⏮ by default:
        # the operator's hands are on the deck, not on the card, and during a
        # pause the next title is the only thing worth reaching for. One
        # modifier above the deck's Ctrl+←/→, which seeks INSIDE the song.
        self._init_desk_keys()

        # F1 — shortcut cheat sheet (also via the ❔ toolbar button).
        self._help_sc = QShortcut(QKeySequence("F1"), self)
        self._help_sc.activated.connect(self._show_shortcuts)
        # F12 — ⚙ Settings, to hit without looking; Ctrl+Alt+S as in the
        # JetBrains IDEs.
        for key in ("F12", "Ctrl+Alt+S"):
            QShortcut(QKeySequence(key), self).activated.connect(
                lambda: self._open_settings())
        # F11 — ⛶ fullscreen, with the clock in the status bar.
        self._setup_fullscreen()

        # Ctrl+X (and Ctrl+W, which is what every other window on the desk
        # answers to) closes the active dialog — or, on the main window, the
        # preview mini player (never the app itself). An app-wide event filter
        # handles it so every dialog is covered without wiring each one; text
        # inputs keep Ctrl+X for "cut" (they're skipped in eventFilter).
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _setup_player_bar(self, right, rl, splitter):
        """Hints bar, player bar, undo/redo and the persisted dividers."""
        # Hints bar (between table and player) — hidden until there's something to say
        self._hints_lbl = QLabel("")
        self._hints_lbl.setWordWrap(True)
        self._hints_lbl.setStyleSheet(
            "background:#fff8e6; color:#7a5b00; border:1px solid #e6d28a;"
            "border-radius:4px; padding:4px 8px; font-size:11px;"
        )
        self._hints_lbl.setVisible(False)
        rl.addWidget(self._hints_lbl)

        # Player bar (bottom of right panel)
        player_bar = QWidget()
        player_bar.setFixedHeight(34)
        pb = QHBoxLayout(player_bar)
        pb.setContentsMargins(4, 2, 4, 2)

        # Undo / redo buttons (mirror Ctrl+Z / Ctrl+Y) for discoverability. They show
        # the number of available steps and go blue⇄grey so it's obvious at a glance
        # whether an undo / redo is possible right now.
        _undo_style = (
            "QToolButton{font-weight:bold; padding:2px 9px; border-radius:4px;}"
            "QToolButton:enabled{color:#1565c0; background:#e7f0fb;"
            " border:1px solid #b9d4f2;}"
            "QToolButton:enabled:hover{background:#d6e6fa;}"
            "QToolButton:disabled{color:#bdbdbd; background:transparent;"
            " border:1px solid #e2e2e2;}")
        self._undo_btn = QToolButton()
        self._undo_btn.setText("↶")
        self._undo_btn.setStyleSheet(_undo_style)
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(self._undo)
        pb.addWidget(self._undo_btn)
        self._redo_btn = QToolButton()
        self._redo_btn.setText("↷")
        self._redo_btn.setStyleSheet(_undo_style)
        self._redo_btn.setEnabled(False)
        self._redo_btn.clicked.connect(self._redo)
        pb.addWidget(self._redo_btn)

        self._now_playing = QLabel("No song selected")
        self._now_playing.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        pb.addWidget(self._now_playing)

        if not HAS_MULTIMEDIA:
            pb.addWidget(QLabel("(multimedia unavailable)"))

        rl.addWidget(player_bar)
        splitter.addWidget(right)
        splitter.setSizes([295, 985])
        # Growing the window (e.g. maximizing) must widen the DECKS, not the left
        # panel — without stretch factors the splitter grows both proportionally.
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Every draggable divider whose position we persist across sessions, so the
        # user's layout (wishlist height, deck column widths, config-panel width, …)
        # comes back exactly as they left it. Restored at the end of construction.
        self._persist_splitters = {
            "main":  self._main_splitter,
            "right": self._grid.right_split,
            "cols":  self._grid.decks_split,
            "col1":  self._grid.decks_col1,
            "col2":  self._grid.decks_col2,
            "cols2": self._grid.decks_split2,
            "col3":  self._grid.decks_col3,
            "col4":  self._grid.decks_col4,
            # NOTE: _wish_split is NOT here — its layout is persisted per wish-state
            # via _wish_sizes (layout/wish_sizes), replayed by _update_wish_area.
        }
        self._restore_layout()
        self._apply_player_layout()   # …before the mode decides who shows
        if self._settings.get("play_mode") == "playing":
            self._set_play_mode(True)
        # Last, so it overrides the restored 📝/▶ side where the mode demands it.
        self._apply_app_mode()
        if self._settings.pop(PLAYER_FIRST_START, False):
            self._apply_player_first_start()

        self.statusBar().showMessage("Loading library…")

    def _setup_library_load(self):
        """⏳ The loading dialog and the background library loader."""
        # ── Loading dialog (shown while the background thread scans files) ──
        self._loading_dlg = LoadingDialog(app_title(app_mode_of(self._settings)),
                                          f"Version {app_version()}")
        self._loading_dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        # Painted now, before the window's own build keeps the GUI thread busy.
        # This is the last event pump before app.exec(): the loader's signals
        # are queued, and nothing may deliver them to a half-built window.
        self._loading_dlg.show()
        QApplication.processEvents()

        # ── Load library in background ──
        # Parented, so _stop_workers finds it: an unparented loader is nobody's
        # child, outlives the window that started it and is destroyed mid-scan
        # when the process ends — which Qt answers by aborting.
        self._library.loader = LibraryLoader(music_dir=self._settings.get("library_dir"),
                                             parent=self)
        self._library.loader.status.connect(self._loading_dlg.set_status)
        self._library.loader.finished_ok.connect(self._on_library_loaded)
        self._library.loader.error.connect(self._on_library_error)
        self._library.loader.start()

    # ── App mode (planner / player / both) ──────────────────────────────────────

    def _apply_app_mode(self):
        """Show only the side of the app this install was set up for.

        Player-only strips the planning half: the 📝 Planning panel and every
        toolbar action that generates, curates or checks a playlist, so an
        operator who only runs the music at the venue never meets a generator.
        Planner-only drops the tournament floor's tools instead — the ▶ Playing
        panel and the 🎛 cartwall. 'Both' shows everything, and is what every
        settings file written before this option reads as.

        Nothing is disabled, only hidden: the decks, the player and the whole
        engine stay wired up, so switching the mode back in ⚙ Settings brings
        the other side straight back without a restart."""
        mode = app_mode_of(self._settings)
        planning = mode in ("planner", "both")
        playing = mode in ("player", "both")
        self.setWindowTitle(app_title(mode, app_version()))
        # The 📝 / ▶ switch only means something when both sides are there.
        # Remembered, because the switch travels: in the wide strip it is
        # re-docked (see _dock_mode_row) and must come back just as hidden.
        self._mode_switch_shown = mode == "both"
        self._mode_row_w.setVisible(self._mode_switch_shown)
        if mode != "both":
            self._set_play_mode(mode == "player")
        for b in self._planner_btns:
            b.setVisible(planning)
        for b in self._player_build_hidden:
            b.setVisible(False)
        self._cart_btn.setVisible(playing)
        if not playing:
            self._cart_btn.setChecked(False)   # also closes the dock
        # The ⚙ gear lives on the planning panel — with that panel gone the
        # playing panel grows its own, in the same corner.
        self._play_panel.set_settings_visible(not planning)
        # The decks' 🔒/🔓/✋ mode button is planning work too — it goes with the panel
        # (and comes back with it, without a restart).
        for d in list(self._deckset.deck_of.values()):
            if d.mode_btn is not None:
                self._refresh_mode_btn(d.table)
        self._apply_warmup_labels(mode)
        # A draw planned before the switch is still on screen, and in a grid a
        # title can only move into another slot of its own dance — re-render it
        # as the running order so every row can be dragged freely.
        if mode == "player":
            self._decks_to_player_lists()
        log.info("🎚️ App mode applied\n"
                 "mode: %s\n"
                 "planning side: %s\n"
                 "playing side: %s", mode, planning, playing)

    def _apply_warmup_labels(self, mode: str):
        """Name the two 🤸 buttons after what the panel is used for here: warming
        up AND running a party where the install plans tournaments, plainly the
        party where it only plays them."""
        name = warmup_name(mode)
        self._set_toolbar_btn_text(self._warmup_gen_btn, f"🤸  {name}")
        self._set_toolbar_btn_text(self._warmup_toggle_btn, f"🤸  {name} ▾")
        self._warmup_toggle_btn.setToolTip(
            i18n.t("Show / hide the %s panel.\n"
                   "Opens an empty panel — drop an existing .m3u onto it, "
                   "or build a fresh list with 🤸 %s.") % (name, name))

    def _apply_player_first_start(self):
        """The venue layout, put in place once when the first start picked
        player-only — never again, so from the second start on it is the user's.

        Someone who only plays does not open on an empty tournament grid: they
        open on a flat run of songs and their library. So no playlist decks, no
        wishlists, no round/dance grouping, the 🤸 party list armed for a
        dropped .m3u, 📚 the library open and the 🎛 cartwall away. The 🎉 party
        set goes with it — full length, auto-advance, no break, equalized
        volume — which is what such a list has to play with."""
        self._deckset.deck_count = 0
        self._apply_deck_view()
        self._set_wish_state(0)
        self._set_compact_state(2)
        self._warmup_toggle_btn.setChecked(True)   # arms an empty party list
        self._lib_btn.setChecked(True)
        self._cart_btn.setChecked(False)
        self._on_table_focused(self._deckset.warmup_table)   # the panel shows the party list
        self._set_party_mode(True)
        save_settings(self._settings)   # the consumed flag must not come back
        log.info("🎚️ Player-only first start — venue layout applied\n"
                 "decks: none\n"
                 "wishlists: none\n"
                 "grouping: off\n"
                 "party list: armed\n"
                 "library: open\n"
                 "cartwall: hidden\n"
                 "party set: on")

    # ── Multi-deck layout (two playlists + wishlist) ────────────────────────────

    _DECK_HDR_IDLE   = ("background:#eceff4; color:#555; border:1px solid #d4d9e0;"
                        "border-radius:4px; padding:2px 8px; font-size:11px; font-weight:bold;")
    _DECK_HDR_ACTIVE = ("background:#2d6cdf; color:#fff; border:1px solid #2456b8;"
                        "border-radius:4px; padding:2px 8px; font-size:11px; font-weight:bold;")












    _WARMUP_LOGO = "🤸"

    # Wishlist-area cycle labels, indexed by _wish_state (0 off · 1..4 wishlists).
    # No ⭐ in front: the button paints it, with the count in its corner.
    _WISH_LABELS = ("No wishlist", "1 wishlist", "2 wishlists",
                    "3 wishlists", "4 wishlists")



























    # The focused deck's generation context (gui.decks.deck.DeckContext), read and
    # written as window attributes. The window holds no copy of its own.
    _mode = DeckField()
    _ui_mode = DeckField()
    _style = DeckField()
    _age = DeckField()
    _dance_class = DeckField()
    _dances = DeckField()
    _playlist = DeckField()
    _replay_label = DeckField()
    _replay_active = DeckField()
    _replay_rounds = DeckField()
    _replay_pools = DeckField()
    _replay_use_timbre = DeckField()
    _active_replay_idx = DeckField()
    _theme_entries = DeckField()
    _theme_label = DeckField()

















    # ── Library callbacks ─────────────────────────────────────────────────────








    # ── In-progress playlist autosave / restore ─────────────────────────────────

    # ── Per-competition work preservation (Past Competitions) ────────────────────


















        # When turned off the browser just stops consulting the set; nothing to do.





    # Beats per bar by dance: filename BPM values are BARS per minute, librosa
    # measures BEATS per minute — the product of the two bridges them.
    _BEATS_PER_BAR = BEATS_PER_BAR
    # Metric levels a beat tracker commonly locks onto instead of the true
    # beat: octaves (×2, ×4), the bar of triple meters (×3) and the dotted /
    # compound groupings (×1.5). Any of these counts as "matching the label".
    # (Samba's old ×0.75 slip excuse was dropped once the analyzer gained a
    # dance-seeded tempo prior — see planner.music.analysis._tempo_prior.)
    _TEMPO_RATIOS = (1.0, 2.0, 0.5, 3.0, 1 / 3, 4.0, 0.25, 1.5, 2 / 3)
    # Check-music length thresholds — DEFAULTS only; the live values come from
    # Settings → 🎵 Checks (check_min_play_secs / check_max_play_secs).
    # Shortest a competition cut may run and still cover the 1:30–1:45 play time
    # (TSO heat length). At or below this (no margin at all) the song would fade
    # out / loop mid-heat.
    _MIN_PLAY_SECS = 105   # 1:45
    # Longest a cut should run — past this it drags and wastes floor time
    # (mirrors the Java checkIfLongLength threshold of 4:00).
    _MAX_PLAY_SECS = 240   # 4:00
    # 🔇 Loudest noise floor a track may have before it counts as hissy. Over
    # 150 random library tracks the median floor is −78 dB and only ~3 % stay
    # above −50 dB — old medleys and anthem rips (Settings → 🎵 Checks).
    _NOISE_FLOOR_DB = -50.0













    def _register_toolbar_btn(self, btn):
        """Remember the full label + leading icon of a toolbar button that shrinks
        to an icon-only square when the toolbar gets too narrow."""
        full = btn.text()
        btn.setProperty("fullText", full)
        btn.setProperty("iconText", self._toolbar_icon_text(btn, full))
        if not btn.toolTip():
            btn.setToolTip(full)

    @staticmethod
    def _toolbar_icon_text(btn, full: str) -> str:
        """What a toolbar button shrinks to: its leading emoji — or, for a button
        wearing a painted icon, the bare count it carries ('countText'), so the
        number stays readable as text and not only as the badge. A button that
        pinned its own square ('iconTextFixed') keeps it through any relabel."""
        fixed = btn.property("iconTextFixed")
        if fixed:
            return fixed
        if not btn.icon().isNull():
            return btn.property("countText") or ""
        return full.split("  ", 1)[0].strip() or full

    def _set_toolbar_btn_text(self, btn, full):
        """Change a toolbar button's caption (e.g. '⧉  2 playlists') while
        honouring the current compaction level — a plain setText would blow an
        icon-only button back up to (clipped) full text."""
        btn.setProperty("fullText", full)
        btn.setProperty("iconText", self._toolbar_icon_text(btn, full))
        iconized = (self._toolbar_compact >= 2
                    or (self._toolbar_compact == 1 and btn in self._toolbar_icon_btns))
        btn.setText(btn.property("iconText") if iconized else full)
        self._paint_count_icon(btn, iconized)

    @staticmethod
    def _paint_count_icon(btn, iconized: bool):
        """The badge on a cycle button, but only once its caption is gone: with
        '2 wishlists' still written on the button the number is already said."""
        ch = btn.property("countEmoji")
        if ch:
            btn.setIcon(counted_emoji(
                ch, btn.property("countText") if iconized else None, 16))

    def _toolbar_icon_width(self, btn) -> int:
        return max(30, btn.fontMetrics().horizontalAdvance(
            btn.property("iconText")) + 12)

    def _apply_toolbar_compact(self, level: int):
        """0 = full labels, 1 = view buttons icon-only, 2 = everything icon-only."""
        if level == self._toolbar_compact:
            return
        self._toolbar_compact = level
        for b in self._toolbar_btns:
            iconized = level >= 2 or (level == 1 and b in self._toolbar_icon_btns)
            self._paint_count_icon(b, iconized)
            if iconized:
                b.setText(b.property("iconText"))
                b.setFixedWidth(self._toolbar_icon_width(b))
            else:
                b.setText(b.property("fullText"))
                b.setMinimumWidth(0)
                b.setMaximumWidth(16777215)

    def closeEvent(self, event):
        """Save the working playlist and the window layout before quitting."""
        if not self._may_quit():
            event.ignore()
            return
        self.save_on_quit()
        # Before the widgets go: the announcer's engine is a child of this
        # window and reports one last state change as it is torn down, and a
        # looping cartwall pad still holds its file open.
        self._announcer.shutdown()
        # A window of its own, so it does not follow this one down by itself.
        log_dlg = getattr(self, "_ai_log", None)
        if log_dlg:
            log_dlg.close()
        self._cartwall_shutdown()
        self._taskbar_shutdown()
        self._stop_remote()
        self._guest_shutdown()
        self._controller_shutdown()
        self._audio_device.hold_system_sounds(False)
        self._stop_workers()
        # The start's backup is from before this session: write today's again,
        # with the evening's plays, once nothing else is writing to the DB.
        backup_safely(refresh=True)
        super().closeEvent(event)

    def _stop_workers(self):
        """Let every background worker finish before this window takes its
        children down with it. Qt aborts the process outright — no traceback,
        just 0xC0000409 — if a QThread is destroyed while it is still running,
        and every play of an un-analyzed track arms a 🔇 silence probe.
        All are told to stop first, so their 5 s waits run side by side."""
        running = [w for w in self.findChildren(QThread) if w.isRunning()]
        for worker in running:
            cancel = getattr(worker, "cancel", None)
            if callable(cancel):
                cancel()
        for worker in running:
            if not worker.wait(5000):
                log.warning("🧵 Worker would not stop at quit\n"
                            "worker: %s", type(worker).__name__)
                # Qt aborts the process if a running QThread is destroyed, and
                # the window is about to destroy its children.
                adopt_running(worker)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_toolbar_compact()

    def _update_toolbar_compact(self):
        """Pick the compaction stage the toolbar's CURRENT width allows.

        Driven from the bar's own resize as well as the window's: the row sits
        in the right pane of the splitter, so folding the config panel away or
        dragging the divider changes its width while the window never moves.
        """
        bar = getattr(self, "_toolbar_widget", None)
        if bar is None:
            return
        # Measure the natural (all full-label) widths only while fully expanded,
        # then pick the deepest compaction stage the row still fits. The stored
        # widths stay stable in compact mode so the threshold doesn't flip-flop.
        if self._toolbar_compact == 0:
            # Only what is on screen: an app mode that hides half the actions
            # (see _apply_app_mode) must not keep demanding their width and
            # compact a row that fits comfortably.
            vis = [b for b in self._toolbar_btns if not b.isHidden()]
            extras = 4 * (len(vis) + 1) + 24 + 24             # gaps + ⯇ + ❔
            full = {b: b.sizeHint().width() for b in vis}
            icon = {b: self._toolbar_icon_width(b) for b in vis}
            self._toolbar_full_width = sum(full.values()) + extras
            self._toolbar_l1_width = (
                self._toolbar_full_width
                + sum(icon[b] - full[b] for b in self._toolbar_icon_btns
                      if b in full))
            self._toolbar_l2_width = sum(icon.values()) + extras
        w = bar.width()
        if w >= self._toolbar_full_width:
            level = 0
        elif w >= self._toolbar_l1_width:
            level = 1
        else:
            level = 2
        self._apply_toolbar_compact(level)

    def _show_shortcuts(self):
        """F1 / ❔: the cheat sheet — see `gui.dialogs.shortcuts`."""
        show_shortcuts(self)

    def _check_menu(self) -> QMenu:
        """🚦 Check: Ready? and, for the planning side, the tools it sums up."""
        menu = _without_gutter(QMenu(self))
        menu.setToolTipsVisible(True)
        menu.addAction("🚦  Ready?", self._check_readiness).setToolTip(
            "Pre-flight before the event, one traffic light per check — over every\n"
            "deck that holds titles and the Practice list, each with its fix.\n"
            "A heading in the report opens its full tool.")
        if app_mode_of(self._settings) in ("planner", "both"):
            menu.addSeparator()
            menu.addAction("🔁  Check duplicates", self._check_duplicates).setToolTip(
                "Scan the visible playlist deck(s) for songs that appear more than once,\n"
                "then resolve each: keep the ones you want and replace the rest with a\n"
                "similar track (chosen from the Similar-Tracks picker).")
            menu.addAction("🎵  Check music", self._check_music).setToolTip(
                "Check every deck track for tournament problems:\n"
                "• Tempo: filename label (T51 = takt/bars per minute, via the dance's\n"
                "  meter) vs the tempo librosa measured — catches mislabeled files.\n"
                "• TSO range: is the tempo inside the official per-dance takt range.\n"
                "• Length: warns when a song is shorter than the 1:30–1:45 play time\n"
                "  or longer than 4:00.\n"
                "• Round structure: uneven dance counts in a round and final/semifinal\n"
                "  heat-count deviations.\n"
                "Suspects can be listened to, removed or replaced from the report.\n"
                "Tempo/range checks need 🔬 Audio Analysis for the measured tempo.")
            menu.addAction("🧭  Fix paths", self._fix_deck_paths).setToolTip(
                "Relocate broken track references in the visible deck(s) to matching\n"
                "real files in the library — fixes moved folders / changed drive\n"
                "letters after an import. Anything still unresolved is reported.")
        return menu

    def _show_check_menu(self):
        btn = self._check_btn
        self._check_menu().exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _help_menu(self) -> QMenu:
        menu = _without_gutter(QMenu(self))
        menu.addAction("⌨  Keyboard shortcuts  (F1)", self._show_shortcuts)
        pdf = manual_pdf()
        if pdf:
            menu.addAction("📖  Manual", lambda: open_manual(pdf))
        menu.addAction("📜  Played titles…", self._show_play_log)
        menu.addAction("⚙  Settings…  (F12 / Ctrl+Alt+S)", lambda: self._open_settings())
        menu.addAction("ℹ  About…", self._show_about)
        menu.addAction("⛶  Exit Fullscreen  (F11)" if self.isFullScreen()
                       else "⛶  Fullscreen  (F11)",
                       lambda: self.set_fullscreen(not self.isFullScreen()))
        return menu

    def _show_help_menu(self):
        """❔: the shortcuts (F1 opens them directly), ⚙ Settings (F12),
        📖 the manual and ℹ About."""
        btn = self._help_btn
        self._help_menu().exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _show_about(self):
        """ℹ About — see `gui.dialogs.about`."""
        show_about(self, app_title(app_mode_of(self._settings)))

    def _show_play_log(self):
        """📜 Played titles — see `player.dialogs.play_log_dialog`."""
        PlayLogDialog(self).exec()

    def eventFilter(self, obj, event):
        """App-wide Ctrl+X / Ctrl+W → close the active dialog; on the main window it only
        dismisses the preview mini player (stop + hide) and NEVER quits the app.
        Skips text-editing widgets so Ctrl+X still cuts text there (line edits,
        the search box, spin boxes…)."""
        # Drag-hover over a deck tab → flip the 8-deck view to that group so the
        # track can be dropped onto one of its 4 decks. The tab bar accepts the
        # drag only to keep the hover events flowing; it never takes the drop.
        if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            for tabs in (self._grid.deck_tabs, self._grid.day_tabs):
                tb = tabs.tabBar()
                if obj is tb:
                    idx = tb.tabAt(event.position().toPoint())
                    if idx >= 0 and idx != tabs.currentIndex():
                        tabs.setCurrentIndex(idx)
                    event.acceptProposedAction()
                    return True
        # Double-click on the 📅 tab → rename it to the competition name.
        if event.type() == QEvent.Type.MouseButtonDblClick:
            tb = self._grid.deck_tabs.tabBar()
            if obj is tb and tb.tabAt(event.position().toPoint()) == 2:
                self._rename_day_tab()
                return True
        # Right-click on a deck tab → 📅: save-competitions / clear / rename /
        # close menu; Group A–D / E–H: clear-that-page menu. Beside the tabs
        # (the bar spans the whole width) → open a 📅 tab.
        if event.type() == QEvent.Type.ContextMenu:
            tb = self._grid.deck_tabs.tabBar()
            if obj is tb:
                idx = tb.tabAt(event.pos())
                if idx == 2:
                    self._day_tab_menu(event.globalPos())
                    return True
                if idx in (0, 1):
                    self._group_tab_menu(idx, event.globalPos())
                    return True
                self._tab_strip_menu(event.globalPos())
                return True
        if event.type() == QEvent.Type.KeyPress:
            # Space (Playing mode): global play/pause of the big player, whatever has
            # focus — so it works without first selecting the playing row. Skips text
            # fields (and the search box) so typing a space still works there.
            if (event.key() == Qt.Key.Key_Space
                    and event.modifiers() == Qt.KeyboardModifier.NoModifier
                    and not event.isAutoRepeat()
                    and self._is_playing_mode() and self._big_player
                    and QApplication.activeWindow() is self):
                fw = QApplication.focusWidget()
                if not isinstance(fw, (QLineEdit, QPlainTextEdit, QSpinBox)):
                    # A double tap is one press, not play-then-pause; the
                    # swallowed tap still must not reach the focused widget.
                    now = time.monotonic()
                    if now - self._space_at >= QApplication.doubleClickInterval() / 1000:
                        self._space_at = now
                        self._big_player.toggle_play()
                    return True
            if (event.key() in (Qt.Key.Key_X, Qt.Key.Key_W)
                    and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                    and not (event.modifiers() & (Qt.KeyboardModifier.ShiftModifier
                                                  | Qt.KeyboardModifier.AltModifier))):
                fw = QApplication.focusWidget()
                # Only Ctrl+X means anything in a text field (cut) — Ctrl+W
                # closes the dialog from wherever the cursor happens to be.
                if (event.key() == Qt.Key.Key_W
                        or not isinstance(fw, (QLineEdit, QPlainTextEdit,
                                               QSpinBox))):
                    win = QApplication.activeWindow()
                    if win is self:
                        cue = self._cue_player()
                        if cue is not None and cue.view.isVisible():
                            cue.stop()            # 🎧 the pre-listen's mini player
                        elif self._preview and self._preview.isVisible():
                            self._on_stop_btn()   # close mini player + stop playback
                        return True               # swallow — never close the app
                    if win is not None:
                        win.close()
                        return True
        # Not super(): QObject.eventFilter only returns False, but it type-checks
        # `obj` — and an app-wide filter can be handed a stale non-QObject wrapper
        # (a QWidgetItem), whose TypeError then poisons every filter after it.
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def _install_crash_log():
    """💥 Hard crashes into crash.log; returns what the previous run left there."""
    # Capture hard crashes even with no console (pythonw / double-click launch):
    # a native fault (segfault / C++ abort) is dumped by faulthandler, and any
    # unhandled Python exception (which PySide6 can turn fatal) is logged too. Both
    # go to crash.log next to the app so we can see WHERE it died.
    import faulthandler
    crash_path = planner.config.APP_DIR / "crash.log"
    # Read the PREVIOUS run's log before the "w" open below truncates it — a
    # non-empty file means the last session crashed (or hit an unhandled
    # exception) and nobody may have seen it.
    prev_crash = ""
    try:
        if crash_path.exists():
            prev_crash = crash_path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as exc:
        log.debug("💥 Could not read the previous crash.log: %s", exc)
    try:
        _crash_log = open(crash_path, "w", encoding="utf-8")
        faulthandler.enable(file=_crash_log)
    except Exception:
        _crash_log = None

    def _log_uncaught(exc_type, exc, tb):
        import traceback as _tb
        text = "".join(_tb.format_exception(exc_type, exc, tb))
        log.error("💥 Uncaught exception:\n%s", text)
        if _crash_log is not None:
            _crash_log.write("\n=== Uncaught Python exception ===\n" + text)
            _crash_log.flush()
    sys.excepthook = _log_uncaught
    return prev_crash


def _open_session_log():
    """📝 The running log into session.log; returns the previous run's log."""
    # Breadcrumbs. A native fault (access violation) dumps only the Python stack,
    # and that stack is always the main thread parked in app.exec() — it says the
    # app died inside Qt, not WHAT it was doing. So the running log goes to
    # session.log next to crash.log, flushed line by line: its last entries name
    # the track that started, the worker that ran, the dialog that opened right
    # before the fault. The previous run is kept as session.prev.log.
    session_path = planner.config.APP_DIR / "session.log"
    prev_session = ""
    try:
        if session_path.exists():
            prev_session = session_path.read_text(encoding="utf-8", errors="replace")
            (planner.config.APP_DIR / "session.prev.log").write_text(
                prev_session, encoding="utf-8")
    except Exception as exc:
        log.debug("📝 Could not keep the previous session log: %s", exc)
    try:
        _fh = logging.FileHandler(session_path, mode="w", encoding="utf-8")
        _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname).1s %(message)s",
                                           datefmt="%H:%M:%S"))
        logging.getLogger().addHandler(_fh)
    except Exception as exc:
        log.debug("📝 Could not open the session log: %s", exc)
    return prev_session


def _route_qt_messages():
    """🧩 Qt's qWarning and friends into the Python log."""
    # Qt's own diagnostics into the same file — the multimedia backend reports
    # its failures through qWarning, where nothing was listening until now.
    # No Qt debug category is switched on to feed it: the handler is Python, so
    # it runs on the sender's thread, and a message from the FFmpeg renderer's
    # thread while the GUI thread waits on that thread in QMediaPlayer.stop()
    # deadlocks on the GIL (tests/player/test_audio_dropouts.py).
    def _qt_message(mode, _ctx, msg):
        log.log({QtMsgType.QtDebugMsg: logging.DEBUG,
                 QtMsgType.QtInfoMsg: logging.INFO,
                 QtMsgType.QtWarningMsg: logging.WARNING,
                 QtMsgType.QtCriticalMsg: logging.ERROR,
                 QtMsgType.QtFatalMsg: logging.CRITICAL}.get(mode, logging.INFO),
                "🧩 Qt: %s", msg)
    qInstallMessageHandler(_qt_message)


def _set_taskbar_identity():
    """🪟 The taskbar button groups under the app's own icon."""
    # Windows groups taskbar buttons by an "AppUserModelID". Without an explicit
    # one a Python-hosted app inherits the interpreter's identity and shows the
    # generic python.exe icon — set our own BEFORE any window is created so the
    # taskbar picks up the app icon below.
    if sys.platform == "win32":
        try:
            import ctypes
            # Bump the suffix to bust Windows' per-AppUserModelID taskbar icon
            # cache when the icon changes (it pins the icon to this string).
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "danceplaylist.ai.planner.v3")
        except Exception as exc:
            log.debug("🪟 Could not set the taskbar AppUserModelID: %s", exc)


def _show_previous_crash(window, prev_crash, prev_session):
    """💥 Tell about last session's crash, with its log under the details."""
    log.warning("💥 Previous session left a non-empty crash.log (%s chars)",
                len(prev_crash))
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Previous session crashed")
    box.setText(
        "💥  The app did not shut down cleanly last time.\n\n"
        "The crash log of that session is under 'Show Details…' "
        "(it is overwritten on every start).")
    # The stack alone never says what the app was doing — the tail of that
    # session's log does. Both go into the details, so one copy-paste is
    # enough to find the crash.
    tail = "\n".join(prev_session.splitlines()[-80:])
    box.setDetailedText(
        prev_crash[-20000:]
        + ("\n\n=== Last log lines of that session ===\n" + tail if tail else ""))
    box.exec()


def run_gui():
    # Planner diagnostics (scans, migrations, analysis errors) go through logging;
    # show them on the console the GUI was launched from. Under pythonw there is
    # no console (sys.stdout is None) → fall back to basicConfig's stderr default.
    if sys.stdout is not None:
        logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    prev_crash = _install_crash_log()
    prev_session = _open_session_log()
    _route_qt_messages()
    # 📥 A venue pack imported in the last session takes over now — before the
    # first read of the settings, and after the last window that could have
    # written over them has closed.
    try:
        venue_pack.apply_pending(state_dir())
    except Exception as exc:
        log.error("⚠️ Venue pack could not be applied: %s", exc)
    # ⚙ Settings → 🔊 Audio backend overrides the platform default picked at the
    # top of this file. Here and nowhere later: Qt loads the backend plugin the
    # first time something plays and never reads the variable again — which is
    # also why the setting only takes effect on the next start.
    apply_media_backend(load_settings())
    # 🐞 Opt-in error reports. After sys.excepthook is set above: the client
    # wraps the hook it finds, so crash.log keeps getting the traceback too.
    error_reports.apply_settings(load_settings())
    log.info("🚀 Session start\n"
             "version: %s\n"
             "python: %s\n"
             "media backend: %s", app_version(), sys.version.split()[0],
             os.environ.get("QT_MEDIA_BACKEND", "default"))
    _set_taskbar_identity()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # App-wide icon → every window + the taskbar button use it.
    app.setWindowIcon(_app_icon())
    # The title bar already shows that icon: "⚙  Settings" would be two.
    install_plain_title_hook()

    # 🎨 The theme, before a single widget exists: the hook has to be in place
    # before the first stylesheet is set, and the shared QColor constants have
    # to be re-shaded before the first table paints a row. Light with the
    # default accent leaves every colour exactly as it was.
    startup_settings = load_settings()
    # The looks of your own first, or a stored own look reads as unknown.
    user_looks.load_looks()
    theme.apply_settings(startup_settings)
    theme.install_stylesheet_hook()
    theme.sync_shared_colors()
    theme.install_titlebar_hook()
    theme.apply_app(app)
    # Under a 🎨 look the chrome's emoji become one icon set; the classic
    # themes keep them. Before i18n, so it splits the translated caption.
    look_icons.install()

    # 🌐 …and the language for the same reason: a label built in English is not
    # revisited later. This has to come before ensure_app_mode(), which is the
    # first thing that puts a dialog on screen. English patches nothing.
    i18n.apply_settings(startup_settings)
    terms.apply_settings(startup_settings)
    i18n.install_text_hook()
    i18n.install_qt_translator(app)

    # First start only: planner, player or both. Asked before the window exists,
    # so MainWindow simply reads the answer out of the settings like any other.
    ensure_app_mode()
    # 🐞 Asked once too, right after it; a yes starts the client now rather
    # than on the next start.
    if ensure_error_reports_choice():
        error_reports.apply_settings(load_settings())
    # 🔔 Asked under that question; asked on its own only where it was not.
    ensure_update_check_choice()

    window = MainWindow()  # kept until app.exec() returns; shows itself after library loads
    update_notice = UpdateNotice(window)
    update_notice.start(load_settings())

    if prev_crash:
        # Deferred into the event loop so the library keeps loading behind the
        # notice instead of startup blocking on the dialog.
        QTimer.singleShot(0, lambda: _show_previous_crash(
            window, prev_crash, prev_session))

    exit_app(app.exec())


if __name__ == "__main__":
    run_gui()
