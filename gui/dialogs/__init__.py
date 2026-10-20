#!/usr/bin/env python3
"""Dialogs, shared widgets and small helpers of the Dancesport Playlist Planner GUI.

Extracted from dancesport_gui.py (light split): the splash/busy dialogs, the
Similar-Tracks / AI-suggestions / duplicate dialogs, the
settings dialog + gui_settings.json / autosave persistence, the shared
palette + table-column constants, the drag-enabled result table, the drop
zone and helpers (toasts, tooltips, open-in-player/folder).
"""

import logging
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel,
    QComboBox, QCheckBox, QLineEdit,
    QDialog,
    QFileDialog, QDialogButtonBox, QRadioButton, QButtonGroup,
    QMessageBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QFrame,
    QSizePolicy,
)
from PySide6.QtCore import (
    Qt, Signal, QProcess, QSize, QStandardPaths, QTimer,
)
from PySide6.QtGui import QColor, QPixmap

import planner.config
from planner.music.gaps import gap_stats, shopping_list, GAP_MIN_POOL, GAP_MIN_PROVEN
from planner.models import DANCE_STYLES, rounds_from_pattern
from planner.terms import dance_name
from planner.playing.play_sets import migrate_play_sets

log = logging.getLogger("dancesport.gui")

# Only what this module uses itself. The big-module split left a re-export of
# all 47 gui.common names here, which gave the same primitive two import paths
# and made gui.dialogs look like the owner of code it does not own; callers now
# import from gui.common, and the dialog classes below stay because the split
# moved them out from under names that were already gui.dialogs'.
# (gui.common/dialog modules never import gui.dialogs, so there is no cycle.)
from gui.common import (
    _DroppedFilesList,
    _MultiFileDropZone,
)
from shared.widgets import (
    _app_icon,
    _hsep,
)
from shared import error_reports, update_check
from shared.appearance import looks
from planner import i18n
from planner.store import JsonStore
from planner.version import DEV
from shared.stores import SETTINGS, save_settings
from gui.dialogs.similar_dialog import SimilarTracksDialog  # noqa: F401
from gui.dialogs.duplicate_dialog import DuplicateResolveDialog  # noqa: F401
from gui.dialogs.ai_dialogs import (  # noqa: F401
    AiPlaylistDialog, AiSuggestDialog, AiTranscriptDialog,
)
# shared.audio.audio_probes pulls in nothing but the planner and QtCore, so no cycle here.
from shared.audio.audio_probes import find_ffmpeg
from shared.audio.playback import device_id

# ─────────────────────────────────────────────────────────────────────────────
# Settings (persisted paths + global-search opt-in)
# ─────────────────────────────────────────────────────────────────────────────
# 🏆 The tournament tree (folders of .m3u files). Its own file for the same
# reason: it is the operator's filing of the weekend, not playlist content, and
# it must not be rolled back by an undo on a deck.
TOURNAMENTS = JsonStore("tournaments.json", note="starting with an empty tree")


def _home_dir(loc, name: str) -> Path:
    """The machine's own Music / Documents folder.

    Qt is asked first because it follows a folder the user (or OneDrive) has
    moved elsewhere; ~/<name> is the fallback when it has nothing to say.
    """
    try:
        p = QStandardPaths.writableLocation(loc)
    except Exception:
        p = ""
    return Path(p) if p else Path.home() / name


def _user_music_dir() -> Path:
    return _home_dir(QStandardPaths.StandardLocation.MusicLocation, "Music")


def _user_docs_dir() -> Path:
    return _home_dir(QStandardPaths.StandardLocation.DocumentsLocation, "Documents")


def _default_library_dir() -> Path:
    """Favorites library default: first existing of F:\\my music\\tanzcds, the
    planner default, then this machine's own Music folder."""
    for p in (Path(r"F:\my music\tanzcds"), planner.config.MUSIC_DIR):
        if p.exists():
            return p
    return _user_music_dir()


def _default_global_dir() -> Path:
    """Whole-repo default: first existing of F:\\my music, then the library's parent."""
    for p in (Path(r"F:\my music"), _default_library_dir().parent):
        if p.exists():
            return p
    return _user_music_dir()


def _default_save_dir() -> Path:
    """Default folder for the 'Save as M3U…' file chooser (the user's tournament
    dropbox), used until the user picks somewhere else."""
    p = Path(r"D:\Dropbox\Turniere")
    return p if p.exists() else _user_docs_dir()


# Where each configured folder lands when it isn't there: a drive letter that
# moved, a stick left at home, or simply a second machine that never had the
# path this file was written on. Music for anything holding music, Documents
# for anything holding playlists.
_PATH_FALLBACKS = {
    "library_dir": _user_music_dir,
    "global_dir": _user_music_dir,
    "save_dir": _user_docs_dir,
    "playlist_dir": _user_docs_dir,
    "reference_path": _user_music_dir,
}


# Where the real folder went while a fallback stands in for it: setting key →
# the path that was configured before. Written into gui_settings.json like any
# other setting, so an unplugged drive survives a restart and is put back the
# moment it is plugged in again.
PATHS_OFFLINE = "paths_offline"


def apply_path_fallbacks(s: dict) -> dict:
    """Point every configured folder that does not exist at its fallback, and
    put the real one back as soon as it is there again.

    A settings file travels — between machines, and between a drive being
    plugged in and not. Rather than let the app come up on five dead paths (an
    empty library, a save dialog that opens nowhere), each one falls back to a
    folder this machine actually has, while the configured path is kept aside
    under `paths_offline`. A folder picked by hand in the meantime is a real
    decision and wins: the memory is dropped and nothing gets put back.
    Modifies and returns `s`.
    """
    offline = s.get(PATHS_OFFLINE)
    offline = dict(offline) if isinstance(offline, dict) else {}
    for key, fallback in _PATH_FALLBACKS.items():
        configured = str(s.get(key) or "").strip()
        remembered = str(offline.get(key) or "").strip()
        alt = fallback()
        if remembered and Path(remembered).is_dir():
            log.info("📁 The folder is back — using it again\n"
                     "setting: %s\n"
                     "stood in: %s\n"
                     "back to: %s", key, configured or "—", remembered)
            s[key] = remembered
            offline.pop(key, None)
            continue
        if configured and Path(configured).is_dir():
            if remembered and configured != str(alt):
                # Not the stand-in any more: picked by hand, so stop waiting.
                log.info("📁 Folder picked by hand — forgetting the old one\n"
                         "setting: %s\n"
                         "now: %s\n"
                         "forgotten: %s", key, configured, remembered)
                offline.pop(key, None)
            continue
        if not alt.is_dir():
            continue        # nothing better to offer — keep what is configured
        log.info("📁 Configured folder is not there — falling back\n"
                 "setting: %s\n"
                 "configured: %s\n"
                 "using: %s", key, configured or "—", alt)
        if configured:
            offline.setdefault(key, configured)
        s[key] = str(alt)
    if offline:
        s[PATHS_OFFLINE] = offline
    else:
        s.pop(PATHS_OFFLINE, None)
    return s


