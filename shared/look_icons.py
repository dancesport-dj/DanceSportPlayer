"""Under a 🎨 look, the emoji the chrome wears become one painted icon set.

Classic Light and Dark keep their emoji: the full icon pass that replaced them
everywhere was turned down for those two (branch rejected/icon-pass). A look is
a designed surface, though, and a row of system emoji on it never reads as one
set — so there, and only there, a leading emoji on a button, check box, tab,
menu entry or label is taken off its text and comes back as an icon from
shared/iconset.py, painted in the look's own ink. A group-box or window title
cannot carry an icon; it only loses the emoji (a window title loses it
under every theme already, gui.common.install_plain_title_hook).

One hook, the shape of the i18n one (planner/i18n.py), so no call site has to
know about it. It must be installed BEFORE the i18n hook: i18n then wraps it,
translates the whole caption (its catalog keys carry the emoji) and hands the
translation on, emoji first, to be split here.

A glyph without an entry below stays what it was — the coloured squares of a
legend, a bullet, an ≈ are text, not chrome.
"""

import html as _html
import logging
import re
from functools import lru_cache

from shared import icons, theme

log = logging.getLogger("dancesport.gui")

# How an icon is coloured: the look's ink, its accent, or a colour that MEANS
# something — the same few the emoji carried (a red erase, a gold star).
INK, ACCENT, DANGER, GOLD, OK, WARN = "ink", "accent", "danger", "gold", "ok", "warn"

# Per tone: (on a light look, on a dark look). Each holds 3:1 against the
# grounds of its side (tests/gui/test_look_icons.py).
_SEMANTIC = {
    DANGER: ("#c62828", "#ff7b72"),
    GOLD: ("#a87400", "#f2c94c"),
    OK: ("#2e7d32", "#5fd38d"),
    WARN: ("#b25e00", "#ffb454"),
}

