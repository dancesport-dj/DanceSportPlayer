"""🔇 A pad can skip the dead air at the start of its file.

Review 2026-11-12, suggestion 4: a one-shot Tusch whose file opens with
300 ms of silence sounded 300 ms after the tap. The silence probe the
library uses only sees stretches of 1.5 s and more, so a pad that asks for
it gets a short probe of its own lead-in, run when the wall loads or the
pad is saved, and starts at the music.

Runs on the stub players of test_cartwall_voices.
"""
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_skiplead_"))

from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from player.audio import cart_voices
from shared.audio import audio_probes
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

KEY = (0, 0, 0)
PREROLL = cart_voices._LEAD_PREROLL_MS


def _started_at(voice):
    """The position the voice was set to right before its last play()."""
    calls = voice.player.calls
    last_play = max(i for i, c in enumerate(calls) if c[0] == "play")
    return [c[1] for c in calls[:last_play] if c[0] == "setPosition"][-1]


class SkipLeadVoicesTest(unittest.TestCase):

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.v.set_level(1.0)
        self.asked = []
        self.v.wantsEdges.connect(self.asked.append)

    def tearDown(self):
        self.v.shutdown()

    def test_a_flagged_pad_starts_where_the_music_does(self):
        pad = _pad(skip_silence=True)
        self.v.set_edges(pad.path, [[0.0, 0.3]])
        self.v.fire(KEY, pad)
        self.assertEqual(_started_at(self.v._voice_for(KEY)), 300 - PREROLL)

    def test_an_unflagged_pad_starts_at_the_top(self):
        pad = _pad()
        self.v.set_edges(pad.path, [[0.0, 0.3]])
        self.v.fire(KEY, pad)
        self.assertEqual(_started_at(self.v._voice_for(KEY)), 0)

    def test_without_a_probe_it_starts_at_the_top_and_asks(self):
        pad = _pad(skip_silence=True)
        self.v.fire(KEY, pad)
        self.assertEqual(_started_at(self.v._voice_for(KEY)), 0)
        self.assertEqual(self.asked, [pad.path])

    def test_a_file_is_asked_for_once(self):
        self.v.ask_edges("C:\\samples\\a.mp3")
        self.v.ask_edges("C:\\samples\\a.mp3")
        self.assertEqual(self.asked, ["C:\\samples\\a.mp3"])

    def test_an_unflagged_pad_asks_for_nothing(self):
        self.v.fire(KEY, _pad())
        self.assertEqual(self.asked, [])

    def test_a_pad_tapped_again_while_fading_restarts_at_the_music(self):
        pad = _pad(skip_silence=True, fade_ms=1000)
        self.v.set_edges(pad.path, [[0.0, 0.5]])
        self.v.fire(KEY, pad, tapped=False)
        voice = self.v._voice_for(KEY)
        self.v.stop(KEY)
        self.assertGreater(voice.fade_step, 0, "on its way out")
        self.v.fire(KEY, pad, tapped=False)
        self.assertIs(self.v._voice_for(KEY), voice, "revived, not a new voice")
        self.assertEqual(_started_at(voice), 500 - PREROLL)

    def test_silence_later_in_the_file_is_not_a_lead(self):
        pad = _pad(skip_silence=True)
        self.v.set_edges(pad.path, [[1.0, 1.4]])
        self.v.fire(KEY, pad)
        self.assertEqual(_started_at(self.v._voice_for(KEY)), 0)

    def test_a_tiny_lead_never_goes_below_zero(self):
        pad = _pad(skip_silence=True)
        self.v.set_edges(pad.path, [[0.0, 0.01]])
        self.v.fire(KEY, pad)
        self.assertEqual(_started_at(self.v._voice_for(KEY)), 0)