def load_settings() -> dict:
    """Read gui_settings.json, falling back to sensible per-machine defaults."""
    s = {
        "library_dir":   str(_default_library_dir()),
        "global_dir":    str(_default_global_dir()),
        "save_dir":      str(_default_save_dir()),
        "playlist_dir":  str(planner.config.PLAYLIST_DIR),
        "reference_path": str(_default_library_dir()),
        # Extra folders 🧭 Fix paths searches when a playlist comes from
        # another PC — empty until the operator names one.
        "remap_paths": [],
        # Columns ticked away per kind of list ("playlist" / "wishlist" /
        # "party") — header right-click. Empty: every list shows them all.
        "hidden_columns": {},
        # …and the width each column was dragged to, per kind. Empty: the
        # seeded defaults. Title is not in here — it takes what is left over.
        "column_widths": {},
        "short_dances": {},
        # The 🎼 library pane keeps the same two choices, but as ONE setting
        # each — it is a single pane, not one list per kind.
        "library_hidden_columns": [],
        "library_short_dances": False,
        "global_search": False,
        # 🏷 Titles without a class tag stay in generation unless ticked.
        "exclude_no_class": False,
        # ⛶ The fullscreen clock without its date: "20:45:12".
        "clock_time_only": False,
        "preview_player": True,
        # Where the master player is docked — see PLAYER_LAYOUT_CHOICES.
        "player_layout": "panel",
        # A double-click CUES the title by default — the desk is a tournament
        # until a party list says otherwise, and there the music starts on ⏯.
        "dblclick_plays": False,
        # ↩ Pick a title up where it was left. Off by default: a heat is danced
        # from the top, so the one player starting a title in its middle is a
        # surprise nobody asked for until they ask for it.
        "remember_pos": False,
        # 🎙 The announcement in both recorded voices, taking turns, and
        # without the heat number until ⚙ Settings asks for it.
        "announce_voice": "random",
        "announce_heat": False,
        # 🗣 …named over the first bars, not into a silence before them.
        "announce_wait": False,
        # 🔇 Hand the sound device back when nothing is playing. Off by
        # default: it costs the click a sound card makes when the next title
        # re-opens it, which is only worth paying if the hiss is audible.
        "release_audio_idle": False,
        # 🔕 The OS's own dings off the shared sound card while the evening
        # runs (Playing mode, or anything audible) — see player.audio.system_sounds.
        "mute_system_sounds": True,
        # ☀ A tournament runs for hours without anyone touching the desk —
        # the screensaver stays off while music plays or the presenter is up.
        "keep_awake": True,
        # 🎵 Check-music thresholds (Settings → Checks tab)
        "check_min_play_secs": 105,   # ⏱ too short at or below (1:45)
        "check_max_play_secs": 240,   # ⏳ too long above (4:00, opt-in check)
        "check_tempo_dev_pct": 10,    # ⚡ measured-vs-label tolerance
        "check_noise_floor_db": -50,  # 🔇 hissy above this floor (opt-in check)
    }
    data = SETTINGS.read()
    if isinstance(data, dict):
        # Keep EVERY persisted key (play settings, pause music, loudness
        # toggle, library column order, …) — the defaults above only fill
        # gaps. A whitelist here used to silently drop all of those.
        s.update(data)
    migrate_column_settings(s)
    migrate_play_sets(s)
    return apply_path_fallbacks(s)


def audio_output_choices() -> list[tuple[str, str]]:
    """🔊 Every output the operating system lists: (hex of its id, its name)."""
    try:
        from PySide6.QtMultimedia import QMediaDevices
    except ImportError:
        return []
    return [(device_id(d).hex(), d.description())
            for d in QMediaDevices.audioOutputs()]


# Bumped when a column is added to the decks or the library: the column ticks,
# widths and the library's order are saved by column INDEX.
COLUMNS_VERSION = 4

# The column each version added: (its index in the decks, in the library).
# v2 ★ Rating, v3 Custom, v4 File name.
_ADDED_COLUMNS = {2: (9, 10), 3: (10, 11), 4: (11, 12)}


def migrate_column_settings(s: dict) -> dict:
    """Bring column choices saved for an older column set up to date, in place.

    Each version added one column: in the decks in front of ↺ (which moves
    one up and stays last), in the library at the end. Every saved deck index
    from the new one on shifts one up, and the new column starts hidden —
    Marcel wanted ★ and Custom out of the way until asked for. A saved library
    order lists exactly the old columns, and one that doesn't list them all
    is thrown away whole, so the new column is appended to it."""
    version = int(s.get("columns_version") or 1)
    for step in range(version + 1, COLUMNS_VERSION + 1):
        _add_column(s, *_ADDED_COLUMNS[step])
    s["columns_version"] = max(version, COLUMNS_VERSION)
    return s


def _add_column(s: dict, added: int, lib_added: int) -> None:
    """One step of migrate_column_settings."""
    def shift(c):
        c = int(c)                  # JSON keys of the widths come back as str
        return c + 1 if c >= added else c

    hidden = s.get("hidden_columns")
    if isinstance(hidden, dict):
        s["hidden_columns"] = {kind: sorted({shift(c) for c in cols} | {added})
                               for kind, cols in hidden.items()}
    widths = s.get("column_widths")
    if isinstance(widths, dict):
        s["column_widths"] = {kind: {str(shift(c)): w for c, w in (ws or {}).items()}
                              for kind, ws in widths.items()}
    lib_hidden = [int(c) for c in s.get("library_hidden_columns") or []]
    s["library_hidden_columns"] = sorted(set(lib_hidden) | {lib_added})
    order = s.get("library_columns")
    if isinstance(order, list) and sorted(int(c) for c in order) == list(range(lib_added)):
        s["library_columns"] = [int(c) for c in order] + [lib_added]


# ─────────────────────────────────────────────────────────────────────────────
# App mode — which side of the app this install is for
# ─────────────────────────────────────────────────────────────────────────────
APP_MODES = ("planner", "player", "both")
DEFAULT_APP_MODE = "both"
# One-shot settings key: set when the first start picked player-only, consumed
# by MainWindow._apply_player_first_start.
PLAYER_FIRST_START = "player_first_start"
# One-shot settings key: set by the first start's app mode, consumed by
# ensure_library_dir right after it.
ASK_LIBRARY_DIR = "ask_library_dir"

# (key, caption, what it means) — shared by the first-start dialog and the
# ⚙ Settings combo so the two can never describe a mode differently.
APP_MODE_CHOICES = (
    ("both", "🎛  Both — plan and play",
     "The full app: build playlists at home, run them at the tournament."),
    ("planner", "📝  Planner only",
     "Build and curate playlists. The tournament floor's playing panel, "
     "its timed play / announcements and the 🎛 cartwall stay hidden."),
    ("player", "▶  Player only",
     "Run prepared playlists at the venue. Everything that generates or "
     "checks a playlist stays hidden."),
)


def app_mode_of(settings: dict) -> str:
    """The stored mode, or 'both' for anything unrecognised — a settings file
    written before this option existed simply has every side switched on.

    A player-only BUILD overrules the setting: that .exe ships without the
    librosa analysis stack, so the planning half could not generate anything
    even if a settings file carried over from another install asked for it."""
    if planner.config.player_build():
        return "player"
    mode = settings.get("app_mode")
    return mode if mode in APP_MODES else DEFAULT_APP_MODE


def app_title(mode: str, version: str = "") -> str:
    """Product name for a mode: each side names itself, both name both. A
    build adds its version (planner.version), so a screenshot of a problem
    says which release it is; a source run ("dev") stays without."""
    name = {"planner": "DanceSport Planner",
            "player": "DanceSport Player"}.get(mode, "DanceSport Planner & Player")
    return f"{name} {version}" if version and version != DEV else name


