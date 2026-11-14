"""Show text that came from outside as text.

Qt turns a string that "might be rich text" into HTML on its own: a QLabel, a
message box and a tooltip all do. Tag text, `#EXTINF` titles, M3U lines and the
names inside a venue pack are not ours, and `<img src="\\\\host\\x">` in one of
them makes Qt open that path: an SMB login to whoever named the host. Windows
file names cannot hold `<` or `>`, so a file name alone is no way in; the text
inside the file is. Security audit run-2 #3.

Three tools, one per kind of sink:

* message boxes: `install_message_boxes()` once at start. After it every
  `QMessageBox`/`QInputDialog` static escapes its text, and a box built by hand
  starts as plain text. A box that wants markup says so with
  `box.setTextFormat(RICH)` and escapes the parts that are data.
* tooltips: `item.setToolTip(plain_tip(text))`. Qt has no switch for a tooltip,
  so text that would be read as markup becomes escaped HTML that shows as typed.
* labels: `plain_label(text)`, or `label.setTextFormat(Qt.TextFormat.PlainText)`.

Text that is OURS and meant as markup does not go through any of these.
"""
import html
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import Qt as GuiQt
from PySide6.QtWidgets import QInputDialog, QLabel, QMessageBox

log = logging.getLogger(__name__)

RICH = Qt.TextFormat.RichText
PLAIN = Qt.TextFormat.PlainText

# (class, method): every one takes (parent, title, text-or-label, ...).
_STATICS = (
    (QMessageBox, "information"),
    (QMessageBox, "question"),
    (QMessageBox, "warning"),
    (QMessageBox, "critical"),
    (QMessageBox, "about"),
    (QInputDialog, "getText"),
    (QInputDialog, "getItem"),
    (QInputDialog, "getInt"),
    (QInputDialog, "getDouble"),
    (QInputDialog, "getMultiLineText"),
)
_TEXT_POS = 2
_TEXT_KEYS = ("text", "label")

_originals: list[tuple] = []  # (owner, attribute, what was there before)


def plain_html(text) -> str:
    """`text` as HTML that Qt shows exactly as typed, line breaks included."""
    return ("<p style='white-space:pre-wrap'>"
            + html.escape("" if text is None else str(text)) + "</p>")


def plain_tip(text) -> str:
    """A tooltip that shows `text` as typed. Empty stays empty: no empty bubble.

    Text Qt would show as plain anyway is returned as it is: the decision is
    Qt's own `mightBeRichText`, the one a tooltip makes. Only text that would be
    read as markup is escaped."""
    if text is None or str(text) == "":
        return ""
    text = str(text)
    return plain_html(text) if GuiQt.mightBeRichText(text) else text


def plain_label(text="", parent=None) -> QLabel:
    """A label that shows `text` as typed."""
    lbl = QLabel(parent)
    lbl.setTextFormat(PLAIN)
    lbl.setText("" if text is None else str(text))
    return lbl


def _escaped_statics_args(args: tuple, kw: dict) -> tuple:
    out = list(args)
    if len(out) > _TEXT_POS and isinstance(out[_TEXT_POS], str):
        out[_TEXT_POS] = plain_html(out[_TEXT_POS])
        return tuple(out), kw
    for key in _TEXT_KEYS:
        if isinstance(kw.get(key), str):
            return tuple(out), {**kw, key: plain_html(kw[key])}
    return tuple(out), kw


def _patch_static(cls, name: str) -> None:
    original = getattr(cls, name)
    _originals.append((cls, name, staticmethod(original)))

    def wrapper(*args, **kw):
        args, kw = _escaped_statics_args(args, kw)
        return original(*args, **kw)

    setattr(cls, name, staticmethod(wrapper))


def _patch_box_ctor() -> None:
    original = QMessageBox.__init__
    _originals.append((QMessageBox, "__init__", original))

    def wrapper(self, *args, **kw):
        original(self, *args, **kw)
        self.setTextFormat(PLAIN)

    QMessageBox.__init__ = wrapper


def install_message_boxes() -> None:
    """Make every message box show its text as typed. Safe to call twice."""
    if _originals:
        return
    for cls, name in _STATICS:
        _patch_static(cls, name)
    _patch_box_ctor()
    log.debug("🔒 Message boxes show their text as plain text")


def restore_message_boxes() -> None:
    """Take the patches off. **For the test suite only:** the app never does."""
    for owner, name, original in reversed(_originals):
        setattr(owner, name, original)
    _originals.clear()
