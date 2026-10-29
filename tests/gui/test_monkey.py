#!/usr/bin/env python3
"""Monkey test: random clicks over the whole main window.

Run:  py -m unittest tests.gui.test_monkey -v
Long: set DANCEPLAYLIST_MONKEY_STEPS=2000 and DANCEPLAYLIST_MONKEY_SEED=<n>
      (DANCEPLAYLIST_MONKEY_DIALOG_CLICKS=15 works the dialogs deeper)
      (DANCEPLAYLIST_MONKEY_TRACE=1 prints every action as it happens)
Nightly: .github/workflows/monkey-nightly.yml walks four seeds long and deep.

The unit tests drive one handler at a time, with the state that handler
expects. Nobody drives the window the way a hurried operator does: Playing
mode with no deck, the cartwall half open, a combo changed while a dialog sits
on top. This test does. It builds a real MainWindow on a small library of
silent MP3s, then for a fixed number of steps picks a random visible, enabled
control and works it — buttons, combos, tabs, sliders, spin boxes, text fields,
table cells, drags onto the playlists, context menus, shortcuts.
PlayerOnlyMonkeyTest does the same on the DanceSport Player build, with a
Party list loaded. Every modal dialog and popup menu that opens gets a few
random clicks of its own and is then closed.

A step fails the test when an exception escapes into Qt's event loop (that is
a traceback the operator would see in the log and an action that half ran),
or when a critical message box opens (a handler that caught its own error),
or when a list shows more or fewer rows than it keeps records for. At the end
every dialog must have closed and every state file must still read (see
LoadedWindow.check_step and _check_end).
The run is seeded, so a failure names the seed and the actions that led up to
it, and the same seed replays the same walk. The seed is the date unless
DANCEPLAYLIST_MONKEY_SEED sets one: a new walk each day, the same all day.

Nothing leaves the sandbox: file dialogs answer "cancelled", Explorer, the
default player, URLs and child processes are refused (as if not installed),
the phone remote and the guest requests cannot bind, and no socket reaches
past this machine (tests/gui/test_monkey_sandbox.py holds that). Settings,
layout, the DB and the music live in temp folders (see tests/__init__.py).

The scripted paths through the manual are tests/gui/test_click_*.py; what
both share is tests/gui/monkey_support.py.
"""

import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest

from shared.columns import _COL_PLAY

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import SEED, STEPS, DropFrom, LoadedWindow, Monkey, describe, printable, settle


class MonkeyTest(LoadedWindow):

    def test_random_walk_raises_nothing(self):
        monkey = Monkey(SEED, self._roots)
        with self.walking(monkey) as trap:
            for monkey.step in range(STEPS):
                if not self.win.isVisible():
                    monkey.note("main window was closed - showing it again")
                    self.win.show()
                try:
                    monkey.act_on(monkey.rng_target(self._roots()))
                except Exception as exc:          # raised straight out of a call
                    trap._on_exc(type(exc), exc, exc.__traceback__)
                QTest.qWait(5)
                self.check_step(trap)
                if trap.caught:
                    break


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


class KeyboardMonkeyTest(LoadedWindow):

    def test_random_shortcuts_raise_nothing(self):
        monkey = _KeyMonkey(SEED, self._roots)
        win = self.win
        QTest.mouseClick(win._cfg.generate_btn, Qt.MouseButton.LeftButton)
        with self.walking(monkey, "key presses") as trap:
            for monkey.step in range(STEPS):
                if not win.isVisible():
                    monkey.note("main window was closed - showing it again")
                    win.show()
                try:
                    monkey.press(win)
                except Exception as exc:          # raised straight out of a call
                    trap._on_exc(type(exc), exc, exc.__traceback__)
                settle(5)
                self.check_step(trap)
                if trap.caught:
                    break


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
            settle(10)
        if self.playing():
            self.playing_steps += 1


class PlayingMonkeyTest(LoadedWindow):

    def test_a_random_walk_while_the_music_plays_raises_nothing(self):
        win = self.win
        monkey = _StageMonkey(SEED, self._roots, win)
        QTest.mouseClick(win._cfg.generate_btn, Qt.MouseButton.LeftButton)
        with self.walking(monkey) as trap:
            try:
                for monkey.step in range(STEPS):
                    if not win.isVisible():
                        monkey.note("main window was closed - showing it again")
                        win.show()
                    try:
                        monkey.keep_playing()
                        settle(5)
                        monkey.act_on(monkey.rng_target(self._roots()))
                    except Exception as exc:          # raised straight out of a call
                        trap._on_exc(type(exc), exc, exc.__traceback__)
                    settle(5)
                    self.check_step(trap)
                    if trap.caught:
                        break
            finally:
                win._on_stop_btn()
        # A walk the music sat out would only repeat the click monkey.
        self.assertGreater(monkey.playing_steps, STEPS // 3,
                           f"music ran in {monkey.playing_steps} of {STEPS} steps")


class PlayerOnlyMonkeyTest(LoadedWindow):
    """The click monkey on DanceSport Player, the build that runs the
    evening: no decks and no planning, the Party list armed with a few titles
    (as a venue loads its .m3u), the library open."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import planner.config
        from gui.dialogs import PLAYER_FIRST_START
        # The first start, as ensure_app_mode leaves it (chapter 14).
        cls.settings.update({"app_mode": "player", PLAYER_FIRST_START: True})
        p = mock.patch.object(planner.config, "build_flavor", lambda: "player")
        p.start()
        cls.addClassCleanup(p.stop)

    def test_a_random_walk_on_the_player_build_raises_nothing(self):
        from PySide6.QtCore import QMimeData, QPointF, QUrl
        win = self.win
        self.assertTrue(win.windowTitle().startswith("DanceSport Player"),
                        printable(win.windowTitle()))
        music = sorted(Path(self.settings["library_dir"]).rglob("*.mp3"))[:6]
        out = Path(tempfile.mkdtemp(prefix="monkey_player_"))
        self.addCleanup(shutil.rmtree, out, True)
        m3u = out / "Party.m3u"
        m3u.write_text("\n".join(["#EXTM3U", *map(str, music)]) + "\n", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(m3u))])
        party = win._deckset.warmup_table
        party.dropEvent(DropFrom(QPointF(20, 20), mime, None))

        def loaded():
            return sum(1 for m in party._row_meta if m and m.entry)
        deadline = time.monotonic() + 3
        while loaded() < len(music) and time.monotonic() < deadline:
            settle(10)
        self.assertEqual(loaded(), len(music), "the .m3u did not load into the Party list")
        monkey = Monkey(SEED, self._roots)
        with self.walking(monkey) as trap:
            try:
                for monkey.step in range(STEPS):
                    if not win.isVisible():
                        monkey.note("main window was closed - showing it again")
                        win.show()
                    try:
                        monkey.act_on(monkey.rng_target(self._roots()))
                    except Exception as exc:          # raised straight out of a call
                        trap._on_exc(type(exc), exc, exc.__traceback__)
                    settle(5)
                    self.check_step(trap)
                    if trap.caught:
                        break
            finally:
                win._on_stop_btn()


if __name__ == "__main__":
    unittest.main()
