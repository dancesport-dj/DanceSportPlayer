#!/usr/bin/env python3
"""
dancesport_gui.py  –  PySide6 GUI for the Dancesport Playlist Planner

Run:  py dancesport_gui.py
CLI:  py dancesport_planner.py
"""
import io
import os
import sys
import logging
from pathlib import Path
from collections.abc import Callable

# The log goes to stdout with emoji in it. A Windows console is cp1252, so wrap
# it as UTF-8; a windowed build has no stdout at all (sys.stdout is None).
if (sys.stdout is not None and sys.stdout.encoding
        and sys.stdout.encoding.lower() not in ('utf-8', 'utf-8-sig')):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QPushButton, QLabel,
        QLineEdit, QPlainTextEdit, QMessageBox, QSizePolicy,
        QSpinBox,
        QToolButton,
        QStackedWidget,
        QTabWidget, QTabBar, QScrollArea, QFrame, QMenu,
    )
    from PySide6.QtCore import (
        Qt, QTimer, QEvent, QSize, QThread, QtMsgType, qInstallMessageHandler,
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
# player/announce.py), reports position 0 at a pause, and is the backend the ⏭
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
from planner.version import app_version
from planner.db import AudioCache
from planner.library import MusicLibrary
from planner.suggester import PlaylistSuggester

log = logging.getLogger("dancesport.gui")

def exit_app(code: int):
    """Leave the process once the event loop has returned.

    Normally a plain `sys.exit`. But destroying a QThread that is still running
    aborts the process (0xC0000409), and interpreter teardown would destroy the
    workers `adopt_running` holds — so while one runs, leave without tearing
    anything down. Every save already ran in `closeEvent`; a worker's open
    SQLite transaction rolls back as it would after a power cut."""
    if orphans_running():
        logging.shutdown()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    sys.exit(code)


# ── Shared GUI modules (light split) ─────────────────────────────────────────
# Background workers and all dialogs/shared widgets live in their own modules;
# the names are re-imported here so the rest of this file keeps using them
# unchanged.
from gui.workers import (
    LibraryLoader, GlobalLibraryLoader, GlobalCacheLoader, AudioAnalyzer,
    SimilarFromFileWorker,
    LoudnessAnalyzer, PdHighlightAnalyzer,
    SilenceAnalyzer, VocalShareAnalyzer,
    adopt_running, orphans_running,
)
from shared.audio_probes import LoudnessWorker, PdHighlightWorker, SilenceWorker
from shared.icons import counted_emoji
from shared import error_reports, theme
from planner import i18n, terms
from gui.deck import Deck, DeckContext, DeckField
from gui.undo_timeline import UndoTimeline
from gui.shortcuts import show_shortcuts
from gui.about import show_about
from gui.common import (
    BusyDialog,
    DEFAULT_HIDDEN_COLUMNS,
    LoadingDialog,
    install_plain_title_hook,
)
from shared.audio_files import (
    set_browse_dir,
)
from shared.widgets import (
    _app_icon,
)
from gui.dialogs import (  # auto-resolved
    load_settings,
    app_mode_of,
    app_title,
    ensure_app_mode,
    ensure_error_reports_choice,
    warmup_name,
    PLAYER_FIRST_START,
    apply_media_backend,
    TOURNAMENTS,
)
from shared.stores import (
    save_settings,
)

# ── View widgets (light split) ───────────────────────────────────────────────
# Each standalone widget class lives in its own gui_* module; the names are
# re-imported here so MainWindow and the smoke scripts keep using them unchanged.
# === split re-exports ===

from gui.playlist_table import (  # noqa: F401  (facade re-export)
    PlaylistTable,
)

from gui.config_panel import (  # noqa: F401  (facade re-export)
    ConfigPanel,
)

from player.play_mode_panel import (  # noqa: F401  (facade re-export)
    PlayModePanel,
)

from player.presenter import (  # noqa: F401  (facade re-export)
    PresenterWindow,
)

from player.taskbar import (  # noqa: F401  (facade re-export)
    TaskbarPlayer,
)

from player.announce import (  # noqa: F401  (facade re-export)
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

from player.mix import OutputMix
from player.audio_device import AudioDevice
from player.playback_state import PlaybackState
from player.between_dances import BetweenDances
from player.pause_filler import PauseFiller
from player.system_sounds import SystemSoundGuard

from player.player import (  # noqa: F401  (facade re-export)
    _fmt_ms,
    _round_half_up,
    _ClickSlider,
    PreviewOverlay,
    BigPlayerWidget,
)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────
# MainWindow is assembled from concern mixins (see gui_main_*):
from gui.main_decks import DeckLayoutMixin
from gui.main_generate import GenerateMixin
from gui.main_import import ImportMixin
from gui.main_persist import PersistenceMixin
from player.main_player import PlayerControlMixin
from gui.main_global import GlobalIndexMixin
from player.main_cartwall import CartwallMixin


class _ToolbarRow(QWidget):
    """The toolbar strip, which reports when its OWN width changes.

    It sits in the right pane of the main splitter, not in the window, so the
    two widths come apart whenever the config panel folds or the divider is
    dragged — and the window, which is all `resizeEvent` hears, never moves.
    Reporting from here rather than through the app-wide filter on qApp keeps
    the callback tied to this widget's lifetime: Resize is far too common an
    event to be dereferencing a torn-down window's attributes on.
    """

    def __init__(self, on_resize):
        super().__init__()
        self._on_resize = on_resize

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_resize()


class MainWindow(QMainWindow, DeckLayoutMixin, GenerateMixin, ImportMixin, PersistenceMixin, PlayerControlMixin, GlobalIndexMixin, CartwallMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DanceSport Planner & Player")
        self.resize(1500, 900)

        # Undo/redo: snapshot-based timeline of full-UI env dicts (see _build_env).
        self._undo_timeline = UndoTimeline(limit=50)
        self._restoring     = False             # guards edit hooks during _apply_env

        self._lib:        MusicLibrary | None      = None
        self._cache:      AudioCache | None         = None
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
        # Every open/add picker starts where the last one ended.
        set_browse_dir(self._settings.get("open_dir", ""),
                       self._remember_open_dir)
        self._global_lib:    MusicLibrary | None     = None
        self._global_loader: GlobalLibraryLoader | None = None
        self._pending_drop:  str | None              = None
        self._pending_after_global: Callable[[], None] | None = None
        self._index_analyzer: AudioAnalyzer | None   = None
        self._cache_loader:  GlobalCacheLoader | None = None
        self._emb_idx_worker = None
        self._allcache = None
        self._allcache_worker = None   # the probe step running inside it

        self.setWindowIcon(_app_icon())

        # ── Media player ──
        # 🎵 The loaded title, its dance, the load token and the silence skipped
        # on it — read across the player, pause, Paso Doble and loudness parts.
        self._playback = PlaybackState()
        # ⏱ Start-up latency of the running play request: when the ▶ was handled
        # and whether the "media ready" line has already been logged for it.
        self._play_t0: float | None = None
        self._play_ready_logged = False
        # 🔊 Every output level, and the factors behind it — see player.mix. Held
        # apart from each other so they never fight: the user's slider, the
        # per-track loudness gain, the fade-out ramp and the two ducks.
        self._mix = OutputMix(float(self._settings.get("master_volume", 0.9)))
        # The 🎛 cartwall's own voice pool, built later in _build_cartwall.
        # Assigned here because _apply_volume() below already reads it.
        self._cart_voices = None
        # 🔕 The OS's own sounds off the PA while the evening runs (see
        # player.audio_device.watch_system_sounds). A run that crashed while
        # holding the mute left it on — lift it before anything else.
        _system_sounds = SystemSoundGuard()
        _leftover = self._settings.pop("system_sounds_muted", None)
        if _leftover is not None:
            _system_sounds.restore_leftover(_leftover)
            save_settings(self._settings)
        if HAS_MULTIMEDIA:
            self._player     = QMediaPlayer(self)
            self._audio_out  = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_out)
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
            self._pause_player.mediaStatusChanged.connect(
                self._on_pause_media_status)
            self._pause_out.setVolume(0.0)
        else:
            self._player = None
            self._audio_out = None
            self._pause_player = None
            self._pause_out = None
        # 🔊 The sound card: follows the Windows default, is handed back while
        # nothing plays, keeps the OS's own sounds off the PA.
        self._audio_device = AudioDevice(
            self._player, self._audio_out, self._pause_player, self._pause_out,
            mix=self._mix,
            settings=lambda: self._settings,
            cart_voices=lambda: self._cart_voices,
            is_playing_mode=self._is_playing_mode,
            apply_volume=self._apply_volume,
            system_sounds=_system_sounds)
        if self._player is not None:
            # 🔇 Idle audio release (setting "release_audio_idle"): both
            # pipelines report back so the sound device is taken again before a
            # title is heard, whichever of the many play paths started it —
            # see player.audio_device.ensure.
            self._player.playbackStateChanged.connect(
                self._audio_device.on_playback_state)
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
            self._device_watch.start()
        self._filler = PauseFiller()   # 🎵 the pause's filler titles and fade

        # Timed-play engine (▶ Playing mode): a 200 ms tick drives the countdown,
        # the fade-out ramp and the end-of-play-length stop. Position-based, so
        # pausing/seeking behaves naturally.
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(200)
        self._fade_timer.timeout.connect(self._on_play_tick)
        # 🔉 Level changes that happen DURING a title ride their own fast timer:
        # the announcement duck and a loudness gain that only arrives once the
        # track is already running. How far each step moves is player.mix's, so
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
            voice=str(self._settings.get("announce_voice", "female")))
        # Manual "fade out now" (🔉↓ on the card): monotonic time the fade ends
        # (None = not fading) and the fade's total length, for the ramp ratio.
        self._fade_now_end: float | None = None
        self._fade_now_total = 0.0
        # True while the 🛑 panic fade runs: at the bottom of the ramp the song
        # is PAUSED in place instead of ended, so nothing auto-advances.
        self._fade_now_hold = False
        # 🕘 (dance, title) of the title before the running one — the presenter
        # screen shows it when asked to; None until a second title starts.
        self._last_played: tuple[str, str] | None = None
        # A track counts as "played" (greyed) once it has actually been heard
        # for this many ms — robust against the operator skipping rows around.
        self._PLAYED_AFTER_MS = 10_000
        self._played_marked = False   # current track already marked played?
        # ↩ Where each title was left, in ms, keyed by path — one player serves
        # every deck, so leaving a title to hear another one is the normal way
        # to lose your place in it. Session-scoped on purpose (the ▶️ Remember
        # switch on the Playing panel): a mark is about the evening being
        # planned, not something to find again next week.
        self._resume_pos: dict[str, int] = {}
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
        if self._player:
            self._preview = PreviewOverlay(self._player, self._audio_out,
                                           get_vol=lambda: self._mix.base,
                                           set_vol=self._set_base_volume)
            self._preview.closeRequested.connect(self._on_stop_btn)
            self._preview.disableRequested.connect(self._disable_preview)
            self._preview.prevRequested.connect(lambda: self._preview_skip(-1))
            self._preview.nextRequested.connect(lambda: self._preview_skip(+1))
            self._preview.duckToggled.connect(self._set_desk_duck)

        # ── Central layout ──
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter = splitter
        outer.addWidget(splitter, stretch=1)

        # Left: config panel
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
        self._analyzer: AudioAnalyzer | None = None
        self._sim_worker: SimilarFromFileWorker | None = None
        self._busy: BusyDialog | None = None

        # Mode switch above the panel: 📝 Planning (combos, generate, settings)
        # ⇄ ▶ Playing (timed-play controls for the tournament floor). The whole
        # left side flips via a QStackedWidget; playback keeps running across it.
        self._play_panel = PlayModePanel(self._settings)
        self._play_panel.settingsChanged.connect(self._save_play_settings)
        self._play_panel.settingsChanged.connect(self._refresh_set_lights)
        self._wire_advance_switch()
        self._play_panel.settingsRequested.connect(self._open_settings)
        # Big master player on top of the Playing-mode panel (UltraMixer-style).
        self._big_player: BigPlayerWidget | None = None
        if self._player:
            self._big_player = BigPlayerWidget(
                self._player, self._audio_out,
                get_vol=lambda: self._mix.base,
                set_vol=self._set_base_volume)
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
        self._loudness_worker: LoudnessAnalyzer | None = None
        self._vocals_worker: VocalShareAnalyzer | None = None
        self._play_panel.pdLearnRequested.connect(self._learn_pd_highlight)
        self._play_panel.pdClearRequested.connect(self._clear_pd_highlight)
        self._play_panel.pdEditToggled.connect(self._on_pd_edit_toggled)
        self._play_panel.pdMarkDeleteRequested.connect(self._delete_pd_mark)
        self._play_panel.announceTestRequested.connect(self._announce_test)
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
        QApplication.instance().screenRemoved.connect(self._on_screen_removed)
        QApplication.instance().screenAdded.connect(self._on_screen_added)
        self._play_panel.presenterThemeChanged.connect(self._theme_presenter)
        self._play_panel.timetableRequested.connect(self._edit_timetable)
        # 🪟 ⏮ ⏯ ⏭ under the taskbar thumbnail on hover.
        self._taskbar: TaskbarPlayer | None = None
        self._init_taskbar()
        # 🏆/🎉 lights: read off the controls, which the settings restored
        # a moment ago — so they need no memory of their own.
        self._refresh_set_lights()
        self._play_panel.partySetToggled.connect(self._set_party_mode)
        self._play_panel.tournamentSetRequested.connect(self._apply_tournament_set)
        # 🖼 Cover art on the player card, as the setting left it.
        self._play_panel.artworkToggled.connect(self._set_artwork_shown)
        self._play_panel.rememberToggled.connect(self._set_remember_pos)
        if self._big_player:
            self._big_player.set_artwork_enabled(self._play_panel.show_artwork())
        self._pd_analyzer: PdHighlightAnalyzer | None = None
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
            b.setStyleSheet(
                "QPushButton{border:1px solid #b9d4f2; background:#f4f7fb;}"
                "QPushButton:checked{background:#1565c0; color:white;"
                " font-weight:bold;}")
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
        splitter.addWidget(left_box)

        # Right: two playlist decks + wishlist + player bar
        right = QWidget()
        rl = QVBoxLayout(right)
        # …kept: the wide player docks into it above the decks.
        self._right_col = rl
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)

        # Three tables: two full playlist decks side-by-side + a flat wishlist below.
        # Controls (Generate / Save / ↺ / play / collapse) act on the focused deck.
        self._tableA    = PlaylistTable()
        self._tableB    = PlaylistTable()
        self._tableC    = PlaylistTable()
        self._tableD    = PlaylistTable()
        # Decks E–H back the 8-playlist mode: a second 2×2 grid shown on its own tab
        # ("Group E–H") so eight playlists never crowd the screen at once.
        self._tableE    = PlaylistTable()
        self._tableF    = PlaylistTable()
        self._tableG    = PlaylistTable()
        self._tableH    = PlaylistTable()
        self._wishlist  = PlaylistTable()
        self._wishlist2 = PlaylistTable()
        self._wishlist3 = PlaylistTable()
        self._wishlist4 = PlaylistTable()
        self._wishlist._flat_mode  = True
        self._wishlist2._flat_mode = True
        self._wishlist3._flat_mode = True
        self._wishlist4._flat_mode = True
        # Dedicated warm-up (Eintanzen) list — its own panel between the decks and the
        # wishlist area, never clobbering a playlist. Holds a single warm-up list with
        # ↺ timbre re-roll + drag-drop replace; hidden until a warm-up is generated.
        self._warmup_table = PlaylistTable()
        # Up to eight full playlist decks (generation targets); 1/2/4/8 shown via _dual_btn
        # (8 = two tabs of four).
        self._decks      = [self._tableA, self._tableB, self._tableC, self._tableD,
                            self._tableE, self._tableF, self._tableG, self._tableH]
        # Eight dedicated 📅 day decks on the third tab ("Tournament day", two
        # sub-tabs of four). Filled only by the 📅 Day-plan planner, so decks A–H
        # always stay normal working playlists; the tab shows while they hold a plan.
        self._day_decks  = [PlaylistTable() for _ in range(8)]
        self._wishlists  = [self._wishlist, self._wishlist2,
                            self._wishlist3, self._wishlist4]
        self._all_tables = (self._decks + self._day_decks
                            + self._wishlists + [self._warmup_table])
        self._table      = self._tableA                   # the focused/active deck
        self._deck_count = 1                              # visible deck count: 1, 2, 4 or 8
        # One Deck per table, holding everything this window keeps about it
        # (see gui.deck); reached through self.deck(table), never directly.
        self._deck_of: dict[PlaylistTable, Deck] = {}
        self.deck(self._tableA).ctx = self._boot_ctx

        for t in self._all_tables:
            t._seek_cb = self._seek   # Ctrl+←/→ seeks ∓30 s
            t._short_secs_cb = lambda t=t: self._configured_play_secs(t)   # orange ⏱ on short tracks
            t._play_secs_cb = self._track_play_secs   # ⏱ tooltip: real play time
            t._edge_silence_cb = self._track_edge_silence   # red ⏱ past 5 s
            t.set_change_callback(self._autosave_playlist)
            t.focused.connect(self._on_table_focused)
            t.playRequested.connect(self._on_deck_play)
            t.saveRequested.connect(self._on_table_save_requested)
            t.saveToTournamentsRequested.connect(
                lambda t: self._on_table_save_requested(t, file_in_tree=True))
            t.cleared.connect(self._on_table_cleared)
            # Order matters: the stop clears the playing title, which is what
            # then lets the cue put the new list's first track on the player.
            t.loaded.connect(self._stop_if_playing_from)
            t.loaded.connect(self._cue_first_track)
            t.dynamicChanged.connect(self._on_deck_dynamic_changed)
            t.set_columns_callback(self._on_columns_changed)
            t.set_widths_callback(self._on_column_widths_changed)
            t.set_dance_names_callback(self._on_dance_names_changed)
            t.set_rating_callback(self._set_entry_rating)
            # ⏭/✋ in the deck's bottom-right corner — THIS deck's auto-advance
            # answer, within reach while a round runs. The panel's switch is
            # what it falls back to (see _deck_advance).
            t.set_advance_toggle(lambda t=t: self._deck_advance(t),
                                 lambda on, t=t: self._set_deck_advance(t, on))
            t.setToolTip(
                "Space: play / stop the selected song\n"
                "Ctrl + ← / → : seek 30 s back / forward\n"
                "Click a round / dance header to collapse or expand it")
        for t in self._decks + self._day_decks:
            # Empty deck → first drop turns dynamic; capacity comes from the Rounds field.
            t._capacity_provider = self._current_capacity

        # Which columns each KIND of list shows (header right-click). A wishlist
        # has no use for Heat and ↺, a deck does — and there are four wishlists
        # and sixteen decks, so the tick belongs to the kind, not to the table
        # the user happened to right-click. Saved in gui_settings.json.
        saved_cols = self._settings.get("hidden_columns") or {}
        saved_widths = self._settings.get("column_widths") or {}
        saved_short = self._settings.get("short_dances") or {}
        for kind, tables in (("playlist", self._decks + self._day_decks),
                             ("wishlist", self._wishlists),
                             ("party", [self._warmup_table])):
            # A saved empty list is a decision (Heat ticked back on), not an
            # absent setting — only the missing key falls back to the default.
            hidden = ([int(c) for c in saved_cols[kind]] if kind in saved_cols
                      else DEFAULT_HIDDEN_COLUMNS.get(kind, []))
            widths = saved_widths.get(kind) or {}
            short = bool(saved_short.get(kind, False))
            for t in tables:
                t.list_kind = kind
                t.set_short_dances(short)
                if hidden:
                    t.set_hidden_columns(hidden)
                if widths:
                    # After the hiding: a width for a column that is put away is
                    # kept for when it comes back, not a reason to show it.
                    t.set_column_widths(widths)

        # Collapse / expand + dual-view toggle toolbar above the decks.
        coll_bar = QHBoxLayout()
        coll_bar.setContentsMargins(0, 0, 0, 0)
        coll_bar.setSpacing(4)
        # One button per job, not two: each says what the NEXT click does.
        self._collapse_btn = QPushButton("⊟  Collapse all")
        self._collapse_btn.setToolTip(
            "Collapse every round and dance header of every playlist —\n"
            "click again to open them all.")
        self._fold_decks_btn = QPushButton("▴  Fold decks")
        self._fold_decks_btn.setToolTip(
            "Fold every visible playlist deck and wishlist to its header tab —\n"
            "click again to open them all.\n"
            "Click a single tab (or its arrow) to open just that one.")
        btn_save_all = QPushButton("💾  Save all")
        btn_save_all.setToolTip(
            "Export every non-empty playlist deck to its own .m3u in the\n"
            "playlist folder at once (wishlists are not included).\n"
            "Each file is named after its deck title.")
        btn_bundle = QPushButton("🧳  USB export")
        btn_bundle.setToolTip(
            "Export playlists as a self-contained venue bundle — asks first\n"
            "whether to take all open decks, only the 📅 tournament day, or\n"
            "saved .m3u files dragged in (wishlists are never bundled).\n"
            "One sub-folder per playlist holding its tracks copied in numbered\n"
            "play order (0_0_1 - Title WW29.mp3) plus the playlist's .m3u — each\n"
            "folder plays in order even without the M3U, from any drive,\n"
            "laptop or UltraMixer at the venue (no path fixing needed there).")
        self._save_state_btn = QPushButton("📌  Save state")
        self._save_state_btn.setToolTip(
            "Save the whole working session right now — every deck, wishlist and the\n"
            "window layout — so it comes back exactly on the next launch.  (Ctrl+Shift+S)\n"
            "(This also happens automatically on every edit and on close.)")
        btn_clear_all = QPushButton("🧹  Clear all")
        btn_clear_all.setToolTip(
            "Empty every playlist deck (wishlists are kept).\n"
            "Tip: Del on a deck's title clears just that one playlist;\n"
            "Del on a wishlist's title clears that wishlist.")
        btn_dups = QPushButton("🔁  Check duplicates")
        btn_dups.setToolTip(
            "Scan the visible playlist deck(s) for songs that appear more than once,\n"
            "then resolve each: keep the ones you want and replace the rest with a\n"
            "similar track (chosen from the Similar-Tracks picker).")
        btn_bpm = QPushButton("🎵  Check Music")
        btn_bpm.setToolTip(
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
        btn_day = QPushButton("📅  Day plan")
        btn_day.setToolTip(
            "Plan a whole tournament day: define the day's competitions\n"
            "(style, age, class, round pattern) and generate them all at once\n"
            "into the 📅 Tournament-day tab — eight dedicated day decks in two\n"
            "sub-tabs, separate from the normal playlists; more than 8\n"
            "competitions stack several per deck. All share one no-repeat\n"
            "pool, so a song never appears in two of the day's competitions\n"
            "(Paso excepted). Exports write one M3U per competition.")
        btn_warmup = QPushButton("🤸  Eintanzen / Party")
        self._warmup_gen_btn = btn_warmup   # caption follows the app mode
        btn_warmup.setToolTip(
            "Build a practice playlist into the focused deck:\n"
            "• Eintanzen for a tournament class — the class's dances round-robin\n"
            "  (e.g. Latin S: SA, CC, RB, PD, JI …), TSO-conform, popular + fresh.\n"
            "• Party — alternating 3-dance rounds across all dances.\n"
            "Draw from your ⭐ Favorites (unused tracks), the open wishlists\n"
            "or a chosen .m3u file.")
        btn_fixpaths = QPushButton("🧭  Fix paths")
        btn_fixpaths.setToolTip(
            "Relocate broken track references in the visible deck(s) to matching\n"
            "real files in the library — fixes moved folders / changed drive\n"
            "letters after an import. Anything still unresolved is reported.")
        btn_print = QPushButton("🖨  Print")
        btn_print.setToolTip(
            "Export the focused playlist as a printable PDF\n"
            "(rounds, heats, titles, lengths) into the playlist folder.")
        # The ⧉ / ⭐ of the two cycle buttons is painted rather than typed, so a
        # count badge can sit in its corner once the toolbar compacts the caption
        # away. 'countEmoji' marks such a button, 'countText' is the number —
        # both the badge and what the caption shrinks to.
        self._dual_btn = QPushButton("1 playlist")
        self._dual_btn.setProperty("countEmoji", "⧉")
        self._dual_btn.setProperty("countText", "1")
        self._dual_btn.setIcon(counted_emoji("⧉", None, 16))
        self._dual_btn.setIconSize(QSize(16, 16))
        # A player build stops the ring at four (_max_decks), so its tooltip may
        # not promise a view that install will never reach.
        eight = self._max_decks() >= 8
        tip = [i18n.t("Cycle 1 → 2 → 4 → 8 → no playlists (and back).") if eight else
               i18n.t("Cycle 1 → 2 → 4 → no playlists (and back)."),
               i18n.t("Right click walks the cycle backwards.")]
        if eight:
            tip.append(i18n.t("8 splits into two tabs of four (Group A–D / Group E–H)."))
        tip += [i18n.t("No-playlist hides every deck so the Eintanzen / wishlist / "
                       "library panes take over."),
                i18n.t("Two or more decks also reveal the wishlist below."),
                i18n.t("Generate / Save / ↺ / play act on whichever deck has focus.")]
        self._dual_btn.setToolTip("\n".join(tip))
        # Header view, cycled in four steps: full → 🗜 compact (no per-dance header
        # rows, the Dance column still names each row) → 🚫 no grouping at all (no
        # round / ─── section headers either — a party list as one flat run) →
        # 🔢 numbers (no grouping, plus an Nb. column counting the titles).
        self._compact_btn = QPushButton("🗜  Compact")
        self._compact_btn.setCheckable(True)
        self._compact_state = int(self._settings.get("compact", 0) or 0)
        if self._compact_state not in (0, 1, 2, 3):
            self._compact_state = 0
        self._compact_btn.setToolTip(
            "Cycle the playlist headers: full → 🗜 Compact (per-dance header rows\n"
            "hidden, each round lists its songs directly) → 🚫 No groups (round and\n"
            "─── section headers dropped too, so the list — an Eintanzen / party\n"
            "list above all — is one flat run of songs) → 🔢 Numbers (no groups,\n"
            "plus an Nb. column up front counting the titles).")
        for t in self._all_tables:
            # Honoured when the tables render during restore. The wishlists are
            # in here too: flat lists have no headers to drop, but their titles
            # get numbered like everything else.
            t._compact = self._compact_state >= 1
            t._nogroup = self._compact_state >= 2
            t.set_numbered(self._compact_state >= 3)
        # Wishlist area cycle button: off → 1 → 2 → 3 → 4 wishlists → 4 stacked 2×2.
        self._wish_state = int(self._settings.get("wish_state", 1))
        if self._wish_state not in (0, 1, 2, 3, 4):
            self._wish_state = 1
        # 2×2 grid only applies with 4 wishlists; ignore a stale flag at other counts.
        self._wish_grid = bool(self._settings.get("wish_grid", False)) and self._wish_state == 4
        self._wish_grid_active = False   # what the splitters are actually wired as
        self._dual_wish_btn = QPushButton(self._wish_label())
        self._dual_wish_btn.setProperty("countEmoji", "⭐")
        self._dual_wish_btn.setProperty("countText", str(self._wish_state))
        self._dual_wish_btn.setIcon(counted_emoji("⭐", None, 16))
        self._dual_wish_btn.setIconSize(QSize(16, 16))
        self._dual_wish_btn.setToolTip(
            "Cycle the wishlist area: off → 1 → 2 → 3 → 4 → 4 stacked 2×2.\n"
            "Right click walks it backwards.\n"
            "Off hides it entirely, even with multiple decks.\n"
            "Double-click any deck/wishlist title to rename it.")
        self._warmup_toggle_btn = QPushButton("🤸  Eintanzen / Party ▾")
        self._warmup_toggle_btn.setCheckable(True)
        # The two 🤸 buttons would be identical at icon size — keep the toggle's ▾
        # (a fixed icon caption, so a mode-driven relabel cannot drop it again).
        self._warmup_toggle_btn.setProperty("iconTextFixed", "🤸▾")
        self._lib_btn = QPushButton("📚  Library")
        self._lib_btn.setCheckable(True)
        self._lib_btn.setChecked(bool(self._settings.get("library_pane", True)))
        self._lib_btn.setToolTip(
            "Show / hide the library browser under the wishlists:\n"
            "filter the whole competition library and drag tracks\n"
            "straight into a deck or wishlist.")
        # Off by default: most tournaments never need sample pads.
        self._cartwall_shown = bool(self._settings.get("cartwall_pane", False))
        self._cart_btn = QPushButton("🎛  Cartwall")
        self._cart_btn.setCheckable(True)
        self._cart_btn.setChecked(self._cartwall_shown)
        self._cart_btn.setToolTip(
            "Show / hide the 🎛 sample-pad wall:\n"
            "drop Tusch, applause or a background bed onto a pad and tap it —\n"
            "it plays on top of the running music instead of replacing it.\n"
            "Drag its title bar to dock it left / right / below, or float it.")
        for b in (self._collapse_btn, self._fold_decks_btn,
                  btn_save_all, btn_bundle, self._save_state_btn, btn_clear_all,
                  btn_dups, btn_bpm, btn_day, btn_warmup, btn_fixpaths, btn_print,
                  self._dual_btn, self._compact_btn, self._dual_wish_btn,
                  self._warmup_toggle_btn, self._lib_btn, self._cart_btn):
            b.setFixedHeight(24)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # The 🤸 Eintanzen / ETDS party list is a playlist like any other here —
        # it has rounds and dance headers to collapse, and being left out of the
        # ⊟ / ⊞ pair made the buttons look broken whenever it was the only list
        # on screen (the no-playlist view).
        self._collapse_btn.clicked.connect(self._toggle_collapse_all)
        self._fold_decks_btn.clicked.connect(self._toggle_fold_all_decks)
        btn_save_all.clicked.connect(self._save_all_playlists)
        btn_bundle.clicked.connect(self._export_bundle)
        btn_day.clicked.connect(self._plan_tournament_day)
        self._save_state_btn.clicked.connect(self._save_state_now)
        btn_clear_all.clicked.connect(self._clear_all_playlists)
        btn_dups.clicked.connect(self._check_duplicates)
        btn_bpm.clicked.connect(self._check_music)
        btn_warmup.clicked.connect(self._generate_warmup)
        btn_fixpaths.clicked.connect(self._fix_deck_paths)
        btn_print.clicked.connect(self._print_running_order)
        # Left click steps the ring forward, right click back. A QPushButton has
        # no right-click signal of its own, so the context-menu request is it —
        # neither button carries a menu, and a right click never fires clicked().
        self._dual_btn.clicked.connect(lambda: self._cycle_deck_view())
        self._dual_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._dual_btn.customContextMenuRequested.connect(
            lambda _pos: self._cycle_deck_view(back=True))
        self._compact_btn.clicked.connect(self._cycle_compact)
        self._dual_wish_btn.clicked.connect(lambda: self._cycle_wish_view())
        self._dual_wish_btn.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._dual_wish_btn.customContextMenuRequested.connect(
            lambda _pos: self._cycle_wish_view(back=True))
        self._warmup_toggle_btn.toggled.connect(self._on_warmup_toggle)
        self._lib_btn.toggled.connect(self._on_library_pane_toggled)
        self._cart_btn.toggled.connect(self._on_cartwall_toggled)
        coll_bar.addWidget(self._collapse_btn)
        coll_bar.addWidget(self._fold_decks_btn)
        coll_bar.addWidget(btn_save_all)
        coll_bar.addWidget(btn_bundle)
        coll_bar.addWidget(self._save_state_btn)
        coll_bar.addWidget(btn_clear_all)
        coll_bar.addWidget(btn_dups)
        coll_bar.addWidget(btn_bpm)
        coll_bar.addWidget(btn_day)
        coll_bar.addWidget(btn_warmup)
        coll_bar.addWidget(btn_fixpaths)
        coll_bar.addWidget(btn_print)
        coll_bar.addStretch(1)
        coll_bar.addWidget(self._dual_btn)
        coll_bar.addWidget(self._compact_btn)
        coll_bar.addWidget(self._dual_wish_btn)
        coll_bar.addWidget(self._warmup_toggle_btn)
        coll_bar.addWidget(self._lib_btn)
        coll_bar.addWidget(self._cart_btn)
        help_btn = QPushButton("❔")
        help_btn.setFixedSize(24, 24)
        help_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        help_btn.setToolTip("Shortcuts (F1) and about this app")
        help_btn.clicked.connect(self._show_help_menu)
        self._help_btn = help_btn
        coll_bar.addWidget(help_btn)
        # Responsive toolbar, two compaction stages: when the row is too narrow to
        # hold every full label (e.g. 1920×1200 at 200 % scale = 960 px effective),
        # first the view buttons collapse to their leading icon; if that still
        # doesn't fit (small displays), EVERY button collapses to its icon — the
        # full label is kept as the tooltip, so nothing gets truncated mid-word.
        self._toolbar_btns = [
            self._collapse_btn, self._fold_decks_btn,
            btn_save_all, btn_bundle, self._save_state_btn, btn_clear_all,
            btn_dups, btn_bpm, btn_day, btn_warmup, btn_fixpaths, btn_print,
            self._dual_btn, self._compact_btn, self._dual_wish_btn,
            self._warmup_toggle_btn, self._lib_btn, self._cart_btn,
        ]
        self._toolbar_icon_btns = [
            self._collapse_btn, self._fold_decks_btn, btn_print,
        ]
        # Toolbar actions that exist only for the planning side: they generate,
        # curate or check a playlist. Hidden in a player-only install
        # (_apply_app_mode); everything else here also serves a tournament.
        self._planner_btns = [btn_bundle, btn_dups, btn_bpm, btn_day, btn_warmup,
                              btn_fixpaths]
        # Hidden by the player-only BUILD rather than by player mode: 🖨 Print
        # renders through Qt6Pdf, which that build does not ship (see
        # dancesport.spec). In every other build it stays, player mode included.
        self._player_build_hidden = [btn_print] if planner.config.player_build() else []
        self._toolbar_compact = 0
        self._toolbar_full_width = 0
        self._toolbar_l1_width = 0
        self._toolbar_l2_width = 0
        for b in self._toolbar_btns:
            self._register_toolbar_btn(b)
        # 🗜 carries a state-dependent caption — set it only now, so the button is
        # registered and the label goes through the compaction-aware setter.
        self._apply_compact_label()
        self._toolbar_widget = _ToolbarRow(self._update_toolbar_compact)
        self._toolbar_widget.setLayout(coll_bar)
        # Buttons report their full-text width as their MINIMUM, which would pin the
        # whole window to a ~3000 px minimum width and stop it being resized narrower
        # (so the icon-compaction below could never trigger). An Ignored horizontal
        # policy lets the bar shrink with the window; resizeEvent then compacts it.
        self._toolbar_widget.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        rl.addWidget(self._toolbar_widget)

        # Decks side-by-side (top) + wishlists (bottom), each under its own header.
        self._rename_edit = None   # active inline header editor (one at a time)
        self._rename_finish = None # teardown callback for the active inline editor
        self._warmup_folded = False                              # Eintanzen panel compacted?
        self._warmup_closed = False                              # Eintanzen panel hidden?
        # Fixed A/B/C/D badge per deck, rendered before the (possibly renamed) title so
        # each playlist stays visually identifiable even after the user renames it.
        for t, letter in zip(self._decks,
                             ("🅰", "🅱", "🅲", "🅳", "🅴", "🅵", "🅶", "🅷")):
            self.deck(t).letter = letter
        # Day decks carry outline (squared) letters so they never get confused
        # with the normal decks' filled 🅰–🅷 badges.
        for t, letter in zip(self._day_decks,
                             ("🄰", "🄱", "🄲", "🄳", "🄴", "🄵", "🄶", "🄷")):
            self.deck(t).letter = letter
        deckA_box        = self._make_deck_box(self._tableA, "Playlist 1")
        self._deckB_box  = self._make_deck_box(self._tableB, "Playlist 2")
        self._deckC_box  = self._make_deck_box(self._tableC, "Playlist 3")
        self._deckD_box  = self._make_deck_box(self._tableD, "Playlist 4")
        self._deckE_box  = self._make_deck_box(self._tableE, "Playlist 5")
        self._deckF_box  = self._make_deck_box(self._tableF, "Playlist 6")
        self._deckG_box  = self._make_deck_box(self._tableG, "Playlist 7")
        self._deckH_box  = self._make_deck_box(self._tableH, "Playlist 8")
        self._day_boxes  = [self._make_deck_box(t, f"📅 Competition {i + 1}")
                            for i, t in enumerate(self._day_decks)]
        self._wish_box   = self._make_deck_box(self._wishlist, "⭐  Wishlist")
        self._wish_box2  = self._make_deck_box(self._wishlist2, "⭐  Wishlist 2")
        self._wish_box3  = self._make_deck_box(self._wishlist3, "⭐  Wishlist 3")
        self._wish_box4  = self._make_deck_box(self._wishlist4, "⭐  Wishlist 4")
        self._warmup_box = self._make_deck_box(self._warmup_table,
                                               self._warmup_title(""))

        # 2×2 grid of decks as two COLUMNS side by side: A above C (left) and
        # B above D (right). Built column-wise (not row-wise) so folding a deck
        # to a tab frees VERTICAL space for the other deck in the same column.
        # Single/Two-deck views use the top decks only.
        self._decks_col1 = QSplitter(Qt.Orientation.Vertical)
        self._decks_col1.addWidget(deckA_box)
        self._decks_col1.addWidget(self._deckC_box)
        self._decks_col1.setSizes([500, 500])
        self._decks_col2 = QSplitter(Qt.Orientation.Vertical)
        self._decks_col2.addWidget(self._deckB_box)
        self._decks_col2.addWidget(self._deckD_box)
        self._decks_col2.setSizes([500, 500])
        self._decks_split = QSplitter(Qt.Orientation.Horizontal)
        self._decks_split.addWidget(self._decks_col1)
        self._decks_split.addWidget(self._decks_col2)
        self._decks_split.setSizes([500, 500])
        # One shared row divider for the whole 2×2 grid: dragging the 🅰/🅲
        # handle also moves the 🅱/🅳 handle and vice-versa, so all four decks keep
        # the same row heights (setSizes doesn't re-emit splitterMoved → no loop).
        self._decks_col1.splitterMoved.connect(
            lambda *_: self._decks_col2.setSizes(self._decks_col1.sizes()))
        self._decks_col2.splitterMoved.connect(
            lambda *_: self._decks_col1.setSizes(self._decks_col2.sizes()))

        # Second 2×2 grid (decks E–H), shown on the "Group E–H" tab in 8-deck mode.
        # Built exactly like the first grid: 🅴 above 🅶 (left), 🅵 above 🅷 (right).
        self._decks_col3 = QSplitter(Qt.Orientation.Vertical)
        self._decks_col3.addWidget(self._deckE_box)
        self._decks_col3.addWidget(self._deckG_box)
        self._decks_col3.setSizes([500, 500])
        self._decks_col4 = QSplitter(Qt.Orientation.Vertical)
        self._decks_col4.addWidget(self._deckF_box)
        self._decks_col4.addWidget(self._deckH_box)
        self._decks_col4.setSizes([500, 500])
        self._decks_split2 = QSplitter(Qt.Orientation.Horizontal)
        self._decks_split2.addWidget(self._decks_col3)
        self._decks_split2.addWidget(self._decks_col4)
        self._decks_split2.setSizes([500, 500])
        self._decks_col3.splitterMoved.connect(
            lambda *_: self._decks_col4.setSizes(self._decks_col3.sizes()))
        self._decks_col4.splitterMoved.connect(
            lambda *_: self._decks_col3.setSizes(self._decks_col4.sizes()))

        # Two more 2×2 grids for the 📅 day decks, mirroring the normal groups:
        # day 🄰 above 🄲 (left) and 🄱 above 🄳 (right), same for 🄴–🄷. They live
        # in their own sub-tab widget on the "📅 Tournament day" page.
        self._day_col1 = QSplitter(Qt.Orientation.Vertical)
        self._day_col1.addWidget(self._day_boxes[0])
        self._day_col1.addWidget(self._day_boxes[2])
        self._day_col1.setSizes([500, 500])
        self._day_col2 = QSplitter(Qt.Orientation.Vertical)
        self._day_col2.addWidget(self._day_boxes[1])
        self._day_col2.addWidget(self._day_boxes[3])
        self._day_col2.setSizes([500, 500])
        self._day_split = QSplitter(Qt.Orientation.Horizontal)
        self._day_split.addWidget(self._day_col1)
        self._day_split.addWidget(self._day_col2)
        self._day_split.setSizes([500, 500])
        self._day_col1.splitterMoved.connect(
            lambda *_: self._day_col2.setSizes(self._day_col1.sizes()))
        self._day_col2.splitterMoved.connect(
            lambda *_: self._day_col1.setSizes(self._day_col2.sizes()))
        self._day_col3 = QSplitter(Qt.Orientation.Vertical)
        self._day_col3.addWidget(self._day_boxes[4])
        self._day_col3.addWidget(self._day_boxes[6])
        self._day_col3.setSizes([500, 500])
        self._day_col4 = QSplitter(Qt.Orientation.Vertical)
        self._day_col4.addWidget(self._day_boxes[5])
        self._day_col4.addWidget(self._day_boxes[7])
        self._day_col4.setSizes([500, 500])
        self._day_split2 = QSplitter(Qt.Orientation.Horizontal)
        self._day_split2.addWidget(self._day_col3)
        self._day_split2.addWidget(self._day_col4)
        self._day_split2.setSizes([500, 500])
        self._day_col3.splitterMoved.connect(
            lambda *_: self._day_col4.setSizes(self._day_col3.sizes()))
        self._day_col4.splitterMoved.connect(
            lambda *_: self._day_col3.setSizes(self._day_col4.sizes()))
        self._day_tabs = QTabWidget()
        self._day_tabs.setDocumentMode(True)
        self._day_tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._day_tabs.addTab(self._day_split, "Group A–D")
        self._day_tabs.addTab(self._day_split2, "Group E–H")
        self._day_tabs.currentChanged.connect(self._on_day_tab_changed)
        # Drag-hover flips the day sub-tab too (handled in eventFilter).
        self._day_tabs.tabBar().setAcceptDrops(True)
        # 🧹 in the day page's tab row: empty all day playlists (with confirm) —
        # unlike the tab's ✕ this reads as "clear", and the tab name is kept.
        day_clear = QToolButton()
        day_clear.setText("🧹")
        day_clear.setAutoRaise(True)
        day_clear.setToolTip("Clear all tournament-day playlists")
        day_clear.clicked.connect(self._clear_day_plan)
        self._day_tabs.setCornerWidget(day_clear, Qt.Corner.TopRightCorner)

        # All grids live in a tab widget. In 1/2/4-deck modes the tab bar is hidden
        # and only the first page shows, so the deck area looks like a plain panel;
        # 8-deck mode reveals "Group E–H", a loaded day plan reveals "📅 Tournament day".
        self._deck_tabs = QTabWidget()
        self._deck_tabs.setDocumentMode(True)
        self._deck_tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._deck_tabs.addTab(self._decks_split, "Group A–D")
        self._deck_tabs.addTab(self._decks_split2, "Group E–H")
        self._deck_tabs.addTab(self._day_tabs, "📅 Tournament day")
        # The 📅 tab only shows when its view is switched on (_apply_deck_view).
        self._deck_tabs.setTabVisible(2, False)
        # ✕ on the 📅 tab closes the whole tournament-day view (clears the day
        # decks after a confirm); double-click on the tab renames it to the
        # competition name, e.g. "DanceComp 2026" (handled in eventFilter).
        self._day_tab_title = ""
        # Keeps the (empty) 📅 tab on screen after 🧹 Clear — only ✕ retires it.
        self._day_tab_keep = False
        day_close = QToolButton()
        day_close.setText("✕")
        day_close.setAutoRaise(True)
        day_close.setToolTip("Close the tournament day — clears all 📅 day decks")
        day_close.clicked.connect(self._close_day_plan)
        self._deck_tabs.tabBar().setTabButton(
            2, QTabBar.ButtonPosition.RightSide, day_close)
        # A QTabWidget normally draws a pane border + margin around its pages; strip
        # both so a single-tab (≤4-deck) view is visually identical to the old layout.
        self._deck_tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; margin: 0; } "
            "QTabWidget::tab-bar { left: 0; }")
        self._deck_tabs.currentChanged.connect(self._on_deck_tab_changed)
        # Accept drag-hover on the tab bar: dragging a track onto a tab flips the
        # 8-deck view to that group's 4 decks so it can be dropped there (handled
        # in eventFilter). The tab bar itself takes no drop — it's just a switcher.
        self._deck_tabs.tabBar().setAcceptDrops(True)
        # 🎛 Sample pads that fire OVER the deck music (Tusch, applause, a bed
        # under the Siegerehrung). Its own dock, not a tab — the wall is used
        # while watching the running heat, not instead of it.
        self._build_cartwall()

        # The wishlist area is a horizontal splitter. In the default row layout it holds
        # the 4 wishlist boxes directly; in 2×2 grid mode (4 wishlists only) it instead
        # holds two vertical column splitters — wish 1/3 left, wish 2/4 right, mirroring
        # the deck grid. _rebuild_wish_layout reparents the boxes between the two shapes.
        self._wish_col1 = QSplitter(Qt.Orientation.Vertical)
        self._wish_col2 = QSplitter(Qt.Orientation.Vertical)
        # One shared row divider for the 2×2 grid (drag either handle, both move).
        self._wish_col1.splitterMoved.connect(
            lambda *_: self._wish_col2.setSizes(self._wish_col1.sizes()))
        self._wish_col2.splitterMoved.connect(
            lambda *_: self._wish_col1.setSizes(self._wish_col2.sizes()))
        self._wish_split = QSplitter(Qt.Orientation.Horizontal)
        self._rebuild_wish_layout()
        # Remember the user's manual divider drags per wish-state (2 vs 3 vs 4 visible
        # wishlists each keep their own layout); _update_wish_area replays these instead
        # of snapping back to the default ratio. Persisted across sessions in _save_layout.
        self._wish_sizes: dict[int, list[int]] = {}
        self._wish_split.splitterMoved.connect(self._on_wish_split_moved)

        self._right_split = QSplitter(Qt.Orientation.Vertical)
        self._right_split.addWidget(self._deck_tabs)
        # Warm-up (Eintanzen) panel sits ABOVE the wishlist, BELOW the playlists;
        # hidden until a warm-up is generated (or restored from autosave).
        self._right_split.addWidget(self._warmup_box)
        self._warmup_box.setVisible(False)
        self._right_split.addWidget(self._wish_split)
        # Library browser docked under the wishlists — foldable to its header,
        # fully hideable via the 📚 toolbar toggle.
        self._lib_browser = LibraryBrowser()
        self._lib_browser.playRequested.connect(self._on_lib_play)
        self._lib_browser.unplannedToggled.connect(self._on_lib_unplanned_toggled)
        self._lib_browser.foldToggled.connect(self._on_lib_fold_toggled)
        self._lib_browser.columnOrderChanged.connect(self._on_lib_columns_reordered)
        self._lib_browser.columnWidthsChanged.connect(self._on_lib_column_widths)
        self._lib_browser.columnsChanged.connect(self._on_lib_columns_hidden)
        self._lib_browser.danceNamesChanged.connect(self._on_lib_dance_names)
        self._lib_browser._table.seek_cb = self._seek   # Ctrl+←/→ seeks ∓30 s
        saved_widths = self._settings.get("library_col_widths")
        if isinstance(saved_widths, dict):
            self._lib_browser.apply_column_widths(saved_widths)
        saved_cols = self._settings.get("library_columns")
        if isinstance(saved_cols, list):
            self._lib_browser.apply_column_order([int(c) for c in saved_cols])
        saved_hidden = self._settings.get("library_hidden_columns")
        if isinstance(saved_hidden, list):
            self._lib_browser.set_hidden_columns([int(c) for c in saved_hidden])
        self._lib_browser.set_short_dances(
            bool(self._settings.get("library_short_dances")))
        # 🏆 The tournament tree shares the pane as a second tab: both are ways
        # of finding music to drag onto a deck, and the desk has the vertical
        # space for one of them, not two.
        self._tourney_tree = TournamentTree(TOURNAMENTS)
        self._tourney_tree.playRequested.connect(
            lambda path, row: self._on_lib_play(path, row, self._tourney_tree))
        self._tourney_tree.loadRequested.connect(self._load_tournament_m3u)
        self._tourney_tree._table.seek_cb = self._seek   # Ctrl+←/→ seeks ∓30 s
        # A tournament list may point outside the library (an older copy of the
        # collection, a stick) — those tracks are read off the file itself.
        self._tourney_tree.resolve_entry = (
            lambda p: self._lib.make_external_entry(p, self._cache)
            if self._lib else None)
        self._lib_tabs = QTabWidget()
        self._lib_tabs.setDocumentMode(True)
        self._lib_tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; margin: 0; } "
            "QTabWidget::tab-bar { left: 0; }")
        self._lib_tabs.addTab(self._lib_browser, "📚  Library")
        self._lib_tabs.addTab(self._tourney_tree, "🏆  Tournaments")
        self._lib_tabs.currentChanged.connect(self._on_lib_tab_changed)
        self._right_split.addWidget(self._lib_tabs)
        self._right_split.setStretchFactor(0, 1)
        self._right_split.setSizes([560, 200, 160, 160])
        self._lib_tabs.setVisible(bool(self._settings.get("library_pane", True)))
        if self._settings.get("library_folded"):
            self._lib_browser.set_folded(True)
        # The ▾ in the tab bar's corner folds the pane as a whole — built last
        # so its restore has the final say over the browser's own fold above.
        self._build_lib_pane_fold_btn()
        # Folded tabs ARE the minimized representation — never let a splitter
        # collapse a pane to 0px on top of that (the tabs would vanish with no
        # way to unfold them).
        for s in (self._decks_col1, self._decks_col2, self._decks_split,
                  self._decks_col3, self._decks_col4, self._decks_split2,
                  self._wish_col1, self._wish_col2,
                  self._wish_split, self._right_split):
            s.setChildrenCollapsible(False)
        rl.addWidget(self._right_split, stretch=1)

        # Single-playlist view by default; _dual_btn reveals decks 2–4 / wishlists.
        self._wish_box2.setVisible(False)
        self._wish_box3.setVisible(False)
        self._wish_box4.setVisible(False)
        self._apply_deck_view()   # hides decks B/C/D + wishlist area for _deck_count == 1
        self._focused_table = self._tableA   # Ctrl+S target, updated on focus
        # The list whose own play values the panel shows and edits.
        self._panel_table = self._focused_table
        self._set_active_table(self._tableA)

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

        # Ctrl+Shift+→ / ← — the ⏭ / ⏮ of the player card, from anywhere in the
        # window: the operator's hands are on the deck, not on the card, and
        # during a pause the next title is the only thing worth reaching for.
        # One modifier above the deck's Ctrl+←/→, which seeks INSIDE the song.
        #
        # Auto-repeat OFF, which QShortcut has ON by default: held a moment too
        # long, the key repeats at the system rate and every repeat throws away
        # another title — the one you skipped to plays for half a second and is
        # gone. A held Ctrl+Z can afford to repeat; a held ⏭ cannot.
        self._next_sc = QShortcut(QKeySequence("Ctrl+Shift+Right"), self)
        self._next_sc.setAutoRepeat(False)
        self._next_sc.activated.connect(self._on_player_next)
        self._prev_sc = QShortcut(QKeySequence("Ctrl+Shift+Left"), self)
        self._prev_sc.setAutoRepeat(False)
        self._prev_sc.activated.connect(lambda: self._preview_skip(-1))

        # F1 — shortcut cheat sheet (also via the ❔ toolbar button).
        self._help_sc = QShortcut(QKeySequence("F1"), self)
        self._help_sc.activated.connect(self._show_shortcuts)

        # Ctrl+X (and Ctrl+W, which is what every other window on the desk
        # answers to) closes the active dialog — or, on the main window, the
        # preview mini player (never the app itself). An app-wide event filter
        # handles it so every dialog is covered without wiring each one; text
        # inputs keep Ctrl+X for "cut" (they're skipped in eventFilter).
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

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
            "right": self._right_split,
            "cols":  self._decks_split,
            "col1":  self._decks_col1,
            "col2":  self._decks_col2,
            "cols2": self._decks_split2,
            "col3":  self._decks_col3,
            "col4":  self._decks_col4,
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

        # ── Loading dialog (shown while the background thread scans files) ──
        self._loading_dlg = LoadingDialog(app_title(app_mode_of(self._settings)),
                                          f"Version {app_version()}")
        self._loading_dlg.setWindowModality(Qt.WindowModality.ApplicationModal)

        # ── Load library in background ──
        # Parented, so _stop_workers finds it: an unparented loader is nobody's
        # child, outlives the window that started it and is destroyed mid-scan
        # when the process ends — which Qt answers by aborting.
        self._loader = LibraryLoader(music_dir=self._settings.get("library_dir"),
                                     parent=self)
        self._loader.status.connect(self._loading_dlg.set_status)
        self._loader.finished_ok.connect(self._on_library_loaded)
        self._loader.error.connect(self._on_library_error)
        self._loader.start()
        self._loading_dlg.show()

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
        for d in list(self._deck_of.values()):
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
        self._deck_count = 0
        self._apply_deck_view()
        self._set_wish_state(0)
        self._set_compact_state(2)
        self._warmup_toggle_btn.setChecked(True)   # arms an empty party list
        self._lib_btn.setChecked(True)
        self._cart_btn.setChecked(False)
        self._on_table_focused(self._warmup_table)   # the panel shows the party list
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



























    # The focused deck's generation context (gui.deck.DeckContext), read and
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
    _BEATS_PER_BAR = {"LW": 3, "TG": 2, "WW": 3, "SF": 4, "QS": 4,
                      "CC": 4, "SA": 2, "RB": 4, "PD": 2, "JI": 4}
    # Metric levels a beat tracker commonly locks onto instead of the true
    # beat: octaves (×2, ×4), the bar of triple meters (×3) and the dotted /
    # compound groupings (×1.5). Any of these counts as "matching the label".
    # (Samba's old ×0.75 slip excuse was dropped once the analyzer gained a
    # dance-seeded tempo prior — see planner.db._tempo_prior.)
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
        self._audio_device.hold_system_sounds(False)
        self._stop_workers()
        super().closeEvent(event)

    def _stop_workers(self):
        """Let every background worker finish before this window takes its
        children down with it. Qt aborts the process outright — no traceback,
        just 0xC0000409 — if a QThread is destroyed while it is still running,
        and every play of an un-analyzed track arms a 🔇 silence probe."""
        for worker in self.findChildren(QThread):
            if not worker.isRunning():
                continue
            cancel = getattr(worker, "cancel", None)
            if callable(cancel):
                cancel()
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
        """F1 / ❔: the cheat sheet — see `gui.shortcuts`."""
        show_shortcuts(self)

    def _help_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("⌨  Keyboard shortcuts  (F1)", self._show_shortcuts)
        menu.addAction("ℹ  About…", self._show_about)
        return menu

    def _show_help_menu(self):
        """❔: the shortcuts (F1 opens them directly) and ℹ About."""
        btn = self._help_btn
        self._help_menu().exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _show_about(self):
        """ℹ About — see `gui.about`."""
        show_about(self, app_title(app_mode_of(self._settings)))

    def eventFilter(self, obj, event):
        """App-wide Ctrl+X / Ctrl+W → close the active dialog; on the main window it only
        dismisses the preview mini player (stop + hide) and NEVER quits the app.
        Skips text-editing widgets so Ctrl+X still cuts text there (line edits,
        the search box, spin boxes…)."""
        # Drag-hover over a deck tab → flip the 8-deck view to that group so the
        # track can be dropped onto one of its 4 decks. The tab bar accepts the
        # drag only to keep the hover events flowing; it never takes the drop.
        if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            for tabs in (self._deck_tabs, self._day_tabs):
                tb = tabs.tabBar()
                if obj is tb:
                    idx = tb.tabAt(event.position().toPoint())
                    if idx >= 0 and idx != tabs.currentIndex():
                        tabs.setCurrentIndex(idx)
                    event.acceptProposedAction()
                    return True
        # Double-click on the 📅 tab → rename it to the competition name.
        if event.type() == QEvent.Type.MouseButtonDblClick:
            tb = self._deck_tabs.tabBar()
            if obj is tb and tb.tabAt(event.position().toPoint()) == 2:
                self._rename_day_tab()
                return True
        # Right-click on a deck tab → 📅: save-competitions / clear / rename /
        # close menu; Group A–D / E–H: clear-that-page menu. Beside the tabs
        # (the bar spans the whole width) → open a 📅 tab.
        if event.type() == QEvent.Type.ContextMenu:
            tb = self._deck_tabs.tabBar()
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
                        if self._preview and self._preview.isVisible():
                            self._on_stop_btn()   # close mini player + stop playback
                        return True               # swallow — never close the app
                    if win is not None:
                        win.close()
                        return True
        # Not super(): QObject.eventFilter only returns False, but it type-checks
        # `obj` — and an app-wide filter can be handed a stale non-QObject wrapper
        # (a QWidgetItem), whose TypeError then poisons every filter after it.
        return False




















    # ── Playback ──────────────────────────────────────────────────────────────

    # ── Playing mode: timed play + fade-out engine ────────────────────────────









    # ── Paso Doble highlight stop ──









































    # ── Generate ──────────────────────────────────────────────────────────────





















    # ── Save ──────────────────────────────────────────────────────────────────





    # ── Loudness analysis (EBU R128 via ffmpeg) ──────────────────────────────








    # ── Paso Doble highlight pre-analysis (🐂 in the Playing panel) ──













    # ── AI suggestions / dropped-file similarity ────────────────────────────────








    # ── Settings + global repository index ──────────────────────────────────────


































# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def run_gui():
    # Planner diagnostics (scans, migrations, analysis errors) go through logging;
    # show them on the console the GUI was launched from. Under pythonw there is
    # no console (sys.stdout is None) → fall back to basicConfig's stderr default.
    if sys.stdout is not None:
        logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

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

    # Qt's own diagnostics into the same file — the multimedia backend reports
    # its failures through qWarning, where nothing was listening until now.
    def _qt_message(mode, _ctx, msg):
        log.log({QtMsgType.QtDebugMsg: logging.DEBUG,
                 QtMsgType.QtInfoMsg: logging.INFO,
                 QtMsgType.QtWarningMsg: logging.WARNING,
                 QtMsgType.QtCriticalMsg: logging.ERROR,
                 QtMsgType.QtFatalMsg: logging.CRITICAL}.get(mode, logging.INFO),
                "🧩 Qt: %s", msg)
    qInstallMessageHandler(_qt_message)
    # ⚙ Settings → 🔊 Audio backend overrides the platform default picked at the
    # top of this file. Here and nowhere later: Qt loads the backend plugin the
    # first time something plays and never reads the variable again — which is
    # also why the setting only takes effect on the next start.
    apply_media_backend(load_settings())
    # 🐞 Opt-in error reports. After sys.excepthook is set above: the client
    # wraps the hook it finds, so crash.log keeps getting the traceback too.
    error_reports.apply(load_settings())
    log.info("🚀 Session start\n"
             "version: %s\n"
             "python: %s\n"
             "media backend: %s", app_version(), sys.version.split()[0],
             os.environ.get("QT_MEDIA_BACKEND", "default"))
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
    theme.apply_settings(startup_settings)
    theme.install_stylesheet_hook()
    theme.sync_shared_colors()
    theme.install_titlebar_hook()
    app.setPalette(theme.app_palette())

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
        error_reports.apply(load_settings())

    app.window = MainWindow()  # keep reference; shows itself after library loads

    if prev_crash:
        # Deferred into the event loop so the library keeps loading behind the
        # notice instead of startup blocking on the dialog.
        def _show_prev_crash():
            log.warning("💥 Previous session left a non-empty crash.log (%s chars)",
                        len(prev_crash))
            box = QMessageBox(app.window)
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
        QTimer.singleShot(0, _show_prev_crash)

    exit_app(app.exec())


if __name__ == "__main__":
    run_gui()
