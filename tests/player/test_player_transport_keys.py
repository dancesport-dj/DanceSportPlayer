#!/usr/bin/env python3
"""Tests for reaching the transport from the keyboard — and for NOT reaching
the faders with the mouse wheel.

Run:  py -m unittest tests.player.test_player_transport_keys -v

Two halves of the same complaint: at the desk the hands are on the deck, not on
the player card. Ctrl+Shift+←/→ steps to the previous / next title from wherever
the focus happens to be, and a wheel notch that was meant to scroll a list no
longer moves the volume, the tempo or the position of a song playing to a hall.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_keys_"))

from pathlib import Path  # noqa: E402

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from player import player as gui_player  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class _WindowTest(unittest.TestCase):
    """A real MainWindow in Playing mode — the desk as the operator has it."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_keys_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.win.show()
        self.app.processEvents()
        self.win._set_play_mode(True)
        self.app.processEvents()
        self.card = self.win._big_player


class TransportShortcutTest(_WindowTest):
    """Ctrl+Shift+← / → — the ⏮ / ⏭ of the card, from anywhere in the window."""

    def setUp(self):
        super().setUp()
        self.stepped = []
        self.win._preview_skip = self.stepped.append   # where both ⏮/⏭ end up

    def test_they_are_the_keys_the_cheat_sheet_promises(self):
        self.assertEqual(self.win._next_sc.key(),
                         QKeySequence("Ctrl+Shift+Right"))
        self.assertEqual(self.win._prev_sc.key(),
                         QKeySequence("Ctrl+Shift+Left"))

    def test_they_do_not_collide_with_seeking_inside_the_song(self):
        """Ctrl+←/→ belongs to the deck (seek ∓30 s) and must stay untouched."""
        for sc in (self.win._next_sc, self.win._prev_sc):
            self.assertNotIn(sc.key(), (QKeySequence("Ctrl+Right"),
                                        QKeySequence("Ctrl+Left")))

    def test_forward_steps_to_the_next_title(self):
        self.win._next_sc.activated.emit()
        self.assertEqual(self.stepped, [+1])

    def test_back_steps_to_the_previous_title(self):
        self.win._prev_sc.activated.emit()
        self.assertEqual(self.stepped, [-1])

    def test_forward_during_a_pause_ends_the_pause_instead(self):
        """The ⏭ path is the card's, not a shortcut of its own: while the
        auto-advance pause runs it fires the queued song rather than stepping
        the deck a second time (which would skip a title outright)."""
        fired = []
        self.win._fire_pending_advance = lambda: fired.append(True)
        self.win._between.pending = (self.win._tableA, 0, Path("x.mp3"))
        self.win._filler.active = False   # nothing audible to fade first
        self.win._next_sc.activated.emit()
        self.assertEqual(fired, [True])
        self.assertEqual(self.stepped, [], "the deck was stepped as well")


class HeldKeyTest(_WindowTest):
    """A key held a moment too long must not fire twice.

    Windows repeats a held key after ~0.5 s, and every transport action costs a
    title: the one you skipped to plays for half a second and is gone. Qt's
    QShortcut auto-repeats by default and the table's own keys arrive as ordinary
    repeated presses, so both have to say no explicitly."""

    @staticmethod
    def _press(table, key, mods=Qt.KeyboardModifier.NoModifier, *, repeat):
        """Straight into the table's handler — in Playing mode the window's own
        Space filter (which already refuses repeats) would answer first, and the
        guard under test is the deck's."""
        table.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, key, mods,
                                      0, 0, 0, "", repeat))

    def test_the_transport_shortcuts_do_not_repeat(self):
        for name, sc in (("⏭", self.win._next_sc), ("⏮", self.win._prev_sc)):
            with self.subTest(shortcut=name):
                self.assertFalse(sc.autoRepeat())

    def test_the_cartwall_pads_do_not_repeat(self):
        """A held pad key would re-fire the sample over the running music."""
        wall = self.win._cartwall
        wall._rebuild_shortcuts()
        self.assertTrue(wall._shortcuts, "no pad keys bound to check")
        for sc in wall._shortcuts:
            with self.subTest(key=sc.key().toString()):
                self.assertFalse(sc.autoRepeat())

    def test_a_held_space_does_not_play_stop_play(self):
        table = self.win._tableA
        played = []
        table._on_play_click = lambda row, path: played.append(row)
        table._selected_song_row = lambda: (0, Path("x.mp3"))

        self._press(table, Qt.Key.Key_Space, repeat=False)
        self._press(table, Qt.Key.Key_Space, repeat=True)
        self._press(table, Qt.Key.Key_Space, repeat=True)
        self.assertEqual(played, [0], "the repeats toggled playback again")

    def test_a_held_ctrl_r_re_rolls_once(self):
        table = self.win._tableA
        rolled = []
        table._regen = rolled.append
        table._selected_song_row = lambda: (0, Path("x.mp3"))

        self._press(table, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier,
                    repeat=False)
        self._press(table, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier,
                    repeat=True)
        self.assertEqual(rolled, [0])

    def test_holding_the_seek_key_still_seeks(self):
        """The one action a repeat is meant for: running through a song."""
        table = self.win._tableA
        seeks = []
        table._seek_cb = seeks.append

        self._press(table, Qt.Key.Key_Right, Qt.KeyboardModifier.ControlModifier,
                    repeat=False)
        self._press(table, Qt.Key.Key_Right, Qt.KeyboardModifier.ControlModifier,
                    repeat=True)
        self.assertEqual(seeks, [30000, 30000])


