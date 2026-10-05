"""Shared GUI primitives of the Dancesport Playlist Planner.

Leaf module (imports nothing GUI-side), extracted 1:1 from gui/dialogs.py in
the big-module split: palette constants, small label/busy/loading
widgets, tooltips, open-in-player/folder helpers, the drag-enabled result
table and the drop-zone widget family. What the evening uses too (columns,
toast, icon, flow layout, audio extensions, browse folder, playback maths)
lives in shared/. gui.dialogs
re-exports everything, so existing importers keep working unchanged."""
import html
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QPushButton, QLabel,
    QAbstractItemView, QHeaderView, QMessageBox,
    QFrame, QDialog, QProgressBar, QMenu, QFileDialog, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import (
    Qt, Signal, QUrl, QMimeData, QTimer,
)
from PySide6.QtGui import (
    QColor, QDrag, QTextDocumentFragment,
)

from planner import i18n
from planner.terms import DANCE_SHORT, dance_name  # noqa: F401 (DANCE_SHORT: re-exported)
from planner.vocals import entry_is_instrumental
from planner.warmup import warmup_code
from shared.audio_files import _AUDIO_EXTS, music_browse_dir, remember_browse_dir
from shared.columns import _COL_CUSTOM, _COL_HEAT, _COL_RATING
from shared.icons import INK, icon
from shared.widgets import _ICON_ICO, _app_icon, _show_toast

log = logging.getLogger("dancesport.gui")

# ── Shared GUI-side constants & helpers ───────────────────────────────────────
# Used across the MainWindow concern mixins; kept in this shared leaf module so
# the controller modules never have to import the dancesport_gui facade.

# How many old playlists a title has to appear in before it counts as PROVEN
# rather than rarely played (the ★ pick in 📚 the library and in the
# Similar-Tracks window). A handful of plays is still a track being tried out;
# ten says the floor has really danced it.
_PROVEN_MIN_PLAYS = 10

# 🎛 First-run width of the cartwall dock (_restore_layout applies it).
CART_DOCK_W = 620


def _sanitize_filename(name: str) -> str:
    """Turn a competition label like 'SEN I LAT' into a safe M3U basename."""
    safe = re.sub(r"[^\w]+", "_", name).strip("_")
    return safe or "Competition"