# ── 🔊 Audio backend ─────────────────────────────────────────────────────────
# Which engine Qt plays through. FFmpeg is Qt's own and the default everywhere,
# Windows included: Windows Media Foundation announces media oddly (see
# dancesport_gui.py) and a pitch change costs a longer gap. WMF stays on the
# list — it is the OS's own engine and the one to fall back to if FFmpeg ever
# stumbles on a file — and it played correctly on Qt 6.10.2, but on 6.11.1 it
# cuts a track a second in, so a version bump has to be tested
# with this set to "windows". "auto" leaves the choice to Qt (AVFoundation on
# macOS, gstreamer on Linux).
MEDIA_BACKENDS = ("auto", "windows", "ffmpeg")
# (key, caption) per platform — the Windows backend exists ONLY on Windows;
# naming it elsewhere leaves the app with no audio at all.
MEDIA_BACKEND_CHOICES = (
    (("ffmpeg", "🎬  FFmpeg — Qt's own engine (default)"),
     ("windows", "🪟  Windows Media Foundation — the OS's own"))
    if sys.platform == "win32" else
    (("auto", "🔊  Automatic — whatever this system uses (default)"),
     ("ffmpeg", "🎬  FFmpeg — Qt's own engine")))


# (planner.playlist.m3u.M3U_FORMATS key, caption) — what 'Save as M3U' and the exports write.
M3U_FORMAT_CHOICES = (
    ("utf-8", "UTF-8 (.m3u) — default"),
    ("utf-8-sig", "UTF-8 with BOM (.m3u) — for Windows tools that guess ANSI"),
    ("m3u8", "UTF-8 (.m3u8) — the encoding named in the extension"),
)


PLAYER_LAYOUT_CHOICES = (
    ("panel", "◧  Beside the playlists — at the head of the ▶ Playing panel",
     "The player card stands in the left panel, above the timed-play "
     "controls."),
    ("wide", "▤  Above the playlists — one wide strip over the decks",
     "The same player, laid out along the width above the decks — the shape "
     "a DJ desk uses. It shows in ▶ Playing mode."),
)


# ── 🎨 Look: theme + accent ───────────────────────────────────────────────────
# The dark theme is derived from the light colours rather than listed as a
# second palette — shared/appearance/theme.py says how and why. Both settings are read once at
# start-up, so changing either offers a restart. The 🎨 looks (shared/appearance/looks.py)
# are listed after these two, in sections of their own.
THEME_CHOICES = (
    ("light", "☀  Light (default)",
     "White decks, dark text: the look every colour in the app was picked for."),
    ("dark", "🌙  Dark",
     "The same colours put through a lightness flip, so a warning stays red "
     "and the ▶ player panel — dark already — is left as it is."),
)


