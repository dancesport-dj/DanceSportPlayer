"""⌨ Keys: every key the player answers to, in one window.

Two tabs. ⌨ Desk keys: the same actions the 📱 phone and a 🎛 controller drive
(planner.playing.controller), on the keyboard — and so on anything that types: a Stream
Deck or a macro keypad needs no MIDI driver for them. 🎛 Cartwall: the pads'
and slots' keys (player.widgets.cart_keys.CartKeysPanel). One window, so a key one tab
takes is flagged on the other before either is saved.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QTabWidget, QToolButton, QVBoxLayout, QWidget)

from planner.playing import controller as pctl
from planner import i18n
from player.widgets.cart_keys import CartKeysPanel, _KeyPicker
from player.dialogs.controller_dialog import action_label


class KeysDialog(QDialog):
    """⌨ Desk keys and 🎛 Cartwall keys, one OK for both. `wall` is the wall's
    (grid, pages, slot_keys); `tab` the one to open on (DESK or WALL)."""

    DESK, WALL = 0, 1

    def __init__(self, desk_keys: dict, wall, parent=None, tab: int = DESK):
        super().__init__(parent)
        self.setWindowTitle("⌨  Keys")
        lyt = QVBoxLayout(self)
        self.desk = DeskKeysPanel(desk_keys)
        self.wall = CartKeysPanel(*wall)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.desk, "⌨  Desk keys")
        self.tabs.addTab(self.wall, "🎛  Cartwall")
        self.tabs.setCurrentIndex(tab)
        lyt.addWidget(self.tabs)
        self.desk.changed.connect(self._sync)
        self.wall.changed.connect(self._sync)
        self._sync()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lyt.addWidget(buttons)

    def desk_keys(self) -> dict:
        return self.desk.keys()

    def pad_keys(self) -> dict:
        return self.wall.pad_keys()

    def slot_keys(self) -> tuple:
        return self.wall.slot_keys()

    def _sync(self):
        """Each tab hears of the other's keys as they stand now: two shortcuts
        on one key are ambiguous to Qt, so neither would fire."""
        self.desk.set_taken({k: f"🎛  {owner}"
                             for k, owner in self.wall.owners().items()})
        self.wall.set_taken(pctl.keys_outside_wall(self.desk.keys()))


class DeskKeysPanel(QWidget):
    """One row per action: its keys — ＋ adds another, − takes it away —,
    and what else answers to each. `taken` is {key: label} of the keys the 🎛 wall answers to."""

    changed = Signal()      # a key was edited — not when set_taken() repaints

    def __init__(self, keys: dict, parent=None, taken: dict | None = None):
        super().__init__(parent)
        self._taken = dict(taken or {})
        lyt = QVBoxLayout(self)
        intro = QLabel(
            "The player's actions on the keyboard, from anywhere in the "
            "window — the same ones the 📱 phone and a 🎛 controller run.")
        intro.setWordWrap(True)
        lyt.addWidget(intro)

        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setColumnStretch(1, 1)
        self._pickers: dict[str, list[_KeyPicker]] = {}
        self._warnings: dict[str, list[QLabel]] = {}
        self._lines: dict[str, list[QWidget]] = {}
        self._stacks: dict[str, QVBoxLayout] = {}
        self._add_buttons: dict[str, QToolButton] = {}
        for row, action in enumerate(pctl.KEY_ACTIONS):
            stack = QVBoxLayout()
            stack.setSpacing(2)
            add = QToolButton()
            add.setText("＋")
            add.setAutoRaise(True)
            add.setToolTip("Another key for this action")
            add.clicked.connect(lambda _=False, a=action: self._add_key(a))
            grid.addWidget(QLabel(action_label(action)), row, 0,
                           Qt.AlignmentFlag.AlignTop)
            grid.addLayout(stack, row, 1)
            self._pickers[action] = []
            self._warnings[action] = []
            self._lines[action] = []
            self._stacks[action] = stack
            self._add_buttons[action] = add
            self._set_keys(action, keys.get(action) or [])
        # Every ＋ makes the list longer: it scrolls, rather than squeezing
        # the fields until their keys can't be read.
        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # The tab's own ground: setWidget() switches the body's fill on.
        scroll.viewport().setAutoFillBackground(False)
        body.setAutoFillBackground(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(body.sizeHint().width()
                               + scroll.verticalScrollBar().sizeHint().width())
        # As tall as the rows, up to what a 768 px screen leaves the list
        # under the tabs and over the buttons: the 🎯 focus rows doubled it.
        scroll.setMinimumHeight(min(body.sizeHint().height(), 400))
        lyt.addWidget(scroll, 1)

        tip = QLabel(
            "💡 A Stream Deck or a macro keypad can send F13–F24: no keyboard "
            "has them, so they never clash. A MIDI pad goes through 🎛 "
            "Controller instead (on Windows via loopMIDI).")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#666; font-size:11px;")
        lyt.addWidget(tip)

        reset = QPushButton("↺  Restore defaults")
        reset.clicked.connect(self._restore_defaults)
        row = QHBoxLayout()
        row.addWidget(reset)
        row.addStretch(1)
        lyt.addLayout(row)
        self._refresh()

    def keys(self) -> dict:
        """{action: [keys]} as set now, [] for none."""
        return {action: [k for k in fields if k]
                for action, fields in self._fields().items()}

    def _fields(self) -> dict:
        """{action: what each of its fields holds}, "" for an empty one."""
        return {action: [p.sequence() for p in pickers]
                for action, pickers in self._pickers.items()}

    def set_taken(self, taken: dict) -> None:
        """{key: label} of the wall changed — the 🎛 tab's, unsaved."""
        self._taken = dict(taken)
        self._refresh()

    def _on_edit(self):
        self._refresh()
        self.changed.emit()

    def _restore_defaults(self):
        for action, keys in pctl.desk_keys({}).items():
            self._set_keys(action, keys)
        self._on_edit()

    def _add_key(self, action: str):
        """＋: one more field for the action, empty until a key is pressed."""
        self._new_field(action)
        self._refresh()

    def _set_keys(self, action: str, keys: list):
        """The action's fields hold `keys`: one field at least, none to spare."""
        pickers = self._pickers[action]
        while len(pickers) > max(1, len(keys)):
            self._drop_field(action, len(pickers) - 1)
        while len(pickers) < max(1, len(keys)):
            self._new_field(action)
        for picker, key in zip(pickers, keys or [""], strict=True):
            picker.set_sequence(key)

    def _new_field(self, action: str):
        picker = _KeyPicker("")
        picker.changed.connect(self._on_edit)
        warn = QLabel("")
        warn.setStyleSheet("color:#b26a00; font-size:11px;")
        holder = QWidget()
        line = QHBoxLayout(holder)
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(picker)
        # The ＋ beside the first field, a − beside each one added after it:
        # one button wide either way, so every warning starts at one place.
        if self._pickers[action]:
            minus = QToolButton()
            minus.setText("−")
            minus.setAutoRaise(True)
            minus.setToolTip("Remove this key")
            minus.setFixedWidth(self._add_buttons[action].sizeHint().width())
            minus.clicked.connect(
                lambda _=False, a=action, h=holder: self._remove_key(a, h))
            line.addWidget(minus)
        else:
            line.addWidget(self._add_buttons[action])
        line.addWidget(warn, 1)
        self._stacks[action].addWidget(holder)
        self._pickers[action].append(picker)
        self._warnings[action].append(warn)
        self._lines[action].append(holder)

    def _remove_key(self, action: str, holder: QWidget):
        """−: the field goes, and the key in it."""
        self._drop_field(action, self._lines[action].index(holder))
        self._on_edit()

    def _drop_field(self, action: str, n: int):
        self._pickers[action].pop(n)
        self._warnings[action].pop(n)
        holder = self._lines[action].pop(n)
        holder.setParent(None)  # out of the row now; deleteLater waits
        holder.deleteLater()

    def _refresh(self):
        fields = self._fields()
        clash = pctl.key_clashes(fields, self._taken)
        for action, warns in self._warnings.items():
            for n, warn in enumerate(warns):
                self._show_clash(warn, fields[action][n], clash.get((action, n)))

    def _show_clash(self, warn: QLabel, key: str, other: str | None):
        if other is None:
            warn.setText("")
            warn.setToolTip("")
        elif key in pctl.RESERVED_KEYS or key in self._taken:
            # What the app does with it, in the cheat sheet's words.
            warn.setText("%s: %s" % (i18n.t("⚠ The app uses this key"),
                                     i18n.t(other)))
            warn.setToolTip(i18n.t(other))
        else:
            warn.setText(i18n.t("⚠ Also on %s — that one keeps it")
                         % i18n.t(other))
            warn.setToolTip("")