def apply_taskbar_icon(window) -> None:
    """Force the Windows taskbar button of `window` to use the app icon.

    Qt's setWindowIcon() set in __init__ doesn't always reach the taskbar
    button, because the native window handle (HWND) isn't realised until the
    window is shown — so the main window falls back to the generic Python
    icon even though the startup splash showed ours. Pushing the icon straight
    to the HWND via WM_SETICON (after show()) fixes it reliably. No-op off
    Windows / when the .ico is missing."""
    if sys.platform != "win32" or not _ICON_ICO.exists():
        return
    try:
        import ctypes
        hwnd = int(window.winId())
        user32 = ctypes.windll.user32
        ico = str(_ICON_ICO)
        IMAGE_ICON, LR_LOADFROMFILE = 1, 0x00000010
        WM_SETICON, ICON_SMALL, ICON_BIG = 0x0080, 0, 1
        # Load the frame Windows wants for each slot directly from the .ico.
        h_small = user32.LoadImageW(None, ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        h_big   = user32.LoadImageW(None, ico, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if h_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_small)
        if h_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
    except Exception as ex:
        log.warning("🖼️ Could not push native taskbar icon: %s", ex)


# Emoji and what rides on them: symbols, variation selectors, joiners.
_TITLE_EMOJI_CATEGORIES = {"So", "Sk", "Mn", "Cf", "Cs"}


def plain_title(text: str) -> str:
    """`text` without a leading emoji. The title bar already shows the app
    icon, so "⚙  Settings" there read as two pictures side by side."""
    import unicodedata
    i = 0
    while i < len(text) and unicodedata.category(text[i]) in _TITLE_EMOJI_CATEGORIES:
        i += 1
    rest = text[i:].lstrip()
    return rest if i and rest else text


def install_plain_title_hook():
    """Strip the leading emoji from every window title, current and future.

    An event filter on the application rather than 18 edited literals: the
    same strings label the buttons that open those windows and key the German
    catalog, and a title set later (the message boxes, similar_dialog's
    history) is caught too. Returns the filter."""
    from PySide6.QtCore import QEvent, QObject

    class _TitleWatcher(QObject):
        def eventFilter(self, obj, event):
            if (event.type() == QEvent.Type.WindowTitleChange
                    and isinstance(obj, QWidget) and obj.isWindow()):
                title = obj.windowTitle()
                plain = plain_title(title)
                if plain != title:
                    obj.setWindowTitle(plain)
            return False

    app = QApplication.instance()
    watcher = _TitleWatcher(app)
    app.installEventFilter(watcher)
    return watcher


def _lbl(text: str) -> QLabel:
    return QLabel(text)


# ─────────────────────────────────────────────────────────────────────────────
# Loading Dialog (shown while LibraryLoader runs)
# ─────────────────────────────────────────────────────────────────────────────
class LoadingDialog(QDialog):
    """Modal splash-style dialog shown while the music library is being scanned."""

    def __init__(self, title: str = "DanceSport Planner & Player",
                 version: str = ""):
        # The name depends on the app mode (gui.dialogs.app_title) — passed in
        # rather than imported, since gui.common must never import gui.dialogs.
        # The version (planner.version) sits under it, so the release is on
        # screen from the first second.
        super().__init__(None)
        self.setWindowTitle(title)
        self.setFixedSize(420, 165 if version else 145)
        # Title bar only – no close / min / max buttons
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(36, 24, 36, 28)
        lyt.setSpacing(12)

        title_lbl = QLabel(title)
        f = title_lbl.font()
        f.setPointSize(13)
        f.setBold(True)
        title_lbl.setFont(f)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lyt.addWidget(title_lbl)
        if version:
            ver_lbl = QLabel(version)
            ver_lbl.setObjectName("splashVersion")
            ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ver_lbl.setStyleSheet("color: #888; font-size: 10px;")
            lyt.addWidget(ver_lbl)

        self._msg = QLabel("Loading music library…")
        # The scan reports "n / total" plus the current file on a second line.
        self._msg.setWordWrap(True)
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg.setStyleSheet("color: #555; font-size: 11px;")
        lyt.addWidget(self._msg)

        bar = QProgressBar()
        bar.setRange(0, 0)      # indeterminate / pulsing animation
        bar.setFixedHeight(7)
        bar.setTextVisible(False)
        lyt.addWidget(bar)
        self.setWindowIcon(_app_icon())

    def set_status(self, msg: str):
        self._msg.setText(msg)

    def closeEvent(self, event):
        event.ignore()          # user cannot close it manually


def _fmt_duration(seconds: float) -> str:
    """Human-readable duration, e.g. 8m 20s / 1h 03m / 45s."""
    s = int(max(0, seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {sec:02d}s"
    return f"{sec}s"


# ─────────────────────────────────────────────────────────────────────────────
# Busy Dialog (deferred — only appears if an operation runs longer than a delay)
# ─────────────────────────────────────────────────────────────────────────────
class BusyDialog(QDialog):
    """Small centered modal 'please wait' dialog with an indeterminate bar.

    Use `show_after(ms)` to display it only if the work hasn't finished within
    `ms`, and `finish()` when the work completes (cancels the pending show or
    closes the dialog if already visible). Pass `cancelable=True` for a Cancel
    button that emits `cancel_requested`.
    """

    cancel_requested = Signal()

    def __init__(self, parent=None, message="Analyzing…", cancelable=False):
        super().__init__(parent)
        self.setWindowTitle("Please wait")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        # The layout (SetMinimumSize) drives the height so the multi-line message +
        # detail + cancel button are never clipped, regardless of font/DPI. To also pin
        # the WIDTH (which SetMinimumSize would otherwise shrink to content), we cap the
        # max width and give the bar a min-width strut so the layout minimum == target.
        _WIDTH = 560
        self.setMaximumWidth(_WIDTH)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self._cancelled = False
        self._shown     = False
        self._base_msg  = message

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(24, 20, 24, 20)
        lyt.setSpacing(12)
        lyt.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        # Main message: explicit \n line breaks (no word-wrap → correct multi-line sizeHint).
        self._lbl = QLabel(message)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        lyt.addWidget(self._lbl)
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)            # indeterminate / pulsing (until set_progress)
        self._bar.setTextVisible(False)
        self._bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bar.setFixedHeight(22)             # tall enough to show the % text
        self._bar.setMinimumWidth(_WIDTH - 48)   # strut: forces dialog to the full width
        lyt.addWidget(self._bar)
        # Secondary line: current file being read (elided to one line if very long)
        self._detail = QLabel("")
        self._detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail.setStyleSheet("color: #777; font-size: 10px;")
        self._detail.setMinimumHeight(16)
        lyt.addWidget(self._detail)

        self._cancel_btn: QPushButton | None = None
        if cancelable:
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            self._cancel_btn = QPushButton("Cancel")
            self._cancel_btn.setFixedWidth(110)
            self._cancel_btn.clicked.connect(self._on_cancel)
            btn_row.addWidget(self._cancel_btn)
            btn_row.addStretch()
            lyt.addLayout(btn_row)

    def _on_cancel(self):
        if self._cancel_btn:
            self._cancel_btn.setEnabled(False)
            self._cancel_btn.setText("Cancelling…")
        self.cancel_requested.emit()

    def reject(self):
        """ESC: on a cancelable dialog this is a REAL abort request (same as the
        Cancel button) instead of just hiding the window while the work keeps
        running; non-cancelable dialogs keep Qt's hide behavior."""
        if self._cancel_btn is not None:
            self._on_cancel()
            return
        super().reject()

    def set_message(self, msg: str):
        self._base_msg = msg
        self._lbl.setText(msg)

    def set_progress(self, done: int, total: int, detail: str = "", eta_seconds: float = -1.0):
        """Switch the bar to determinate and show 'done/total', a live ETA + current file."""
        if total > 0:
            if self._bar.maximum() != total:
                self._bar.setRange(0, total)
            self._bar.setValue(done)
            self._bar.setTextVisible(True)
            remaining = total - done
            line = i18n.t("%s / %s  (%s left)") % (f"{done:,}", f"{total:,}", f"{remaining:,}")
            if eta_seconds is not None and eta_seconds >= 0:
                line += "\n" + i18n.t("~%s remaining") % _fmt_duration(eta_seconds)
            self._lbl.setText(f"{i18n.t(self._base_msg)}\n{line}")
        else:
            # total unknown yet (listing phase) → keep pulsing
            self._bar.setRange(0, 0)
            self._lbl.setText(f"{i18n.t(self._base_msg)}\n" + i18n.t("Listing files…"))
        # Elide a long file name to a single line so the dialog height stays stable.
        avail = max(60, self._detail.width() or (self.width() - 48))
        fm = self._detail.fontMetrics()
        self._detail.setText(fm.elidedText(detail, Qt.TextElideMode.ElideMiddle, avail))

    def show_after(self, ms: int = 500):
        QTimer.singleShot(ms, self._maybe_show)

    def _maybe_show(self):
        if self._cancelled:
            return
        self.adjustSize()   # never shown yet = Qt's default size, not the layout's
        self._center()
        self.show()
        self._shown = True

    def _center(self):
        par = self.parent()
        if isinstance(par, QWidget) and par.isVisible():
            geo = par.window().geometry()
        else:
            geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.center().x() - self.width() // 2,
                  geo.center().y() - self.height() // 2)

    def finish(self):
        self._cancelled = True
        if self._shown:
            self.accept()
            self._shown = False

    def closeEvent(self, event):
        event.ignore()           # not manually closable; closed via finish()


# ─────────────────────────────────────────────────────────────────────────────
# Palette colours (referenced throughout)
# ─────────────────────────────────────────────────────────────────────────────
_C_ROUND_BG  = QColor(200, 210, 240)   # soft blue-gray header
_C_ROUND_FG  = QColor(30,  50, 120)   # dark navy text
_C_DANCE_BG  = QColor(210, 235, 210)  # soft green header
_C_DANCE_FG  = QColor(30,  90,  30)   # dark green text
_C_ROW_EVEN  = QColor(255, 255, 255)  # white
_C_ROW_ODD   = QColor(245, 247, 252)  # very light blue-gray
_C_POP_FG    = QColor(180, 110,   0)  # dark amber (visible on white)
_C_NEW_FG    = QColor( 30, 110, 200)  # medium blue
_C_SIM_FG    = QColor( 20, 130,  50)  # dark green
_C_WARN_FG   = QColor(200,  30,  30)  # red
_C_LEN_WARN_FG = QColor(215, 120,   0)  # orange — ⏱ length needs a second look
_C_DEFAULT   = QColor( 30,  30,  30)  # near-black


# Columns a KIND of list starts without (header right-click ticks them back on,
# and that choice is then saved). Heat only ever reads "Heat 2" on a deck whose
# dance runs several heats; a wishlist and a party list are flat, so it is 56 px
# of blank there. ★ Rating and Custom start put away in every kind: Marcel
# asked for them hidden until wanted.
DEFAULT_HIDDEN_COLUMNS = {
    "playlist": [_COL_RATING, _COL_CUSTOM],
    "wishlist": [_COL_HEAT, _COL_RATING, _COL_CUSTOM],
    "party": [_COL_HEAT, _COL_RATING, _COL_CUSTOM],
}

# The Custom column's header, in the decks and the library alike.
CUSTOM_HEADER_TIP = ("Custom — a free field per track, typed in the 🏷 editor.\n"
                     "Right-click the header to fill it from an MP3 tag.")


def add_custom_mapping_action(menu, widget) -> None:
    """The header menu's "Map Custom to an MP3 tag…"; the window owns the
    mapping (MusicCheckMixin._map_custom_field)."""
    win = widget.window()
    if not hasattr(win, "_map_custom_field"):
        return
    menu.addSeparator()
    menu.addAction("Map Custom to an MP3 tag…").triggered.connect(
        lambda: win._map_custom_field())

def _fmt_track_secs(secs: int) -> str:
    """Track/total length as m:ss (or h:mm:ss for round totals over an hour)."""
    secs = int(secs)
    if secs >= 3600:
        return f"{secs // 3600}:{secs % 3600 // 60:02d}:{secs % 60:02d}"
    return f"{secs // 60}:{secs % 60:02d}"


def _entry_tooltip(e, sim=None, sim_label: str = "Match", tags=None) -> str:
    """Rich hover description of a track (metadata + where it's used).

    Shared by the Similar-Tracks window. `tags` (sound tags) are
    optional — the similar window passes None.
    """
    esc = lambda s: html.escape(str(s))
    rows = [f"<b>{esc(e.title)}</b>"]
    if getattr(e, "tag_artist", None):
        rows.append(f"<i>{esc(e.tag_artist)}</i>")
    if getattr(e, "tag_album", None):
        rows.append(f"<span style='color:#aaa'>💿 {esc(e.tag_album)}</span>")
    meta = []
    dance = dance_name(warmup_code(e), e.dance or getattr(e, "other_genre", None) or "")
    if dance:
        meta.append(esc(dance))
    if e.bpm is not None:
        meta.append(f"T{e.bpm}")
    if getattr(e, "year", None):
        meta.append(str(e.year))
    if getattr(e, "is_instrumental", False):
        meta.append(i18n.t("instrumental"))
    elif entry_is_instrumental(e):
        meta.append(i18n.t("instrumental (🎙️ Demucs-measured)")
                    if getattr(e, "vocal_share", None) is not None
                    else i18n.t("instrumental (🎙️ audio-detected)"))
    if getattr(e, "is_xmas", False):
        meta.append(i18n.t("🎄 Christmas"))
    if meta:
        rows.append(" · ".join(meta))
    if tags:
        rows.append("🎧 <b>" + esc(" · ".join(tags)) + "</b>")
    if sim is not None:
        rows.append(f"{esc(i18n.t(sim_label))}: <b>{sim * 100:.1f}%</b>")
    if getattr(e, "classes_ok", None):
        rows.append(i18n.t("Classes: %s") % esc(", ".join(e.classes_ok)))
    if getattr(e, "comment_tags", None):
        rows.append("🏷️ " + esc(", ".join(e.comment_tags)))
    replay_sources = getattr(e, "replay_sources", None)
    if replay_sources:
        rows.append(i18n.t("In these matching past lists:"))
        for src in replay_sources[:8]:
            rows.append(f"<span style='color:#9c9'>• {esc(src)}</span>")
        if len(replay_sources) > 8:
            rows.append("<span style='color:#888'>%s</span>"
                        % (i18n.t("… +%d more") % (len(replay_sources) - 8)))
    elif getattr(e, "popularity", 0):
        rows.append(i18n.t("In %d of your playlists") % e.popularity)
        class_plays = getattr(e, "class_plays", None)
        if class_plays:
            by_cls = " · ".join(f"{c}×{n}" for c, n in
                                sorted(class_plays.items(), key=lambda kv: -kv[1]))
            rows.append("<span style='color:#888'>%s</span>"
                        % (i18n.t("Played in: %s") % esc(by_cls)))
        if getattr(e, "source_info", ""):
            rows.append(f"<span style='color:#888'>{esc(e.source_info)}</span>")
    rows.append(f"<span style='color:#888; font-size:10px'>{esc(e.path)}</span>")
    return "<div>" + "<br>".join(rows) + "</div>"


def _open_in_default_player(path: Path, parent: QWidget | None = None) -> None:
    """Open a file in the OS default application (music player on Windows)."""
    if path.suffix.lower() not in _AUDIO_EXTS:
        log.warning("🚫 Refused to open a non-audio file\n"
                    "path: %s\n"
                    "suffix: %s", path, path.suffix)
        QMessageBox.warning(parent, "Open file",
                            i18n.t("This is not an audio file, so it won't be opened:\n%s") % path)
        return
    if not path.exists():
        QMessageBox.warning(parent, "Open file",
                            i18n.t("File not found:\n%s") % path)
        return
    try:
        if sys.platform == "win32":
            os.startfile(str(path))                      # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as ex:
        QMessageBox.warning(parent, "Open file",
                            i18n.t("Couldn't open the file:\n%s") % ex)


def _open_folder(path, parent: QWidget | None = None) -> None:
    """Open a directory in the OS file manager (Explorer / Finder / xdg)."""
    path = Path(path)
    if not path.exists():
        QMessageBox.warning(parent, "Open folder", i18n.t("Folder not found:\n%s") % path)
        return
    try:
        if sys.platform == "win32":
            os.startfile(str(path))                      # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as ex:
        QMessageBox.warning(parent, "Open folder",
                            i18n.t("Couldn't open the folder:\n%s") % ex)


def _select_in_explorer_shell(path: Path) -> bool:
    """Windows: highlight `path` in Explorer through the shell's own API.

    Worth the ctypes because `explorer.exe /select` is only a REQUEST to the
    shell, and the shell drops it whenever a window for that folder is already
    open: it raises that window and leaves the selection where it was. So every
    reveal after the first one lands on the folder with nothing picked out —
    which in a folder of a few hundred tracks is no help at all.
    SHOpenFolderAndSelectItems does the selecting itself, open window or not.

    Returns False if the call didn't go through, so the caller can fall back."""
    import ctypes
    from ctypes import wintypes
    try:
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
        # The default restype is int, which on 64-bit truncates the returned
        # ID-list POINTER into an invalid one — hence the explicit signatures.
        shell32.ILCreateFromPathW.argtypes = [wintypes.LPCWSTR]
        shell32.ILCreateFromPathW.restype = ctypes.c_void_p
        shell32.ILFree.argtypes = [ctypes.c_void_p]
        shell32.ILFree.restype = None
        shell32.SHOpenFolderAndSelectItems.argtypes = [
            ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, wintypes.DWORD]
        shell32.SHOpenFolderAndSelectItems.restype = ctypes.HRESULT
        # Qt has already put this thread into an apartment, so CoInitialize
        # answers S_FALSE (fine — we hold a reference) or, if Qt chose the other
        # threading model, RPC_E_CHANGED_MODE: negative, and NO reference taken,
        # so uninitialising on the way out would decrement somebody else's.
        hr = ole32.CoInitialize(None)
        try:
            pidl = shell32.ILCreateFromPathW(str(path))
            if not pidl:
                return False
            try:
                shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
            finally:
                shell32.ILFree(pidl)
            return True
        finally:
            if hr >= 0:
                ole32.CoUninitialize()
    except Exception as ex:
        log.debug("📂 Shell reveal unavailable — falling back to explorer.exe\n"
                  "path: %s\n"
                  "error: %s", path, ex)
        return False


def reveal_in_explorer(path, parent: QWidget | None = None) -> None:
    """Open the OS file manager with the file selected/highlighted (focused).
    Windows: the shell API, falling back to explorer /select; macOS: open -R;
    Linux: open the parent dir."""
    path = Path(path)
    if not path.exists():
        QMessageBox.warning(parent, "Show in Explorer",
                            i18n.t("File not found:\n%s") % path)
        return
    try:
        if sys.platform == "win32":
            if _select_in_explorer_shell(path):
                return
            # /select needs a single, comma-separated, backslash native path —
            # and explorer.exe parses its own command line, so the quotes have
            # to sit around the PATH alone. Handing Popen a list quotes the
            # whole argument ("/select,F:\my music\…") as soon as the path
            # holds a space, which explorer reads as one folder name, fails to
            # find, and answers by opening Documents. Hence the raw string.
            subprocess.Popen(f'explorer /select,"{os.path.normpath(str(path))}"')
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])
    except Exception as ex:
        QMessageBox.warning(parent, "Show in Explorer",
                            i18n.t("Couldn't reveal the file:\n%s") % ex)


