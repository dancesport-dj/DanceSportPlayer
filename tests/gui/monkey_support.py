#!/usr/bin/env python3
"""What the GUI monkeys and the click-through scenarios share.

The random monkeys (tests/gui/test_monkey.py) and the operator's scripted
paths through the manual (tests/gui/test_click_*.py) both drive a real
MainWindow built on a small library of silent MP3s, inside a sandbox that
answers every way out of the process (see LoadedWindow._sandbox). Not a test
module itself: nothing here is collected.
"""

import os
import random
import subprocess
import sys
import tempfile
import threading
import traceback
import unittest
import urllib.error
import urllib.request
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_monkey_"))

import numpy as np
import shiboken6
from PySide6.QtCore import (
    QAbstractListModel, QEvent, QPoint, QPointF, QProcess, Qt, QTimer)
from PySide6.QtGui import (
    QColor, QContextMenuEvent, QDesktopServices, QDrag, QDropEvent, QKeyEvent,
    QShortcut)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton, QAbstractItemView, QAbstractScrollArea, QAbstractSlider,
    QAbstractSpinBox, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog,
    QDoubleSpinBox, QFileDialog, QInputDialog, QLineEdit, QMenu, QMessageBox,
    QScrollBar, QSpinBox, QStyle, QStyleOptionButton, QTabBar, QWidget)
from planner.music.analysis import AudioFeatures
from shared.columns import _COL_PLAY, _COL_TITLE
from tests.qt_test_support import reap_widget

STEPS = int(os.environ.get("DANCEPLAYLIST_MONKEY_STEPS", "150"))
SEED = int(os.environ.get("DANCEPLAYLIST_MONKEY_SEED", "20261011"))
TRACE = bool(os.environ.get("DANCEPLAYLIST_MONKEY_TRACE"))

# Clicks a dialog gets before the monkey closes it.
_CLICKS_PER_DIALOG = 4

# What gets typed into a text field: the empty string, a real word, umlauts,
# an emoji, quoting, a number, and something far too long.
_TEXTS = ("", "Tango", "Ägäis Öl ß", "🎵 Samba", "it's \"quoted\"", "-1",
          "x" * 300)

# Standard dance, BPM — enough for every generator to find a round.
_DANCES = (("LW", 29), ("TG", 31), ("WW", 58), ("SF", 28), ("QS", 50),
           ("SB", 50), ("CC", 30), ("RB", 24), ("PD", 60), ("JV", 42))

_MP3_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 413   # 128 kbit/s, 44.1 kHz, silent


