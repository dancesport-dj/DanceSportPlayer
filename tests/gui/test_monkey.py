#!/usr/bin/env python3
"""Monkey test: random clicks over the whole main window.

Run:  py -m unittest tests.gui.test_monkey -v
Long: set DANCEPLAYLIST_MONKEY_STEPS=2000 and DANCEPLAYLIST_MONKEY_SEED=<n>
      (DANCEPLAYLIST_MONKEY_TRACE=1 prints every action as it happens)

The unit tests drive one handler at a time, with the state that handler
expects. Nobody drives the window the way a hurried operator does: Playing
mode with no deck, the cartwall half open, a combo changed while a dialog sits
on top. This test does. It builds a real MainWindow on a small library of
silent MP3s, then for a fixed number of steps picks a random visible, enabled
control and works it — buttons, combos, tabs, sliders, spin boxes, text fields,
table cells, context menus, menu-bar actions, shortcuts. Every modal dialog and
popup menu that opens gets a few random clicks of its own and is then closed.

A step fails the test when an exception escapes into Qt's event loop (that is
a traceback the operator would see in the log and an action that half ran).
The run is seeded, so a failure names the seed and the actions that led up to
it, and the same seed replays the same walk.

Nothing leaves the sandbox: file dialogs answer "cancelled", Explorer, the
default player, URLs and child processes are refused (as if not installed),
the phone remote cannot bind, and the network is down. Settings, layout, the
DB and the music live in temp folders (see tests/__init__.py).

The scripted paths through the manual are tests/gui/test_click_*.py; what
both share is tests/gui/monkey_support.py.
"""

import time
import unittest

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import (
    ExceptionTrap, LoadedWindow, Monkey, SEED, STEPS, describe, printable)

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from shared.columns import _COL_PLAY


class MonkeyTest(LoadedWindow):

    def test_random_walk_raises_nothing(self):
        monkey = Monkey(SEED, self._roots)
        with ExceptionTrap(monkey) as trap:
            monkey.start()
            try:
                for monkey.step in range(STEPS):
                    if not self.win.isVisible():
                        monkey.note("main window was closed - showing it again")
                        self.win.show()
                    try:
                        monkey.act_on(monkey.rng_target(self._roots()))
                    except Exception as exc:          # raised straight out of a call
                        trap._on_exc(type(exc), exc, exc.__traceback__)
                    QTest.qWait(5)
                    if trap.caught:
                        break
            finally:
                monkey.stop()
        if trap.caught:
            self.fail(f"seed {SEED}: an exception escaped after "
                      f"{monkey.step + 1} steps (replay with "
                      f"DANCEPLAYLIST_MONKEY_SEED={SEED})\n\n"
                      + "\n\n".join(trap.caught))


_CTRL = Qt.KeyboardModifier.ControlModifier
_SHIFT = Qt.KeyboardModifier.ShiftModifier
_NONE = Qt.KeyboardModifier.NoModifier

# Every key of the cheat sheet (docs/manual-planner/07-shortcuts.md), plus the
# arrows and Return that move between and into rows.
_CHORDS = (
    (Qt.Key.Key_Space, _NONE), (Qt.Key.Key_Left, _CTRL), (Qt.Key.Key_Right, _CTRL),
    (Qt.Key.Key_Left, _CTRL | _SHIFT), (Qt.Key.Key_Right, _CTRL | _SHIFT),
    (Qt.Key.Key_R, _CTRL), (Qt.Key.Key_N, _CTRL), (Qt.Key.Key_S, _CTRL),
    (Qt.Key.Key_S, _CTRL | _SHIFT), (Qt.Key.Key_Z, _CTRL), (Qt.Key.Key_Y, _CTRL),
    (Qt.Key.Key_Z, _CTRL | _SHIFT), (Qt.Key.Key_X, _CTRL), (Qt.Key.Key_W, _CTRL),
    (Qt.Key.Key_Delete, _NONE), (Qt.Key.Key_Delete, _CTRL | _SHIFT),
    (Qt.Key.Key_Delete, _CTRL), (Qt.Key.Key_M, _CTRL), (Qt.Key.Key_1, _CTRL),
    (Qt.Key.Key_2, _CTRL), (Qt.Key.Key_A, _CTRL), (Qt.Key.Key_F, _CTRL),
    (Qt.Key.Key_F2, _NONE), (Qt.Key.Key_T, _NONE), (Qt.Key.Key_Escape, _NONE),
    (Qt.Key.Key_F1, _NONE), (Qt.Key.Key_Up, _NONE), (Qt.Key.Key_Down, _NONE),
    (Qt.Key.Key_Return, _NONE),
)


class _KeyMonkey(Monkey):
    """Presses the shortcuts on whatever list or window has the focus, with a
    mode switch or a fresh selection thrown in now and then. The dialogs the
    keys open are worked and closed by the watchdog, as for the click monkey."""

    def press(self, win):
        rng = self.rng
        roll = rng.random()
        if roll < 0.04:
            btn = rng.choice((win._mode_plan_btn, win._mode_play_btn))
            self.note(f"mode {describe(btn)}")
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            return
        lists = [t for t in (*win._deckset.decks, *win._deckset.wishlists, win._deckset.warmup_table)
                 if t.isVisible()]
        target = rng.choice(lists + [win]) if lists else win
        if roll < 0.2 and target is not win and target.rowCount():
            row = rng.randrange(target.rowCount())
            self.note(f"select row {row} of {describe(target)}")
            target.selectRow(row)
        key, mods = rng.choice(_CHORDS)
        self.note(f"key {printable(QKeySequence(key.value | mods.value).toString())}"
                  f" on {describe(target)}")
        target.setFocus()
        QTest.keyClick(target, key, mods)


