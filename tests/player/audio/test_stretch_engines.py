#!/usr/bin/env python3
"""⏩ Which pitch-kept tempo a tapped player uses (player.audio.stretch_engines).

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_stretch_engines -v
"""
import unittest
from unittest import mock

from player.audio import stretch_engines, stretch_ffmpeg, stretch_signalsmith
from player.audio.stretch import TimeStretch


class StretchEnginesTest(unittest.TestCase):

    def tearDown(self):
        stretch_engines.set_engine(stretch_engines.DEFAULT)
        stretch_engines._broken.clear()

    # ===== Acceptance criteria =====

    def test_qt_is_the_default_and_taps_nothing(self):
        """Marcel: Qt's own tempo as it was, the default."""
        self.assertEqual(stretch_engines.DEFAULT, "qt")
        self.assertEqual(stretch_engines.chosen(), "qt")
        self.assertFalse(stretch_engines.taps_music())

    def test_the_apps_own_engines_take_every_music_stream(self):
        """Marcel: the choice is for every music stream, not only tapped ones."""
        for engine in ("signalsmith", "rubberband"):
            stretch_engines.set_engine(engine)
            self.assertTrue(stretch_engines.taps_music(), engine)

    def test_only_rubber_band_asks_ffmpeg_for_its_filter(self):
        """set_engine runs on the GUI thread at every start: asking ffmpeg
        took ~125 ms there, and only Rubber Band needs the answer."""
        with mock.patch.object(stretch_ffmpeg, "available") as asked:
            for engine in ("qt", "signalsmith", "turntable"):
                stretch_engines.set_engine(engine)
            asked.assert_not_called()
            stretch_engines.set_engine("rubberband")
            asked.assert_called_once()

    @unittest.skipUnless(stretch_signalsmith.available(), "sstretch.dll not built")
    def test_a_tapped_stream_under_qt_gets_signalsmith(self):
        """The EQ taps it: Qt's own stretch is the same Signalsmith. Rubber
        Band costs clearly more CPU: only when chosen."""
        self.assertEqual(stretch_engines.current(), "signalsmith")
        made = stretch_engines.make(48000)
        self.assertIsInstance(made, stretch_signalsmith.SignalsmithStretch)

    @unittest.skipUnless(stretch_ffmpeg.available(), "no ffmpeg with the rubberband filter")
    def test_rubberband_when_chosen_where_ffmpeg_has_it(self):
        stretch_engines.set_engine("rubberband")
        self.assertEqual(stretch_engines.current(), "rubberband")
        made = stretch_engines.make(48000)
        self.addCleanup(made.close)
        self.assertIsInstance(made, stretch_ffmpeg.FfmpegStretch)
        self.assertEqual(made.engine, "rubberband")

    @unittest.skipUnless(stretch_signalsmith.available(), "sstretch.dll not built")
    def test_without_rubberband_signalsmith_stands_in(self):
        stretch_engines.set_engine("rubberband")
        with mock.patch.object(stretch_ffmpeg, "available", return_value=False):
            self.assertEqual(stretch_engines.current(), "signalsmith")
            made = stretch_engines.make(48000)
        self.assertIsInstance(made, stretch_signalsmith.SignalsmithStretch)
        self.assertEqual(made.engine, "signalsmith")

    def test_without_either_numpy_stands_in(self):
        stretch_engines.set_engine("rubberband")
        with mock.patch.object(stretch_ffmpeg, "available", return_value=False), \
                mock.patch.object(stretch_signalsmith, "available", return_value=False):
            self.assertEqual(stretch_engines.current(), "numpy")
            made = stretch_engines.make(48000)
        self.assertIsInstance(made, TimeStretch)
        self.assertEqual(made.engine, "numpy")

    # ===== Core behavior =====

    @unittest.skipUnless(stretch_signalsmith.available(), "sstretch.dll not built")
    def test_signalsmith_when_chosen(self):
        stretch_engines.set_engine("rubberband")
        stretch_engines.set_engine("signalsmith")
        self.assertEqual(stretch_engines.current(), "signalsmith")

    @unittest.skipUnless(stretch_signalsmith.available(), "sstretch.dll not built")
    def test_a_broken_rubberband_is_passed_over_for_the_session(self):
        stretch_engines.set_engine("rubberband")
        with mock.patch.object(stretch_ffmpeg, "available", return_value=True):
            stretch_engines.note_broken("rubberband")
            self.assertEqual(stretch_engines.current(), "signalsmith")

    @unittest.skipUnless(stretch_signalsmith.available(), "sstretch.dll not built")
    def test_rubberband_that_fails_to_start_falls_back_to_signalsmith(self):
        with mock.patch.object(stretch_ffmpeg, "FfmpegStretch", side_effect=RuntimeError("gone")):
            with self.assertLogs(level="WARNING"):
                made = stretch_engines.make(48000, "rubberband")
        self.assertIsInstance(made, stretch_signalsmith.SignalsmithStretch)
        self.assertEqual(made.engine, "signalsmith")

    def test_a_library_that_fails_to_start_falls_back_to_numpy(self):
        with mock.patch.object(stretch_signalsmith, "SignalsmithStretch",
                               side_effect=RuntimeError("gone")):
            with self.assertLogs(level="WARNING"):
                made = stretch_engines.make(48000, "signalsmith")
        self.assertIsInstance(made, TimeStretch)
        self.assertEqual(made.engine, "numpy")

    # ===== Coverage and null checks =====

    def test_an_unknown_choice_is_the_default(self):
        stretch_engines.set_engine("turntable")
        self.assertEqual(stretch_engines.chosen(), stretch_engines.DEFAULT)


if __name__ == "__main__":
    unittest.main()