def _silent_mp3(path: Path, seconds: int) -> None:
    """A real, parseable, silent MP3 — so playback goes through the real
    player without making a sound on the machine running the suite."""
    path.write_bytes(_MP3_FRAME * (seconds * 44100 // 1152))


def _output_dir_modules():
    """Every module holding its own copy of planner.config.OUTPUT_DIR."""
    import gui.window.main_export
    import gui.window.main_import
    import gui.window.main_print
    import planner.playlist.m3u
    return [planner.playlist.m3u, gui.window.main_export, gui.window.main_import, gui.window.main_print]


def printable(text: str) -> str:
    """Widget text for the report. Labels are full of emoji and the console
    the suite reports to is cp1252."""
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


def describe(w) -> str:
    text = ""
    for getter in ("text", "windowTitle", "accessibleName", "toolTip"):
        fn = getattr(w, getter, None)
        if callable(fn):
            try:
                text = fn()
            except TypeError:
                continue
            if text:
                break
    name = w.objectName() if hasattr(w, "objectName") else ""
    return printable(f"{type(w).__name__}"
                  f"{'#' + name if name else ''} '{str(text)[:40]}'")


class Monkey:
    """Picks and works random controls; answers and closes the dialogs those
    open. Every choice comes from one seeded generator."""

    def __init__(self, seed: int, roots, dialog_clicks: int = _CLICKS_PER_DIALOG):
        self.rng = random.Random(seed)
        self.roots = roots          # callable → the windows the monkey may touch
        self.dialog_clicks = dialog_clicks
        self.log: deque[str] = deque(maxlen=25)
        self.step = 0
        self._timer = QTimer()
        self._timer.setInterval(15)
        self._timer.timeout.connect(self._tick)

    def note(self, what: str) -> None:
        line = f"[{self.step}] {what}"
        self.log.append(line)
        if TRACE:
            print(line, file=sys.stderr, flush=True)

    # ── the modal / popup watchdog ──────────────────────────────────────────
    # A modal dialog or a popup menu runs its own event loop, so the step that
    # opened it does not return until it is closed. This timer keeps firing
    # inside that loop. It never does the work itself — a click can open the
    # next dialog and block, and Qt does not re-fire a timer whose handler is
    # still running — it only schedules the work, one at a time per widget.

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _tick(self):
        top = QApplication.activePopupWidget() or QApplication.activeModalWidget()
        if top is None or top.property("monkey_busy"):
            return
        top.setProperty("monkey_busy", True)
        QTimer.singleShot(0, lambda w=top: self._handle(w))

    def _handle(self, w):
        try:
            if not shiboken6.isValid(w) or not w.isVisible():
                return
            if isinstance(w, QMenu):
                self._pick_from_menu(w)
                return
            n = w.property("monkey_clicks") or 0
            w.setProperty("monkey_clicks", n + 1)
            # Never click around in a file dialog: its "Save" writes for real.
            if (n < self.dialog_clicks and not isinstance(w, QFileDialog)
                    and self.rng.random() < 0.8):
                self.act_on(self.rng_target([w]), inside=describe(w))
                return
            self.note(f"close {describe(w)}")
            if isinstance(w, QDialog):
                w.reject()
            else:
                w.close()
            if shiboken6.isValid(w) and w.isVisible() and n > self.dialog_clicks + 3:
                w.hide()        # refused to close: ends its exec() loop anyway
        finally:
            if shiboken6.isValid(w):
                w.setProperty("monkey_busy", False)

    def _pick_from_menu(self, menu: QMenu):
        acts = [a for a in menu.actions()
                if a.isEnabled() and a.isVisible() and not a.isSeparator()
                and a.menu() is None]
        if not acts or self.rng.random() < 0.15:
            self.note(f"dismiss menu {describe(menu)}")
            menu.close()
            return
        act = self.rng.choice(acts)
        self.note(f"menu item '{printable(act.text())}'")
        # Return on the active action, not act.trigger(): a menu shown with
        # exec() hands back the chosen action, and that is what the caller
        # checks.
        menu.setActiveAction(act)
        QTest.keyClick(menu, Qt.Key.Key_Return)

    # ── choosing ────────────────────────────────────────────────────────────

    def targets(self, roots):
        out = []
        for root in roots:
            for w in [root, *root.findChildren(QWidget)]:
                if not (w.isVisible() and w.isEnabled()):
                    continue
                if isinstance(w, QAbstractButton):
                    out.append(("click", w))
                elif isinstance(w, QComboBox) and w.count() > 1:
                    out.append(("combo", w))
                elif isinstance(w, QTabBar) and w.count() > 1:
                    out.append(("tab", w))
                elif isinstance(w, QAbstractSlider) and not isinstance(w, QScrollBar):
                    out.append(("slide", w))
                elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                    out.append(("spin", w))
                elif (isinstance(w, QLineEdit) and not w.isReadOnly()
                      and not isinstance(w.parent(), (QComboBox, QAbstractSpinBox))):
                    out.append(("type", w))
                elif (isinstance(w, QAbstractItemView) and w.model() is not None
                      and w.model().rowCount() > 0):
                    out.append(("cell", w))
            menubar = getattr(root, "menuBar", None)
            if callable(menubar) and root.menuBar() is not None:
                out.extend(("action", a) for a in self._leaf_actions(root.menuBar()))
            for sc in root.findChildren(QShortcut):
                parent = sc.parent()
                if sc.isEnabled() and isinstance(parent, QWidget) and parent.isVisible():
                    out.append(("shortcut", sc))
        return out

    def _leaf_actions(self, owner):
        for a in owner.actions():
            if not (a.isEnabled() and a.isVisible()) or a.isSeparator():
                continue
            if a.menu() is not None:
                yield from self._leaf_actions(a.menu())
            else:
                yield a

    def rng_target(self, roots):
        found = self.targets(roots)
        return self.rng.choice(found) if found else None

    # ── acting ──────────────────────────────────────────────────────────────

    def act_on(self, target, inside: str = "") -> None:
        if target is None:
            return
        kind, w = target
        where = f" in {inside}" if inside else ""
        rng = self.rng
        if kind == "click":
            if rng.random() < 0.08:
                self._context_menu(w, w.rect().center(), where)
                return
            self.note(f"click {describe(w)}{where}")
            QTest.mouseClick(w, Qt.MouseButton.LeftButton)
        elif kind == "combo":
            i = rng.randrange(w.count())
            self.note(f"combo {describe(w)} -> {i} '{printable(w.itemText(i))}'{where}")
            w.setCurrentIndex(i)
        elif kind == "tab":
            i = rng.randrange(w.count())
            self.note(f"tab {printable(w.tabText(i))!r}{where}")
            w.setCurrentIndex(i)
        elif kind == "slide":
            v = rng.randint(w.minimum(), w.maximum())
            self.note(f"slide {describe(w)} -> {v}{where}")
            w.setSliderDown(True)
            w.setValue(v)
            w.setSliderDown(False)
        elif kind == "spin":
            lo, hi = w.minimum(), w.maximum()
            v = rng.choice((lo, hi, rng.uniform(lo, hi)))
            v = int(v) if isinstance(w, QSpinBox) else v
            self.note(f"spin {describe(w)} -> {v}{where}")
            w.setValue(v)
        elif kind == "type":
            text = rng.choice(_TEXTS)
            self.note(f"type {text[:20]!r} into {describe(w)}{where}")
            w.selectAll()
            QTest.keyClick(w, Qt.Key.Key_Delete)
            # Not QTest.keyClicks: it asserts (and aborts the process) on any
            # character outside ASCII. A key event carrying the text is also
            # how an umlaut arrives from a real keyboard.
            for ch in text:
                QApplication.sendEvent(w, QKeyEvent(
                    QEvent.Type.KeyPress, Qt.Key.Key_unknown,
                    Qt.KeyboardModifier.NoModifier, ch))
            QTest.keyClick(w, Qt.Key.Key_Return)
        elif kind == "cell":
            self._click_cell(w, where)
        elif kind == "action":
            self.note(f"menu-bar action '{printable(w.text())}'")
            w.trigger()
        elif kind == "shortcut":
            self.note(f"shortcut {printable(w.key().toString())}")
            w.activated.emit()

    def _click_cell(self, view, where):
        model = view.model()
        root = view.rootIndex()
        rows = model.rowCount(root)
        # A list model keeps columnCount private in PySide: one column.
        cols = (1 if isinstance(model, QAbstractListModel)
                else max(1, model.columnCount(root)))
        idx = model.index(self.rng.randrange(rows), self.rng.randrange(cols), root)
        rect = view.visualRect(idx)
        if not rect.isValid() or not view.viewport().rect().intersects(rect):
            view.scrollTo(idx, QAbstractItemView.ScrollHint.EnsureVisible)
            rect = view.visualRect(idx)
        pos = rect.center()
        roll = self.rng.random()
        if roll < 0.15:
            self._context_menu(view, pos, where, cell=(idx.row(), idx.column()))
        elif roll < 0.35:
            self.note(f"double-click {describe(view)} cell "
                      f"({idx.row()},{idx.column()}){where}")
            QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton,
                              Qt.KeyboardModifier.NoModifier, pos)
        else:
            self.note(f"click {describe(view)} cell "
                      f"({idx.row()},{idx.column()}){where}")
            QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier, pos)

    def _context_menu(self, w, pos: QPoint, where, cell=None):
        """Right-click. QTest sends no QContextMenuEvent, and a scroll area
        only takes one on its viewport (Testing Practices: header menus)."""
        target = w.viewport() if isinstance(w, QAbstractScrollArea) else w
        at = f" cell {cell}" if cell else ""
        self.note(f"right-click {describe(w)}{at}{where}")
        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos,
                               target.mapToGlobal(pos))
        QApplication.sendEvent(target, ev)