class TempoStepTest(_WindowTest):
    """− / + beside the tempo fader: walk the tempo instead of dragging for it."""

    def setUp(self):
        super().setUp()
        self.card._tempo.setValue(0)
        self.minus, self.plus = (b for b in self.card.findChildren(QToolButton)
                                 if b.text() in ("−", "+"))

    def test_plus_raises_the_tempo_by_a_tenth_of_a_percent(self):
        self.plus.click()
        self.assertEqual(self.card._tempo.value(), gui_player._TEMPO_STEP)

    def test_a_step_is_the_finest_the_fader_has(self):
        """0.1 % — the fader's own unit. A takt is hit by tenths."""
        self.assertEqual(gui_player._TEMPO_STEP, 1)

    def test_minus_lowers_it_by_the_same(self):
        self.minus.click()
        self.assertEqual(self.card._tempo.value(), -gui_player._TEMPO_STEP)

    def test_steps_accumulate(self):
        for _ in range(4):
            self.plus.click()
        self.assertEqual(self.card._tempo.value(), 4 * gui_player._TEMPO_STEP)

    def test_they_stop_at_the_ends_of_the_range(self):
        """Holding + at +16 % must not run the value past the fader."""
        self.card._tempo.setValue(self.card._tempo.maximum())
        self.plus.click()
        self.assertEqual(self.card._tempo.value(), self.card._tempo.maximum())
        self.card._tempo.setValue(self.card._tempo.minimum())
        self.minus.click()
        self.assertEqual(self.card._tempo.value(), self.card._tempo.minimum())

    def test_holding_one_glides(self):
        """The one control where auto-repeat is the point, not the hazard."""
        for b in (self.minus, self.plus):
            with self.subTest(button=b.text()):
                self.assertTrue(b.autoRepeat())

    def test_a_glide_costs_one_rate_change_not_thirty(self):
        """Every setPlaybackRate re-inits the resampler — an audible gap. The
        steps must debounce like a wheel notch and apply once at the end."""
        applied = []
        self.card.apply_tempo = lambda: applied.append(self.card._tempo.value())
        for _ in range(6):
            self.plus.click()
        self.assertEqual(applied, [], "the rate was set mid-glide")
        self.assertTrue(self.card._tempo_apply.isActive())
        self.card._tempo_apply.timeout.emit()
        self.assertEqual(applied, [6 * gui_player._TEMPO_STEP])

    def test_the_readout_follows_every_step(self):
        self.plus.click()
        self.assertIn("0.1", self.card._tempo_lbl.text())

    def test_a_heat_pitched_to_a_half_takt_says_so(self):
        """🎚 TSO on a round of a T24 and a T25 Rumba lands on 24.5. Printed as
        a whole takt it read T25 — the same thing a hard 25 would say."""
        self.card.set_takt(24)
        self.card.set_tempo_to_target(24.5)
        self.assertIn("T24.5", self.card._tempo_lbl.text())

    def test_a_whole_takt_keeps_its_bare_number(self):
        self.card.set_takt(24)
        self.card.set_tempo_to_target(26)
        self.assertIn("T26", self.card._tempo_lbl.text())
        self.assertNotIn("T26.0", self.card._tempo_lbl.text())


class TempoDragTest(_WindowTest):
    """Dragging the fader: the music keeps playing, and the rate lands once.

    Following the handle live was tried and reverted. Every setPlaybackRate
    re-inits the backend's resampler, so applying the rate as the fader moves
    broke the music up under the thumb for the whole length of the drag — worse
    to work with than setting the tempo and hearing it on release. What follows
    the handle live is the readout, which costs nothing."""

    def setUp(self):
        super().setUp()
        self.card._tempo.setValue(0)
        self.applied = []
        self.card.apply_tempo = lambda: self.applied.append(
            self.card._tempo.value())

    def _drag_to(self, value: int):
        """Move the handle with the button down, as a real drag does."""
        self.card._tempo.setSliderDown(True)
        self.card._tempo.setValue(value)

    def test_the_music_is_not_touched_while_the_handle_is_held(self):
        for v in (5, 30, 61, 4, -80):
            self._drag_to(v)
        self.assertEqual(self.applied, [], "the drag broke the music up")

    def test_no_timer_is_left_armed_behind_the_drag(self):
        """A debounce started before the press must not fire mid-drag either."""
        self.card._tempo_apply.start(220)
        self._drag_to(30)
        self.assertFalse(self.card._tempo_apply.isActive())

    def test_releasing_the_handle_applies_the_final_value(self):
        self._drag_to(-77)
        # setSliderDown(False) emits sliderReleased by itself — emitting it as
        # well here would count one drag as two.
        self.card._tempo.setSliderDown(False)
        self.assertEqual(self.applied, [-77], "one rate change per drag")
        self.assertFalse(self.card._tempo_apply.isActive())

    def test_the_readout_follows_the_handle_live(self):
        """The one thing that is free, and the whole reason the drag can be
        silent: the number under the fader says where it is."""
        self._drag_to(123)
        self.assertIn("12.3", self.card._tempo_lbl.text())