class CenteredIconHeader(QHeaderView):
    """Header view that centres a section's ICON, not just its text.

    Qt hands the style `iconAlignment = AlignVCenter`, i.e. no horizontal flag,
    so a header item's icon is always drawn hard against the left edge — off to
    one side of the centred values beneath it.
    """

    def initStyleOptionForIndex(self, option, logical_index):
        super().initStyleOptionForIndex(option, logical_index)
        option.iconAlignment = (Qt.AlignmentFlag.AlignCenter
                                if not option.text else Qt.AlignmentFlag.AlignVCenter)


def stopwatch_header(table, col: int, px: int = 6):
    """Swap a result table's ⏱ column caption for the painted stopwatch.

    Every table in the app has the same play-length column, so they all go
    through here and end up with the same glyph, centred over the times below.
    Drawn small: the stopwatch's crown and stem make it read much taller than a
    letter at the same size.
    """
    hh = CenteredIconHeader(Qt.Orientation.Horizontal, table)
    # A hand-built QHeaderView starts with clicking and section highlighting
    # off — QTableWidget's own header turns them on, so restore both.
    hh.setSectionsClickable(True)
    hh.setHighlightSections(True)
    table.setHorizontalHeader(hh)
    item = table.horizontalHeaderItem(col)
    if item is not None:
        item.setText("")
        item.setIcon(icon("stopwatch", px, INK))
    return hh