class ExceptionTrap:
    """Collects exceptions that escape into Qt's event loop — from slots,
    event handlers and worker threads — instead of letting them print and
    vanish."""

    def __init__(self, monkey: Monkey):
        self.monkey = monkey
        self.caught: list[str] = []

    def __enter__(self):
        self._hook, self._thook = sys.excepthook, threading.excepthook
        sys.excepthook = self._on_exc
        threading.excepthook = lambda a: self._on_exc(
            a.exc_type, a.exc_value, a.exc_traceback)
        return self

    def __exit__(self, *_exc):
        sys.excepthook, threading.excepthook = self._hook, self._thook

    def _on_exc(self, etype, value, tb):
        trail = "\n".join(self.monkey.log)
        self.caught.append(
            f"step {self.monkey.step}, last actions:\n{trail}\n"
            + printable("".join(traceback.format_exception(etype, value, tb))))
        if TRACE:
            print(self.caught[-1], file=sys.stderr, flush=True)


class LoadedWindow(unittest.TestCase):
    """A real MainWindow on the silent library, inside the sandbox."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = Path(tempfile.mkdtemp(prefix="dp_monkey_files_"))
        music = cls.tmp / "music"
        for i, (dance, bpm) in enumerate(_DANCES * 3):
            # The planner draws a style only from its own folder (STYLE_FOLDERS).
            folder = music / ("StandardCD" if dance in "LW TG WW SF QS" else "LateinCD")
            folder.mkdir(parents=True, exist_ok=True)
            # A length of its own: two silent files of one length are the same
            # audio, and an import keeps only the last copy (♊ duplicate titles).
            _silent_mp3(folder / f"Song {i:02d} ({dance} {bpm}).mp3", 20 + i)
        out = cls.tmp / "out"
        out.mkdir()
        cls.settings = {
            "library_dir": str(music), "global_dir": str(music),
            "save_dir": str(out), "playlist_dir": str(out),
            "import_dir": str(out), "open_dir": str(out),
            "language": "en", "mute_system_sounds": False,
        }
        cls._sandbox()

    @classmethod
    def _sandbox(cls):
        """Everything a click can reach outside this process, answered from
        here. Started once for the class, stopped after it."""
        import dancesport_gui
        import gui.window.main_global
        import shared.error_reports
        import shared.remote.remote_server

        def refuse(*_a, **_kw):
            raise FileNotFoundError("monkey test: no child processes")

        def network_down(*_a, **_kw):
            raise urllib.error.URLError("monkey test: network is down")

        def no_sockets(_server):
            raise OSError("monkey test: no sockets")

        def boxes(default):
            """A QMessageBox static: picks one of the buttons it offers."""
            def answer(*a, **kw):
                offered = kw.get("buttons", a[3] if len(a) > 3 else default)
                options = [b for b in QMessageBox.StandardButton
                           if b.value and (offered & b) == b]
                return cls.answers.choice(options or [default])
            return staticmethod(answer)

        sb = QMessageBox.StandardButton
        patches = [
            (dancesport_gui, "load_settings",
             staticmethod(lambda *_a, **_kw: dict(cls.settings))),
            (gui.window.main_global, "apply_taskbar_icon", lambda _win: None),
            (QMessageBox, "question", boxes(sb.Yes | sb.No)),
            (QMessageBox, "warning", boxes(sb.Ok)),
            (QMessageBox, "information", boxes(sb.Ok)),
            (QMessageBox, "critical", boxes(sb.Ok)),
            (QMessageBox, "about", staticmethod(lambda *_a, **_kw: None)),
            (QFileDialog, "getOpenFileName", staticmethod(lambda *_a, **_kw: ("", ""))),
            (QFileDialog, "getOpenFileNames", staticmethod(lambda *_a, **_kw: ([], ""))),
            (QFileDialog, "getSaveFileName", staticmethod(lambda *_a, **_kw: ("", ""))),
            (QFileDialog, "getExistingDirectory", staticmethod(lambda *_a, **_kw: "")),
            (QInputDialog, "getText", staticmethod(lambda *_a, **_kw: ("", False))),
            (QColorDialog, "getColor", staticmethod(lambda *_a, **_kw: QColor())),
            (QDesktopServices, "openUrl", staticmethod(lambda *_a, **_kw: False)),
            (QProcess, "startDetached", staticmethod(lambda *_a, **_kw: False)),
            (QApplication, "quit", staticmethod(lambda *_a, **_kw: None)),
            (subprocess, "Popen", refuse),
            (subprocess, "run", refuse),
            (urllib.request, "urlopen", network_down),
            (shared.remote.remote_server.RemoteServer, "start", no_sockets),
            # Ticking 🐞 Send error reports in ⚙ Settings must not start Sentry.
            (shared.error_reports, "available", lambda: False),
        ]
        if hasattr(os, "startfile"):
            patches.append((os, "startfile", refuse))
        # 💾 Save all, 🖨 Print and the wishlist export write into the output
        # folder without a dialog — the repo's playlists/ unless redirected.
        patches += [(module, "OUTPUT_DIR", cls.tmp / "out")
                    for module in _output_dir_modules()]
        cls.answers = random.Random(SEED)
        for owner, name, value in patches:
            p = mock.patch.object(owner, name, value)
            p.start()
            cls.addClassCleanup(p.stop)
        cls.gui = dancesport_gui

    def setUp(self):
        self._before = set(QApplication.topLevelWidgets())
        self.win = self.gui.MainWindow()
        self.addCleanup(self._reap_all)
        self._wait_until_loaded()
        self.win.resize(1500, 900)

    def _wait_until_loaded(self):
        """The real LibraryLoader scans the silent library in its thread; the
        window shows once it has, and enables Generate a few deferred steps
        later."""
        for _ in range(3000):
            QTest.qWait(10)
            if (self.win.isVisible() and not self.win._loading_dlg.isVisible()
                    and self.win._cfg.generate_btn.isEnabled()):
                return
        self.fail("the window never finished loading the test library")

    def _reap_all(self):
        """The window first, then whatever the walk left open on screen. Not
        the hidden parentless widgets: the window keeps those (and uses them
        in its closeEvent), and some are module-level singletons later tests
        still need."""
        left_open = [w for w in self._roots() if w is not self.win]
        # A ▶ leaves a 2 s playback watchdog behind (a bare singleShot that
        # outlives the window). A new token makes it no-op, as it does when the
        # operator moves on; else it fires in the next test on a dead player.
        self.win._playback.token += 1
        reap_widget(self.win)
        for w in left_open:
            reap_widget(w)

    def _roots(self):
        """The main window and every window it opened. Not windows other
        test modules left behind in this process."""
        return [w for w in QApplication.topLevelWidgets()
                if w.isVisible() and w not in self._before
                and not isinstance(w, QMenu)
                and w.windowType() != Qt.WindowType.ToolTip]


class DropFrom(QDropEvent):
    """The drop of a drag that started in `source`. A real QDrag delivers it
    from inside its own loop, which QTest cannot drive."""

    def __init__(self, pos: QPointF, mime, source,
                 mods=Qt.KeyboardModifier.NoModifier):
        super().__init__(pos, Qt.DropAction.CopyAction, mime,
                         Qt.MouseButton.LeftButton, mods)
        self._source = source

    def source(self):
        return self._source


class _FirstOffered:
    """Answers every message box with the first button it offers: Yes
    before No, so a confirm goes through."""

    def choice(self, options):
        return options[0]


def _action(menu: QMenu, prefix: str):
    return next((a for a in menu.actions()
                 if a.isEnabled() and a.text().startswith(prefix)), None)


class Operator(Monkey):
    """Works the dialogs and menus a scenario scripted, and closes every other
    one the moment it opens (a monkey with no clicks to spare).

    `pick(prefix)` chooses the item of the next popup menu that offers it;
    `answer(match, act)` hands the next modal window `match` accepts to `act`.
    Each script line answers one window, in any order."""

    def __init__(self, roots):
        super().__init__(SEED, roots, dialog_clicks=0)
        self.script: list = []
        self.opened: list[str] = []

    def answer(self, match, act):
        self.script.append((match, act))

    def pick(self, prefix: str):
        def act(menu):
            self.note(f"menu item '{printable(prefix)}'")
            menu.setActiveAction(_action(menu, prefix))
            QTest.keyClick(menu, Qt.Key.Key_Return)
        self.answer(lambda w: isinstance(w, QMenu) and _action(w, prefix) is not None,
                    act)

    def _handle(self, w):
        if not (shiboken6.isValid(w) and w.isVisible()):
            return super()._handle(w)
        if not w.property("operator_seen"):
            w.setProperty("operator_seen", True)
            self.opened.append(describe(w))
        for i, (match, act) in enumerate(self.script):
            if match(w):
                del self.script[i]
                try:
                    act(w)
                finally:
                    if shiboken6.isValid(w):
                        w.setProperty("monkey_busy", False)
                return
        from gui.common import BusyDialog
        if isinstance(w, BusyDialog):
            # A progress window asks nothing: the operator waits for it. Its
            # reject() is Cancel — closing it aborted a check that only ran
            # past the 250 ms show delay on a loaded machine.
            return
        super()._handle(w)


class ClickThrough(LoadedWindow):
    """The operator's paths through the manual (docs/manual-planner), clicked
    in order: what the random walk only hits by luck. Each one checks what the
    manual promises, not only that nothing raised. The scenarios live one
    chapter to a module, tests/gui/test_click_<chapter>_*.py."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.answers = _FirstOffered()

    def setUp(self):
        # A scenario starts from a clean desk: its own state dir (autosave,
        # deck modes) and its own output folder. A playlist an earlier scenario
        # saved there counts towards popularity and steers the next draw.
        self.out = Path(tempfile.mkdtemp(prefix="dp_click_out_"))
        state = tempfile.mkdtemp(prefix="dp_click_state_")
        dirs = {k: str(self.out) for k in
                ("save_dir", "playlist_dir", "import_dir", "open_dir")}
        for p in (mock.patch.dict(os.environ, {"DANCEPLAYLIST_STATE_DIR": state}),
                  mock.patch.dict(self.settings, dirs),
                  *(mock.patch.object(m, "OUTPUT_DIR", self.out)
                    for m in _output_dir_modules())):
            p.start()
            self.addCleanup(p.stop)
        super().setUp()

    # ── driving ─────────────────────────────────────────────────────────────

    @contextmanager
    def clicking(self):
        op = Operator(self._roots)
        with ExceptionTrap(op) as trap:
            # A handler that catches its own exception shows it in a critical
            # box: as much a failure as a traceback.
            def critical(_parent, title, text, *_a, **_kw):
                trap.caught.append(printable(f"critical box '{title}': {text}"))
                return QMessageBox.StandardButton.Ok
            op.start()
            try:
                with mock.patch.object(QMessageBox, "critical", critical):
                    yield op
            finally:
                op.stop()
        if trap.caught:
            self.fail("an exception escaped:\n\n" + "\n\n".join(trap.caught))
        self.assertEqual(op.script, [], "a scripted dialog or menu never opened")

    def click(self, button):
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        QTest.qWait(5)

    def tick(self, box: QCheckBox):
        """On the box itself: a check box stretched across its row takes no
        click in the empty space right of its label."""
        opt = QStyleOptionButton()
        box.initStyleOption(opt)
        rect = box.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, opt, box)
        QTest.mouseClick(box, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, rect.center())
        QTest.qWait(5)

    def key(self, key, mods=Qt.KeyboardModifier.NoModifier, widget=None):
        QTest.keyClick(widget or self.win._deckset.table, key, mods)
        QTest.qWait(5)

    def type_into(self, edit: QLineEdit, text: str):
        edit.setFocus()
        edit.selectAll()
        QTest.keyClicks(edit, text)      # ASCII only, see Monkey.act_on
        QTest.keyClick(edit, Qt.Key.Key_Return)
        QTest.qWait(5)

    def wait_until(self, cond, ms: int = 3000) -> bool:
        for _ in range(ms // 10):
            if cond():
                return True
            QTest.qWait(10)
        return cond()

    def cell_pos(self, table, row: int, col: int) -> QPoint:
        idx = table.model().index(row, col)
        table.scrollTo(idx)
        return table.visualRect(idx).center()

    def click_cell(self, table, row: int, col: int, double=False):
        click = QTest.mouseDClick if double else QTest.mouseClick
        click(table.viewport(), Qt.MouseButton.LeftButton,
              Qt.KeyboardModifier.NoModifier, self.cell_pos(table, row, col))
        QTest.qWait(5)

    def drag(self, src, row: int, dst, dst_row: int | None = None,
             mods=Qt.KeyboardModifier.NoModifier):
        """Drag `row` of `src` onto `dst_row` of `dst` (below its last row
        when None), `mods` held at the drop. The table's own startDrag builds
        the drag; only the drop is handed over, at the spot a real QDrag would
        release it."""
        src.selectRow(row)
        if dst_row is not None:
            dst.scrollTo(dst.model().index(dst_row, _COL_TITLE))

        def release(drag, *_a, **_kw):
            y = (dst.rowViewportPosition(dst_row) + dst.rowHeight(dst_row) // 2
                 if dst_row is not None else dst.viewport().height() - 2)
            dst.dropEvent(DropFrom(QPointF(20, y), drag.mimeData(), drag.source(), mods))
            return Qt.DropAction.CopyAction
        with mock.patch.object(QDrag, "exec", release):
            src.startDrag(Qt.DropAction.CopyAction)
        QTest.qWait(5)

    def restart(self):
        """Quit and start again: the window closes as the operator closes
        it, and a new one restores the session it left behind."""
        old = self.win
        old._playback.token += 1
        old.close()
        reap_widget(old)
        self.win = self.gui.MainWindow()
        self._wait_until_loaded()
        self.win.resize(1500, 900)

    def right_click(self, op: Operator, table, row: int, col: int = _COL_TITLE):
        op._context_menu(table, self.cell_pos(table, row, col), "")
        QTest.qWait(5)

    def button(self, tooltip_start: str, root=None):
        found = [b for b in (root or self.win).findChildren(QAbstractButton)
                 if b.isVisible() and b.toolTip().startswith(tooltip_start)]
        self.assertTrue(found, f"no visible button '{printable(tooltip_start)}'")
        return found[0]

    toolbar_button = button

    # ── reading the deck ────────────────────────────────────────────────────

    def song_rows(self, table=None) -> list[int]:
        table = table or self.win._deckset.table
        return [r for r, m in enumerate(table._row_meta) if m and m.entry]

    def entry_at(self, row: int, table=None):
        return (table or self.win._deckset.table)._row_meta[row].entry

    def titles(self, table=None) -> list[str]:
        table = table or self.win._deckset.table
        return [m.entry.title for m in table._row_meta if m and m.entry]

    def generate(self, rounds: str | None = None):
        if rounds is not None:
            self.type_into(self.win._cfg.rounds_edit, rounds)
        self.click(self.win._cfg.generate_btn)
        self.assertGreater(self.win._deckset.table.rowCount(), 0, "Generate filled no deck")

    def analysed(self):
        """Every title gets the same audio features: the silent library cannot
        be analysed here (no child processes), and Find similar and the
        replacement picker list only analysed titles."""
        feats = AudioFeatures(bpm=120.0, mfcc=np.zeros(84, dtype=np.float32),
                              centroid=1500.0, rms=0.1)
        for e in self.win._library.lib.entries:
            e.features = feats

    def play_row(self, row: int, table=None):
        table = table or self.win._deckset.table
        self.click_cell(table, row, _COL_PLAY)
        self.assertTrue(self.wait_until(lambda: table._current_play_row == row),
                        f"row {row} did not start")

    # ── used by several chapters ────────────────────────────────────────────

    def saved_files(self, pattern="*.m3u*"):
        return sorted(self.out.rglob(pattern), key=lambda p: p.stat().st_mtime)

    def titled(self, start: str):
        """Matches the window whose title starts with `start`."""
        return lambda w: (isinstance(w, QWidget) and not isinstance(w, QMenu)
                          and w.windowTitle().startswith(start))

    def import_list(self, path: Path):
        with mock.patch.object(QFileDialog, "getOpenFileNames",
                               lambda *_a, **_kw: ([str(path)], "")):
            self.click(self.win._cfg.import_btn)
