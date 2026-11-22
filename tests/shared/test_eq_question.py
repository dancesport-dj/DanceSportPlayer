"""🎚 The question before the music's equalizer goes on (shared.audio.eq_question).

Run:  .venv/Scripts/python.exe -m unittest tests.shared.test_eq_question -v
"""
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from planner.playing.equalizer import PITCH_OK_KEY
from shared.audio import eq_question
from shared.audio.eq_question import MusicEqQuestion, confirm_music_eq


class _Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def answer(self, on, remember):
        return mock.patch.object(MusicEqQuestion, "ask", return_value=(on, remember))


class ConfirmTest(_Test):

    # ===== Acceptance criteria =====

    def test_yes_turns_it_on_and_remembers(self):
        settings = {}
        with self.answer(True, True):
            self.assertTrue(confirm_music_eq(settings))
        self.assertIs(settings[PITCH_OK_KEY], True)

    def test_no_leaves_it_off_and_asks_again_next_time(self):
        settings = {}
        with self.answer(False, False):
            self.assertFalse(confirm_music_eq(settings))
        self.assertNotIn(PITCH_OK_KEY, settings)

    def test_accepted_before_asks_nothing(self):
        with mock.patch.object(MusicEqQuestion, "ask") as ask:
            self.assertTrue(confirm_music_eq({PITCH_OK_KEY: True}))
        ask.assert_not_called()

    # ===== Core behavior =====

    def test_yes_without_the_tick_asks_again_next_time(self):
        settings = {}
        with self.answer(True, False):
            self.assertTrue(confirm_music_eq(settings))
        self.assertNotIn(PITCH_OK_KEY, settings)


class QuestionTest(_Test):

    def make(self, settings):
        box = MusicEqQuestion(settings)
        self.addCleanup(box.deleteLater)
        return box

    # ===== Acceptance criteria =====

    def test_it_names_the_chosen_engine(self):
        self.assertIn("(now: Signalsmith)", self.make({}).informativeText())
        self.assertIn("(now: Rubber Band)",
                      self.make({"tapped_tempo_engine": "rubberband"}).informativeText())

    # ===== Core behavior =====

    def test_esc_leaves_it_off(self):
        box = self.make({})
        self.assertIs(box.escapeButton(), box.off_btn)

    def test_dont_ask_again_starts_ticked(self):
        self.assertTrue(self.make({}).remember.isChecked())

    def test_leave_it_off_never_remembers(self):
        box = self.make({})
        with mock.patch.object(box, "exec"), \
                mock.patch.object(box, "clickedButton", return_value=box.off_btn):
            self.assertEqual(box.ask(), (False, False))

    def test_turn_it_on_with_the_tick(self):
        box = self.make({})
        with mock.patch.object(box, "exec"), \
                mock.patch.object(box, "clickedButton", return_value=box.on_btn):
            self.assertEqual(box.ask(), (True, True))

    # ===== Coverage and null checks =====

    def test_an_unknown_engine_reads_as_signalsmith(self):
        self.assertEqual(eq_question.engine_name({"tapped_tempo_engine": "numpy"}),
                         "Signalsmith")


if __name__ == "__main__":
    unittest.main(verbosity=2)