# leading glyph → (icon, tone)
GLYPHS = {
    # transport
    "▶": ("play", INK), "⏸": ("pause", INK), "⏯": ("play_pause", INK),
    "■": ("stop", INK), "⏹": ("stop", INK), "⏭": ("next", INK), "⏮": ("prev", INK),
    "🛑": ("panic", DANGER), "🔁": ("repeat", INK), "🔀": ("shuffle", INK),
    "🔈": ("speak", INK), "🔉": ("volume_low", INK), "🔊": ("volume", INK),
    "🔇": ("mute", INK), "🎧": ("headphones", INK), "🎙": ("mic", INK),
    "🎛": ("sliders", INK), "🎚": ("sliders", INK), "⏱": ("stopwatch", INK),
    "🕒": ("clock", INK), "⏳": ("hourglass", INK), "🖥": ("display", INK),
    "🎉": ("party", INK), "🤸": ("warmup", INK), "🐂": ("bull", INK),
    "🎵": ("music", INK), "🎼": ("music_list", INK), "🎬": ("film", INK),
    # files & lists
    "📂": ("folder_open", INK), "📁": ("folder", INK), "💾": ("save", INK),
    "🖨": ("print", INK), "📋": ("clipboard", INK), "📄": ("file", INK),
    "📝": ("journal", INK), "📜": ("scroll", INK), "📤": ("export", INK),
    "📥": ("import", INK), "🧳": ("suitcase", INK), "📚": ("library", INK),
    "📅": ("calendar", INK), "📌": ("pin", INK), "🏷": ("tag", INK),
    "🖼": ("image", INK), "⧉": ("decks", INK), "🪟": ("window", INK),
    "♊": ("duplicate", INK), "🔗": ("link", INK), "🧩": ("puzzle", INK),
    # editing
    "➕": ("plus", INK), "＋": ("plus", INK), "➖": ("minus", INK), "−": ("minus", INK),
    "✕": ("close", INK), "✖": ("close", INK), "✔": ("check", OK), "✓": ("check", OK),
    "✅": ("check_circle", OK), "✏": ("pencil", INK), "✎": ("pencil", INK),
    "🗑": ("trash", DANGER), "🧹": ("clean", INK), "🔍": ("search", INK),
    "🔎": ("search", INK), "🔒": ("lock", INK), "🔓": ("unlock", INK),
    "✋": ("hand", INK), "↺": ("regen", INK), "↻": ("regen", INK), "🔄": ("regen", INK),
    "↶": ("undo", INK), "↷": ("redo", INK), "↩": ("return", INK), "⇅": ("sort", INK),
    "⬆": ("arrow_up", INK), "⊟": ("collapse", INK), "⊞": ("expand", INK),
    "🗜": ("compact", INK), "📐": ("layout", INK), "🔢": ("numbers", INK),
    "♻": ("recycle", INK),
    # carets
    "▾": ("caret_down", INK), "▼": ("caret_down", INK), "▴": ("caret_up", INK),
    "▲": ("caret_up", INK), "▸": ("caret_right", INK), "◂": ("caret_left", INK),
    # the app and its tools
    "⚙": ("gear", INK), "🧭": ("compass", INK), "🎯": ("target", INK),
    "🧠": ("brain", INK), "🤖": ("robot", INK), "📊": ("chart", INK),
    "🔬": ("analysis", INK), "⚗": ("analysis", INK),
    "⚡": ("bolt", INK), "🧱": ("bricks", INK),
    "🌐": ("globe", INK), "🎨": ("palette", INK), "🔑": ("key", INK),
    "🔧": ("wrench", INK), "⌨": ("keyboard", INK), "💬": ("chat", INK),
    "🐞": ("bug", INK), "🩺": ("pulse", INK), "🌱": ("sprout", INK),
    "☀": ("sun", INK), "🌙": ("moon", INK), "🆕": ("stars", INK), "✦": ("stars", INK),
    "ℹ": ("info", ACCENT), "❔": ("help", INK), "🔔": ("bell", INK),
    "🔕": ("bell_off", INK), "🏁": ("flag", INK), "🚫": ("blocked", INK),
    # meaning carried by colour
    "⭐": ("star", GOLD), "★": ("star", GOLD), "🏆": ("trophy", GOLD),
    "⚠": ("warning", WARN), "❗": ("issue", DANGER), "💥": ("crash", DANGER),
}

_VARIATION = "️"     # the emoji-presentation selector some glyphs carry


def split(text) -> tuple[str, str, str, str] | None:
    """(glyph, icon, tone, rest) for a caption that starts with a known glyph,
    else None. `rest` loses the spacing that stood between the two."""
    if not isinstance(text, str) or not text or text[0] not in GLYPHS:
        return None
    name, tone = GLYPHS[text[0]]
    rest = text[1:]
    if rest.startswith(_VARIATION):
        rest = rest[1:]
    return text[0], name, tone, rest.lstrip(" ")


def color(tone: str) -> str:
    """The active look's colour for `tone`."""
    look = theme.active_look()
    t = look.tokens
    if tone == INK:
        return t.text
    if tone == ACCENT:
        return t.accent_ink
    return _SEMANTIC[tone][1 if look.dark else 0]


@lru_cache(maxsize=512)
def icon(name: str, tone: str = INK, toggles: bool = False):
    """The look's icon, sharp at 1× and 2×. `toggles`: a push button or tool
    button that may be checked — a checked one is filled with the accent, so
    its On state is painted in the colour written on that fill."""
    from PySide6.QtGui import QIcon

    ic = QIcon()
    for px in (16, 32):
        ic.addPixmap(icons.raw_pixmap(name, px, color(tone)))
        if toggles:
            on = icons.raw_pixmap(name, px, theme.active_look().tokens.on_accent)
            ic.addPixmap(on, QIcon.Mode.Normal, QIcon.State.On)
    return ic


