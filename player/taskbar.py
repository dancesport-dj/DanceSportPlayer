"""🪟 The taskbar mini player — VLC's trick, on our taskbar button.

Hovering the taskbar icon pops the window's live thumbnail with ⏮ ⏯ ⏭ under
it, so the desk can skip a title without ever raising the window.

Only the thumb toolbar: the icon overlay badge and the progress fill were
dropped on purpose. They rode the playback tick — a shell round trip every
100 ms for decoration — and the toolbar is the part that does the work.

The shell talking is all in player.taskbar_win32; this file owns what the buttons
ARE and what a click means, and does nothing at all off Windows.
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal
from PySide6.QtGui import QGuiApplication, QImage, Qt
from PySide6.QtWidgets import QApplication

from player import sf_icons as sf

# Thumb button ids. They travel to the shell and come back in a WM_COMMAND, so
# they only have to be stable within one run — but 0 is not usable as an id.
ID_PREV = 1
ID_PLAY = 2
ID_NEXT = 3

_WM_COMMAND = 0x0111
_THBN_CLICKED = 0x1800


def decode_click(msg_id: int, wparam: int) -> int | None:
    """The thumb button behind a native message, or None if it is not one.

    A thumb button click arrives as an ordinary WM_COMMAND whose high word is
    THBN_CLICKED and whose low word is the id we registered — the same wParam
    layout a menu or an accelerator uses, which is exactly why the high word
    has to be checked before the low word is believed."""
    if msg_id != _WM_COMMAND or (wparam >> 16) & 0xFFFF != _THBN_CLICKED:
        return None
    ident = wparam & 0xFFFF
    return ident if ident in (ID_PREV, ID_PLAY, ID_NEXT) else None


def glyph_color() -> str:
    """Icons follow the SYSTEM theme, not the app's: they are painted onto the
    shell's thumbnail toolbar, which is the one surface we do not own."""
    hints = QGuiApplication.styleHints()
    scheme = getattr(hints, "colorScheme", None)
    dark = scheme is not None and scheme() == Qt.ColorScheme.Dark
    return "#f2f2f2" if dark else "#1c1c1e"


def load_win32():
    """The Win32 adapter, or None where there is no taskbar to talk to.

    A function rather than a module-level import so the tests can put a
    recording stub in its place and drive the whole class headlessly."""
    if sys.platform != "win32":
        return None
    try:
        from player import taskbar_win32
    except (ImportError, OSError, AttributeError):   # pragma: no cover
        return None
    return taskbar_win32


