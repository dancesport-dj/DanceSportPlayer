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
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel,
    QComboBox, QCheckBox, QLineEdit, QGroupBox,
    QScrollArea, QDialog, QProgressBar, QSpinBox, QDoubleSpinBox, QTimeEdit,
    QFileDialog, QDialogButtonBox, QTabWidget, QRadioButton, QButtonGroup,
    QMessageBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QFrame,
    QPlainTextEdit, QColorDialog, QListWidget, QListWidgetItem, QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt, Signal, QProcess, QSize, QStandardPaths, QTime, QTimer,
)
from PySide6.QtGui import QColor, QPixmap

import planner.config
from planner.db import HAS_LIBROSA
from planner.gaps import gap_stats, shopping_list, GAP_MIN_POOL, GAP_MIN_PROVEN
from planner.models import DANCE_STYLES, TEMPO_RANGES, rounds_from_pattern
from planner.terms import dance_name
from planner.play_sets import (
    _LEN_MAX, _LEN_STEP, migrate_play_sets, parse_play_length, play_set_of, tso_of)

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
from shared.audio_files import (
    music_browse_dir,
)
from shared.playback import (
    _AUDIO_IDLE_S,
)
from shared.widgets import (
    _app_icon,
    _hsep,
)
from shared import error_reports, looks, theme, user_looks
from planner import i18n
from planner.paths import parse_remap_paths
from planner.store import JsonStore
from planner.version import DEV
from shared.stores import SETTINGS, player_layout_of, save_settings
from gui.look_editor import LookEditor, LookPreview
from gui.similar_dialog import SimilarTracksDialog  # noqa: F401
from gui.duplicate_dialog import DuplicateResolveDialog  # noqa: F401
from gui.ai_dialogs import (  # noqa: F401
    AiPlaylistDialog, AiSuggestDialog, AiTranscriptDialog,
)
# shared.audio_probes pulls in nothing but the planner and QtCore, so no cycle here.
from shared.audio_probes import find_ffmpeg

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
        "announce_advanced": False,
        # 🔇 Hand the sound device back when nothing is playing. Off by
        # default: it costs the click a sound card makes when the next title
        # re-opens it, which is only worth paying if the hiss is audible.
        "release_audio_idle": False,
        # 🔕 The OS's own dings off the shared sound card while the evening
        # runs (Playing mode, or anything audible) — see player.system_sounds.
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


# Bumped when a column is added to the decks or the library: the column ticks,
# widths and the library's order are saved by column INDEX.
COLUMNS_VERSION = 3

# The column each version added: (its index in the decks, in the library).
# v2 ★ Rating, v3 Custom.
_ADDED_COLUMNS = {2: (9, 10), 3: (10, 11)}


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
# second palette — shared/theme.py says how and why. Both settings are read once at
# start-up, so changing either offers a restart. The 🎨 looks (shared/looks.py)
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
    return "Party" if mode == "player" else "Eintanzen / Party"


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
                      "📁 Paths & search.")
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
    save_settings(settings)
    log.info("🎚️ App mode chosen on first start\n"
             "mode: %s", mode)
    # Straight after the welcome question: the machine is being set up right
    # now, which is the one moment a missing ffmpeg is cheap to fix.
    warn_if_ffmpeg_missing()
    return mode