def _unreadable_playlist(anchor: QWidget, m3u, exc) -> None:
    """A dropped playlist whose text could not be decoded without losing
    characters: it counts as empty, and the window says so instead of
    silently showing nothing from it."""
    log.warning("⚠️ Playlist not read\n"
                "file: %s\n"
                "reason: %s", m3u, exc)
    _show_toast(anchor, i18n.t("⚠️  Not read — %s") % exc, 6000)


class _DragTable(QTableWidget):
    """Minimal QTableWidget that drags the file paths of selected rows.

    `paths` is row-aligned; entries that are None (e.g. AI suggestions not in
    the library) are simply skipped when building the drag payload.
    Right-click a row to copy its file path to the clipboard.
    """

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self._paths = paths
        self._seek_cb = None         # fn(delta_ms): seek the shared player
        self._play_toggle_cb = None  # fn(row): play/stop the given row

    def keyPressEvent(self, event):
        """Space: play/stop the current row.  Ctrl+←/→: seek ∓30 s.
        (Ctrl+arrows are intercepted here so the table's default column
        navigation doesn't swallow them.)"""
        key  = event.key()
        mods = event.modifiers()
        if (key in (Qt.Key.Key_Left, Qt.Key.Key_Right)
                and (mods & Qt.KeyboardModifier.ControlModifier)
                and self._seek_cb):
            self._seek_cb(-30000 if key == Qt.Key.Key_Left else 30000)
            event.accept()
            return
        if (key == Qt.Key.Key_Space and mods == Qt.KeyboardModifier.NoModifier
                and self._play_toggle_cb):
            r = self.currentRow()
            if r >= 0:
                self._play_toggle_cb(r)
                event.accept()
                return
        super().keyPressEvent(event)

    def startDrag(self, _actions):
        rows = sorted({idx.row() for idx in self.selectedIndexes()})
        urls = [QUrl.fromLocalFile(str(self._paths[r])) for r in rows
                if 0 <= r < len(self._paths) and self._paths[r]]
        if not urls:
            return
        mime = QMimeData()
        mime.setUrls(urls)
        mime.setText("\n".join(u.toLocalFile() for u in urls))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
                  | Qt.DropAction.LinkAction, Qt.DropAction.CopyAction)

    def contextMenuEvent(self, event):
        row = self.rowAt(event.pos().y())
        path = (self._paths[row]
                if 0 <= row < len(self._paths) and self._paths[row] else None)
        # The full hover tooltip is stored on the row's items — recover it (as plain
        # text) so its content can be copied; tooltips themselves can't be selected.
        it = self.item(row, 3) if row >= 0 else None
        details = (QTextDocumentFragment.fromHtml(it.toolTip()).toPlainText()
                   if it is not None and it.toolTip() else "")
        menu = QMenu(self)
        copy_act = menu.addAction("📋  Copy file path")
        if path is None:
            copy_act.setEnabled(False)
            copy_act.setText("📋  Copy file path (not in your library)")
        details_act = menu.addAction("📝  Copy details")
        details_act.setEnabled(bool(details))
        chosen = menu.exec(event.globalPos())
        if chosen is copy_act and path is not None:
            QApplication.clipboard().setText(str(path))
            _show_toast(self, "📋  Path copied to clipboard")
        elif chosen is details_act and details:
            QApplication.clipboard().setText(details)
            _show_toast(self, "📝  Details copied to clipboard")