@lru_cache(maxsize=256)
def img_tag(name: str, tone: str) -> str:
    """The icon as an inline <img> for a label's rich text."""
    from PySide6.QtCore import QBuffer, QIODevice

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    icons.raw_pixmap(name, 32, color(tone)).save(buf, "PNG")
    data = bytes(buf.data().toBase64()).decode("ascii")
    return (f'<img src="data:image/png;base64,{data}" width="16" height="16" '
            f'style="vertical-align:middle">')


def label_html(name: str, tone: str, rest: str) -> str:
    """A plain label's text with the icon in front, as rich text."""
    body = _html.escape(rest).replace("\n", "<br>")
    return f"{img_tag(name, tone)}&nbsp;{body}"


# Rich text whose first visible character is a known glyph: "<b>🎨 Theme</b>…"
_RICH_LEAD = re.compile(r"^((?:\s*<[^>]+>)*\s*)(\S)️? *")


def rich_html(text: str) -> str | None:
    """`text` with its leading glyph swapped for the icon, or None."""
    m = _RICH_LEAD.match(text)
    if m is None or m.group(2) not in GLYPHS:
        return None
    name, tone = GLYPHS[m.group(2)]
    return f"{m.group(1)}{img_tag(name, tone)}&nbsp;{text[m.end():]}"


# ── Wiring it into Qt ────────────────────────────────────────────────────────

_installed = False
_originals: list = []      # (owner, name, original) — for the test suite


def _patch(cls, name: str, make) -> None:
    original = getattr(cls, name)
    _originals.append((cls, name, original))
    setattr(cls, name, make(original))


def _dress_button(btn, set_text) -> None:
    parts = split(btn.text())
    if parts is None:
        return
    glyph, name, tone, rest = parts
    from PySide6.QtWidgets import QPushButton, QToolButton

    set_text(btn, rest)
    btn.setIcon(icon(name, tone, isinstance(btn, (QPushButton, QToolButton))))
    btn.setProperty("lookGlyph", glyph)


def _dress_action(act, set_text) -> None:
    parts = split(act.text())
    if parts is not None:
        glyph, name, tone, rest = parts
        set_text(act, rest)
        act.setIcon(icon(name, tone))


def _dress_menu(menu, set_title) -> None:
    parts = split(menu.title())
    if parts is not None:
        glyph, name, tone, rest = parts
        set_title(menu, rest)
        menu.setIcon(icon(name, tone))


def _dress_label(label, set_text) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import Qt as GuiQt     # where mightBeRichText lives

    text = label.text()
    if label.textFormat() == Qt.TextFormat.PlainText:
        return
    if label.textFormat() == Qt.TextFormat.RichText \
            or GuiQt.mightBeRichText(text):
        dressed = rich_html(text)
        if dressed is not None:
            set_text(label, dressed)
        return
    parts = split(text)
    if parts is None:
        return
    glyph, name, tone, rest = parts
    label.setTextFormat(Qt.TextFormat.RichText)
    set_text(label, label_html(name, tone, rest))


def _dress_tab(tabs, index: int, set_text) -> None:
    if index < 0:
        return
    parts = split(tabs.tabText(index))
    if parts is not None:
        glyph, name, tone, rest = parts
        set_text(tabs, index, rest)
        tabs.setTabIcon(index, icon(name, tone))


def _bare(text):
    parts = split(text)
    return parts[3] if parts is not None else text