class LeadProbeParseTest(unittest.TestCase):
    WINDOW = audio_probes.LEAD_PROBE_SECS

    def _err(self, *lines, duration="00:00:04.00"):
        return "\n".join([f"  Duration: {duration}, start: 0.000000, bitrate: 320 kb/s",
                          *lines])

    def test_the_leading_stretch_is_found(self):
        err = self._err("[silencedetect @ 0x1] silence_start: 0",
                        "[silencedetect @ 0x1] silence_end: 0.312 | silence_duration: 0.312",
                        "[silencedetect @ 0x1] silence_start: 2.5",
                        "[silencedetect @ 0x1] silence_end: 2.7 | silence_duration: 0.2")
        self.assertEqual(audio_probes.parse_lead_silence(err), [[0.0, 0.312]])

    def test_music_from_the_first_sample_has_no_lead(self):
        self.assertEqual(audio_probes.parse_lead_silence(self._err()), [])

    def test_a_stretch_that_starts_later_is_no_lead(self):
        err = self._err("[silencedetect @ 0x1] silence_start: 1.2",
                        "[silencedetect @ 0x1] silence_end: 1.5 | silence_duration: 0.3")
        self.assertEqual(audio_probes.parse_lead_silence(err), [])

    def test_silence_past_the_probed_window_is_not_skipped(self):
        """Nothing heard in the probed seconds: where the music starts is
        unknown, so the pad plays from the top."""
        err = self._err("[silencedetect @ 0x1] silence_start: 0", duration="00:03:00.00")
        self.assertEqual(audio_probes.parse_lead_silence(err), [])

    def test_a_silent_file_is_not_skipped(self):
        err = self._err("[silencedetect @ 0x1] silence_start: 0", duration="00:00:02.00")
        self.assertEqual(audio_probes.parse_lead_silence(err), [])


class SkipLeadPadTest(unittest.TestCase):

    def test_the_flag_is_off_by_default(self):
        self.assertFalse(pc.CartPad(path="a.mp3").skip_silence)

    def test_the_flag_survives_the_file(self):
        pad = pc.CartPad(path="a.mp3", skip_silence=True)
        data = pc._pad_to_dict(pad)
        self.assertTrue(data["skip_silence"])
        self.assertTrue(pc._pad_from_dict(data).skip_silence)

    def test_an_unflagged_pad_writes_nothing_for_it(self):
        self.assertNotIn("skip_silence", pc._pad_to_dict(pc.CartPad(path="a.mp3")))

    def test_the_dialog_carries_it(self):
        from player.dialogs import cart_pad_dialog as cpd
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", skip_silence=True))
        self.addCleanup(dlg.deleteLater)
        self.assertTrue(dlg._skip_silence.isChecked())
        self.assertTrue(dlg.pad().skip_silence)
        dlg._skip_silence.setChecked(False)
        self.assertFalse(dlg.pad().skip_silence)


class AskBeforeTheFirstTapTest(unittest.TestCase):
    """The probe runs when the wall loads or a pad is saved, so the evening's
    first Tusch already knows where its music starts."""

    def _host(self):
        return SimpleNamespace(_cart_voices=mock.Mock(), _settings={})

    def test_flagged_pads_are_asked_for_under_the_path_that_fires(self):
        from player.window import main_cartwall as mc
        host = self._host()
        pads = [pc.CartPad(path="C:\\old\\a.mp3", skip_silence=True),
                pc.CartPad(path="C:\\old\\b.mp3")]
        with mock.patch.object(mc, "resolve_file",
                               side_effect=lambda p, s: f"D:\\found\\{p[-5:]}"):
            mc.CartwallMixin._ask_pad_edges(host, pads)
        host._cart_voices.ask_edges.assert_called_once_with("D:\\found\\a.mp3")

    def test_a_missing_file_is_not_asked_for(self):
        from player.window import main_cartwall as mc
        host = self._host()
        with mock.patch.object(mc, "resolve_file", return_value=None):
            mc.CartwallMixin._ask_pad_edges(
                host, [pc.CartPad(path="a.mp3", skip_silence=True)])
        host._cart_voices.ask_edges.assert_not_called()

    def test_a_saved_pad_is_asked_for(self):
        from player.window import main_cartwall as mc
        host = self._host()
        host._ask_pad_edges = mock.Mock()
        pad = pc.CartPad(path="a.mp3", skip_silence=True)
        mc.CartwallMixin._on_cart_pad_refreshed(host, KEY, pad)
        host._ask_pad_edges.assert_called_once_with([pad])


if __name__ == "__main__":
    unittest.main()