class ThemePreview(QLabel):
    """A theme's picture: 1:1 where it fits, scaled down where it does not —
    never up, which would blur the very text it is there to show."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pix = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.setMinimumSize(480, 272)

    def show_theme(self, key: str) -> None:
        path = looks.preview_path(key)
        self._pix = QPixmap(str(path)) if path.exists() else QPixmap()
        if self._pix.isNull():
            self.setText(i18n.t("No preview picture for this theme."))
            return
        # Rendered at this screen's scale, so one image pixel per screen pixel.
        self._pix.setDevicePixelRatio(self.devicePixelRatioF())
        self.updateGeometry()
        self._fit()

    def sizeHint(self) -> QSize:
        if self._pix.isNull():
            return super().sizeHint()
        return self._pix.deviceIndependentSize().toSize()

    # Scaled down to the width, the picture is shorter too — so is the label,
    # or the blurb below it would hang under an empty band.
    def hasHeightForWidth(self) -> bool:
        return not self._pix.isNull()

    def heightForWidth(self, width: int) -> int:
        if self._pix.isNull():
            return super().heightForWidth(width)
        size = self._pix.deviceIndependentSize()
        scale = min(1.0, width / size.width())
        return max(self.minimumHeight(), round(size.height() * scale))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        if self._pix.isNull():
            return
        size = self._pix.deviceIndependentSize()
        if size.width() <= self.width() and size.height() <= self.height():
            self.setPixmap(self._pix)
            return
        ratio = self._pix.devicePixelRatio()
        fitted = self._pix.scaled(
            QSize(self.width(), self.height()) * ratio,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        fitted.setDevicePixelRatio(ratio)
        self.setPixmap(fitted)


def media_backend_of(settings: dict) -> str:
    """The configured audio backend, or this platform's default for anything
    unrecognised (a settings file written before the option existed)."""
    default = "ffmpeg" if sys.platform == "win32" else "auto"
    choice = str(settings.get("media_backend") or "").strip().lower()
    return choice if choice in MEDIA_BACKENDS else default


def media_backend_env(settings: dict) -> str:
    """What QT_MEDIA_BACKEND has to say for that choice — "" meaning: don't set
    it, let Qt pick. Read once at startup; Qt loads the backend plugin the first
    time something plays and never looks at the variable again."""
    choice = media_backend_of(settings)
    return "" if choice == "auto" else choice


def apply_media_backend(settings: dict) -> str:
    """Put that choice into the environment and report what Qt will use. Must
    run before the first title plays — see `media_backend_env`."""
    want = media_backend_env(settings)
    if want:
        os.environ["QT_MEDIA_BACKEND"] = want
    else:
        os.environ.pop("QT_MEDIA_BACKEND", None)
    return want


def restart_command() -> tuple:
    """(program, arguments) that starts this app again exactly as it was
    started. A frozen build IS the program; from source the interpreter is, and
    the script it ran is the first argument."""
    if getattr(sys, "frozen", False):
        return sys.executable, list(sys.argv[1:])
    return sys.executable, list(sys.argv)


def restart_app() -> bool:
    """Launch a fresh instance, detached from this one, and report whether it
    started. The caller closes this window afterwards — never before, or a
    cancelled close leaves two apps fighting over the audio device."""
    prog, args = restart_command()
    try:
        ok = QProcess.startDetached(prog, args, os.getcwd())
    except Exception as exc:
        log.error("🔄 Could not restart the app\n"
                  "program: %s\n"
                  "error: %s", prog, exc)
        return False
    log.info("🔄 Restarting the app\n"
             "program: %s\n"
             "args: %s\n"
             "started: %s", prog, args, ok)
    return bool(ok)


def warmup_name(mode: str) -> str:
    """What the 🤸 panel is called. Warming up ('Eintanzen') and running a party
    are the same flat list, but 'Eintanzen' is a tournament-preparation word — a
    player-only install never prepares one, it only plays the party."""
    return "Party" if mode == "player" else i18n.t("Practice / Party")


class AppModeDialog(QDialog):
    """First start: is this machine the planning desk, the tournament player,
    or both? The answer only hides UI — nothing is uninstalled by it, and
    ⚙ Settings changes it again at any time."""

    def __init__(self, mode: str = DEFAULT_APP_MODE, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to DanceSport Planner & Player")
        self.setMinimumWidth(480)
        lyt = QVBoxLayout(self)
        lyt.setSpacing(8)

        head = QLabel("<b>What do you want to use this app for?</b>")
        lyt.addWidget(head)
        # Plain text, so the & must NOT be escaped — a QLabel only reads markup
        # when the string actually contains a tag, and this one does not.
        note = QLabel("You can change this later under ⚙ Settings → "
                      "⚙ General.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#666; font-size:11px;")
        lyt.addWidget(note)
        lyt.addWidget(_hsep())

        self._group = QButtonGroup(self)
        self._radios = {}
        for key, caption, blurb in APP_MODE_CHOICES:
            rb = QRadioButton(caption)
            rb.setChecked(key == mode)
            self._group.addButton(rb)
            self._radios[key] = rb
            lyt.addWidget(rb)
            desc = QLabel(blurb)
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#666; font-size:11px; margin-left:22px;")
            lyt.addWidget(desc)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        lyt.addWidget(bb)

    def mode(self) -> str:
        for key, rb in self._radios.items():
            if rb.isChecked():
                return key
        return DEFAULT_APP_MODE


def ensure_app_mode() -> str:
    """Read the app mode, asking once on the very first start.

    Called from run_gui() before the main window exists — deliberately not from
    MainWindow.__init__, where a modal dialog would block the headless tests
    that construct the window against an empty settings folder."""
    settings = load_settings()
    # A player-only build has nothing to choose between — the question would
    # have one answer. The first start still gets the venue layout and the
    # ffmpeg check, exactly as if the mode had been picked here.
    if planner.config.player_build():
        if settings.get("app_mode") == "player":
            return "player"
        settings["app_mode"] = "player"
        settings[PLAYER_FIRST_START] = True
        settings[ASK_LIBRARY_DIR] = True
        save_settings(settings)
        log.info("🎚️ Player-only build — app mode fixed: player")
        warn_if_ffmpeg_missing()
        return "player"
    if settings.get("app_mode") in APP_MODES:
        return settings["app_mode"]
    dlg = AppModeDialog()
    dlg.exec()
    mode = dlg.mode()
    settings["app_mode"] = mode
    if mode == "player":
        # A player-only install opens on the venue layout instead of an empty
        # tournament grid. Flagged rather than written out here: the deck view,
        # the 🎉 party set and the panes need the live widgets, so MainWindow
        # applies them once and consumes the flag.
        settings[PLAYER_FIRST_START] = True
    settings[ASK_LIBRARY_DIR] = True
    save_settings(settings)
    log.info("🎚️ App mode chosen on first start\n"
             "mode: %s", mode)
    # Straight after the welcome question: the machine is being set up right
    # now, which is the one moment a missing ffmpeg is cheap to fix.
    warn_if_ffmpeg_missing()
    return mode


class LibraryDirQuestion(QMessageBox):
    """📂 The first start's question where the music is, with the guessed
    folder preselected: closing the box keeps it."""

    def __init__(self, guess: str, parent=None):
        super().__init__(parent)
        self._guess = guess
        self.setWindowTitle("Music folder")
        self.setIcon(QMessageBox.Icon.Question)
        self.setText("Where is your dance music?")
        self.setInformativeText(i18n.t(
            "Every start reads the MP3 files in this folder and in all\n"
            "folders below it. The first start reads each file once,\n"
            "which takes long on a whole drive or an external disk,\n"
            "so pick the folder that holds your dance music.\n\n"
            "Found: %s\n\n"
            "You can change it at any time under ⚙ Settings → 📁 Paths.") % guess)
        self.keep_btn = self.addButton("Use this folder",
                                       QMessageBox.ButtonRole.AcceptRole)
        self.pick_btn = self.addButton("Choose another folder…",
                                       QMessageBox.ButtonRole.ActionRole)
        self.setDefaultButton(self.keep_btn)
        self.setEscapeButton(self.keep_btn)

    def ask(self) -> str:
        self.exec()
        if self.clickedButton() is self.pick_btn:
            folder = QFileDialog.getExistingDirectory(self, "Music folder", self._guess)
            if folder:
                return os.path.normpath(folder)
        return self._guess


def ensure_library_dir() -> str:
    """The favorites library folder, asked once on the very first start.

    Otherwise it is guessed, and a guess can land on a whole external drive: a
    tester's first start sat at 17,500 of 34,000 files before the window
    opened. Only the start ensure_app_mode() armed asks; an install that
    already has a folder keeps it. Called from run_gui() right after
    ensure_app_mode()."""
    settings = load_settings()
    guess = settings.get("library_dir") or str(_default_library_dir())
    if not settings.pop(ASK_LIBRARY_DIR, False):
        return guess
    folder = LibraryDirQuestion(guess).ask()
    settings["library_dir"] = folder
    save_settings(settings)
    log.info("📂 Music folder chosen on first start\n"
             "folder: %s", folder)
    return folder


# The 🔔 update check's opt-in: the checkbox under the error reports question,
# and the question of its own where that one is not asked.
_UPDATE_CHECK_TIP = (
    "Once per start, the app asks GitHub (api.github.com) for the latest\n"
    "release. The request carries nothing about you or your music; GitHub\n"
    "sees the IP address it comes from. A newer version is announced once,\n"
    "with a link to its download page. Nothing is downloaded or installed.\n\n"
    "You can change this at any time under ⚙ Settings → ⚙ General.")


class ErrorReportsQuestion(QMessageBox):
    """🐞 The one-time question whether error reports may go out. Not sending
    is the default, and what Esc or closing the box answers.

    With `ask_updates` it carries the 🔔 update check's opt-in as a checkbox,
    off by default: one question about going online, not two."""

    def __init__(self, parent=None, ask_updates: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Error reports")
        self.setIcon(QMessageBox.Icon.Question)
        self.setText("Send error reports to the developer?")
        self.setInformativeText(
            "When the app hits an error, it can send the technical details\n"
            "to the developer's GlitchTip project (app.glitchtip.com),\n"
            "so the error gets fixed. GlitchTip also sees the IP address\n"
            "a report comes from.\n\n"
            "Responsible: marcelkb, the developer. Questions about your data\n"
            "or deleting reports: github.com/dancesport-dj/DanceSportPlayer/issues\n\n"
            "Sent: the error and where in the program it happened, the last\n"
            "log lines before it (they can name the title that was playing),\n"
            "the operating system and the app version.\n\n"
            "Not sent: your music, your playlists, your computer's name.\n"
            "Your user folder is cut out of every path.\n\n"
            "You can change this at any time under ⚙ Settings → "
            "⚙ General.")
        self.send_btn = self.addButton("Send reports",
                                       QMessageBox.ButtonRole.YesRole)
        self.keep_btn = self.addButton("Don't send",
                                       QMessageBox.ButtonRole.NoRole)
        self.setDefaultButton(self.keep_btn)
        self.setEscapeButton(self.keep_btn)
        self.update_chk = None
        if ask_updates:
            self.update_chk = QCheckBox(
                "🔔  Also tell me when a new version is out")
            self.update_chk.setToolTip(_UPDATE_CHECK_TIP)
            self.setCheckBox(self.update_chk)

    def ask(self) -> bool:
        self.exec()
        return self.clickedButton() is self.send_btn

    def wants_updates(self) -> bool:
        return self.update_chk is not None and self.update_chk.isChecked()


def ensure_error_reports_choice() -> bool:
    """Whether error reports are on, asking once on the first start that can
    send them. The answer is kept either way, so it is never asked again;
    ⚙ Settings changes it from then on. Called from run_gui() after
    ensure_app_mode(), for the same reason that one is."""
    if not error_reports.available():
        return False
    settings = load_settings()
    if "error_reports" in settings:
        return bool(settings["error_reports"])
    ask_updates = (update_check.available()
                   and update_check.SETTING not in settings)
    question = ErrorReportsQuestion(ask_updates=ask_updates)
    on = question.ask()
    settings["error_reports"] = on
    if ask_updates:
        settings[update_check.SETTING] = question.wants_updates()
    save_settings(settings)
    log.info("🐞 Error reports chosen on first start\n"
             "on: %s", on)
    return on


class UpdateCheckQuestion(QMessageBox):
    """🔔 The one-time question whether to check for new versions, for a run
    that did not ask it under the error reports question. Not checking is the
    default, and what Esc or closing the box answers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New versions")
        self.setIcon(QMessageBox.Icon.Question)
        self.setText("Tell you when a new version is out?")
        self.setInformativeText(_UPDATE_CHECK_TIP)
        self.check_btn = self.addButton("Check for new versions",
                                        QMessageBox.ButtonRole.YesRole)
        self.keep_btn = self.addButton("Don't check",
                                       QMessageBox.ButtonRole.NoRole)
        self.setDefaultButton(self.keep_btn)
        self.setEscapeButton(self.keep_btn)

    def ask(self) -> bool:
        self.exec()
        return self.clickedButton() is self.check_btn


