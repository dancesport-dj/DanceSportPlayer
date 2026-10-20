"""🎛 Cartwall: a wall of sample pads that play ON TOP of the deck music.

Two pieces live here:
  • _CartPadButton – one pad: drop a file on it, tap it, right-click to set it up
  • CartwallWidget – the page: grid + page nav + ✏ edit lock + ⏹ Stop all

Every Qt event handler lives in these widget classes and never in the
MainWindow mixin: QMainWindow comes first in MainWindow's bases, so a mixin's
dropEvent would be shadowed and silently never run.

The audio pool the pads sound on is player.audio.cart_voices, the shortcut
panel player.widgets.cart_keys, the pad and wall-fade dialogs (with the pad
colours) player.dialogs.cart_pad_dialog.
"""
import html
import logging
import os
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import (
    QMimeData, QPoint, QTimer, QUrl, Qt, Signal)
from PySide6.QtGui import (
    QColor, QDrag, QIcon, QKeySequence, QPainter, QPixmap, QShortcut)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog,
    QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
    QLayout, QLineEdit, QMenu, QMessageBox, QSizePolicy,
    QStyle, QStyleOption, QToolButton, QVBoxLayout, QWidget)

from shared.appearance import icons
from planner.playing import cartwall as pc
from planner import i18n
from shared.audio.audio_files import (_AUDIO_EXTS, music_browse_dir,
                                remember_browse_dir)
from shared.widgets import FlowLayout
from player.dialogs.cart_pad_dialog import (
    PAD_COLOURS, CartPadDialog, WallFadeDialog, _ClickableLabel,
)
from player.widgets.player_parts import _ClickSlider, _fmt_ms
from planner.music.parsing import _read_duration

log = logging.getLogger("dancesport.gui.cartwall")

_PAD_MIME = "application/x-dancesport-cartpad"

_IDLE_BG = "#eceff4"
_IDLE_BORDER = "#d4d9e0"
_LIGHT_BORDER = "#b9c0cc"    # a white pad needs a darker edge to exist at all
_PLAY_BG = "#bcd4f7"         # running: light blue, so the deep band reads on it
_PLAY_BORDER = "#7ba4e8"
_GONE_BG = "#dfe1e5"
_SEL_BORDER = "#3f4653"      # ✏ multi-select: an outline, never a fill
# ✏ edit mode. Amber, and not one of the pad colours: it frames the whole wall
# and has to read as "this is a mode", not as "somebody painted a pad".
_EDIT_ACCENT = "#c8871a"
# Deep blue, filling left to right over the light-blue running pad. Translucent
# on purpose: solid enough to read as the darker blue, open enough that the pad's
# own dark caption still survives on top of it.
_PLAYED_BAND = (45, 108, 223, 120)
_BLINK_MS = 160

_SWATCH = 14             # edge of the colour square in the 🎨 menus
_PAD_MIN_W = 44


def _luma(colour: str) -> float:
    """Rec. 709 luma 0–255, or -1 for anything unparseable."""
    if not (len(colour) == 7 and colour.startswith("#")):
        return -1.0
    try:
        r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        return -1.0
    # Weighted, not a plain average: a saturated green reads far brighter than a
    # blue with the same RGB sum, and averaging puts white text on olive.
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _text_on(colour: str) -> str:
    """Dark or light text — whichever the pad colour can actually carry."""
    return "#2b3038" if _luma(colour) > 145 else "#ffffff"


_DURATIONS: dict[str, int] = {}      # path → whole seconds, 0 = unknown


def _duration_text(path: str) -> str:
    """The sample's length, the way a PlayIt cart shows it while idle.

    Cached per path: the wall is rebuilt on every page turn and every reshape,
    and re-reading sixteen headers each time would be felt."""
    secs = _DURATIONS.get(path)
    if secs is None:
        secs = _read_duration(Path(path))
        if secs:
            # Only a real length is remembered: a 0 means the file was missing or
            # unreadable, and a stick that comes back must show its lengths again.
            _DURATIONS[path] = secs
    return _fmt_ms(secs * 1000) if secs > 0 else "--:--"


def _colour_icon(colour: str) -> QIcon:
    """A filled swatch for a colour menu. Reading nine colour NAMES to find the
    green one is slower than looking at nine squares."""
    pix = QPixmap(_SWATCH, _SWATCH)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(colour) if _luma(colour) >= 0 else QColor(_IDLE_BG))
    painter.setPen(QColor(_LIGHT_BORDER))
    painter.drawRoundedRect(1, 1, _SWATCH - 3, _SWATCH - 3, 3, 3)
    painter.end()
    return QIcon(pix)