# ─────────────────────────────────────────────────────────────────────────────
# Drop zone + background workers for "similar from file" and AI suggestions
# ─────────────────────────────────────────────────────────────────────────────


class DropZone(QFrame):
    """A drop target: drop a single audio file to find similar library tracks."""
    fileDropped = Signal(str)

    def __init__(self, parent=None,
                 text="🎵  Drop a music file here, or click to browse,\nto find similar tracks"):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Drop an audio file here, or click to browse")
        self._base = ("#DropZone { border:2px dashed #9aa6c0; border-radius:6px;"
                      " background:#f3f6fc; }")
        self._hot  = ("#DropZone { border:2px dashed #4a82d2; border-radius:6px;"
                      " background:#e3ecfb; }")
        self.setStyleSheet(self._base)
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(6, 4, 6, 4)
        self._lbl = QLabel(text)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet("color:#556; font-size:11px; border:0; background:transparent;")
        lyt.addWidget(self._lbl)

    @staticmethod
    def _is_audio(url) -> bool:
        return url.isLocalFile() and url.toLocalFile().lower().endswith(_AUDIO_EXTS)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(self._is_audio(u) for u in e.mimeData().urls()):
            e.acceptProposedAction()
            self.setStyleSheet(self._hot)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.setStyleSheet(self._base)

    def dropEvent(self, e):
        self.setStyleSheet(self._base)
        for u in e.mimeData().urls():
            if self._is_audio(u):
                e.acceptProposedAction()
                self.fileDropped.emit(u.toLocalFile())
                return
        e.ignore()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()
        super().mousePressEvent(e)

    def _browse(self):
        exts = " ".join(f"*{x}" for x in _AUDIO_EXTS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a music file", music_browse_dir(),
            f"Audio files ({exts});;All files (*)",
        )
        if path:
            remember_browse_dir(path)
            self.fileDropped.emit(path)