def ensure_update_check_choice() -> bool:
    """Whether the 🔔 update check is on, asking once when no question asked
    it yet: in a build without error reports, or on the first start of a
    version that brought the check to a user who had answered those already.
    A source run has no release to compare and asks nothing. Called from
    run_gui() right after ensure_error_reports_choice()."""
    settings = load_settings()
    if update_check.SETTING in settings:
        return bool(settings[update_check.SETTING])
    if not update_check.available():
        return False
    on = UpdateCheckQuestion().ask()
    settings[update_check.SETTING] = on
    save_settings(settings)
    log.info("🔔 Update check chosen\n"
             "on: %s", on)
    return on


# ─────────────────────────────────────────────────────────────────────────────
# ffmpeg — present, or how to get it
# ─────────────────────────────────────────────────────────────────────────────
# How to install ffmpeg, per platform: (caption, command) rows plus a closing
# note. Only the running platform's block is ever shown — a Windows user reading
# three package managers learns nothing. Commands are kept as bare strings, not
# baked into a sentence, so each can go into its own copyable field.
# Homebrew's own bootstrap. Shown under any `brew install` line, because that
# command is no use on a machine that has no brew yet. The same script serves
# macOS and Linux.
_BREW_BOOTSTRAP = ("…no Homebrew yet? That line first:",
                   '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/'
                   'Homebrew/install/HEAD/install.sh)"')

_FFMPEG_HINTS = {
    "windows": (
        (("In a terminal:", "winget install Gyan.FFmpeg"),),
        "…or download a build from <a href='https://www.gyan.dev/ffmpeg/"
        "builds/'>gyan.dev/ffmpeg/builds</a> and drop <code>ffmpeg.exe</code> "
        "into this app's folder.",
    ),
    "macos": (
        (("In a terminal:", "brew install ffmpeg"), _BREW_BOOTSTRAP),
        "",
    ),
    "linux": (
        (("Debian / Ubuntu:", "sudo apt install ffmpeg"),
         ("Fedora:", "sudo dnf install ffmpeg"),
         ("Arch:", "sudo pacman -S ffmpeg"),
         # Homebrew runs on Linux too, and needs no root — the way out when the
         # distro's ffmpeg is too old or there is no sudo on this machine.
         ("…or with Homebrew, on any distro:", "brew install ffmpeg"),
         _BREW_BOOTSTRAP),
        "",
    ),
}


def ffmpeg_platform(platform: str = sys.platform) -> str:
    """'windows' / 'macos' / 'linux' for a `sys.platform` string. Anything else
    Python runs on (BSD, Solaris) installs ffmpeg from a package manager too, so
    it gets the Linux hint rather than nothing."""
    if platform.startswith("win"):
        return "windows"
    if platform == "darwin":
        return "macos"
    return "linux"


def ffmpeg_install_steps(platform: str = sys.platform) -> tuple:
    """((caption, command), …) for the platform the app is running on."""
    return _FFMPEG_HINTS[ffmpeg_platform(platform)][0]


def ffmpeg_install_note(platform: str = sys.platform) -> str:
    """The closing sentence under the commands, or "" when there is none."""
    return _FFMPEG_HINTS[ffmpeg_platform(platform)][1]


class _CopyRow(QWidget):
    """A command with a ⧉ button that puts it on the clipboard.

    A shell command that has to be retyped off a dialog is a command that gets
    typed wrong — and the Homebrew bootstrap line is 90 characters of URL. The
    field is a read-only QLineEdit rather than a label so the text can also be
    selected by hand and scrolls instead of stretching the dialog."""

    _COPIED_MS = 1200

    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.field = QLineEdit(command)
        self.field.setReadOnly(True)
        self.field.setStyleSheet("font-family: Consolas, Menlo, monospace;")
        self.field.setCursorPosition(0)
        row.addWidget(self.field)
        self.btn = QPushButton("⧉")
        self.btn.setToolTip("Copy to clipboard")
        self.btn.setFixedWidth(34)
        self.btn.clicked.connect(self.copy)
        row.addWidget(self.btn)

    def copy(self):
        """Copy the command and say so on the button itself — a clipboard write
        is invisible otherwise, and the user re-clicks wondering if it took."""
        QApplication.clipboard().setText(self.field.text())
        self.btn.setText("✓")
        # The button as context: closed within the delay, the timer goes with it.
        QTimer.singleShot(self._COPIED_MS, self.btn, lambda: self.btn.setText("⧉"))