# ─────────────────────────────────────────────────────────────────────────────
# One pad
# ─────────────────────────────────────────────────────────────────────────────
class _CartPadButton(QFrame):
    """A single pad. Empty it is a drop target; filled it is a button."""

    tapped = Signal(object)              # key
    assigned = Signal(object, list)      # key, [path, …] — a library multi-select
    dropped_pad = Signal(object, object)  # source cell, this key
    edit_requested = Signal(object)
    clear_requested = Signal(object)
    colour_requested = Signal(object, str)
    wall_colour_requested = Signal(str)  # the fallback colour of every pad
    wall_fade_requested = Signal()       # the fade-out every pad follows
    shortcuts_requested = Signal()       # the ⌨ Keys window, on the wall's tab
    selected_requested = Signal(object, bool)   # key, add to the selection

    def __init__(self, key, parent=None):
        super().__init__(parent)
        self._key = key                  # (page, row, col)
        self._pad: pc.CartPad | None = None
        self._playing = False
        self._missing = False
        self._press: QPoint | None = None
        self._frac = 0.0                 # how much of the sample has played
        self._shortcut = ""              # the key that fires it, shown on the face
        self._default_bg = _IDLE_BG
        self._editable = False           # ✏ off = a pad can only be FIRED
        self._selected = False           # part of a multi-pad edit
        self._sel_count = 0              # how many pads that edit would hit
        self._fading = False
        self._blink_on = False
        self._blink = QTimer(self)
        self._blink.setInterval(_BLINK_MS)
        self._blink.timeout.connect(self._flash)
        # Small enough that a whole 8-wide wall still fits a side dock the user
        # can narrow; the size policy is what makes pads big on a wide wall.
        self.setMinimumSize(_PAD_MIN_W, 46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(6, 4, 6, 4)
        lyt.setSpacing(0)
        self._title = QLabel("")
        self._title.setWordWrap(True)
        # Rich text for the 🅂 mark's own size; _restyle escapes the title.
        self._title.setTextFormat(Qt.TextFormat.RichText)
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter
                                 | Qt.AlignmentFlag.AlignTop)
        # Big and dead centre: the running time is what the operator reads from
        # two metres away with a microphone in the other hand.
        self._time = QLabel("")
        self._time.setObjectName("cartTime")
        self._time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._key_lbl = QLabel("")
        self._key_lbl.setObjectName("cartKey")     # styled separately: light grey
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft
                                   | Qt.AlignmentFlag.AlignBottom)
        # Ignored, not Preferred: otherwise the widest caption sets a floor under
        # the whole wall and a side dock can never be narrowed. Text clips instead.
        for label in (self._title, self._time, self._key_lbl):
            label.setSizePolicy(QSizePolicy.Policy.Ignored,
                                label.sizePolicy().verticalPolicy())
        # ✏ only: emptying a pad without going through the right-click menu.
        # Bottom right, because that corner is the one nothing else uses and it
        # is the furthest point from where a tap lands.
        self._del_btn = QToolButton(self)
        self._del_btn.setObjectName("cartDel")
        self._del_btn.setText("✕")
        self._del_btn.setToolTip("Clear this pad")
        self._del_btn.setAutoRaise(True)
        self._del_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._del_btn.setFixedSize(16, 16)
        self._del_btn.clicked.connect(
            lambda: self.clear_requested.emit(self._key))
        self._del_btn.hide()
        # Title on top, time filling the middle, slot key in the bottom corner.
        # The stretch goes to the TIME, so it stays centred as the pad grows.
        lyt.addWidget(self._title)
        lyt.addWidget(self._time, 1)
        foot = QHBoxLayout()
        foot.setContentsMargins(0, 0, 0, 0)
        foot.setSpacing(2)
        # Stretch on the LABEL, never a spacer: the key label is Ignored-policy
        # and a spacer beside one squeezes it to nothing.
        foot.addWidget(self._key_lbl, 1)
        foot.addWidget(self._del_btn, 0, Qt.AlignmentFlag.AlignBottom)
        lyt.addLayout(foot)
        self._restyle()

    def key(self):
        return self._key

    def pad(self) -> pc.CartPad | None:
        return self._pad

    def set_pad(self, pad: pc.CartPad | None, missing: bool = False) -> None:
        self._pad = pad
        self._missing = missing
        if pad is None:
            self._playing = False
            self.set_fading(False)
        self._restyle()

    def set_default_colour(self, colour: str) -> None:
        self._default_bg = colour or _IDLE_BG
        self._restyle()

    def set_shortcut(self, text: str) -> None:
        self._shortcut = text
        self._restyle()

    def set_editable(self, editable: bool) -> None:
        """✏ off is the tournament state: pads fire, and nothing else. No drops,
        no drags, no right-click, no browse dialog on an empty pad — a wall you
        can rearrange by accident with a running heat is a hazard."""
        self._editable = bool(editable)
        self.setAcceptDrops(self._editable)
        self._restyle()

    def set_selected(self, selected: bool, count: int = 0) -> None:
        """Part of a multi-pad edit — recolour six pads in one go instead of six
        right-clicks. `count` is only there so the menu can say how many."""
        selected = bool(selected)
        if (selected, count) == (self._selected, self._sel_count):
            return
        self._selected = selected
        self._sel_count = count
        self._restyle()

    def selected(self) -> bool:
        return self._selected

    def set_playing(self, playing: bool) -> None:
        if playing != self._playing:
            self._playing = playing
            if not playing:
                self._frac = 0.0
                self.set_fading(False)
                self._time.setText(
                    _duration_text(self._pad.path) if self._pad else "")
            self._restyle()

    def set_fading(self, fading: bool) -> None:
        """Blink while a pad fades out, so a 1 s tail is still visibly a pad
        on its way out rather than one that ignored the tap."""
        if fading == self._fading:
            return
        self._fading = fading
        self._blink_on = False
        if fading:
            self._blink.start()
        else:
            self._blink.stop()
        self._restyle()

    def _flash(self) -> None:
        self._blink_on = not self._blink_on
        self._restyle()

    def set_remaining(self, ms_left: int, frac: float) -> None:
        if self._pad is None:
            return
        self._frac = max(0.0, min(1.0, frac))
        if self._pad.loop:
            self._time.setText("∞")
        elif ms_left < 0:
            self._time.setText("--:--")
        else:
            self._time.setText(_fmt_ms(ms_left))
        self.update()      # repaint the progress band

    # ── looks ────────────────────────────────────────────────────────────────
    def _restyle(self) -> None:
        # There is nothing to clear on an empty pad, and nothing to clear at all
        # while the wall is locked.
        self._del_btn.setVisible(self._editable and self._pad is not None)
        if self._pad is None:
            self._title.setText("＋" if self._editable else "")
            self._time.setText("")
            self._key_lbl.setText("")
            self.setToolTip(
                "Drop one or more audio files here, or click to browse"
                if self._editable else "Empty — switch ✏ Edit on to fill it")
            self.setStyleSheet(
                "QFrame { border: 1px dashed #b9c0cc; border-radius: 6px;"
                " background: transparent; }"
                "QLabel { border: 0; color: #9aa3b2; background: transparent; }")
            return

        title = pc.pad_title(self._pad)
        marks = ""
        if self._pad.loop:
            marks += " 🔁"
        if self._pad.duck and not self._pad.background:
            # Not 🔈: Windows draws that as a pale grey emoji, lost on a
            # coloured pad. The arrow takes the pad's text colour, like ♫.
            marks += " ↓"
        if self._pad.background:
            # The plain note, not the purple 🎶 emoji: it takes the pad's text
            # colour and so reads on every pad colour.
            marks += " ♫"
        if self._pad.stops_others:
            # A boxed S, not ■ (reads as the pad's own stop button) and not a
            # bare S (reads as part of the title). At the title's 11 px the
            # box's S is too small to read; 16 px stood out, 14 px is the size
            # asked for.
            marks += " <span style='font-size:14px'>\U0001F142</span>"
        if self._pad.volume < 1.0:
            marks += f" {int(round(self._pad.volume * 100))}%"
        self._title.setText(("⚠ " if self._missing else "")
                            + html.escape(title, quote=False) + marks)
        if not self._playing:
            # Idle pads show how long the sample IS; a running one counts down.
            self._time.setText(_duration_text(self._pad.path))
        self._key_lbl.setText(self._shortcut)
        self.setToolTip(f"{title}\n{self._pad.path}"
                        + (i18n.t("\nKey: %s") % self._shortcut
                           if self._shortcut else "")
                        + (i18n.t("\n⚠️ File not found") if self._missing else ""))

        if self._missing:
            bg, border = _GONE_BG, "#c9ced6"
            fg = "#8a8f98"
        elif self._fading and self._blink_on:
            # Half of the blink shows the pad's own colour again, so the eye
            # reads "this one is letting go", not "this one changed".
            bg = self._pad.colour or self._default_bg
            border, fg = _LIGHT_BORDER, _text_on(bg)
        elif self._playing:
            # Light blue for "this one is up", so the deep-blue progress band
            # painted over it in paintEvent stays legible against it.
            bg, border = _PLAY_BG, _PLAY_BORDER
            fg = _text_on(_PLAY_BG)
        else:
            bg = self._pad.colour or self._default_bg
            border = _LIGHT_BORDER if _luma(bg) > 225 else _IDLE_BORDER
            fg = _text_on(bg)
        # The slot key is a hint, not information the operator reads mid-heat —
        # light grey, so it never competes with the title next to it.
        key_fg = "#8f96a3" if fg == "#2b3038" else "#dfe3ea"
        # A selected pad is outlined, never filled: a fill would collide with the
        # blues that mean "running", and with the pad's own colour.
        edge = f"2px solid {_SEL_BORDER}" if self._selected else f"1px solid {border}"
        self.setStyleSheet(
            f"QFrame {{ border: {edge}; border-radius: 6px;"
            f" background: {bg}; }}"
            f"QLabel {{ border: 0; background: transparent; color: {fg};"
            " font-size: 11px; }"
            f"QLabel#cartKey {{ color: {key_fg}; }}"
            "QLabel#cartTime { font-size: 17px; font-weight: 600; }"
            f"QToolButton#cartDel {{ border: 0; padding: 0; background:"
            f" transparent; color: {key_fg}; font-size: 11px; }}"
            f"QToolButton#cartDel:hover {{ color: {fg};"
            " background: rgba(0, 0, 0, 0.12); border-radius: 3px; }")

    def paintEvent(self, e):
        """Draw the stylesheet background first, then wash the played part of
        the sample over it left to right."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        if not self._playing or self._frac <= 0.0:
            return
        width = int(round(self.width() * self._frac))
        if width <= 0:
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(*_PLAYED_BAND))
        painter.drawRect(0, 0, width, self.height())

    # ── mouse ────────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.position().toPoint()
        elif e.button() == Qt.MouseButton.RightButton:
            self._context_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._press is None or self._pad is None or not self._editable:
            return
        moved = (e.position().toPoint() - self._press).manhattanLength()
        if moved < QApplication.startDragDistance():
            return
        self._press = None
        mime = QMimeData()
        mime.setData(_PAD_MIME, pc.cell_key(self._key[1:]).encode())
        mime.setUrls([QUrl.fromLocalFile(str(self._pad.path))])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        self._press = None
        if self._pad is None:
            if self._editable:
                self._browse()
        elif self._editable:
            # While ✏ is on a click SELECTS instead of firing: building a wall
            # must not set off every pad you touch. Ctrl or Shift adds to the
            # selection, so one right-click can then recolour all of them.
            self.selected_requested.emit(
                self._key,
                bool(e.modifiers() & (Qt.KeyboardModifier.ControlModifier
                                      | Qt.KeyboardModifier.ShiftModifier)))
        else:
            self.tapped.emit(self._key)

    def _context_menu(self, pos) -> None:
        if not self._editable:
            return
        if self._pad is not None and not self._selected:
            # Right-clicking outside the selection works on THAT pad, the way
            # every file manager behaves — the old selection is dropped.
            self.selected_requested.emit(self._key, False)
        menu = QMenu(self)
        # How many pads the actions below will hit, so nothing is recoloured by
        # surprise.
        many = (i18n.t("  (%s pads)") % self._sel_count
                if self._sel_count > 1 else "")
        if self._pad is None:
            menu.addAction("📂  Assign files…", self._browse)
        else:
            menu.addAction(i18n.t("⚙  Settings…") + many,
                           lambda: self.edit_requested.emit(self._key))
            # Colour straight from the right-click: recolouring a wall one pad at
            # a time through the settings dialog is four clicks per pad.
            colours = menu.addMenu(i18n.t("🎨  Colour") + many)
            for name, value in PAD_COLOURS.items():
                act = colours.addAction(
                    _colour_icon(value or self._default_bg), name,
                    lambda v=value: self.colour_requested.emit(self._key, v))
                act.setCheckable(True)
                act.setChecked(self._pad.colour == value)
            menu.addAction(i18n.t("🗑  Clear pad") + many,
                           lambda: self.clear_requested.emit(self._key))
        # The wall-wide fallback colour lives here too, rather than in a header
        # button of its own: it is the same decision as a pad colour, and the
        # swatches are already on screen.
        wall = menu.addMenu("🖌  Wall colour")
        # White is not offered per pad — it is what "Wall default" already means —
        # but it has to be here, or a wall painted green can never go back.
        for name, value in {"White": pc.DEFAULT_PAD_COLOUR,
                            **{n: v for n, v in PAD_COLOURS.items() if v}}.items():
            act = wall.addAction(
                _colour_icon(value), name,
                lambda v=value: self.wall_colour_requested.emit(v))
            act.setCheckable(True)
            act.setChecked(self._default_bg == value)
        menu.addAction("⏱  Wall fade-out…", self.wall_fade_requested.emit)
        menu.addAction("⌨  Shortcuts…", self.shortcuts_requested.emit)
        menu.exec(pos)

    def _browse(self) -> None:
        exts = " ".join(f"*{x}" for x in _AUDIO_EXTS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose samples — the first lands here, the rest fill up",
            music_browse_dir(), f"Audio files ({exts});;All files (*)")
        if paths:
            remember_browse_dir(paths[0])
            self.assigned.emit(self._key, [os.path.normpath(p) for p in paths])

    # ── drag & drop ──────────────────────────────────────────────────────────
    @staticmethod
    def _audio_urls(mime) -> list[str]:
        """Every audio file in the drop, in the order it was dragged — a library
        multi-select arrives as one drop and fills the free slots after this one."""
        out = []
        for url in mime.urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(_AUDIO_EXTS):
                # toLocalFile() hands back forward slashes even on Windows; the
                # stored path is shown in tooltips and compared with library
                # paths, so normalise it to what the rest of the app writes.
                out.append(os.path.normpath(url.toLocalFile()))
        return out

    def _welcomes(self, mime) -> bool:
        """setAcceptDrops(False) already turns real drags away while ✏ is off;
        this is the same rule where the handlers can be reached directly."""
        return self._editable and bool(mime.hasFormat(_PAD_MIME)
                                       or self._audio_urls(mime))

    def dragEnterEvent(self, e):
        if self._welcomes(e.mimeData()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._welcomes(e.mimeData()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not self._editable:
            e.ignore()
            return
        mime = e.mimeData()
        if mime.hasFormat(_PAD_MIME):
            src = pc.parse_cell(bytes(mime.data(_PAD_MIME)).decode())
            if src is not None and src != self._key[1:]:
                self.dropped_pad.emit(src, self._key)
            e.acceptProposedAction()
            return
        paths = self._audio_urls(mime)
        if paths:
            # A track dragged out of a deck offers Copy | Move | Link — take the
            # copy, or the deck would lose the row we just borrowed.
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            self.assigned.emit(self._key, paths)
            return
        e.ignore()


# ─────────────────────────────────────────────────────────────────────────────
# The page
# ─────────────────────────────────────────────────────────────────────────────
class CartwallWidget(QWidget):
    """The 🎛 page: a configurable grid of pads, page nav and the wall transport."""

    padClicked = Signal(object)          # cell key (page, row, col)
    changed = Signal()                   # anything worth persisting
    stopAll = Signal()
    padRefreshed = Signal(object, object)  # key, pad — settings changed live
    previewVolume = Signal(object, float)  # key, level — heard while dragging
    previewFire = Signal(object, bool)     # key, on — ▶ in the pad dialog
    fadeChanged = Signal(int)              # the wall-wide fade-out, in ms
    dockRequested = Signal()               # 📌 put me back into the main window
    padsMoved = Signal(object)             # {old key: new key} — turn / reshape
    keysRequested = Signal()               # ⌨ the Keys window, on the wall's tab
    levelChanged = Signal(float)           # 🔊 the wall's own fader, 0…1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = pc.DEFAULT_GRID
        self._pages: list[pc.Page] = pc.new_wall()
        self._page = 0
        self._default_colour = pc.DEFAULT_PAD_COLOUR
        self._fade_ms = pc.DEFAULT_FADE_MS      # every pad follows it by default
        self._slot_keys = pc.SLOT_KEYS          # what each position answers to
        self._missing = set()
        self._live = set()      # keys sounding right now, kept across rebuilds
        self._selected = set()  # ✏ multi-select: the pads an edit applies to
        self._buttons: dict[tuple[int, int, int], _CartPadButton] = {}
        self._shortcuts: list[QShortcut] = []
        self._edit = False      # ✏ locked: pads fire, the wall cannot be changed

        outer = QVBoxLayout(self)
        # Without this the layout stamps its own minimumSize onto the widget and
        # the header would pin the dock at its natural width — it could then only
        # ever grow, never be dragged narrow.
        outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        outer.setContentsMargins(6, 4, 6, 6)
        outer.setSpacing(6)
        outer.addLayout(self._build_nav())
        outer.addLayout(self._build_tools())
        # Only up while ✏ is on, and it says the one thing that surprises people:
        # a wall being edited does not play.
        self._edit_lbl = QLabel("✏  Editing — pads do not play")
        self._edit_lbl.setObjectName("cartEditBanner")
        self._edit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit_lbl.setWordWrap(True)
        self._edit_lbl.setStyleSheet(
            f"QLabel#cartEditBanner {{ background: {_EDIT_ACCENT};"
            " color: #ffffff; border-radius: 4px; padding: 3px;"
            " font-weight: 600; }")
        outer.addWidget(self._edit_lbl)
        self._grid_host = QWidget()
        self._grid_host.setObjectName("cartGrid")
        self._grid_lyt = QGridLayout(self._grid_host)
        self._grid_lyt.setContentsMargins(0, 0, 0, 0)
        self._grid_lyt.setSpacing(4)
        outer.addWidget(self._grid_host, 1)
        self._rebuild()
        self.set_edit(False)            # paints the locked state of the ✏ button

        stop = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        stop.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        stop.activated.connect(self.stopAll.emit)

    def _build_nav(self) -> QHBoxLayout:
        """The page nav gets a row of its own — it is the one control the
        operator hunts for mid-heat, and it must never wrap away."""
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self._prev_btn = QToolButton()
        self._prev_btn.setText("◀")
        self._prev_btn.setAutoRaise(True)
        self._prev_btn.setToolTip("Previous page")
        self._prev_btn.clicked.connect(lambda: self.step_page(-1))
        self._next_btn = QToolButton()
        self._next_btn.setText("▶")
        self._next_btn.setAutoRaise(True)
        self._next_btn.setToolTip("Next page")
        self._next_btn.clicked.connect(lambda: self.step_page(1))
        self._page_lbl = _ClickableLabel("")
        self._page_lbl.setMinimumWidth(70)
        self._page_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_lbl.setToolTip("Double-click to rename this page")
        self._page_lbl.double_clicked.connect(self._rename_page)
        # ➕ only exists in ✏ mode: adding a page is building the wall, not
        # playing it, and it must not be one mis-tap away mid-heat.
        self._add_btn = QToolButton()
        self._add_btn.setText("➕")
        self._add_btn.setAutoRaise(True)
        self._add_btn.setToolTip("Add a page")
        self._add_btn.clicked.connect(self._add_page)
        self._add_btn.hide()
        # ➖ at the far left, ➕ at the far right: the two page edits are opposite
        # acts and sit at opposite ends, so neither is next to the ◀ ▶ you reach
        # for mid-heat.
        self._rm_btn = QToolButton()
        self._rm_btn.setText("➖")
        self._rm_btn.setAutoRaise(True)
        self._rm_btn.setToolTip("Remove this page")
        self._rm_btn.clicked.connect(self._remove_page)
        self._rm_btn.hide()
        bar.addWidget(self._rm_btn)
        bar.addWidget(self._prev_btn)
        bar.addWidget(self._page_lbl, 1)
        bar.addWidget(self._next_btn)
        bar.addWidget(self._add_btn)
        return bar

    def _build_tools(self) -> FlowLayout:
        """Grid, ✏ and the transport. A flow layout, so a dock too narrow for one
        row breaks them onto a second instead of clipping them."""
        bar = FlowLayout(spacing=6)
        # The combo's row IS the index into pc.GRID_SIZES — findData() compares
        # QVariants and never matches a Python tuple, so there is no userData.
        self._size_box = QComboBox()
        for cols, rows in pc.GRID_SIZES:
            self._size_box.addItem(f"{cols} × {rows}")
        self._size_box.setToolTip(
            "Pads per page. Making the grid smaller never loses a pad —\n"
            "whatever no longer fits moves to the first free slot.")
        self._size_box.activated.connect(self._on_size_picked)
        bar.addWidget(self._size_box)

        # Locked by default. A tournament wall gets built once and fired for
        # eight hours; a stray drag during a heat must not rearrange it.
        self._edit_btn = QToolButton()
        self._edit_btn.setIcon(icons.icon("pencil"))
        self._edit_btn.setCheckable(True)
        self._edit_btn.setAutoRaise(True)
        self._edit_btn.toggled.connect(self.set_edit)
        bar.addWidget(self._edit_btn)

        # ⌨ only in ✏ mode, like ➕: setting keys is building the wall. The
        # pad's right-click "⌨ Shortcuts…" opens the same window.
        self._keys_btn = QToolButton()
        self._keys_btn.setText("⌨")
        self._keys_btn.setAutoRaise(True)
        self._keys_btn.setToolTip("Keys: the pads' and the desk's, in one window")
        self._keys_btn.clicked.connect(self.keysRequested.emit)
        self._keys_btn.hide()
        bar.addWidget(self._keys_btn)

        self._stop_btn = QToolButton()
        self._stop_btn.setText("⏹  Stop all")
        self._stop_btn.setToolTip("Fade every running pad out (Esc)")
        self._stop_btn.clicked.connect(self.stopAll.emit)
        bar.addWidget(self._stop_btn)
        bar.addWidget(self._build_level())

        # One button rather than two: the wall autosaves itself, so export and
        # import are the rare deliberate acts of carrying a wall to another PC.
        self._file_btn = QToolButton()
        self._file_btn.setText("🗂")
        self._file_btn.setAutoRaise(True)
        # The ▾ takes no width of its own: the row flows, and the few pixels
        # it adds were enough to push the button onto a second row.
        self._file_btn.setFixedWidth(self._file_btn.sizeHint().width())
        self._file_btn.setText("🗂▾")
        self._file_btn.setToolTip("Export or import this wall")
        # The menu opens from the click, not from setMenu(): a button with a
        # menu attached paints its own ⌄ in the bottom corner. The ▾ in the
        # text sits on the 🗂's line, right of it, in the middle.
        self._file_menu = QMenu(self._file_btn)
        self._file_menu.addAction("📄  All pads on one page", self._pack_one_page)
        self._file_menu.addSeparator()
        self._file_menu.addAction("📤  Export wall…", self._export_wall)
        self._file_menu.addAction("📥  Import wall…", self._import_wall)
        self._file_btn.clicked.connect(
            lambda: self._file_menu.popup(
                self._file_btn.mapToGlobal(self._file_btn.rect().bottomLeft())))
        bar.addWidget(self._file_btn)

        # Only up while the wall floats. Qt's own way back is a drag or a
        # double-click on the title bar, and neither is findable mid-heat —
        # this is, and it sits where the operator is already looking.
        self._dock_btn = QToolButton()
        self._dock_btn.setIcon(icons.icon("pin"))
        self._dock_btn.setAutoRaise(True)
        self._dock_btn.setToolTip(
            "Snap the wall back into the main window.\n"
            "It returns to the edge it was last docked at.")
        self._dock_btn.clicked.connect(self.dockRequested.emit)
        self._dock_btn.setVisible(False)
        bar.addWidget(self._dock_btn)
        self.set_active(0)
        return bar

    def _build_level(self) -> QWidget:
        """🔊 The wall's own fader: every pad, under each pad's own trim. One
        piece, so the flow layout never breaks the slider from its readout."""
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(QLabel("🔊"))
        self._level = _ClickSlider(Qt.Orientation.Horizontal)
        self._level.setRange(0, 100)
        self._level.setValue(100)
        self._level.setFixedWidth(90)
        self._level.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._level.setToolTip(
            "Cartwall volume — every pad, apart from the music volume.\n"
            "Also on a controller fader and the desk keys (⌨).")
        self._level.valueChanged.connect(self._on_level)
        row.addWidget(self._level)
        self._level_lbl = QLabel("100 %")
        self._level_lbl.setFixedWidth(40)
        self._level_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                                     | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._level_lbl)
        return box

    def _on_level(self, value: int) -> None:
        self._level_lbl.setText(f"{value} %")
        self.levelChanged.emit(value / 100.0)

    def set_level(self, level: float) -> None:
        """Show a level set from elsewhere (controller fader, desk key) without
        sending it back as a change."""
        value = round(level * 100)
        self._level.blockSignals(True)
        self._level.setValue(value)
        self._level.blockSignals(False)
        self._level_lbl.setText(f"{value} %")

    def level(self) -> float:
        return self._level.value() / 100.0

    def set_floating(self, on: bool) -> None:
        """The wall was dragged out of the window, or put back into it.

        Only the 📌 button cares: docked there is nothing to snap back, and a
        dead button on the one toolbar that stays readable through a heat is
        worse than no button."""
        self._dock_btn.setVisible(bool(on))

    # ── edit lock ────────────────────────────────────────────────────────────
    def set_edit(self, on: bool) -> None:
        """✏ on = the wall can be built; off = it can only be played."""
        was = self._edit
        self._edit = bool(on)
        if self._edit_btn.isChecked() != self._edit:
            self._edit_btn.setChecked(self._edit)
        self._edit_btn.setToolTip(
            "Editing ON — drop, drag, recolour and reshape the wall.\n"
            "Switch off before the tournament so nothing moves by accident."
            if self._edit else
            "Locked: pads only fire. Click to edit the wall.")
        # The grid combo is NOT locked: reshaping the wall to the dock you just
        # dragged is a view decision, and it never loses a pad.
        if not self._edit:
            self._selected.clear()      # a locked wall has nothing selected
        elif not was and self._live:
            # Editing silences the wall. A pad that keeps sounding while you
            # rearrange the cell it lives in is a pad you can no longer stop by
            # tapping it — the tap selects now.
            self.stopAll.emit()
        for button in self._buttons.values():
            button.set_editable(self._edit)
        self._paint_selection()
        self._paint_edit_state()

    def _paint_edit_state(self) -> None:
        """Make an editable wall unmistakable. It is the mode in which pads do
        NOT fire, and mistaking it for the locked one mid-heat means tapping a
        Tusch and hearing nothing."""
        self._edit_lbl.setVisible(self._edit)
        self._add_btn.setVisible(self._edit)
        self._rm_btn.setVisible(self._edit)
        self._keys_btn.setVisible(self._edit)
        self._grid_host.setStyleSheet(
            f"QWidget#cartGrid {{ border: 2px dashed {_EDIT_ACCENT};"
            " border-radius: 6px; }" if self._edit
            else "QWidget#cartGrid { border: 2px solid transparent; }")

    def edit_mode(self) -> bool:
        return self._edit

    # ── following the dock around ────────────────────────────────────────────
    def set_portrait(self, portrait: bool) -> None:
        """Turn the wall to match the edge it was docked on — tall and narrow at
        the side, short and wide on top. The pads come along (pc.transpose), so
        moving the dock back puts every pad exactly where it was."""
        portrait = bool(portrait)
        if portrait == pc.is_portrait(self._grid):
            return
        before = self._pages
        self._grid, self._pages = pc.transpose(self._grid, self._pages)
        moved = self._follow_pads(before)
        self._size_box.setCurrentIndex(
            pc.GRID_SIZES.index(self._grid)
            if self._grid in pc.GRID_SIZES else -1)
        self._rebuild()
        if moved:
            self.padsMoved.emit(moved)
        self.changed.emit()

    def _follow_pads(self, before: list[pc.Page]) -> dict:
        """{old key: new key} for every pad a turn or reshape put elsewhere —
        found by the pad itself, which both carry over unchanged. A sounding
        pad stays lit in its new cell."""
        where = {id(pad): (p, row, col) for p, page in enumerate(before)
                 for (row, col), pad in page.pads.items()}
        moved = {}
        for p, page in enumerate(self._pages):
            for (row, col), pad in page.pads.items():
                old = where.get(id(pad))
                if old is not None and old != (p, row, col):
                    moved[old] = (p, row, col)
        self._live = {moved.get(k, k) for k in self._live}
        return moved

    # ── model in / out ───────────────────────────────────────────────────────
    def set_wall(self, grid, pages: list[pc.Page], page: int = 0,
                 default_colour: str = pc.DEFAULT_PAD_COLOUR,
                 fade_ms: int = pc.DEFAULT_FADE_MS,
                 slot_keys=None) -> None:
        self._grid = grid
        self._pages = pages or pc.new_wall()
        self._page = max(0, min(page, len(self._pages) - 1))
        self._default_colour = default_colour or pc.DEFAULT_PAD_COLOUR
        self._fade_ms = max(0, min(pc.MAX_FADE_MS, int(fade_ms)))
        self._slot_keys = (pc.SLOT_KEYS if slot_keys is None
                           else pc.clean_slot_keys(slot_keys))
        self.fadeChanged.emit(self._fade_ms)
        # A hand-edited cartwall.json may hold a size the combo does not offer;
        # that is honoured, the combo just shows nothing selected.
        self._size_box.setCurrentIndex(
            pc.GRID_SIZES.index(grid) if grid in pc.GRID_SIZES else -1)
        self._rebuild()

    def grid(self):
        return self._grid

    def pages(self) -> list[pc.Page]:
        return self._pages

    def current_page(self) -> int:
        return self._page

    def default_colour(self) -> str:
        return self._default_colour

    def fade_ms(self) -> int:
        return self._fade_ms

    def slot_keys(self) -> tuple[str, ...]:
        return self._slot_keys

    def set_slot_keys(self, keys) -> None:
        """What each position on the wall answers to. Rebinding is enough to
        change the keys — the faces re-read them from _rebuild_shortcuts."""
        keys = pc.clean_slot_keys(keys)
        if keys == self._slot_keys:
            return
        self._slot_keys = keys
        self._rebuild_shortcuts()
        self.changed.emit()

    def set_fade_ms(self, ms: int) -> None:
        """The wall's fade-out. Every pad follows it unless it was given one of
        its own — see pc.fade_for."""
        ms = max(0, min(pc.MAX_FADE_MS, int(ms)))
        if ms == self._fade_ms:
            return
        self._fade_ms = ms
        self.fadeChanged.emit(ms)
        self.changed.emit()

    def pad_at(self, key) -> pc.CartPad | None:
        page, row, col = key
        if 0 <= page < len(self._pages):
            return self._pages[page].pads.get((row, col))
        return None

    def refresh_missing(self) -> None:
        """Re-sync every visible pad with the model — which files are gone, and
        which key fires which cell after a move or a clear."""
        self._missing = pc.missing_paths(self._pages)
        for key, button in self._buttons.items():
            page, row, col = key
            button.set_pad(self._pages[page].pads.get((row, col)),
                           missing=(page, (row, col)) in self._missing)
        self._rebuild_shortcuts()

    # ── playback feedback ────────────────────────────────────────────────────
    def set_playing(self, key, playing: bool) -> None:
        if playing:
            self._live.add(key)
        else:
            self._live.discard(key)
        button = self._buttons.get(key)
        if button is not None:
            button.set_playing(playing)

    def set_fading(self, key, fading: bool) -> None:
        button = self._buttons.get(key)
        if button is not None:
            button.set_fading(fading)

    def set_remaining(self, key, ms_left: int, frac: float) -> None:
        button = self._buttons.get(key)
        if button is not None:
            button.set_remaining(ms_left, frac)

    def set_active(self, count: int) -> None:
        """Grey ⏹ out while the wall is silent — it says at a glance whether
        anything is running."""
        self._stop_btn.setEnabled(count > 0)

    # ── grid ─────────────────────────────────────────────────────────────────
    def _rebuild(self) -> None:
        for button in self._buttons.values():
            button.setParent(None)
            button.deleteLater()
        self._buttons.clear()
        self._missing = pc.missing_paths(self._pages)
        page = self._pages[self._page]
        for row, col in pc.cells_in_order(self._grid):
            key = (self._page, row, col)
            pad = page.pads.get((row, col))
            button = _CartPadButton(key)
            button.set_editable(self._edit)
            button.set_default_colour(self._default_colour)
            button.set_pad(pad, missing=(self._page, (row, col)) in self._missing)
            # A pad that is sounding stays lit through a page flip or a grid
            # change — the operator has to see what they still have to stop.
            button.set_playing(key in self._live)
            button.tapped.connect(self._fire)
            button.assigned.connect(self._on_assigned)
            button.dropped_pad.connect(self._on_pad_dropped)
            button.edit_requested.connect(self._on_edit)
            button.clear_requested.connect(self._on_clear)
            button.colour_requested.connect(self._on_colour)
            button.wall_colour_requested.connect(self._on_default_colour)
            button.wall_fade_requested.connect(self._on_wall_fade)
            button.shortcuts_requested.connect(self._on_shortcuts)
            button.selected_requested.connect(self._on_select)
            self._grid_lyt.addWidget(button, row, col)
            self._buttons[key] = button
        self._rebuild_shortcuts()
        # A selection cannot survive a page turn or a reshape: it is a set of
        # cells, and those cells now hold something else.
        self._selected = {k for k in self._selected if k in self._buttons}
        self._paint_selection()
        # Every row and column shares the space equally, so the pads always fill
        # the wall. Stretches on the columns a SMALLER grid left behind have to be
        # cleared: QGridLayout never shrinks its column count, and a stretch on an
        # empty column would hold open a gap the pads cannot use.
        cols, rows = self._grid
        for col in range(max(cols, self._grid_lyt.columnCount())):
            self._grid_lyt.setColumnStretch(col, 1 if col < cols else 0)
        for row in range(max(rows, self._grid_lyt.rowCount())):
            self._grid_lyt.setRowStretch(row, 1 if row < rows else 0)
        name = page.name or i18n.t("Page %d") % (self._page + 1)
        self._page_lbl.setText(f"{name}  ({self._page + 1}/{len(self._pages)})")
        self._prev_btn.setEnabled(self._page > 0)
        self._next_btn.setEnabled(self._page + 1 < len(self._pages))
        # One page has nowhere to go: ◀ ▶ only show once there is a second.
        self._prev_btn.setVisible(len(self._pages) > 1)
        self._next_btn.setVisible(len(self._pages) > 1)
        self._add_btn.setEnabled(len(self._pages) < pc.MAX_PAGES)
        self._rm_btn.setEnabled(len(self._pages) > 1)

    # ── keyboard ─────────────────────────────────────────────────────────────
    def _rebuild_shortcuts(self) -> None:
        """Ctrl+1…Ctrl+9 for the first nine slots of the page on screen, plus the
        keys individual pads were given — those work from any page, since that is
        the whole reason to give a pad a key rather than use the slot default.

        Application-wide: the operator is usually clicking around a playlist when
        the Tusch is due, and a wall that only answers when it has focus is not a
        cartwall. They die with the widget, so hiding the wall frees the keys.

        Also the one place that decides which key a pad SHOWS, so the face can
        never advertise a key that a pad elsewhere had already claimed.
        """
        for shortcut in self._shortcuts:
            shortcut.setParent(None)
            shortcut.deleteLater()
        self._shortcuts.clear()
        taken, bound = set(), {}
        for idx, page in enumerate(self._pages):
            for cell, pad in sorted(page.pads.items()):
                if pad.shortcut:
                    self._add_shortcut(pad.shortcut, (idx, *cell), taken, bound)
        for cell in pc.cells_in_order(self._grid):
            self._add_shortcut(pc.slot_key(self._grid, cell, self._slot_keys),
                               (self._page, *cell), taken, bound)
        for key, button in self._buttons.items():
            button.set_shortcut(bound.get(key, ""))

    def _add_shortcut(self, sequence: str, key, taken: set,
                      bound: dict) -> None:
        seq = QKeySequence(sequence)
        text = seq.toString()
        # First one wins, twice over: a pad's own key beats the slot default that
        # would have fired the same cell, and beats another cell wanting that key.
        if not text or text in taken or key in bound:
            return
        taken.add(text)
        bound[key] = text
        shortcut = QShortcut(seq, self)
        # No auto-repeat: a pad key held a moment too long would re-fire the sample
        # at the system repeat rate — over the running music, in a hall.
        shortcut.setAutoRepeat(False)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(lambda k=key: self._fire(k))
        self._shortcuts.append(shortcut)

    def _fire(self, key) -> None:
        """The one way a pad sounds. Silent while ✏ is on — a wall being built
        must not go off, whether the pad was clicked or its key was pressed."""
        if not self._edit:
            self.padClicked.emit(key)

    def play_pad(self, key) -> None:
        """A pad fired from outside the wall (📱 the phone remote) — through
        the same gate as a click."""
        self._fire(key)

    def step_page(self, delta: int) -> None:
        """Turn the page. It never CREATES one — ➕ does that, and only in ✏
        mode. A nav that makes a page whenever you overshoot is how a wall grows
        pages nobody asked for."""
        target = self._page + delta
        if not 0 <= target < len(self._pages):
            return
        self._page = target
        self._rebuild()
        # The page you are on is part of the saved wall (dump_doc writes it), so
        # a plain page turn has to be written too — otherwise the app reopens on
        # whichever page happened to be up at the last pad edit.
        self.changed.emit()

    def _add_page(self) -> None:
        """➕, ✏ only: one more page of pads, and jump straight to it — you
        pressed it because you have something to put there."""
        if len(self._pages) >= pc.MAX_PAGES:
            return
        self._pages.append(pc.blank_page())
        self._page = len(self._pages) - 1
        self._rebuild()
        self.changed.emit()

    def _on_size_picked(self, index: int) -> None:
        if not 0 <= index < len(pc.GRID_SIZES):
            return
        grid = pc.GRID_SIZES[index]
        if grid == self._grid:
            return
        pages, moved = pc.resize_grid(self._pages, grid)
        if len(pages) > pc.FILE_PAGE_CAP:
            # cartwall.json is read back up to this many pages — the pads past
            # them would be gone on the next start.
            self._size_box.setCurrentIndex(
                pc.GRID_SIZES.index(self._grid)
                if self._grid in pc.GRID_SIZES else -1)
            QMessageBox.information(
                self, "Cartwall",
                i18n.t("%d pads need %d pages at %d × %d; the wall keeps at most "
                       "%d.\nClear some pads or pick a bigger layout.")
                % (pc.pad_count(self._pages), len(pages), grid[0], grid[1], pc.FILE_PAGE_CAP))
            return
        before = self._pages
        self._pages = pages
        self._grid = grid
        self._page = min(self._page, len(self._pages) - 1)
        keys = self._follow_pads(before)
        self._rebuild()
        if keys:
            self.padsMoved.emit(keys)
        if moved:
            log.info("🎛 Cartwall grid changed\n"
                     "size: %d × %d\n"
                     "pads relocated: %d", grid[0], grid[1], moved)
        self.changed.emit()

    def _remove_page(self) -> None:
        """➖, ✏ only: drop the page you are on.

        The last page never goes — a page-less wall is not a state the grid, the
        nav or cartwall.json can describe. A page that still holds pads asks
        first: there is no undo on the wall, and those pads were set up for a
        tournament.
        """
        if len(self._pages) <= 1:
            return
        page = self._pages[self._page]
        if page.pads:
            name = page.name or i18n.t("page %d") % (self._page + 1)
            if QMessageBox.question(
                    self, "Remove page",
                    i18n.t("Remove %s and the %d pads on it?\n"
                           "The sample files are left alone — only the pads go.")
                    % (name, len(page.pads))
                    ) != QMessageBox.StandardButton.Yes:
                return
        self._pages.pop(self._page)
        self._page = min(self._page, len(self._pages) - 1)
        self._selected.clear()
        self._rebuild()
        log.info("🎛 Cartwall page removed\n"
                 "pages left: %d\n"
                 "pads left: %d", len(self._pages), pc.pad_count(self._pages))
        self.changed.emit()

    def _rename_page(self) -> None:
        """'Page 1' says nothing on a wall that has a fanfare page and a
        ceremony page. The name is already in the model — this puts it there."""
        page = self._pages[self._page]
        name, ok = QInputDialog.getText(
            self, "Rename page", "Page name:", QLineEdit.EchoMode.Normal,
            page.name)
        if not ok:
            return
        page.name = name.strip()[:pc.LABEL_MAX]
        self._rebuild()
        self.changed.emit()

    def _on_wall_fade(self) -> None:
        dlg = WallFadeDialog(self._fade_ms, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.set_fade_ms(dlg.fade_ms())

    def _on_shortcuts(self) -> None:
        """The pad menu's ⌨ Shortcuts…: the window owns the ⌨ Keys dialog, as
        it holds the desk keys too, and answers with apply_keys()."""
        self.keysRequested.emit()

    def apply_keys(self, pad_keys: dict, slot_keys) -> None:
        """Both layers at once: the slot keys are the wall's, the pad keys are
        each pad's, and only one rebuild happens however many changed."""
        touched = False
        for key, shortcut in pad_keys.items():
            pad = self.pad_at(key)
            if pad is None or pad.shortcut == shortcut:
                continue
            page, row, col = key
            updated = replace(pad, shortcut=shortcut)
            pc.set_pad(self._pages, page, (row, col), updated)
            self.padRefreshed.emit(key, updated)
            touched = True
        keys = tuple(slot_keys)
        if keys != self._slot_keys:
            self._slot_keys = keys
            touched = True
        if touched:
            self._rebuild_shortcuts()
            self.changed.emit()

    def _on_default_colour(self, colour: str) -> None:
        if colour == self._default_colour:
            return
        self._default_colour = colour
        for button in self._buttons.values():
            button.set_default_colour(colour)
        self.changed.emit()

    def _pack_one_page(self) -> None:
        """Collapse the wall onto page 1. A wall you never have to page through
        mid-heat is worth more than the tidy grouping that spread it in the first
        place — but only the user gets to decide that, hence the menu entry."""
        moved = pc.pad_count(self._pages[1:])
        pages, ok = pc.pack_one_page(self._pages, self._grid)
        if not ok:
            QMessageBox.information(
                self, "Cartwall",
                i18n.t("%d pads do not fit one %d × %d page.\nPick a bigger layout first.")
                % (pc.pad_count(self._pages), self._grid[0], self._grid[1]))
            return
        if not moved and len(self._pages) == 1:
            return
        self._selected.clear()
        self._pages = pages
        self._page = 0
        self._rebuild()
        log.info("🎛 Cartwall packed onto one page\n"
                 "pads moved: %d\n"
                 "pads total: %d", moved, pc.pad_count(pages))
        self.changed.emit()

    # ── carrying a wall between machines ─────────────────────────────────────
    def _export_wall(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export cartwall", f"cartwall{pc.WALL_SUFFIX}",
            "Cartwall (*.json)")
        if not path:
            return
        doc = pc.dump_doc(self._grid, self._pages, self._page,
                          self._default_colour, self._fade_ms, self._slot_keys)
        try:
            pc.write_wall(path, doc)
        except OSError as exc:
            log.warning("🎛 Cartwall export failed\n"
                        "path: %s\n"
                        "error: %s", path, exc)
            QMessageBox.warning(self, "Export cartwall",
                                i18n.t("Could not write the wall:\n%s") % exc)
            return
        log.info("🎛 Cartwall exported\n"
                 "path: %s\n"
                 "pads: %d", path, pc.pad_count(self._pages))
        # The pads are NOT copied along: a wall is a list of paths, and a stick
        # that holds the samples too is the 🧳 venue bundle's job, not this one.
        QMessageBox.information(
            self, "Export cartwall",
            i18n.t("%d pads written to\n%s\n\nThe sample files themselves are not "
                   "copied — the wall stores their paths.") % (pc.pad_count(self._pages), path))

    def _import_wall(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import cartwall", "", "Cartwall (*.json)")
        if not path:
            return
        doc = pc.read_wall(path)
        if not doc.ok:
            log.warning("🎛 Cartwall import refused\n"
                        "path: %s\n"
                        "reason: not a wall this build understands", path)
            QMessageBox.warning(
                self, "Import cartwall",
                "That file is not a cartwall this version can read.")
            return
        # It replaces the wall wholesale, so it has to be asked for — the current
        # wall is only in cartwall.json, and the import overwrites that too.
        if QMessageBox.question(
                self, "Import cartwall",
                i18n.t("Replace the current wall with %d pads from\n%s?")
                % (pc.pad_count(doc.pages), path)) != QMessageBox.StandardButton.Yes:
            return
        self._selected.clear()
        self.set_wall(doc.grid, doc.pages, doc.page, doc.colour, doc.fade_ms,
                      doc.slot_keys)
        self.changed.emit()         # the import IS the edit that saves it
        log.info("🎛 Cartwall imported\n"
                 "path: %s\n"
                 "grid: %d × %d\n"
                 "pads: %d", path, doc.grid[0], doc.grid[1],
                 pc.pad_count(doc.pages))

    # ── multi-select (✏ only) ────────────────────────────────────────────────
    def _on_select(self, key, add: bool) -> None:
        if add:
            self._selected ^= {key}     # Ctrl-click a selected pad to drop it
        else:
            self._selected = {key}
        self._paint_selection()

    def _paint_selection(self) -> None:
        count = len(self._selected)
        for key, button in self._buttons.items():
            button.set_selected(key in self._selected, count)

    def selection(self) -> set:
        return set(self._selected)

    def _scope(self, key) -> list[tuple[int, int, int]]:
        """Which pads an edit hits: the whole selection when the pad that was
        right-clicked belongs to it, otherwise just that one."""
        if key in self._selected and len(self._selected) > 1:
            return [k for k in sorted(self._selected) if self.pad_at(k) is not None]
        return [key]

    # ── pad edits ────────────────────────────────────────────────────────────
    def _on_assigned(self, key, paths: list[str]) -> None:
        """One file replaces the pad you aimed at; a whole library selection puts
        the first one there and fills the free slots after it."""
        page, row, col = key
        filled = pc.fill_pads(self._pages, page, (row, col), list(paths), self._grid)
        self._rebuild()      # a multi-drop can spill onto pages that did not exist
        self.refresh_missing()
        self.changed.emit()
        if len(filled) > 1:
            log.info("🎛 Cartwall filled from a multi-select\n"
                     "dropped: %d\n"
                     "placed: %d", len(paths), len(filled))
        if len(filled) < len(paths):
            QMessageBox.information(
                self, "Cartwall",
                i18n.t("The wall is full: %d of %d tracks were placed.\n"
                       "Clear some pads or pick a bigger layout for the rest.")
                % (len(filled), len(paths)))

    def _on_colour(self, key, colour: str) -> None:
        touched = False
        for target in self._scope(key):
            pad = self.pad_at(target)
            if pad is None or pad.colour == colour:
                continue
            pad.colour = colour
            button = self._buttons.get(target)
            if button is not None:
                button.set_pad(pad,
                               missing=(target[0], target[1:]) in self._missing)
            touched = True
        if touched:
            self.changed.emit()

    def _on_pad_dropped(self, src_cell, dst_key) -> None:
        page, row, col = dst_key
        pc.move_pad(self._pages, self._page, src_cell, page, (row, col))
        self.refresh_missing()
        self.changed.emit()

    def _on_clear(self, key) -> None:
        for page, row, col in self._scope(key):
            pc.clear_pad(self._pages, page, (row, col))
            self._selected.discard((page, row, col))
        self._paint_selection()
        self.refresh_missing()
        self.changed.emit()

    def _on_edit(self, key) -> None:
        pad = self.pad_at(key)
        if pad is None:
            return
        page, row, col = key
        scope = self._scope(key)
        dlg = CartPadDialog(pad, self,
                            slot_key=pc.slot_key(self._grid, (row, col),
                                                 self._slot_keys),
                            pad_count=len(scope), wall_fade_ms=self._fade_ms)
        dlg.previewVolume.connect(
            lambda vol, k=key: self.previewVolume.emit(k, vol))
        dlg.previewFire.connect(
            lambda on, k=key: self.previewFire.emit(k, on))
        try:
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
        finally:
            # Whatever the dialog did to the live level, the pad's own trim wins
            # again the moment it closes.
            self.previewVolume.emit(key, pad.volume)
        updated = dlg.pad()
        pc.set_pad(self._pages, page, (row, col), updated)
        self.padRefreshed.emit(key, updated)
        # The rest of the selection takes only what a pad can SHARE: its path,
        # label and shortcut are its own, six pads cannot answer to one key.
        # And only what this edit CHANGED: ticking 🔈 for six pads must not
        # also copy this pad's colour and volume over theirs.
        changed = [f for f in ("colour", "volume", "loop", "duck", "background",
                               "stops_others", "fade_ms")
                   if getattr(updated, f) != getattr(pad, f)]
        for target in scope:
            if target == key:
                continue
            other = self.pad_at(target)
            if other is None:
                continue
            for field in changed:
                setattr(other, field, getattr(updated, field))
            self.padRefreshed.emit(target, other)
        self.refresh_missing()      # re-labels the pads and re-binds the keys
        self.changed.emit()