class ErrorReportsQuestion(QMessageBox):
    """🐞 The one-time question whether error reports may go out. Not sending
    is the default, and what Esc or closing the box answers."""

    def __init__(self, parent=None):
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
            "📁 Paths & search.")
        self.send_btn = self.addButton("Send reports",
                                       QMessageBox.ButtonRole.YesRole)
        self.keep_btn = self.addButton("Don't send",
                                       QMessageBox.ButtonRole.NoRole)
        self.setDefaultButton(self.keep_btn)
        self.setEscapeButton(self.keep_btn)

    def ask(self) -> bool:
        self.exec()
        return self.clickedButton() is self.send_btn


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
    on = ErrorReportsQuestion().ask()
    settings["error_reports"] = on
    save_settings(settings)
    log.info("🐞 Error reports chosen on first start\n"
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


class SettingsDialog(QDialog):
    """Configure the library paths + global search (tab 1) and run every
    analysis / index build, grouped light vs heavy (tab 2)."""

    def __init__(self, settings: dict, parent=None, build_cb=None, embed_cb=None,
                 index_summary=None, all_cb=None, maintenance_cb=None, relearn_cb=None,
                 analyze_cb=None, loudness_cb=None, silence_cb=None, pd_cb=None,
                 vocals_cb=None, gaps_cb=None, n_unanalyzed: int = 0,
                 pd_export_cb=None, pd_import_cb=None):
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
        summ = index_summary or {}
        lyt = QVBoxLayout(self)
        tabs = QTabWidget()
        lyt.addWidget(tabs)

        # ═══ Tab 1: Paths & search ═══
        paths_tab = QWidget()
        plyt = QVBoxLayout(paths_tab)
        plyt.setSpacing(10)

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
            "<b>Referenzpfad</b> — base folder the playlist files live in on THIS PC; "
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
            "🧭 Fix paths tries the Referenzpfad first and then these folders,\n"
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

        plyt.addWidget(_hsep())

        # ── Preview player overlay ──
        self._preview_chk = QCheckBox(
            "🎧  Preview player — float a mini player (seek / skip / volume) over "
            "the deck when a ▶ button is clicked")
        self._preview_chk.setChecked(bool(settings.get("preview_player", True)))
        plyt.addWidget(self._preview_chk)

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

        # ── Advanced announcement controls ──
        self._voice_adv_chk = QCheckBox(
            "🎙  Advanced voice controls — show '…with takt', '…with heat' and "
            "🔈 Test under 'Announce next dance'")
        self._voice_adv_chk.setChecked(
            bool(settings.get("announce_advanced", False)))
        self._voice_adv_chk.setToolTip(
            "Three switches that are set once and then never touched again,\n"
            "in the busiest column of the desk. Hidden they keep whatever they\n"
            "were set to — only the controls go away.")
        plyt.addWidget(self._voice_adv_chk)

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

        plyt.addWidget(_hsep())

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

        plyt.addStretch()
        tabs.addTab(paths_tab, "📁 Paths && search")

        # ═══ Tab 2: Look — theme and accent colour ═══
        look_tab = QWidget()
        llyt = QVBoxLayout(look_tab)
        llyt.setSpacing(10)

        llyt.addWidget(QLabel(
            "<b>🎨 Theme</b> — the classic light or dark, or one of the looks:"))
        pick_row = QHBoxLayout()
        # One list with section headers rather than a combo: the classic pair
        # stands apart from the looks, and every entry is visible at once.
        # QListWidgetItem is not among the hooked setters, so each caption asks
        # for its translation itself.
        self._theme_list = QListWidget()
        self._theme_list.setMinimumWidth(230)
        self._theme_blurbs: dict[str, str] = {}
        # Keys of looks of your own made, changed or deleted while this is
        # open: when the running look is among them, saving offers a restart.
        self._looks_touched: set[str] = set()
        self._fill_theme_list()
        list_col = QVBoxLayout()
        list_col.addWidget(self._theme_list, stretch=1)
        own_row = QGridLayout()
        self._look_new = QPushButton("＋  New look…")
        self._look_new.setToolTip(
            "A look of your own, starting as a copy of the selected one.")
        self._look_new.clicked.connect(self._new_look)
        self._look_edit = QPushButton("✎  Edit…")
        self._look_edit.clicked.connect(self._edit_look)
        self._look_delete = QPushButton("🗑  Delete")
        self._look_delete.clicked.connect(self._delete_look)
        self._look_import = QPushButton("Import…")
        self._look_import.setToolTip("Add a look someone exported.")
        self._look_import.clicked.connect(self._import_look)
        self._look_export = QPushButton("Export…")
        self._look_export.setToolTip("Save the selected look of your own as a "
                                     "file, to pass it on.")
        self._look_export.clicked.connect(self._export_look)
        own_row.addWidget(self._look_new, 0, 0, 1, 2)
        own_row.addWidget(self._look_edit, 1, 0)
        own_row.addWidget(self._look_delete, 1, 1)
        own_row.addWidget(self._look_import, 2, 0)
        own_row.addWidget(self._look_export, 2, 1)
        list_col.addLayout(own_row)
        pick_row.addLayout(list_col)
        preview_col = QVBoxLayout()
        self._theme_preview = ThemePreview()
        preview_col.addWidget(self._theme_preview)
        # A look of your own has no picture of the main window: these controls,
        # dressed in it, stand in.
        self._look_preview = LookPreview()
        self._look_preview.hide()
        preview_col.addWidget(self._look_preview)
        self._theme_blurb = QLabel()
        self._theme_blurb.setWordWrap(True)
        preview_col.addWidget(self._theme_blurb)
        preview_col.addStretch()
        pick_row.addLayout(preview_col, stretch=1)
        llyt.addLayout(pick_row, stretch=1)

        llyt.addWidget(_hsep())

        llyt.addWidget(QLabel(
            "<b>🎚 Accent colour</b> — the blue the buttons, sliders and the "
            "▶ player panel are built around:"))
        self._accent = theme.accent_of(settings)
        accent_row = QHBoxLayout()
        self._accent_btn = QPushButton("  Pick a colour…")
        self._accent_btn.setToolTip(
            "Only the accent's own family of tints follows this colour.\n"
            "A red warning, a green proven mark and the popularity amber mean\n"
            "something, so they keep their hue.")
        self._accent_btn.clicked.connect(self._pick_accent)
        accent_row.addWidget(self._accent_btn, stretch=1)
        self._accent_reset = QPushButton("↺  Default blue")
        self._accent_reset.clicked.connect(
            lambda: self._set_accent(theme.ACCENT_DEFAULT))
        accent_row.addWidget(self._accent_reset)
        llyt.addLayout(accent_row)
        self._accent_note = QLabel(
            "A look brings its own accent colour — this one is for Light and Dark.")
        self._accent_note.setStyleSheet("color:#666; font-size:11px;")
        llyt.addWidget(self._accent_note)
        self._set_accent(self._accent)
        self._theme_list.currentItemChanged.connect(self._on_theme_picked)
        self._select_theme(theme.theme_of(settings))

        llyt.addWidget(_hsep())

        llyt.addWidget(QLabel(
            "<b>🌐 Language</b> — menus, buttons and dialogs:"))
        self._language_combo = QComboBox()
        for code, caption, blurb in i18n.LANGUAGES:
            self._language_combo.addItem(caption, code)
            # The caption reaches German through the patched addItem; the
            # blurb rides setItemData, which stays unpatched on purpose, so
            # it asks for itself.
            self._language_combo.setItemData(
                self._language_combo.count() - 1, i18n.t(blurb),
                Qt.ItemDataRole.ToolTipRole)
        self._language_combo.setCurrentIndex(
            max(0, self._language_combo.findData(i18n.language_of(settings))))
        llyt.addWidget(self._language_combo)

        self._german_terms_chk = QCheckBox(
            "Keep the German dance and round names on an English screen "
            "(Langsamer Walzer, Vorrunde, Standardrunde 1 …)")
        self._german_terms_chk.setToolTip(
            "On: the presenter screen and the recorded announcements are "
            "German too.\n"
            "Off: Slow Waltz, Round 1, Standard round 1 … — the playlists "
            "and exports keep the German words either way.")
        self._german_terms_chk.setChecked(bool(settings.get("german_dance_terms")))
        llyt.addWidget(self._german_terms_chk)

        look_note = QLabel(
            "Theme, accent and language are read when the app starts, so a "
            "change takes effect after a restart — you are asked once you save.")
        look_note.setWordWrap(True)
        look_note.setStyleSheet("color:#666; font-size:11px;")
        llyt.addWidget(look_note)

        tabs.addTab(look_tab, "🎨 Look")

        # ═══ Tab 3: Analysis — every analyze/index action, light vs heavy ═══
        from planner import embeddings as ae
        from planner.vocals import demucs_available
        ana_tab = QWidget()
        alyt = QVBoxLayout(ana_tab)
        alyt.setSpacing(8)

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
        # …and what each of the three has actually done so far. Without these the
        # tab showed a coverage line for every librosa/AI index and none at all
        # for the ffmpeg ones, so "is my loudness done?" had no answer here.
        llyt.addWidget(self._index_label("📊  Loudness measured", summ.get("loudness")))
        llyt.addWidget(self._index_label("🐂  PD highlights detected", summ.get("pd")))
        llyt.addWidget(self._index_label("🔇  Silences probed", summ.get("silences")))
        alyt.addWidget(light_box)

        # ── Heavy: torch AI stack, needs the FULL build / optional installs ──
        # In a frozen .exe (planner.build_flavor() != "dev") a missing backend
        # can't be pip-installed, so its controls are hidden entirely; a dev
        # install keeps them visible with the "– not installed" hint instead.
        dev = planner.config.build_flavor() == "dev"
        have_openl3 = ae.openl3_available()
        have_demucs = demucs_available()
        self._embed_combo = None
        self._embed_btn = None
        self._vocals_btn = None
        if dev or have_openl3 or have_demucs:
            heavy_box = QGroupBox("🐘 Heavy — AI models, needs the FULL build (or the "
                                  "requirements-full.txt extras)")
            hlyt = QVBoxLayout(heavy_box)

            if dev or have_openl3:
                erow = QHBoxLayout()
                self._embed_combo = QComboBox()
                if dev or have_openl3:
                    ol3 = i18n.t("🧠  OpenL3 'sounds-alike' index")
                    if not have_openl3:
                        ol3 += i18n.t("  – not installed")
                    self._embed_combo.addItem(ol3, ae.MODEL_OPENL3)
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
                if dev or have_openl3:
                    hlyt.addWidget(self._index_label("🧠  OpenL3 indexed", summ.get("openl3")))

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

        # ── One-click: build every cache on this tab ──
        self._all_btn = QPushButton("🧱  Build ALL caches…")
        self._all_btn.setToolTip(
            "Build everything on this tab in one go for a chosen library, in turn:\n"
            "🎚 librosa → 📊 loudness → 🔇 silences → 🐂 PD highlights → 🧠 OpenL3 →\n"
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
                 "Applied by itself as soon as you play from the 🤸 Eintanzen / "
                 "party list, and switched back when a tournament deck takes over.")):
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
            row.addStretch(1)
            blyt.addLayout(row)

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
            self._set_widgets[which] = {"length": length, "fade": fade,
                                        "boxes": boxes, "secs": cur["secs"]}
            tlyt.addWidget(box)

        pd_note = QLabel(
            "The 🐂 Paso Doble highlight stop is <i>switched off</i> by the "
            "🏆 tournament set: its detection is not good enough yet to cut a "
            "competition Paso Doble on, and a heat stopped in the wrong bar is "
            "danced twice. It is not configurable here — the 🎉 party set "
            "leaves it wherever you set it on the Playing panel, and you can "
            "switch it back on there for a demo.")
        pd_note.setWordWrap(True)
        pd_note.setStyleSheet("color:#666; font-size:11px;")
        tlyt.addWidget(pd_note)

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

        tlyt.addStretch()
        sets_idx = tabs.addTab(sets_tab, "🎛 Play sets")

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
                 "on (Eintanzen playlists); default 4:00.")

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
        if self._embed_cb:
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

    # ── 🎨 Look ───────────────────────────────────────────────────────────────
    _OWN_BLURB = ("A look of your own, kept on this computer. ✎ Edit changes it, "
                  "Export passes it on.")
    # What ＋ New copies when Light or Dark is selected: the look nearest to it.
    _NEW_FROM_CLASSIC = {"light": "paper", "dark": "graphite"}

    def _fill_theme_list(self) -> None:
        """The sections: the classic pair, the built-in groups, your own looks.
        Own captions are names you gave, so they are shown as they are."""
        self._theme_list.blockSignals(True)
        self._theme_list.clear()
        self._theme_blurbs.clear()
        sections = [("Standard", [(k, i18n.t(c), i18n.t(b))
                                  for k, c, b in THEME_CHOICES])]
        for group, label in looks.GROUPS:
            sections.append((label, [(look.key, i18n.t(look.caption), i18n.t(look.blurb))
                                     for look in looks.LOOKS.values()
                                     if look.group == group]))
        sections.append(("Own looks", [(look.key, look.caption, i18n.t(self._OWN_BLURB))
                                       for look in user_looks.mine()]))
        for label, entries in sections:
            head = QListWidgetItem(i18n.t(label))
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            font = head.font()
            font.setBold(True)
            head.setFont(font)
            self._theme_list.addItem(head)
            for key, caption, blurb in entries:
                item = QListWidgetItem("   " + caption)
                item.setData(Qt.ItemDataRole.UserRole, key)
                self._theme_list.addItem(item)
                self._theme_blurbs[key] = blurb
        if not user_looks.mine():
            empty = QListWidgetItem("   " + i18n.t("none yet — ＋ New look…"))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._theme_list.addItem(empty)
        self._theme_list.blockSignals(False)

    def _selected_own(self) -> "looks.Look | None":
        look = looks.get(self.selected_theme())
        return look if look is not None and look.group == user_looks.GROUP else None

    def running_look_touched(self) -> bool:
        """Whether the look the app runs in was changed or deleted here — saved
        at once, so the app has to restart to show it even with the same pick."""
        return theme.active_theme() in self._looks_touched

    def _relist(self, select: str) -> None:
        self._fill_theme_list()
        self._select_theme(select)
        self._on_theme_picked()

    def _new_look(self) -> None:
        key = self.selected_theme()
        source = looks.get(self._NEW_FROM_CLASSIC.get(key, key))
        own = source.group == user_looks.GROUP
        name = i18n.t("%s (own)") % (source.caption if own else i18n.t(source.caption))
        self._edit(user_looks.copy_of(source, name))

    def _edit_look(self) -> None:
        look = self._selected_own()
        if look is not None:
            self._edit(look)

    def _edit(self, look: looks.Look) -> None:
        editor = LookEditor(look, self)
        if editor.exec() != QDialog.DialogCode.Accepted:
            return
        look = editor.look()
        if not user_looks.put(look):
            QMessageBox.warning(self, "Look not saved",
                                "The looks file could not be written. "
                                "The log names the reason.")
        self._looks_touched.add(look.key)
        self._relist(look.key)

    def _delete_look(self) -> None:
        look = self._selected_own()
        if look is None:
            return
        answer = QMessageBox.question(
            self, "Delete look",
            i18n.t("Delete the look “%s”? This cannot be undone; "
                   "an exported file of it stays.") % look.caption)
        if answer != QMessageBox.StandardButton.Yes:
            return
        user_looks.remove(look.key)
        self._looks_touched.add(look.key)
        self._relist("light")

    def _import_look(self) -> None:
        # QFileDialog is not one of the patched statics: its texts ask here.
        path, _filter = QFileDialog.getOpenFileName(
            self, i18n.t("Import a look"), "", i18n.t("Looks (*.json)"))
        if not path:
            return
        try:
            look = user_looks.import_file(Path(path))
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Look not imported",
                                i18n.t("This file holds no look the app can use:\n%s")
                                % exc)
            return
        self._relist(look.key)

    def _export_look(self) -> None:
        look = self._selected_own()
        if look is None:
            return
        name = (user_looks.slug(look.caption) or "look") + ".json"
        path, _filter = QFileDialog.getSaveFileName(
            self, i18n.t("Export the look"), name, i18n.t("Looks (*.json)"))
        if not path:
            return
        try:
            user_looks.export(look, Path(path))
        except OSError as exc:
            QMessageBox.warning(self, "Look not exported",
                                i18n.t("The file could not be written:\n%s") % exc)

    def selected_theme(self) -> str:
        item = self._theme_list.currentItem()
        key = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return key or "light"

    def _select_theme(self, key: str) -> None:
        for row in range(self._theme_list.count()):
            item = self._theme_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                self._theme_list.setCurrentItem(item)
                return

    def _on_theme_picked(self, _item=None, _previous=None):
        key = self.selected_theme()
        mine = self._selected_own()
        if mine is None:
            self._theme_preview.show_theme(key)
        else:
            self._look_preview.set_look(mine)
        self._theme_preview.setVisible(mine is None)
        self._look_preview.setVisible(mine is not None)
        for button in (self._look_edit, self._look_delete, self._look_export):
            button.setEnabled(mine is not None)
        self._theme_blurb.setText(self._theme_blurbs.get(key, ""))
        # A look's accent is part of its design; the picker is for the classic pair.
        own = looks.get(key) is None
        self._accent_btn.setEnabled(own)
        self._accent_reset.setEnabled(own)
        self._accent_note.setVisible(not own)
        # The swatch is painted in the picked colour on purpose, so it shows no
        # disabled state of its own; fade it instead.
        fade = None if own else QGraphicsOpacityEffect(self._accent_btn)
        if fade is not None:
            fade.setOpacity(0.35)
        self._accent_btn.setGraphicsEffect(fade)

    def _pick_accent(self):
        # Not one of the patched statics — only QMessageBox and QInputDialog
        # are — so the picker's own title is translated here.
        chosen = QColorDialog.getColor(
            QColor(self._accent), self, i18n.t("Accent colour"))
        if chosen.isValid():
            self._set_accent(chosen.name())

    def _set_accent(self, color: str):
        """Remember the accent and paint the button in it.

        The swatch is the only preview there is — the app itself only picks the
        accent up on the next start — so the button has to show the colour
        honestly, with text that stays readable on whatever was picked."""
        self._accent = theme.rgb_to_hex(theme.hex_to_rgb(color))
        on_dark = theme.contrast_ratio(self._accent, "#ffffff") >= 3.0
        ink = "#ffffff" if on_dark else "#141414"
        # Not via the themed setStyleSheet hook: this swatch must be exactly the
        # colour that was picked, not that colour shaded for the active theme.
        theme.set_stylesheet_unthemed(
            self._accent_btn,
            f"background:{self._accent}; color:{ink};"
            f" border:1px solid #888; padding:6px; font-weight:bold;")
        self._accent_btn.setText(i18n.t("  %s  —  pick a colour…") % self._accent)

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
            "playlist_dir":  self._pl_edit.text().strip(),
            "reference_path": self._ref_edit.text().strip(),
            "remap_paths": parse_remap_paths(self._remap_edit.toPlainText()),
            "global_search": self._global_chk.isChecked(),
            "preview_player": self._preview_chk.isChecked(),
            "player_layout": self._player_layout_combo.currentData(),
            "announce_advanced": self._voice_adv_chk.isChecked(),
            "media_backend": self._backend_combo.currentData(),
            "theme": self.selected_theme(),
            "accent_color": self._accent,
            "language": self._language_combo.currentData(),
            "german_dance_terms": self._german_terms_chk.isChecked(),
            "release_audio_idle": self._release_audio_chk.isChecked(),
            "mute_system_sounds": self._mute_sys_chk.isChecked(),
            **({"error_reports": self._error_reports_chk.isChecked()}
               if self._error_reports_chk is not None else {}),
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
        for which, w in self._set_widgets.items():
            vals[f"{which}_set"] = dict(
                {k: chk.isChecked() for k, chk in w["boxes"].items()},
                secs=self._play_set_secs(w),
                fade=w["fade"].value())
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