class FfmpegMissingDialog(QDialog):
    """ffmpeg is not installed: what that costs, and the command to fix it."""

    def __init__(self, platform: str = sys.platform, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ffmpeg not found")
        self.setMinimumWidth(560)
        lyt = QVBoxLayout(self)
        lyt.setSpacing(8)

        head = QLabel("⚠️  <b>ffmpeg is not installed on this computer.</b>")
        lyt.addWidget(head)
        lost = QLabel(
            "Playlists still build and play without it. These need it and stay "
            "unavailable:<ul>"
            "<li>analysing the library — tempo, similar tracks</li>"
            "<li>🔊 loudness levelling (EBU R128)</li>"
            "<li>🔇 silence detection at the start and end of a track</li></ul>")
        lost.setWordWrap(True)
        lyt.addWidget(lost)
        lyt.addWidget(_hsep())

        self.rows = []
        for caption, command in ffmpeg_install_steps(platform):
            cap = QLabel(caption)
            cap.setStyleSheet("color:#666; font-size:11px;")
            lyt.addWidget(cap)
            row = _CopyRow(command)
            self.rows.append(row)
            lyt.addWidget(row)

        note = ffmpeg_install_note(platform)
        if note:
            nl = QLabel(note)
            nl.setWordWrap(True)
            nl.setOpenExternalLinks(True)      # the note links a download page
            nl.setStyleSheet("color:#666; font-size:11px;")
            lyt.addWidget(nl)

        tail = QLabel("Then restart the app — nothing else to configure.")
        tail.setWordWrap(True)
        lyt.addWidget(tail)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        lyt.addWidget(bb)


def warn_if_ffmpeg_missing(parent=None) -> bool:
    """Say once that ffmpeg is missing, and how to install it here. Returns
    whether the warning was shown.

    Nothing about this is fatal — playlists still build and play. What is gone
    without ffmpeg is everything that decodes audio: the library analysis
    (tempo, similar tracks), the R128 loudness levelling and the silence
    detection. Better said at the setup moment than discovered as three broken
    features later."""
    exe = find_ffmpeg()
    if exe:
        log.info("🎬 ffmpeg found\n"
                 "path: %s", exe)
        return False
    log.warning("🎬 ffmpeg not found — audio analysis, loudness levelling "
                "and silence detection stay unavailable")
    FfmpegMissingDialog(parent=parent).exec()
    return True


# In-progress playlist autosave: the working grid is written here after every
# edit (generate / ↺ / move / external drop) and restored on the next start, so a
# closed app reopens with the playlist exactly as it was left.
AUTOSAVE = JsonStore("autosave_playlist.json", note="starting without restore")
# v1 = single playlist; v2 = envelope with deck_a / deck_b / wishlist / dual;
# v3 = adds decks E–H (deck_e … deck_h) for the 8-playlist tabbed mode;
# v4 = adds the eight 📅 day decks (day_a … day_h) on the Tournament-day tab.
AUTOSAVE_VERSION = 4
# Rotating history: autosave_playlist.1.json (newest) … .5.json (oldest). A new
# backup is only cut when the newest one is older than this, so the 5 slots span
# real editing history instead of the last 5 keystrokes.
AUTOSAVE_BACKUPS = 5
_AUTOSAVE_BACKUP_MIN_AGE = 300  # seconds


def _autosave_backup_path(n: int) -> Path:
    live = AUTOSAVE.path
    return live.with_name(f"{live.stem}.{n}.json")


def _rotate_autosave_backups() -> None:
    """Shift autosave_playlist.json into the .1 … .5 backup chain (best-effort).

    Skipped while the newest backup is still fresh (< _AUTOSAVE_BACKUP_MIN_AGE),
    so bursts of grid edits don't flush the whole history with near-identical
    copies — the chain keeps ≥25 minutes of session history to fall back to."""
    if not AUTOSAVE.exists():
        return
    newest = _autosave_backup_path(1)
    try:
        import time
        if newest.exists() and time.time() - newest.stat().st_mtime < _AUTOSAVE_BACKUP_MIN_AGE:
            return
        for n in range(AUTOSAVE_BACKUPS - 1, 0, -1):
            src = _autosave_backup_path(n)
            if src.exists():
                src.replace(_autosave_backup_path(n + 1))
        # Copy (not move) the current file into slot 1: a failure between rotate
        # and the new write must never leave us without a current autosave.
        import shutil
        shutil.copy2(AUTOSAVE.path, newest)
    except Exception as exc:
        log.warning("⚠️ Autosave backup rotation failed: %s", exc)


def save_autosave(state: dict) -> None:
    """Persist the current working-playlist state (best-effort, never raises).

    Written atomically so a crash mid-save can't corrupt the previous autosave;
    time-spaced backup copies (.1 … .5) keep older session states recoverable."""
    _rotate_autosave_backups()
    AUTOSAVE.write(state)


def autosave_kept_path() -> Path:
    """Where the autosave goes when a launch could not bring all of it back."""
    live = AUTOSAVE.path
    return live.with_name(f"{live.stem}.incomplete-restore.json")


def keep_autosave_copy() -> Path | None:
    """Copy the autosave aside before the thinned-out desk of an incomplete
    restore gets written over it — F: unplugged at launch drops every track on
    it, and the .1 … .5 chain rotates the good file out within half an hour.
    Returns the copy, or None when there was nothing to copy."""
    if not AUTOSAVE.exists():
        return None
    kept = autosave_kept_path()
    try:
        import shutil
        shutil.copy2(AUTOSAVE.path, kept)
    except OSError as exc:
        log.warning("⚠️ Could not keep the autosave aside: %s", exc)
        return None
    return kept


def load_autosave() -> dict | None:
    """Read the autosaved playlist state, or None when absent / unreadable."""
    data = AUTOSAVE.read()
    # Accept the current envelope, earlier envelope versions (they simply
    # lack the newer keys) and the legacy single-playlist file (v1);
    # _restore_playlist normalises them all.
    if isinstance(data, dict) and data.get("version") in (1, 2, 3, AUTOSAVE_VERSION):
        return data
    return None


class PrintExportDialog(QDialog):
    """🖨 choose what the print button exports: the focused deck, every open deck,
    or a set of .m3u/audio files dragged in (like the Check-duplicates drop tab).
    `mode()` → 'focused' | 'all' | 'dropped'; `dropped_paths()` → list[Path]."""

    def __init__(self, parent=None, deck_count: int = 1):
        super().__init__(parent)
        self.setWindowTitle("Print / Export")
        self.setMinimumWidth(420)
        self._dropped: list[Path] = []
        lyt = QVBoxLayout(self)

        self._grp = QButtonGroup(self)
        self._rb_focused = QRadioButton("Focused playlist (current deck)")
        self._rb_all = QRadioButton((i18n.t("All open playlists (%d deck)") if deck_count == 1
                                     else i18n.t("All open playlists (%d decks)")) % deck_count)
        self._rb_dropped = QRadioButton("Drag in playlists / files…")
        for rb in (self._rb_focused, self._rb_all, self._rb_dropped):
            self._grp.addButton(rb)
            lyt.addWidget(rb)
        self._rb_focused.setChecked(True)
        if deck_count <= 1:
            self._rb_all.setEnabled(False)

        self._drop_zone = _MultiFileDropZone()
        self._drop_zone.filesDropped.connect(self._on_dropped)
        lyt.addWidget(self._drop_zone)
        self._drop_lbl = QLabel("No files added yet.")
        self._drop_lbl.setStyleSheet("color:#556; font-size:11px;")
        lyt.addWidget(self._drop_lbl)

        self._grp.buttonToggled.connect(self._sync_drop_enabled)
        self._sync_drop_enabled()

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._ok = btns.addButton("🖨  Export PDF",
                                  QDialogButtonBox.ButtonRole.AcceptRole)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lyt.addWidget(btns)

    def _sync_drop_enabled(self, *_):
        on = self._rb_dropped.isChecked()
        self._drop_zone.setEnabled(on)
        self._drop_lbl.setEnabled(on)

    def _on_dropped(self, paths: list):
        have = set(self._dropped)
        for p in paths:
            pp = Path(p)
            if pp not in have:
                self._dropped.append(pp)
                have.add(pp)
        if not self._rb_dropped.isChecked():
            self._rb_dropped.setChecked(True)
        n = len(self._dropped)
        self._drop_lbl.setText((i18n.t("%d file added.") if n == 1
                                else i18n.t("%d files added.")) % n)

    def mode(self) -> str:
        if self._rb_all.isChecked():
            return "all"
        if self._rb_dropped.isChecked():
            return "dropped"
        return "focused"

    def dropped_paths(self) -> list[Path]:
        return list(self._dropped)


class _M3uOnlyDropZone(_MultiFileDropZone):
    """A drop zone accepting only .m3u/.m3u8 playlists — a venue folder can only
    be built from a playlist file, not from single tracks."""
    _DROP_EXTS = ('.m3u', '.m3u8')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip("Drop saved .m3u playlists here, or click to browse")
        lbl = self.findChild(QLabel)
        if lbl is not None:
            lbl.setText("📂  Drop saved .m3u playlists here, or click to browse")

    def mousePressEvent(self, e):
        # Bypass _MultiFileDropZone's browse (it offers audio files too).
        if e.button() == Qt.MouseButton.LeftButton:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select playlists", str(_default_save_dir()),
                "M3U playlists (*.m3u *.m3u8);;All files (*)",
            )
            if paths:
                self.filesDropped.emit(paths)
        QFrame.mousePressEvent(self, e)


class _M3uDroppedList(_DroppedFilesList):
    """The reviewable list under the USB-export drop zone — what was added so
    far, with ➕ / ➖ / 🗑 curation — restricted to .m3u/.m3u8 (a bundle folder
    can only be built from a playlist file)."""

    def _browse(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select playlists", str(_default_save_dir()),
            "M3U playlists (*.m3u *.m3u8);;All files (*)",
        )
        if paths:
            self.add_paths(paths)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(
                _M3uOnlyDropZone._is_droppable(u) for u in e.mimeData().urls()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls()
                 if _M3uOnlyDropZone._is_droppable(u)]
        if files:
            e.acceptProposedAction()
            self.add_paths(files)
        else:
            e.ignore()