def _settle(ms: int) -> None:
    """QTest.qWait, minus a hang: a qWait that is waiting when the player
    reaches EndOfMedia never returns (Qt 6.11, ffmpeg backend, Windows: its
    processEvents(WaitForMoreEvents) never wakes again). Ctrl+-> clamped to
    the duration does exactly that. A QEventLoop rides it out, as the app's
    own loop does."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class KeyboardMonkeyTest(LoadedWindow):

    def test_random_shortcuts_raise_nothing(self):
        monkey = _KeyMonkey(SEED, self._roots)
        win = self.win
        QTest.mouseClick(win._cfg.generate_btn, Qt.MouseButton.LeftButton)
        with ExceptionTrap(monkey) as trap:
            monkey.start()
            try:
                for monkey.step in range(STEPS):
                    if not win.isVisible():
                        monkey.note("main window was closed - showing it again")
                        win.show()
                    try:
                        monkey.press(win)
                    except Exception as exc:          # raised straight out of a call
                        trap._on_exc(type(exc), exc, exc.__traceback__)
                    _settle(5)
                    if trap.caught:
                        break
            finally:
                monkey.stop()
        if trap.caught:
            self.fail(f"seed {SEED}: an exception escaped after "
                      f"{monkey.step + 1} key presses (replay with "
                      f"DANCEPLAYLIST_MONKEY_SEED={SEED})\n\n"
                      + "\n\n".join(trap.caught))


class _StageMonkey(Monkey):
    """The click monkey on the ▶ Playing side while a title runs: it leaves
    the 📝 switch back to Planning alone, and whenever the music has stopped
    the next step starts a title of the deck again (a fresh draw first, when
    the walk emptied the deck)."""

    def __init__(self, seed: int, roots, win):
        super().__init__(seed, roots)
        self.win = win
        self.playing_steps = 0

    def targets(self, roots):
        return [t for t in super().targets(roots)
                if t[1] is not self.win._mode_plan_btn]

    def playing(self) -> bool:
        from PySide6.QtMultimedia import QMediaPlayer
        return self.win._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def keep_playing(self):
        win = self.win
        if self.playing():
            self.playing_steps += 1
            return
        table = win._deckset.table
        rows = [r for r, m in enumerate(table._row_meta) if m and m.entry]
        if not rows:
            self.note("deck empty - a fresh draw")
            QTest.mouseClick(win._mode_plan_btn, Qt.MouseButton.LeftButton)
            QTest.mouseClick(win._cfg.generate_btn, Qt.MouseButton.LeftButton)
            rows = [r for r, m in enumerate(table._row_meta) if m and m.entry]
        if not win._mode_play_btn.isChecked():
            self.note("back to Playing")
            QTest.mouseClick(win._mode_play_btn, Qt.MouseButton.LeftButton)
        if not rows or not table.isVisible():
            return
        row = self.rng.choice(rows)
        self.note(f"play row {row}")
        idx = table.model().index(row, _COL_PLAY)
        table.scrollTo(idx)
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, table.visualRect(idx).center())
        # A title starts asynchronously, and under the suite's 16 workers
        # PlayingState comes well after the click: acting at once would work a
        # deck that is still stopped. Wait for the music, as the operator does.
        deadline = time.monotonic() + 2
        while not self.playing() and time.monotonic() < deadline:
            _settle(10)
        if self.playing():
            self.playing_steps += 1


class PlayingMonkeyTest(LoadedWindow):

    def test_a_random_walk_while_the_music_plays_raises_nothing(self):
        win = self.win
        monkey = _StageMonkey(SEED, self._roots, win)
        QTest.mouseClick(win._cfg.generate_btn, Qt.MouseButton.LeftButton)
        with ExceptionTrap(monkey) as trap:
            monkey.start()
            try:
                for monkey.step in range(STEPS):
                    if not win.isVisible():
                        monkey.note("main window was closed - showing it again")
                        win.show()
                    try:
                        monkey.keep_playing()
                        _settle(5)
                        monkey.act_on(monkey.rng_target(self._roots()))
                    except Exception as exc:          # raised straight out of a call
                        trap._on_exc(type(exc), exc, exc.__traceback__)
                    _settle(5)
                    if trap.caught:
                        break
            finally:
                monkey.stop()
                win._on_stop_btn()
        if trap.caught:
            self.fail(f"seed {SEED}: an exception escaped after "
                      f"{monkey.step + 1} steps (replay with "
                      f"DANCEPLAYLIST_MONKEY_SEED={SEED})\n\n"
                      + "\n\n".join(trap.caught))
        # A walk the music sat out would only repeat the click monkey.
        self.assertGreater(monkey.playing_steps, STEPS // 3,
                           f"music ran in {monkey.playing_steps} of {STEPS} steps")


if __name__ == "__main__":
    unittest.main()