class _PathListWidget(QListWidget):
    """A list whose items can be dragged OUT as file URLs (the full path is held in
    each item's tooltip), so a dropped title can be dragged on into another zone — e.g.
    promoting one of the listed playlists into the reference-base field. Dragging an
    item out removes it from this list (move), reported via `draggedOut`."""
    draggedOut = Signal(list)   # full paths of the items dragged out

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def startDrag(self, supportedActions):
        paths = [it.toolTip() for it in self.selectedItems() if it.toolTip()]
        if not paths:
            return
        md = QMimeData()
        md.setUrls([QUrl.fromLocalFile(p) for p in paths])
        drag = QDrag(self)
        drag.setMimeData(md)
        drag.exec(Qt.DropAction.MoveAction)
        # Dragging a title out of the list removes it from here (move semantics).
        self.draggedOut.emit(paths)


class _DroppedFilesList(QWidget):
    """A visible list of the files added so far, with ➕ Add… / ➖ Remove selected /
    🗑 Clear controls. Lets the user review what was dropped and curate it (add from
    other folders, drop the wrong ones) before running. Emits `changed` on every edit."""
    changed = Signal()

    def __init__(self, parent=None, clear_hook=None):
        super().__init__(parent)
        self._paths: list[str] = []
        self._clear_hook = clear_hook   # extra reset run by 🗑 Clear (e.g. wipe the ref)
        # Accept drops on the whole widget; the inner list keeps external drops
        # disabled (DragOnly) so the events fall through to here.
        self.setAcceptDrops(True)
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)
        self._list = _PathListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.setMaximumHeight(90)
        self._list.setToolTip("Drag .m3u playlists or audio files here; "
                              "drag a title out (e.g. to the reference field) to remove it")
        self._list.draggedOut.connect(self._remove_paths)
        lyt.addWidget(self._list)
        bar = QHBoxLayout()
        add = QPushButton("➕  Add files…")
        add.clicked.connect(self._browse)
        rem = QPushButton("➖  Remove selected")
        rem.clicked.connect(self._remove_selected)
        clr = QPushButton("🗑  Clear")
        clr.clicked.connect(self.clear)
        bar.addWidget(add)
        bar.addWidget(rem)
        bar.addStretch(1)
        bar.addWidget(clr)
        lyt.addLayout(bar)

    def paths(self) -> list[str]:
        return list(self._paths)

    def add_paths(self, paths: list):
        have = set(self._paths)
        added = False
        for p in paths:
            p = str(p)
            if p not in have:
                self._paths.append(p)
                have.add(p)
                added = True
        if added:
            self._rebuild()
            self.changed.emit()

    def clear(self):
        had = bool(self._paths)
        if had:
            self._paths = []
            self._rebuild()
        # Run the extra reset even when the list was already empty (so 🗑 Clear still
        # wipes a set reference base), then signal the change once.
        if self._clear_hook is not None:
            self._clear_hook()
        if had:
            self.changed.emit()

    def _remove_paths(self, paths: list):
        drop = set(paths)
        kept = [p for p in self._paths if p not in drop]
        if len(kept) != len(self._paths):
            self._paths = kept
            self._rebuild()
            self.changed.emit()

    def _remove_selected(self):
        rows = sorted((self._list.row(i) for i in self._list.selectedItems()),
                      reverse=True)
        if not rows:
            return
        for r in rows:
            del self._paths[r]
        self._rebuild()
        self.changed.emit()

    def _rebuild(self):
        self._list.clear()
        for p in self._paths:
            it = QListWidgetItem(f"  {Path(p).name}")
            it.setToolTip(str(p))
            self._list.addItem(it)

    def _browse(self):
        audio = " ".join(f"*{x}" for x in _AUDIO_EXTS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add playlists or music files", music_browse_dir(),
            f"Playlists & audio (*.m3u *.m3u8 {audio});;All files (*)")
        if paths:
            remember_browse_dir(paths[0])
            self.add_paths(paths)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(
                _MultiFileDropZone._is_droppable(u) for u in e.mimeData().urls()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls()
                 if _MultiFileDropZone._is_droppable(u)]
        if files:
            e.acceptProposedAction()
            self.add_paths(files)
        else:
            e.ignore()