class UsbExportDialog(QDialog):
    """🧳 choose what goes into the USB venue bundle: every open playlist deck,
    only the 📅 tournament day, or saved .m3u files dragged in (like the
    Check-duplicates drop tab). Wishlists are never bundled. Or, instead of a
    bundle, the 📦 venue pack (the one ⚙ Settings exports too).
    `mode()` → 'all' | 'day' | 'dropped' | 'venue'; `dropped_paths()` → list[Path]."""

    def __init__(self, parent=None, n_decks: int = 0, n_day: int = 0,
                 day_selected: bool = False):
        super().__init__(parent)
        self.setWindowTitle("🧳 USB export")
        self.setMinimumWidth(440)
        lyt = QVBoxLayout(self)
        lyt.addWidget(QLabel("What should go into the venue bundle?"))

        n_all = n_decks + n_day
        self._grp = QButtonGroup(self)
        self._rb_all = QRadioButton((i18n.t("All open playlists (%d deck)") if n_all == 1
                                     else i18n.t("All open playlists (%d decks)")) % n_all)
        self._rb_day = QRadioButton((i18n.t("📅 Tournament day only (%d playlist)") if n_day == 1
                                     else i18n.t("📅 Tournament day only (%d playlists)")) % n_day)
        self._rb_dropped = QRadioButton("Saved playlists dragged in (.m3u)…")
        self._rb_venue = QRadioButton("📦 Venue pack: this desk for another PC…")
        self._rb_venue.setToolTip(
            "One file with the settings, every deck and wishlist and the\n"
            "cartwall, the music they use if you want: the same as\n"
            "⚙ Settings → 📦 Venue pack → Export venue pack….")
        for rb in (self._rb_all, self._rb_day, self._rb_dropped, self._rb_venue):
            self._grp.addButton(rb)
            lyt.addWidget(rb)
        self._rb_all.setEnabled(n_all > 0)
        self._rb_day.setEnabled(n_day > 0)
        if day_selected and n_day:
            self._rb_day.setChecked(True)
        elif n_all:
            self._rb_all.setChecked(True)
        else:
            self._rb_dropped.setChecked(True)

        self._drop_zone = _M3uOnlyDropZone()
        self._drop_zone.filesDropped.connect(self._on_dropped)
        lyt.addWidget(self._drop_zone)
        self._files = _M3uDroppedList()
        self._files.changed.connect(self._on_files_changed)
        lyt.addWidget(self._files)

        self._grp.buttonToggled.connect(self._sync_state)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._ok = btns.addButton("🧳  Export",
                                  QDialogButtonBox.ButtonRole.AcceptRole)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lyt.addWidget(btns)
        self._sync_state()

    def _sync_state(self, *_):
        self._ok.setEnabled(not self._rb_dropped.isChecked()
                            or bool(self._files.paths()))

    def _on_dropped(self, paths: list):
        self._files.add_paths(paths)

    def _on_files_changed(self):
        # Touching the list means the user wants the dropped-files source.
        if self._files.paths() and not self._rb_dropped.isChecked():
            self._rb_dropped.setChecked(True)
        self._sync_state()

    def mode(self) -> str:
        if self._rb_day.isChecked():
            return "day"
        if self._rb_dropped.isChecked():
            return "dropped"
        if self._rb_venue.isChecked():
            return "venue"
        return "all"

    def dropped_paths(self) -> list[Path]:
        return [Path(p) for p in self._files.paths()]


class M3uDropDialog(QDialog):
    """A QDialog that accepts a dropped .m3u/.m3u8 file anywhere on it, emitting its
    path via m3uDropped — so e.g. the Eintanzen dialog can be filled by dragging a
    playlist onto it instead of clicking Browse…."""
    m3uDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    @staticmethod
    def _m3u_of(e) -> str | None:
        md = e.mimeData()
        if md.hasUrls():
            for u in md.urls():
                if u.isLocalFile() and u.toLocalFile().lower().endswith((".m3u", ".m3u8")):
                    return u.toLocalFile()
        return None

    def dragEnterEvent(self, e):
        if self._m3u_of(e):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._m3u_of(e):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        path = self._m3u_of(e)
        if path:
            e.acceptProposedAction()
            self.m3uDropped.emit(path)
        else:
            e.ignore()


# ─────────────────────────────────────────────────────────────────────────────
# Music Speed Dialog (one track's tempo from three sources)
# ─────────────────────────────────────────────────────────────────────────────
class MusicSpeedDialog(QDialog):
    """Shows ONE track's tempo from three independent sources side by side:
    the file NAME (takt T##, bars/min), the MP3 BPM tag (ID3 TBPM, beats/min),
    and the tempo librosa MEASURED (beats/min) — so a mislabeled file stands out.
    All values are also converted to a comparable takt where the dance meter is known."""

    _METERS = {3: "3/4", 2: "2/4", 4: "4/4"}

    def __init__(self, title, dance, bpb, file_takt, tag_bpm, measured,
                 tempo_ratios=(1.0,), parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎵 Music speed")
        self.setWindowIcon(_app_icon())
        self.setModal(True)
        lay = QVBoxLayout(self)

        head = QLabel(title or "—")
        head.setStyleSheet("font-weight:600; font-size:13px;")
        head.setWordWrap(True)
        lay.addWidget(head)

        dname = dance_name(dance, dance) if dance else "—"
        meter = self._METERS.get(bpb)
        lay.addWidget(QLabel(
            i18n.t("Dance: %s") % dname
            + ("  ·  " + i18n.t("%s (%d beats/bar)") % (meter, bpb) if bpb else "")))
        lay.addWidget(_hsep())

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._b("Source"), 0, 0)
        grid.addWidget(self._b("Speed"),  0, 1)
        grid.addWidget(self._b("≈ Takt"), 0, 2)

        def to_takt(beats):
            return f"T{beats / bpb:.0f}" if (bpb and beats) else "—"

        if file_takt:
            fval = (f"T{file_takt} = {file_takt} bars/min"
                    + (f" → {file_takt * bpb} beats/min" if bpb else ""))
        else:
            fval = "— (none in name)"
        self._row(grid, 1, "📄 File name", fval, f"T{file_takt}" if file_takt else "—")

        if tag_bpm:
            self._row(grid, 2, "🏷 MP3 tag", f"{tag_bpm:.0f} BPM", to_takt(tag_bpm))
        else:
            self._row(grid, 2, "🏷 MP3 tag", "— (no BPM tag)", "—")

        if measured > 0:
            self._row(grid, 3, "🔬 Measured", f"~{measured:.0f} beats/min", to_takt(measured))
        else:
            self._row(grid, 3, "🔬 Measured", "— (not measured)", "—")

        lay.addLayout(grid)
        lay.addWidget(_hsep())

        v = QLabel(self._verdict(file_takt, bpb, measured, tempo_ratios))
        v.setWordWrap(True)
        v.setStyleSheet("font-weight:600;")
        lay.addWidget(v)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)

    @staticmethod
    def _b(text):
        l = QLabel(text)
        l.setStyleSheet("font-weight:600;")
        return l

    @staticmethod
    def _row(grid, r, src, val, takt):
        grid.addWidget(QLabel(src), r, 0)
        grid.addWidget(QLabel(val), r, 1)
        t = QLabel(takt)
        t.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(t, r, 2)

    @staticmethod
    def _verdict(file_takt, bpb, measured, ratios) -> str:
        if not (file_takt and bpb and measured > 0):
            return ("ℹ️ Not enough to compare — need a filename takt, a known dance, "
                    "and a measurement.")
        expected = file_takt * bpb
        dev = min(abs(measured * r - expected) / expected for r in ratios)
        if dev <= 0.10:
            return f"✅ File name matches the measured tempo (off {dev * 100:.0f}%)."
        return f"⚠️ File name and measured tempo disagree — off {dev * 100:.0f}%."