class TaskbarPlayer(QObject, QAbstractNativeEventFilter):
    """⏮ ⏯ ⏭ under one window's taskbar thumbnail."""

    prevClicked = Signal()
    playPauseClicked = Signal()
    nextClicked = Signal()

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._w32 = load_win32()
        self._tb: int | None = None
        self._hwnd: int | None = None
        self._created_msg: int | None = None
        self._added = False
        self._playing = False
        self._title = ""
        self._icons: dict[str, int] = {}

    # ── setting up ──────────────────────────────────────────────────────
    def attach(self, window) -> bool:
        """Watch `window`'s taskbar button. False where there is none.

        The buttons cannot go on yet: ThumbBarAddButtons only works once the
        shell HAS made a taskbar button, and it announces that with a
        registered message we have to sit and wait for."""
        if self._w32 is None:
            return False
        self._hwnd = int(window.winId())
        self._created_msg = self._w32.button_created_message()
        app = QApplication.instance()
        if app is None:
            return False
        app.installNativeEventFilter(self)
        return True

    def _icon(self, name: str) -> int | None:
        """A cached HICON for one glyph.

        Cached because the shell keeps the handle rather than the pixels: an
        icon destroyed after handing it over leaves the button blank, so every
        one we ever make is held until teardown."""
        if name in self._icons:
            return self._icons[name]
        px = self._w32.small_icon_px()
        painter = {"prev": sf.backward, "next": sf.forward,
                   "play": sf.play, "pause": sf.pause}[name]
        # Premultiplied BGRA is exactly what a 32-bit DIB section holds, so the
        # converted image can be memmove'd across whole.
        img = painter(px, glyph_color()).toImage().convertToFormat(
            QImage.Format.Format_ARGB32_Premultiplied)
        icon = self._w32.hicon_from_argb(bytes(img.constBits()),
                                         img.width(), img.height())
        if icon is not None:
            self._icons[name] = icon
        return icon

    def _buttons(self):
        """⏮ ⏯ ⏭, with the middle one showing what pressing it would DO."""
        middle = "pause" if self._playing else "play"
        tip = "Pause" if self._playing else "Play"
        return [(ID_PREV, self._icon("prev"), "Previous title", True),
                (ID_PLAY, self._icon(middle), tip, True),
                (ID_NEXT, self._icon("next"), "Next title", True)]

    def _on_button_created(self) -> None:
        """The shell has a taskbar button for OUR window — install the toolbar.

        Only ever for this hwnd: adding the buttons to a window the taskbar
        does not know yet is accepted with S_OK and then quietly thrown away,
        which burns the one attempt the shell allows.

        A second one for this hwnd means the shell came back without them —
        Explorer restarted — so they go on again, through a fresh interface:
        the old one belongs to the Explorer that died. A shell that refuses
        that repeat still has our toolbar, and it is kept."""
        again = self._added
        if again and self._tb is not None:
            self._w32.release(self._tb)
            self._tb = None
        if self._tb is None:
            self._tb = self._w32.create()
        if self._tb is None:
            self._added = False
            return
        hr = self._w32.add_buttons(self._tb, self._hwnd, self._buttons())
        self._added = hr >= 0 or again
        if self._added and self._title:
            self._w32.set_thumbnail_tooltip(self._tb, self._hwnd, self._title)
        logging.info("🪟 Taskbar thumb toolbar\n"
                     "hwnd: %#x\n"
                     "hresult: %#010x\n"
                     "icons: %s",
                     self._hwnd or 0, hr & 0xFFFFFFFF, self._icons)

    # ── state coming in from the player ─────────────────────────────────
    def set_playing(self, playing: bool) -> None:
        """▶/⏸ on the middle button. Called on state changes only — never on
        the position tick, which is what keeps this free."""
        if bool(playing) == self._playing:
            return
        self._playing = bool(playing)
        if self._added:
            self._w32.update_buttons(self._tb, self._hwnd, self._buttons())

    def set_title(self, title: str) -> None:
        """The running title, as the caption over the hover thumbnail — the
        thumbnail itself is only a small picture of the window, and at that
        size the player card's own text is not readable.

        Once per song, so it costs nothing on the tick. An empty title hands
        the caption back to the window title."""
        title = (title or "").strip()
        if title == self._title:
            return
        self._title = title
        if self._added:
            hr = self._w32.set_thumbnail_tooltip(self._tb, self._hwnd, title)
            # Logged with its HRESULT: this caption is now the ONLY place the
            # title shows up there, and a shell that refused it has to be
            # tellable from a title that was never sent.
            logging.info("🪟 Taskbar thumbnail caption\n"
                         "title: %s\n"
                         "hresult: %#010x", title or "(window title)",
                         (hr or 0) & 0xFFFFFFFF)

    # ── clicks coming back from the shell ───────────────────────────────
    def nativeEventFilter(self, event_type, message):
        if self._w32 is None or event_type != b"windows_generic_MSG":
            return False, 0
        fields = self._w32.msg_fields(message)
        if fields is None:
            return False, 0
        hwnd, msg_id, wparam = fields
        if hwnd != self._hwnd:
            # Another of the app's windows — the loading dialog owns the first
            # taskbar button of the run, and acting on ITS message would spend
            # our one add on a main window that has no button yet.
            return False, 0
        if msg_id == self._created_msg:
            self._on_button_created()
            return False, 0
        ident = decode_click(msg_id, wparam)
        if ident is None:
            return False, 0
        {ID_PREV: self.prevClicked,
         ID_PLAY: self.playPauseClicked,
         ID_NEXT: self.nextClicked}[ident].emit()
        return True, 0

    # ── giving it all back ──────────────────────────────────────────────
    def shutdown(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeNativeEventFilter(self)
        if self._w32 is None:
            return
        for icon in self._icons.values():
            self._w32.destroy_icon(icon)
        self._icons.clear()
        if self._tb is not None:
            self._w32.release(self._tb)
            self._tb = None
        self._added = False