class _MultiFileDropZone(QFrame):
    """A drop target that accepts SEVERAL files at once — .m3u/.m3u8 playlists and/or
    plain audio files (and click-to-browse, multi-select). Emits the dropped local
    file paths as a list."""
    filesDropped = Signal(list)
    _DROP_EXTS = ('.m3u', '.m3u8') + _AUDIO_EXTS

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Drop .m3u playlists or audio files here, or click to browse")
        self._base = ("#DropZone { border:2px dashed #9aa6c0; border-radius:6px;"
                      " background:#f3f6fc; }")
        self._hot  = ("#DropZone { border:2px dashed #4a82d2; border-radius:6px;"
                      " background:#e3ecfb; }")
        self.setStyleSheet(self._base)
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(6, 6, 6, 6)
        lbl = QLabel("📂  Drop .m3u playlists (or audio files) here, or click to browse")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#556; font-size:11px; border:0; background:transparent;")
        lyt.addWidget(lbl)

    @classmethod
    def _is_droppable(cls, url) -> bool:
        return url.isLocalFile() and url.toLocalFile().lower().endswith(cls._DROP_EXTS)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(self._is_droppable(u) for u in e.mimeData().urls()):
            e.acceptProposedAction()
            self.setStyleSheet(self._hot)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.setStyleSheet(self._base)

    def dropEvent(self, e):
        self.setStyleSheet(self._base)
        files = [u.toLocalFile() for u in e.mimeData().urls() if self._is_droppable(u)]
        if files:
            e.acceptProposedAction()
            self.filesDropped.emit(files)
        else:
            e.ignore()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            audio = " ".join(f"*{x}" for x in _AUDIO_EXTS)
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select playlists or music files", music_browse_dir(),
                f"Playlists & audio (*.m3u *.m3u8 {audio});;All files (*)",
            )
            if paths:
                remember_browse_dir(paths[0])
                self.filesDropped.emit(paths)
        super().mousePressEvent(e)


