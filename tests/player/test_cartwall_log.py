"""The cartwall's pads leave a start and an end line in the session log.

The deck logs "Play requested" and "Song ended"; a pad played under the same
evening used to leave nothing, so a pad that stopped early could not be told
from a natural end afterwards.

Run:  py -m unittest tests.player.test_cartwall_log -v
"""
from tests.player.test_cartwall_voices import _pad, _VoiceCase


class PadLogTest(_VoiceCase):

    def _lines(self, logs):
        return [r.getMessage() for r in logs.records]

    def test_a_pad_logs_when_it_starts(self):
        with self.assertLogs("dancesport.gui.cartwall", "INFO") as logs:
            self.v.fire((0, 1, 2), _pad("birthday.mp3"))
        text = "\n".join(self._lines(logs))
        self.assertIn("Pad started", text)
        self.assertIn("birthday.mp3", text)

    def test_a_pad_that_plays_to_the_end_says_so(self):
        self.v.fire((0, 0, 0), _pad("birthday.mp3"))
        with self.assertLogs("dancesport.gui.cartwall", "INFO") as logs:
            self._end_of_media(self._voice((0, 0, 0)))
        text = "\n".join(self._lines(logs))
        self.assertIn("Pad ended", text)
        self.assertIn("reason: end of file", text)
        self.assertIn("birthday.mp3", text)

    def test_a_pad_the_operator_stopped_says_so(self):
        self.v.fire((0, 0, 0), _pad("birthday.mp3"))
        with self.assertLogs("dancesport.gui.cartwall", "INFO") as logs:
            self.v.stop((0, 0, 0))
            self._drain_fades()
        text = "\n".join(self._lines(logs))
        self.assertIn("Pad ended", text)
        self.assertIn("reason: faded out", text)

    def _heard(self):
        got = []
        self.v.padPlayed.connect(lambda pad, secs: got.append((pad.path, secs)))
        return got

    def test_a_pad_that_ran_to_the_end_reports_what_was_heard(self):
        got = self._heard()
        self.v.fire((0, 0, 0), _pad("birthday.mp3"))
        voice = self._voice((0, 0, 0))
        voice.player._pos = 31_000
        self._end_of_media(voice)
        self.assertEqual(got, [(r"C:\samples\birthday.mp3", 31.0)])

    def test_a_pad_the_operator_stopped_reports_how_far_it_got(self):
        got = self._heard()
        self.v.fire((0, 0, 0), _pad("birthday.mp3"))
        self._voice((0, 0, 0)).player._pos = 12_500
        self.v.stop((0, 0, 0))
        self._drain_fades()
        self.assertEqual(got, [(r"C:\samples\birthday.mp3", 12.5)])

    def test_a_pad_that_failed_says_so(self):
        self.v.fire((0, 0, 0), _pad("birthday.mp3"))
        voice = self._voice((0, 0, 0))
        with self.assertLogs("dancesport.gui.cartwall", "INFO") as logs:
            self.v._on_error(voice, "ResourceError", "cannot decode")
        text = "\n".join(self._lines(logs))
        self.assertIn("Pad ended", text)
        self.assertIn("reason: error", text)