class TempoClickTest(_WindowTest):
    """A click on the tempo fader jumps to the spot it hit.

    Qt's own answer to a click on the groove is a page step — 1.0 % on a fader
    scaled in tenths — so putting the tempo at +4 % took four clicks and a look
    at the readout between each. The seek and volume faders have jumped to the
    cursor all along; this one was left behind."""

    def setUp(self):
        super().setUp()
        self.fader = self.card._tempo
        self.fader.setValue(0)
        self.fader.resize(200, 20)
        self.applied = []
        self.card.apply_tempo = lambda: self.applied.append(self.fader.value())

    def _click_at(self, x: int):
        QApplication.sendEvent(self.fader, QMouseEvent(
            QEvent.Type.MouseButtonPress, QPointF(x, 10),
            self.fader.mapToGlobal(QPoint(x, 10)),
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier))

    def _value_at(self, x: int) -> float:
        """Where the fader's range says that pixel is."""
        lo, hi = self.fader.minimum(), self.fader.maximum()
        return lo + (hi - lo) * x / self.fader.width()

    def test_it_lands_where_the_click_was(self):
        for x in (25, 50, 150, 190):
            with self.subTest(x=x):
                self.fader.setValue(0)
                self._click_at(x)
                self.assertAlmostEqual(self.fader.value(), self._value_at(x),
                                       delta=8)   # ±0.8 %, handle width aside

    def test_it_is_not_a_one_percent_page_step(self):
        self._click_at(190)
        self.assertGreater(self.fader.value(), 10)

    def test_a_click_below_the_middle_goes_negative(self):
        self._click_at(25)
        self.assertLess(self.fader.value(), 0)

    def test_the_music_is_not_pitched_before_a_double_click_is_ruled_out(self):
        """The click may still be the first half of the double-click reset —
        pitching the song to a value about to be undone costs a gap for
        nothing."""
        self._click_at(190)
        self.card._on_tempo_released()
        self.assertEqual(self.applied, [])
        self.assertTrue(self.card._tempo_apply.isActive())

    def test_the_rate_lands_once_the_wait_is_over(self):
        self._click_at(190)
        self.card._on_tempo_released()
        self.card._tempo_apply.timeout.emit()
        self.assertEqual(self.applied, [self.fader.value()])

    def test_a_double_click_still_resets_the_fader(self):
        self._click_at(190)
        QApplication.sendEvent(self.fader, QMouseEvent(
            QEvent.Type.MouseButtonDblClick, QPointF(190, 10),
            self.fader.mapToGlobal(QPoint(190, 10)),
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier))
        self.assertEqual(self.fader.value(), 0)


class FaderWheelTest(_WindowTest):
    """A wheel notch over a fader must not move it."""

    @staticmethod
    def _wheel(widget, notches: int = 1):
        """One roll of the wheel over the widget. Returns the event, so the
        caller can see whether it was eaten or passed on."""
        ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0),
                         QPoint(0, 120 * notches), Qt.MouseButton.NoButton,
                         Qt.KeyboardModifier.NoModifier,
                         Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(widget, ev)
        return ev

    def _faders(self):
        """Volume, tempo and seek — with a value in the middle to move away
        from (the seek bar is empty until a track is loaded)."""
        self.card._slider.setRange(0, 100_000)
        for name, slider in (("volume", self.card._vol),
                             ("tempo", self.card._tempo),
                             ("seek", self.card._slider)):
            slider.setValue(0 if slider is self.card._tempo else 50)
            yield name, slider

    def test_the_wheel_leaves_them_where_they_were(self):
        for name, slider in self._faders():
            with self.subTest(fader=name):
                before = slider.value()
                self._wheel(slider, +1)
                self._wheel(slider, -1)
                self.assertEqual(slider.value(), before)

    def test_the_scroll_is_passed_on_and_not_eaten(self):
        """Ignoring beats accepting: the playing column is a scroll area, so a
        notch aimed at it still scrolls when the pointer crosses a fader."""
        for name, slider in self._faders():
            with self.subTest(fader=name):
                self.assertFalse(self._wheel(slider).isAccepted())

    def test_the_faders_still_take_a_value(self):
        """The block is the wheel alone — clicking and dragging is the point."""
        for name, slider in self._faders():
            with self.subTest(fader=name):
                slider.setValue(37)
                self.assertEqual(slider.value(), 37)


if __name__ == "__main__":
    unittest.main(verbosity=2)