def install() -> None:
    """Hook the chrome's text setters — only while a 🎨 look is active, so the
    classic themes are untouched. Before the first widget, and before i18n."""
    global _installed
    if _installed or theme.active_look() is None:
        return
    from PySide6 import QtGui, QtWidgets as W

    raw_btn_text = W.QAbstractButton.setText
    raw_act_text = QtGui.QAction.setText
    raw_title = W.QMenu.setTitle
    raw_label_text = W.QLabel.setText
    raw_tab_text = W.QTabWidget.setTabText

    def btn_set_text(original):
        def wrapper(self, text):
            original(self, text)
            _dress_button(self, raw_btn_text)
        return wrapper

    def btn_ctor(original):
        def wrapper(self, *args, **kw):
            original(self, *args, **kw)
            _dress_button(self, raw_btn_text)
        return wrapper

    _patch(W.QAbstractButton, "setText", btn_set_text)
    for cls in (W.QPushButton, W.QToolButton, W.QCheckBox, W.QRadioButton):
        _patch(cls, "__init__", btn_ctor)

    def act_set_text(original):
        def wrapper(self, text):
            original(self, text)
            _dress_action(self, raw_act_text)
        return wrapper

    def act_ctor(original):
        def wrapper(self, *args, **kw):
            original(self, *args, **kw)
            _dress_action(self, raw_act_text)
        return wrapper

    _patch(QtGui.QAction, "setText", act_set_text)
    _patch(QtGui.QAction, "__init__", act_ctor)

    def menu_add_action(original):
        def wrapper(self, *args, **kw):
            act = original(self, *args, **kw)
            if isinstance(act, QtGui.QAction):
                _dress_action(act, raw_act_text)
            return act
        return wrapper

    def menu_add_menu(original):
        def wrapper(self, *args, **kw):
            sub = original(self, *args, **kw)
            if isinstance(sub, W.QMenu):
                _dress_menu(sub, raw_title)
            return sub
        return wrapper

    def menu_ctor(original):
        def wrapper(self, *args, **kw):
            original(self, *args, **kw)
            _dress_menu(self, raw_title)
        return wrapper

    def menu_set_title(original):
        def wrapper(self, title):
            original(self, title)
            _dress_menu(self, raw_title)
        return wrapper

    _patch(W.QMenu, "addAction", menu_add_action)
    _patch(W.QMenu, "addMenu", menu_add_menu)
    _patch(W.QMenu, "__init__", menu_ctor)
    _patch(W.QMenu, "setTitle", menu_set_title)

    def label_set_text(original):
        def wrapper(self, text):
            original(self, text)
            _dress_label(self, raw_label_text)
        return wrapper

    def label_ctor(original):
        def wrapper(self, *args, **kw):
            original(self, *args, **kw)
            _dress_label(self, raw_label_text)
        return wrapper

    _patch(W.QLabel, "setText", label_set_text)
    _patch(W.QLabel, "__init__", label_ctor)

    def tab_add(original):
        def wrapper(self, *args, **kw):
            index = original(self, *args, **kw)
            _dress_tab(self, index, raw_tab_text)
            return index
        return wrapper

    def tab_insert(original):
        def wrapper(self, *args, **kw):
            index = original(self, *args, **kw)
            _dress_tab(self, index, raw_tab_text)
            return index
        return wrapper

    def tab_set_text(original):
        def wrapper(self, index, text):
            original(self, index, text)
            _dress_tab(self, index, raw_tab_text)
        return wrapper

    _patch(W.QTabWidget, "addTab", tab_add)
    _patch(W.QTabWidget, "insertTab", tab_insert)
    _patch(W.QTabWidget, "setTabText", tab_set_text)

    # No icon fits here: the title just loses its glyph.
    def strip_first(original):
        def wrapper(self, text, *args, **kw):
            return original(self, _bare(text), *args, **kw)
        return wrapper

    def strip_ctor(original):
        def wrapper(self, *args, **kw):
            if args and isinstance(args[0], str):
                args = (_bare(args[0]),) + args[1:]
            original(self, *args, **kw)
        return wrapper

    _patch(W.QGroupBox, "setTitle", strip_first)
    _patch(W.QGroupBox, "__init__", strip_ctor)
    # Window titles lose theirs already, under every theme
    # (gui.common.install_plain_title_hook).

    _installed = True
    log.debug("🎨 Look icons installed (look=%s)", theme.active_look().key)


def _restore() -> None:
    """Take every patch back off. **For the test suite only.**"""
    global _installed
    for owner, name, original in reversed(_originals):
        setattr(owner, name, original)
    _originals.clear()
    icon.cache_clear()
    img_tag.cache_clear()
    _installed = False