class TournamentDayDialog(QDialog):
    """Plan a whole tournament day: one row per competition (style, age, class,
    round pattern). Each competition lands in its own free deck; all of them
    share one "already played today" pool so no song repeats across
    competitions (Paso Doble excepted). Returns the rows via competitions()."""

    _AGES = [
        "Kinder", "Junioren", "Jugend",
        "Hauptgruppe", "Senioren I", "Senioren II", "Senioren III",
        "Senioren IV", "Senioren V",
    ]
    _CLASSES = ["D", "C", "B", "A", "S"]

    def __init__(self, style="Latin", age="Hauptgruppe", cls="S",
                 pattern="6-3-2-1", parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅 Plan tournament day")
        self.setWindowIcon(_app_icon())
        self.setModal(True)
        self._rows = []

        lay = QVBoxLayout(self)
        hint = QLabel(
            "One row per competition — each fills its own 📅 day deck on the\n"
            "Tournament-day tab; more than 8 competitions share decks (labeled\n"
            "round headers). All competitions share one no-repeat pool for the "
            "day (Paso Doble may repeat).")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addWidget(_hsep())

        head = QHBoxLayout()
        for text, stretch in (("Style", 2), ("Age", 2), ("Class", 1), ("Rounds", 2)):
            l = QLabel(text)
            l.setStyleSheet("font-weight:600;")
            head.addWidget(l, stretch)
        head.addSpacing(28)
        lay.addLayout(head)

        self._rows_lyt = QVBoxLayout()
        self._rows_lyt.setSpacing(4)
        lay.addLayout(self._rows_lyt)

        add_btn = QPushButton("➕ Add competition")
        add_btn.clicked.connect(lambda: self._add_row())
        lay.addWidget(add_btn)
        lay.addWidget(_hsep())

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self._add_row(style, age, cls, pattern)

    def _add_row(self, style="Latin", age="Hauptgruppe", cls="S", pattern="6-3-2-1"):
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)

        style_cb = QComboBox()
        style_cb.addItems(list(DANCE_STYLES))
        style_cb.setCurrentText(style)
        age_cb = QComboBox()
        age_cb.addItems(self._AGES)
        age_cb.setCurrentText(age)
        cls_cb = QComboBox()
        cls_cb.addItems(self._CLASSES)
        cls_cb.setCurrentText(cls)
        pat_ed = QLineEdit(pattern)
        pat_ed.setPlaceholderText("e.g. 6-3-2-1")

        rm = QPushButton("✖")
        rm.setFixedWidth(24)
        rm.setToolTip("Remove this competition")
        rm.clicked.connect(lambda: self._remove_row(row))

        hl.addWidget(style_cb, 2)
        hl.addWidget(age_cb, 2)
        hl.addWidget(cls_cb, 1)
        hl.addWidget(pat_ed, 2)
        hl.addWidget(rm)

        self._rows.append((row, style_cb, age_cb, cls_cb, pat_ed))
        self._rows_lyt.addWidget(row)

    def _remove_row(self, row_widget):
        if len(self._rows) <= 1:
            return   # keep at least one competition
        self._rows = [r for r in self._rows if r[0] is not row_widget]
        row_widget.setParent(None)

    def _on_ok(self):
        for _, style_cb, age_cb, _cls_cb, pat_ed in self._rows:
            if not rounds_from_pattern(pat_ed.text()):
                QMessageBox.warning(
                    self, "Invalid rounds",
                    i18n.t("'%s' is not a valid round pattern for %s %s — "
                           "use heat counts like 6-3-2-1.")
                    % (pat_ed.text(), style_cb.currentText(), age_cb.currentText()))
                pat_ed.setFocus()
                return
        self.accept()

    def competitions(self) -> list[dict]:
        return [{
            "style": style_cb.currentText(),
            "age": age_cb.currentText(),
            "cls": cls_cb.currentText(),
            "pattern": pat_ed.text().strip(),
        } for _, style_cb, age_cb, cls_cb, pat_ed in self._rows]


class LibraryGapsDialog(QDialog):
    """📊 Library gaps: one stats row per dance × start class — pool size,
    tempo compliance, proven/fresh split and staleness — with red/orange marks
    on the thin spots. Opened from the Settings dialog's 🎵 Checks tab."""

    _HDRS = ["Style", "Class", "Dance", "TPM", "Pool", "Tempo OK",
             "Proven", "Fresh", "Never played", "Stale"]
    _C_BAD = QColor("#ffcdd2")   # red — the pool can't fill a competition
    _C_WARN = QColor("#ffe0b2")  # orange — worth a look

    def __init__(self, lib, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Library gaps")
        self.setWindowIcon(_app_icon())
        self.resize(860, 560)
        self._lib = lib
        self._rows = gap_stats(lib)
        # (dance, class) the caller should open the 📚 library on — set when a
        # row is double-clicked / 📚 pressed, read after exec().
        self.jump_to: tuple[str, str] | None = None

        lay = QVBoxLayout(self)
        hint = QLabel(
            i18n.t("Red: the pool can't carry a competition (pool < %d or proven < %d — a 6-3-2-1 "
                   "needs 12 per dance).  Orange: < 80 %% of the takt-labelled tracks are tournament "
                   "tempo, or over half the pool is stale (no dateable playlist in ≥ 3 years; "
                   "'never played' always counts as stale).  Double-click a row to browse its "
                   "never-played tracks in 📚 the library.") % (GAP_MIN_POOL, GAP_MIN_PROVEN))
        hint.setWordWrap(True)
        lay.addWidget(hint)

        t = QTableWidget(len(self._rows), len(self._HDRS))
        t.setHorizontalHeaderLabels(self._HDRS)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for i, r in enumerate(self._rows):
            tempo_pct = (100.0 * r["tempo_ok"] / r["tempo_known"]
                         if r["tempo_known"] else None)
            stale_pct = 100.0 * r["stale"] / r["pool"] if r["pool"] else 0.0
            cells = [
                (r["style"], None),
                (r["cls"], None),
                (f"{dance_name(r['dance'], r['dance'])} ({r['dance']})", None),
                (f"{r['lo']}–{r['hi']}", None),
                (r["pool"], self._C_BAD if r["pool"] < GAP_MIN_POOL else None),
                (f"{tempo_pct:.0f} %  ({r['tempo_ok']}/{r['tempo_known']})"
                 if tempo_pct is not None else "—",
                 self._C_WARN if tempo_pct is not None and tempo_pct < 80 else None),
                (r["proven"],
                 self._C_BAD if r["proven"] < GAP_MIN_PROVEN else None),
                (r["fresh"], None),
                (r["never"], None),
                (f"{stale_pct:.0f} %  ({r['stale']}/{r['pool']})",
                 self._C_WARN if stale_pct > 50 else None),
            ]
            for c, (val, color) in enumerate(cells):
                it = QTableWidgetItem()
                if isinstance(val, int):
                    it.setData(Qt.ItemDataRole.EditRole, val)
                else:
                    it.setText(str(val))
                if color is not None:
                    it.setBackground(color)
                    it.setForeground(QColor("#000000"))
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, i)   # row-dict index
                t.setItem(i, c, it)
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.cellDoubleClicked.connect(lambda row, _col: self._jump(row))
        lay.addWidget(t, stretch=1)
        self._table = t

        gaps = shopping_list(self._rows)
        btns = QHBoxLayout()
        summary = QLabel(i18n.t("⚠️ %d gap(s) found") % len(gaps) if gaps
                         else "✅ No gaps — every dance × class pool is healthy")
        btns.addWidget(summary)
        btns.addStretch(1)
        show_btn = QPushButton("📚  Show never-played tracks")
        show_btn.setToolTip(
            "Close this and filter the library pane to the selected\n"
            "row's dance + class, showing only tracks you have never played.")
        show_btn.clicked.connect(lambda: self._jump(self._table.currentRow()))
        btns.addWidget(show_btn)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        lay.addLayout(btns)

    def _jump(self, row: int):
        """Remember which dance × class to browse, and close — the caller opens
        the 📚 library pane on it (the dialog can't reach past ⚙ Settings)."""
        it = self._table.item(row, 0) if row >= 0 else None
        idx = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
        if idx is None:
            return
        stats = self._rows[int(idx)]
        self.jump_to = (stats["dance"], stats["cls"])
        self.accept()