class _DropCheckCancelled(Exception):
    """Raised from FileDropCheckPanel's progress tick when Cancel was pressed."""


class FileDropCheckPanel(QWidget):
    """Reusable 'drag .m3u playlists / audio files in and check them' panel: the drop
    zone, a curatable list of the files added so far (➕ add / ➖ remove / 🗑 clear,
    like the Check-duplicates window), a progress bar and a results area. Used as
    the second tab of the Check-music and Fix-paths dialogs.

    `run_fn(paths, progress_cb)` renders the results for the current files; it returns
    either a `QWidget` or a `(QWidget, summary_dict)` tuple. `summary_dict` is re-emitted
    via `resultsReady` so a host dialog can drive its own bottom summary / action button.
    When `action_label`/`action_fn` are given, an in-panel action button runs
    `action_fn(paths)` and then re-runs the check so the results update.

    The check pumps events on every `progress_cb` tick, so a click can land mid-run:
    the action button is off until the pass ends, and `checkStarted` tells a host to
    do the same with an action button of its own (`resultsReady` follows). A pass
    with many tracks, or one running past 250 ms, shows a Cancel next to the bar;
    it stops the pass at the next tick."""
    resultsReady = Signal(dict)
    checkStarted = Signal()

    def __init__(self, info_html: str, run_fn, action_label: str = "",
                 action_fn=None, parent=None):
        super().__init__(parent)
        self._run_fn    = run_fn
        self._action_fn = action_fn
        self._busy  = False
        self._dirty = False
        self._cancelled = False
        self._started = 0.0

        lyt = QVBoxLayout(self)
        info = QLabel(info_html)
        info.setWordWrap(True)
        lyt.addWidget(info)

        self._zone = _MultiFileDropZone()
        self._zone.filesDropped.connect(lambda ps: self._files.add_paths(ps))
        lyt.addWidget(self._zone)

        self._files = _DroppedFilesList()
        self._files.changed.connect(self._refresh)
        lyt.addWidget(self._files)

        self._action_btn = None
        if action_label and action_fn is not None:
            bar = QHBoxLayout()
            bar.addStretch(1)
            self._action_btn = QPushButton(action_label)
            self._action_btn.setEnabled(False)
            self._action_btn.clicked.connect(self._on_action)
            bar.addWidget(self._action_btn)
            lyt.addLayout(bar)

        self._pbar = QProgressBar()
        self._pbar.setVisible(False)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        pbar_row = QHBoxLayout()
        pbar_row.addWidget(self._pbar, stretch=1)
        pbar_row.addWidget(self._cancel_btn)
        lyt.addLayout(pbar_row)

        self._results = QScrollArea()
        self._results.setWidgetResizable(True)
        lyt.addWidget(self._results, stretch=1)
        self._refresh()

    def _on_action(self):
        if self._action_fn is not None:
            paths = self.paths()
            if paths:
                self._action_fn(paths)
                self._refresh()

    def _on_cancel(self):
        self._cancelled = True

    def _progress(self, done: int, total: int):
        # A short load finishes instantly — no bar flicker — unless its tracks are
        # slow (🔇 noise probes take seconds each).
        if total > 12 or time.monotonic() - self._started >= 0.25:
            self._pbar.setVisible(True)
            self._cancel_btn.setVisible(True)
            self._pbar.setRange(0, total)
            self._pbar.setValue(done)
        QApplication.processEvents()
        if self._cancelled:
            raise _DropCheckCancelled()

    def paths(self) -> list[Path]:
        """The files currently dropped into the panel."""
        return [Path(p) for p in self._files.paths()]

    def refresh(self):
        """Re-run the check (e.g. after a host-driven action rewrote files)."""
        self._refresh()

    def _refresh(self):
        # processEvents() during the check can deliver another drop, re-entering here;
        # defer it so the running pass finishes first.
        if self._busy:
            self._dirty = True
            return
        self._busy = True
        self._cancelled = False
        self._started = time.monotonic()
        self.checkStarted.emit()
        summary: dict = {}
        n = 0
        if self._action_btn is not None:
            self._action_btn.setEnabled(False)
        try:
            paths = self.paths()
            n = len(paths)
            try:
                out = (self._run_fn(paths, self._progress)
                       if n else QLabel("Drop playlists above to check them."))
            except _DropCheckCancelled:
                out = QLabel("Check cancelled — drop or ➕ add files to run it again.")
            widget, summary = out if isinstance(out, tuple) else (out, {})
            summary.setdefault("files", n)
            self._results.setWidget(widget)
        finally:
            self._busy = False
            self._pbar.setVisible(False)
            self._cancel_btn.setVisible(False)
            if self._action_btn is not None:
                self._action_btn.setEnabled(n > 0)
        self.resultsReady.emit(summary)
        if self._dirty:
            self._dirty = False
            QTimer.singleShot(0, self._refresh)


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
    Check-duplicates drop tab). Wishlists are never bundled.
    `mode()` → 'all' | 'day' | 'dropped'; `dropped_paths()` → list[Path]."""

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
        for rb in (self._rb_all, self._rb_day, self._rb_dropped):
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


