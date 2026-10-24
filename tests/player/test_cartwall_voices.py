"""CartVoices: the cartwall's own audio pool.

Runs against a stub player factory, so nothing here touches Windows Media
Foundation — the point is the pool's *policy* (which voice a fire lands on,
what a fade does, when the duck goes up), not the backend.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_voices_"))

from PySide6.QtCore import QCoreApplication, QObject, QUrl, Signal
from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from player.audio import cart_voices
from player.widgets import cartwall as gc

_app = QApplication.instance() or QApplication(sys.argv)


class _StubPlayer(QObject):
    """Records what the pool asks of it. Deliberately not a QMediaPlayer."""

    mediaStatusChanged = Signal(object)
    errorOccurred = Signal(object, str)

    def __init__(self):
        super().__init__()
        self._source = QUrl()
        self._state = "stopped"
        self._pos = 0
        self._out = None
        self.calls = []          # every mutation, in order

    def source(self):
        return self._source

    def setSource(self, url):
        self._source = url
        self.calls.append(("setSource", url.toLocalFile()))

    def setPosition(self, ms):
        self._pos = ms
        self.calls.append(("setPosition", ms))

    def position(self):
        return self._pos

    def duration(self):
        return 10_000

    def play(self):
        self._state = "playing"
        self.calls.append(("play", None))

    def pause(self):
        self._state = "paused"
        self.calls.append(("pause", None))

    def stop(self):
        self._state = "stopped"
        self.calls.append(("stop", None))

    def setLoops(self, n):           # must never be reached
        self.calls.append(("setLoops", n))

    # The pool hands the sound device back while nothing plays and takes it
    # again on the next fire — see CartVoices.release_outputs.
    def audioOutput(self):
        return self._out

    def setAudioOutput(self, out):
        self._out = out
        self.calls.append(("setAudioOutput", out is not None))

    def names(self):
        return [c[0] for c in self.calls]


class _StubOutput:
    def __init__(self):
        self._vol = 0.0
        self.device = None

    def setVolume(self, v):
        self._vol = v

    def volume(self):
        return self._vol

    def setDevice(self, dev):
        self.device = dev


def _factory():
    return _StubPlayer(), _StubOutput()


def _pad(name="tusch.mp3", **kw):
    return pc.CartPad(path=f"C:\\samples\\{name}", **kw)


class _VoiceCase(unittest.TestCase):
    """A four-voice pool over stub players, drained by hand."""

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.v.set_level(1.0)

    def tearDown(self):
        self.v.shutdown()

    def _pool(self):
        return self.v._pool

    def _live(self):
        return [x for x in self._pool() if x.busy]

    def _drain_fades(self, steps=200):
        """Run the fade ramp to completion without waiting on the event loop."""
        for _ in range(steps):
            if not any(x.fade_step > 0 for x in self._pool()):
                return
            self.v._step_fades()
        self.fail("a fade never finished")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _voice(self, key):
        voice = self.v._voice_for(key)
        self.assertIsNotNone(voice, f"no voice holds {key}")
        return voice

    @staticmethod
    def _end_of_media(voice):
        from PySide6.QtMultimedia import QMediaPlayer
        voice.player.mediaStatusChanged.emit(
            QMediaPlayer.MediaStatus.EndOfMedia)
        QCoreApplication.processEvents()


class VoiceChoiceTest(_VoiceCase):
    """Which voice a tap gets, and which one it is allowed to steal."""

    def test_four_pads_take_four_distinct_voices(self):
        for i in range(4):
            self.assertTrue(self.v.fire((0, 0, i), _pad(f"s{i}.mp3")))
        self.assertEqual(len(self._live()), 4)
        self.assertEqual(len({id(x) for x in self._live()}), 4)

    def test_a_fifth_pad_steals_the_oldest_voice(self):
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"s{i}.mp3"))
        oldest = min(self._pool(), key=lambda x: x.started)
        self.assertTrue(self.v.fire((0, 1, 0), _pad("late.mp3")))
        self._drain_fades()
        self.assertEqual(oldest.key, (0, 1, 0))
        self.assertEqual(len(self._live()), 4)

    def test_a_looping_bed_is_never_stolen(self):
        """A bed under a Siegerehrung is the one sound that must not be cut."""
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"bed{i}.mp3", loop=True))
        self.assertFalse(self.v.fire((0, 1, 0), _pad("fanfare.mp3")))
        self.assertEqual(len(self._live()), 4)

    def test_a_tap_during_stop_all_takes_a_fading_voice(self):
        """⏹ all on a full wall with a long fade: every voice is on its way
        out for seconds. The next tap must not be refused for that."""
        self.v.set_wall_fade(8000)
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"s{i}.mp3"))
        self.v.stop_all()
        self.assertTrue(self.v.fire((0, 1, 0), _pad("fanfare.mp3")))
        self._drain_fades(steps=400)   # 8 s in 25 ms ramp steps
        self.assertEqual([x.key for x in self._live()], [(0, 1, 0)])

    def test_a_fading_voice_already_taken_over_is_not_taken_twice(self):
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"bed{i}.mp3", loop=True))
        self.v.stop((0, 0, 0))
        self.assertTrue(self.v.fire((0, 1, 0), _pad("first.mp3")))
        self.assertFalse(self.v.fire((0, 1, 1), _pad("second.mp3")))
        self._drain_fades()
        self.assertIn((0, 1, 0), [x.key for x in self._live()])

    def _steal(self):
        """Four one-shots, then a fifth pad that takes over the oldest voice."""
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"s{i}.mp3"))
        oldest = min(self._pool(), key=lambda x: x.started)
        self.assertTrue(self.v.fire((0, 1, 0), _pad("late.mp3")))
        self.assertIsNotNone(oldest.then)
        return oldest

    def test_a_stolen_voice_that_ends_mid_fade_still_starts_the_new_pad(self):
        """The old sample running out during the steal ramp must not swallow
        the pad that was waiting for its voice."""
        oldest = self._steal()
        self._end_of_media(oldest)
        self.assertEqual(oldest.key, (0, 1, 0))
        self.assertIsNone(oldest.then)
        self._drain_fades()
        self.assertEqual(oldest.key, (0, 1, 0))

    def test_stop_all_during_a_steal_starts_nothing(self):
        """⏹ all means silence — also for a pad still waiting for its voice."""
        oldest = self._steal()
        self.v.stop_all()
        self._drain_fades()
        self.assertEqual(self._live(), [])
        self.assertIsNone(oldest.then)

    def test_one_bed_plus_one_shots_still_steals_a_one_shot(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", loop=True))
        for i in (1, 2, 3):
            self.v.fire((0, 0, i), _pad(f"s{i}.mp3"))
        bed = self._pool()[0]
        self.assertTrue(self.v.fire((0, 2, 0), _pad("tusch.mp3")))
        self._drain_fades()
        self.assertEqual(bed.key, (0, 0, 0))

    def test_refiring_the_same_sample_never_touches_setSource(self):
        """The whole point of the pool: the same Tusch forty times a day costs
        one setPosition, not forty WMF media-session rebuilds."""
        key, pad = (0, 0, 0), _pad("tusch.mp3")
        self.v.fire(key, pad)
        voice = self._voice(key)
        self.assertEqual(voice.player.names().count("setSource"), 1)
        for _ in range(20):
            self.v.stop(key)
            self._drain_fades()
            self.v._last_fire.clear()      # skip the double-click debounce
            self.v.fire(key, pad)
        self.assertEqual(voice.player.names().count("setSource"), 1)

    def test_recycling_a_voice_for_another_file_sets_the_source_once(self):
        self.v.fire((0, 0, 0), _pad("a.mp3"))
        voice = self._voice((0, 0, 0))
        self.v.stop((0, 0, 0))
        self._drain_fades()
        # Only one voice has ever been used, so the LRU pick lands on it again —
        # but the other three are still untouched, so force the issue.
        for i in range(1, 4):
            self.v.fire((0, 0, i), _pad(f"x{i}.mp3"))
        self.v.fire((0, 1, 0), _pad("b.mp3"))
        self.assertEqual(voice.key, (0, 1, 0))
        self.assertEqual(voice.player.names().count("setSource"), 2)

    def test_stopping_keeps_the_source_but_shutdown_clears_it(self):
        self.v.fire((0, 0, 0), _pad("a.mp3"))
        voice = self._voice((0, 0, 0))
        self.v.stop((0, 0, 0))
        self._drain_fades()
        self.assertFalse(voice.player.source().isEmpty())
        self.v.shutdown()
        self.assertTrue(voice.player.source().isEmpty())


class VoiceRekeyTest(_VoiceCase):
    """The wall turned or reshaped: a sounding pad now lives in another cell,
    and the voice playing it must answer to that cell."""

    def test_a_sounding_pad_answers_to_its_new_cell(self):
        self.v.fire((0, 7, 0), _pad("a.mp3"))
        self.v.rekey({(0, 7, 0): (0, 0, 7)})
        self.assertTrue(self.v.is_playing((0, 0, 7)))
        self.assertFalse(self.v.is_playing((0, 7, 0)))

    def test_a_pad_waiting_on_a_steal_follows_too(self):
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"s{i}.mp3"))
        oldest = min(self._pool(), key=lambda x: x.started)
        self.v.fire((0, 1, 0), _pad("late.mp3"))
        self.v.rekey({(0, 1, 0): (0, 0, 1), (0, 0, 1): (0, 1, 0)})
        self.assertEqual(oldest.then[0], (0, 0, 1))
        self._drain_fades()
        self.assertEqual(oldest.key, (0, 0, 1))

    def test_what_stops_is_reported_under_the_new_cell(self):
        stopped = []
        self.v.padStopped.connect(stopped.append)
        self.v.fire((0, 7, 0), _pad("a.mp3"))
        self.v.rekey({(0, 7, 0): (0, 0, 7)})
        self.v.stop((0, 0, 7))
        self._drain_fades()
        self.assertEqual(stopped, [(0, 0, 7)])


class WallAndVoicesTurnTogetherTest(_VoiceCase):
    """Wired as `_build_cartwall` wires them: after the dock moves, a tap on
    the sounding pad stops it instead of starting a second copy."""

    def test_tapping_the_turned_pad_stops_it(self):
        w = gc.CartwallWidget()
        self.addCleanup(w.deleteLater)
        w.padsMoved.connect(self.v.rekey)
        pad = _pad("a.mp3")
        w.set_wall((2, 8), [pc.Page(pads={(7, 0): pad})])
        self.v.fire((0, 7, 0), pad)
        w.set_playing((0, 7, 0), True)
        w.set_portrait(False)
        self.assertTrue(self.v.is_playing((0, 0, 7)))


class VoiceFadeTest(_VoiceCase):
    """A tap on something already playing fades it out, never cuts."""

    # ── fading ───────────────────────────────────────────────────────────────
    def test_a_tap_on_a_playing_pad_fades_instead_of_cutting(self):
        key = (0, 0, 0)
        self.v.fire(key, _pad())
        voice = self._voice(key)
        self.v.stop(key)
        self.assertTrue(voice.busy, "the voice must not drop on the first step")
        levels = []
        for _ in range(200):
            if not voice.busy:
                break
            self.v._step_fades()
            levels.append(voice.out.volume())
        self.assertGreater(len(levels), 4, "1 s at 25 ms is many steps")
        self.assertTrue(all(b <= a for a, b in zip(levels, levels[1:], strict=False)),
                        "the level must only ever go down")
        self.assertIsNone(voice.key)
        self.assertIn("pause", voice.player.names())

    def test_tapping_mid_fade_re_fires_at_full_level(self):
        key = (0, 0, 0)
        self.v.fire(key, _pad())
        voice = self._voice(key)
        self.v.stop(key)
        self.v._step_fades()
        self.v._step_fades()
        self.assertFalse(self.v.is_playing(key), "a fading pad counts as free")
        self.v._last_fire.clear()
        self.assertTrue(self.v.fire(key, _pad()))
        self.assertEqual(voice.fade, 1.0)
        self.assertEqual(voice.fade_step, 0.0)
        self.assertAlmostEqual(voice.out.volume(), 1.0)

    def test_stop_all_fades_everything(self):
        for i in range(3):
            self.v.fire((0, 0, i), _pad(f"s{i}.mp3"))
        self.v.stop_all()
        self.assertEqual(len(self._live()), 3)
        self._drain_fades()
        self.assertEqual(self._live(), [])

    def test_stop_all_says_how_long_the_longest_fade_runs(self):
        # ✕ waits that long before the window goes (_fade_out_to_quit).
        self.v.set_wall_fade(1500)
        self.v.fire((0, 0, 0), _pad("s0.mp3"))
        self.v.fire((0, 0, 1), _pad("s1.mp3", fade_ms=4000))
        self.assertEqual(self.v.stop_all(), 4000)
        self.assertEqual(self.v.stop_all(), 0, "already fading: nothing new")

    # ── rate limiting ────────────────────────────────────────────────────────
    def test_a_double_click_is_one_tap(self):
        key = (0, 0, 0)
        self.assertTrue(self.v.fire(key, _pad()))
        # None, not False: the second half is ignored, no voice was missing.
        self.assertIsNone(self.v.fire(key, _pad()))
        self.assertEqual(len(self._live()), 1)

    def test_only_a_full_pool_answers_false(self):
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"bed{i}.mp3", loop=True))
        self.assertIs(self.v.fire((0, 1, 0), _pad("late.mp3")), False)


class PadTapMessageTest(unittest.TestCase):
    """What the tap says when the pool did not start the pad: "no free voice"
    only when that is true — not for a double-click's ignored second half."""

    def tap(self, fired):
        from unittest import mock
        from player.window.main_cartwall import CartwallMixin
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            self.addCleanup(os.remove, f.name)
        host = mock.Mock()
        host._cartwall.pad_at.return_value = pc.CartPad(path=f.name)
        host._cart_voices.is_playing.return_value = False
        host._cart_voices.fire.return_value = fired
        CartwallMixin._on_pad_clicked(host, (0, 0, 0))
        return host

    def test_a_double_click_says_nothing(self):
        host = self.tap(None)
        host.statusBar().showMessage.assert_not_called()
        host._cartwall.set_playing.assert_not_called()

    def test_a_full_pool_says_so(self):
        host = self.tap(False)
        self.assertIn("No free pad voice",
                      host.statusBar().showMessage.call_args.args[0])

    def test_a_started_pad_lights_up(self):
        self.tap(True)._cartwall.set_playing.assert_called_once_with((0, 0, 0), True)


class VoiceLevelTest(_VoiceCase):
    """Levels: the pad trim, the master, mute, the device, the duck."""

    def test_the_pad_volume_reaches_the_output(self):
        self.v.fire((0, 0, 0), _pad(volume=0.25))
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.25)

    def test_changing_the_volume_of_a_running_pad_applies_at_once(self):
        key = (0, 0, 0)
        self.v.fire(key, _pad(volume=1.0))
        self.v.refresh_pad(key, _pad(volume=0.25))
        self.assertAlmostEqual(self._voice(key).out.volume(), 0.25)

    def test_the_master_level_multiplies_the_pad_trim(self):
        self.v.fire((0, 0, 0), _pad(volume=0.5))
        self.v.set_level(0.5)
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.25)

    def test_mute_silences_without_pausing_and_restores_on_unmute(self):
        """The difference from ⏹: a bed pulled out for a speech comes back
        exactly where it was."""
        key = (0, 0, 0)
        self.v.fire(key, _pad(loop=True))
        voice = self._voice(key)
        self.v.set_muted(True)
        self.assertEqual(voice.out.volume(), 0.0)
        self.assertNotIn("pause", voice.player.names())
        self.assertTrue(voice.busy)
        self.v.set_muted(False)
        self.assertAlmostEqual(voice.out.volume(), 1.0)

    def test_set_device_reaches_every_output(self):
        self.v.set_device("speaker")
        self.assertTrue(all(x.out.device == "speaker" for x in self._pool()))

    def test_a_ducking_pad_ducks_and_a_bed_does_not(self):
        seen = []
        self.v.duckChanged.connect(seen.append)
        self.v.fire((0, 0, 0), _pad("bed.mp3", loop=True, duck=False))
        self.assertEqual(seen, [], "a 25 % bed must not hold the music down")
        self.v.fire((0, 0, 1), _pad("tusch.mp3", duck=True))
        self.assertEqual(seen, [True])
        self.v.stop((0, 0, 1))
        self._drain_fades()
        self.assertEqual(seen, [True, False])

    def test_the_duck_stays_down_while_a_second_ducking_pad_runs(self):
        seen = []
        self.v.duckChanged.connect(seen.append)
        self.v.fire((0, 0, 0), _pad("a.mp3"))
        self.v.fire((0, 0, 1), _pad("b.mp3"))
        self.v.stop((0, 0, 0))
        self._drain_fades()
        self.assertEqual(seen, [True], "the first pad ending must not lift it")


class BackgroundPadTest(_VoiceCase):
    """🎶 A background pad dips under the running title instead of pulling the
    title down — the reverse of the 🔈 duck."""

    def _drain_background(self, steps=200):
        levels = []
        for _ in range(steps):
            if not self.v._bg_ramp.isActive():
                return levels
            self.v._step_background()
            levels.append(self._voice((0, 0, 0)).out.volume())
        self.fail("the background ramp never settled")

    def test_it_dips_while_the_music_plays(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True, volume=0.5))
        self.v.set_music_playing(True)
        levels = self._drain_background()
        self.assertGreater(len(levels), 2, "a dip is a ramp, never a jump")
        self.assertTrue(all(b <= a for a, b in zip(levels, levels[1:], strict=False)))
        # All the way down: under a title the bed is silent, not quieter.
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.0)

    def test_an_ordinary_pad_is_left_alone(self):
        self.v.fire((0, 0, 0), _pad("tusch.mp3", volume=0.5))
        self.v.set_music_playing(True)
        self._drain_background()
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.5)

    def test_fired_under_a_running_title_it_starts_low(self):
        self.v.set_music_playing(True)
        while self.v._bg_ramp.isActive():
            self.v._step_background()
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.0)

    def test_it_comes_back_only_after_a_hold(self):
        """The deck stops for a moment at every title switch; the bed must not
        swell up in that gap."""
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self._rise_levels()                     # the fire fade-in lands first
        self.v.set_music_playing(True)
        self._drain_background()
        self.v.set_music_playing(False)
        self.assertTrue(self.v._bg_hold.isActive())
        self.assertFalse(self.v._bg_ramp.isActive(), "nothing moves during the hold")
        self.v.set_music_playing(True)          # the next title is already on
        self.assertFalse(self.v._bg_hold.isActive())
        self.v.set_music_playing(False)
        self.v._lift_background()               # the hold ran out
        levels = self._drain_background()
        self.assertTrue(all(b >= a for a, b in zip(levels, levels[1:], strict=False)))
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 1.0)

    def test_it_fades_in_soon_after_the_music_stops(self):
        """'lags the restart after a music finished playing. i want a fadein
        after music stop playing': a short hold, then a fade of seconds."""
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_music_playing(True)
        self._drain_background()
        self.v.set_music_playing(False)
        self.assertLessEqual(self.v._bg_hold.interval(), 400)
        self.v._lift_background()
        fade_ms = len(self._drain_background()) * self.v._bg_ramp.interval()
        self.assertGreaterEqual(fade_ms, 1500)

    def test_coming_back_is_slower_than_going_down(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_music_playing(True)
        down = len(self._drain_background())
        self.v.set_music_playing(False)
        self.v._lift_background()
        up = len(self._drain_background())
        self.assertGreater(up, down)

    def _fade_back_in_ms(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self._rise_levels()                     # the fire fade-in lands first
        self.v.set_music_playing(True)
        self._drain_background()
        self.v.set_music_playing(False)
        self.v._lift_background()
        return len(self._drain_background(400)) * self.v._bg_ramp.interval()

    def test_the_fade_back_in_follows_the_setting(self):
        """'make the fade-in for cartwall also configurable … use current std
        value as default': 2 s until ⚙ Settings says otherwise."""
        # Within a tick: the float steps may need one more to land.
        self.assertAlmostEqual(self._fade_back_in_ms(), pc.DEFAULT_BG_FADE_IN_MS,
                               delta=self.v._bg_ramp.interval())

    def test_a_longer_fade_back_in_takes_longer(self):
        self.v.set_background_fade_in(5000)
        self.assertAlmostEqual(self._fade_back_in_ms(), 5000,
                               delta=self.v._bg_ramp.interval())

    def test_no_fade_back_in_brings_it_back_at_once(self):
        self.v.set_background_fade_in(0)
        self.assertEqual(self._fade_back_in_ms(), self.v._bg_ramp.interval(),
                         "one tick, no division by zero")
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 1.0)

    def _dip_ms(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_music_playing(True)
        return len(self._drain_background(400)) * self.v._bg_ramp.interval()

    def test_the_dip_is_0_2_s_by_default(self):
        """'set to 0.2 instead of 0.18'."""
        self.assertEqual(pc.DEFAULT_BG_FADE_OUT_MS, 200)

    def test_the_dip_follows_the_setting(self):
        """'make also both fade in and fade out configurable': the dip keeps
        its standard 0.2 s until ⚙ Settings says otherwise."""
        self.assertAlmostEqual(self._dip_ms(), pc.DEFAULT_BG_FADE_OUT_MS,
                               delta=self.v._bg_ramp.interval())

    def test_a_longer_dip_takes_longer(self):
        self.v.set_background_fade_out(3000)
        self.assertAlmostEqual(self._dip_ms(), 3000,
                               delta=self.v._bg_ramp.interval())
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.0)

    def test_no_dip_cuts_it_at_once(self):
        self.v.set_background_fade_out(0)
        self.assertEqual(self._dip_ms(), self.v._bg_ramp.interval())
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.0)

    def test_the_wait_before_it_comes_back_follows_the_setting(self):
        """'i want everything changeable nothing fixed': the 0.3 s wait too."""
        self.assertEqual(self.v._bg_hold.interval(), pc.DEFAULT_BG_HOLD_MS)
        self.v.set_background_hold(1200)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_music_playing(True)
        self._drain_background()
        self.v.set_music_playing(False)
        self.assertTrue(self.v._bg_hold.isActive())
        self.assertEqual(self.v._bg_hold.interval(), 1200)

    def _rise_levels(self, key=(0, 0, 0), steps=400):
        levels = []
        for _ in range(steps):
            if not self.v._ramp.isActive():
                return levels
            self.v._step_fades()
            levels.append(self._voice(key).out.volume())
        self.fail("the fade-in never finished")

    def test_by_default_a_fired_bed_fades_in_over_0_2_s(self):
        """'fade in and fade out should be per default both 0.2'."""
        self.assertEqual(pc.DEFAULT_BG_FIRE_FADE_MS, 200)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True, volume=0.5))
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.0)
        levels = self._rise_levels()
        self.assertAlmostEqual(len(levels) * self.v._ramp.interval(), 200,
                               delta=self.v._ramp.interval())
        self.assertAlmostEqual(levels[-1], 0.5)

    def test_no_fire_fade_in_starts_it_at_full_volume(self):
        self.v.set_background_fire_fade(0)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True, volume=0.5))
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.5)
        self.assertFalse(self.v._ramp.isActive())

    def test_a_fired_bed_fades_in_over_the_setting(self):
        """'add a fade in': fired, a 🎶 pad comes up from silence."""
        self.v.set_background_fire_fade(1000)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True, volume=0.5))
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.0)
        levels = self._rise_levels()
        self.assertAlmostEqual(len(levels) * self.v._ramp.interval(), 1000,
                               delta=self.v._ramp.interval())
        self.assertTrue(all(b >= a for a, b in zip(levels, levels[1:], strict=False)))
        self.assertAlmostEqual(levels[-1], 0.5)

    def test_an_ordinary_pad_ignores_the_fade_in(self):
        self.v.set_background_fire_fade(1000)
        self.v.fire((0, 0, 0), _pad("tusch.mp3", volume=0.5))
        self.assertAlmostEqual(self._voice((0, 0, 0)).out.volume(), 0.5)

    def test_tapped_while_fading_in_it_fades_out_from_where_it_got(self):
        self.v.set_background_fire_fade(2000)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        for _ in range(20):
            self.v._step_fades()
        reached = self._voice((0, 0, 0)).out.volume()
        self.assertLess(reached, 1.0)
        self.v.stop((0, 0, 0))
        self.v._step_fades()
        self.assertLess(self._voice((0, 0, 0)).out.volume(), reached,
                        "it never swells up on its way out")
        self._drain_fades()
        self.assertEqual(self.v.playing_keys(), [])
        self.assertAlmostEqual(self._pool()[0].rise, 1.0, msg="reset for the next pad")

    def test_it_never_pulls_the_music_down(self):
        seen = []
        self.v.duckChanged.connect(seen.append)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True, duck=True))
        self.assertEqual(seen, [])

    def test_mute_still_wins(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_muted(True)
        self.v.set_music_playing(True)
        self._drain_background()
        self.assertEqual(self._voice((0, 0, 0)).out.volume(), 0.0)

    def test_by_default_it_keeps_running_under_the_title(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_music_playing(True)
        self._drain_fades()
        self.assertEqual(self.v.playing_keys(), [(0, 0, 0)])

    def test_set_to_pause_a_starting_title_holds_it_once_silent(self):
        """'the pad option stop is wrong it should be pause, it should continue
        playing when music in main player stops'."""
        stopped = []
        self.v.padStopped.connect(stopped.append)
        self.v.set_background_pauses(True)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.fire((0, 0, 1), _pad("tusch.mp3"))
        self.v.set_music_playing(True)
        self._drain_background()
        self.assertEqual(self._voice((0, 0, 0)).player._state, "paused")
        self.assertEqual(self._voice((0, 0, 1)).player._state, "playing",
                         "only background pads pause, a one-shot plays on")
        self.assertEqual(stopped, [])
        self.assertIn((0, 0, 0), self.v.playing_keys(), "it keeps its voice")

    def test_set_to_pause_it_carries_on_from_where_it_was(self):
        self.v.set_background_pauses(True)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self._rise_levels()                     # the fire fade-in lands first
        voice = self._voice((0, 0, 0))
        voice.player._pos = 4200                # 4.2 s into the bed
        self.v.set_music_playing(True)
        self._drain_background()
        self.v.set_music_playing(False)
        self.v._lift_background()               # the hold ran out
        self.assertEqual(voice.player._state, "playing")
        self.assertEqual(voice.player.position(), 4200)
        levels = self._drain_background()
        self.assertTrue(all(b >= a for a, b in zip(levels, levels[1:], strict=False)),
                        "it fades back in, it does not jump")
        self.assertAlmostEqual(voice.out.volume(), 1.0)

    def test_set_to_pause_a_bed_fired_under_a_title_waits(self):
        self.v.set_background_pauses(True)
        self.v.set_music_playing(True)
        while self.v._bg_ramp.isActive():       # no pad yet for _drain_background
            self.v._step_background()
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        voice = self._voice((0, 0, 0))
        self.assertEqual(voice.player._state, "paused")
        self.v.set_music_playing(False)
        self.v._lift_background()
        self.assertEqual(voice.player._state, "playing")

    def test_a_title_starting_again_in_the_hold_keeps_it_paused(self):
        self.v.set_background_pauses(True)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_music_playing(True)
        self._drain_background()
        self.v.set_music_playing(False)         # the gap between two titles
        self.v.set_music_playing(True)
        self.assertFalse(self.v._bg_hold.isActive())
        self.assertEqual(self._voice((0, 0, 0)).player._state, "paused")

    def test_a_paused_bed_can_still_be_stopped(self):
        stopped = []
        self.v.padStopped.connect(stopped.append)
        self.v.set_background_pauses(True)
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))
        self.v.set_music_playing(True)
        self._drain_background()
        self.v.stop_all()
        self._drain_fades()
        self.assertEqual(stopped, [(0, 0, 0)])
        self.assertEqual(self.v.playing_keys(), [])

    def test_the_setting_reads_pause_only_when_it_says_so(self):
        self.assertFalse(pc.background_pauses({}))
        self.assertFalse(pc.background_pauses({"cart_bg_mode": "mute"}))
        self.assertFalse(pc.background_pauses({"cart_bg_mode": 7}))
        self.assertTrue(pc.background_pauses({"cart_bg_mode": "pause"}))
        # What the old option saved: it was meant as pause all along.
        self.assertTrue(pc.background_pauses({"cart_bg_mode": "stop"}))

    def test_the_fade_back_in_setting_is_bounded(self):
        self.assertEqual(pc.background_fade_in_ms({}), pc.DEFAULT_BG_FADE_IN_MS)
        self.assertEqual(pc.background_fade_in_ms({"cart_bg_fade_in_ms": 3500}), 3500)
        self.assertEqual(pc.background_fade_in_ms({"cart_bg_fade_in_ms": 0}), 0)
        self.assertEqual(pc.background_fade_in_ms({"cart_bg_fade_in_ms": -5}), 0)
        self.assertEqual(pc.background_fade_in_ms({"cart_bg_fade_in_ms": 99_000}),
                         pc.MAX_FADE_MS)
        self.assertEqual(pc.background_fade_in_ms({"cart_bg_fade_in_ms": "x"}),
                         pc.DEFAULT_BG_FADE_IN_MS)

    def test_the_dip_setting_is_bounded(self):
        self.assertEqual(pc.background_fade_out_ms({}), pc.DEFAULT_BG_FADE_OUT_MS)
        self.assertEqual(pc.background_fade_out_ms({"cart_bg_fade_out_ms": 900}), 900)
        self.assertEqual(pc.background_fade_out_ms({"cart_bg_fade_out_ms": -1}), 0)
        self.assertEqual(pc.background_fade_out_ms({"cart_bg_fade_out_ms": 99_000}),
                         pc.MAX_FADE_MS)
        self.assertEqual(pc.background_fade_out_ms({"cart_bg_fade_out_ms": None}),
                         pc.DEFAULT_BG_FADE_OUT_MS)

    def test_the_fire_fade_in_setting_is_bounded(self):
        self.assertEqual(pc.background_fire_fade_ms({}), pc.DEFAULT_BG_FIRE_FADE_MS)
        self.assertEqual(pc.background_fire_fade_ms({"cart_bg_fire_fade_ms": 0}), 0)
        self.assertEqual(pc.background_fire_fade_ms({"cart_bg_fire_fade_ms": 1500}), 1500)
        self.assertEqual(pc.background_fire_fade_ms({"cart_bg_fire_fade_ms": 99_000}),
                         pc.MAX_FADE_MS)
        self.assertEqual(pc.background_fire_fade_ms({"cart_bg_fire_fade_ms": "x"}),
                         pc.DEFAULT_BG_FIRE_FADE_MS)

    def test_the_wait_setting_is_bounded(self):
        self.assertEqual(pc.background_hold_ms({}), pc.DEFAULT_BG_HOLD_MS)
        self.assertEqual(pc.background_hold_ms({"cart_bg_hold_ms": 0}), 0)
        self.assertEqual(pc.background_hold_ms({"cart_bg_hold_ms": 99_000}),
                         pc.MAX_FADE_MS)


class StopsOthersPadTest(_VoiceCase):
    """Marcel: "for a pad add an option that it stops other running pads"."""

    def test_it_fades_the_other_pads_out(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", loop=True))
        self.v.fire((0, 0, 1), _pad("applause.mp3"))
        self.v.fire((0, 1, 0), _pad("anthem.mp3", stops_others=True))
        self.assertTrue(self.v.is_playing((0, 1, 0)))
        self.assertFalse(self.v.is_playing((0, 0, 0)))
        self.assertFalse(self.v.is_playing((0, 0, 1)))
        self._drain_fades()
        self.assertEqual([x.key for x in self._live()], [(0, 1, 0)])

    def test_an_ordinary_pad_leaves_the_others_running(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", loop=True))
        self.v.fire((0, 1, 0), _pad("tusch.mp3"))
        self._drain_fades()
        self.assertEqual(len(self._live()), 2)

    def test_a_pad_waiting_for_a_voice_does_not_start_after_it(self):
        for i in range(4):
            self.v.fire((0, 0, i), _pad(f"s{i}.mp3"))
        self.v.fire((0, 1, 0), _pad("late.mp3"))       # steals, waits on the ramp
        self.v.fire((0, 2, 0), _pad("anthem.mp3", stops_others=True))
        self._drain_fades()
        self.assertEqual([x.key for x in self._live()], [(0, 2, 0)])


class BackgroundFollowsTheDeckTest(unittest.TestCase):
    """The window tells the pool when the deck plays — and the wire moves with
    the deck when a crossfade swaps the players."""

    def test_the_deck_state_reaches_the_pool(self):
        from types import SimpleNamespace
        from PySide6.QtMultimedia import QMediaPlayer
        from player.window.main_cartwall import CartwallMixin
        seen = []
        host = SimpleNamespace(
            _cart_voices=SimpleNamespace(set_music_playing=seen.append))
        CartwallMixin._cart_follow_deck(host, QMediaPlayer.PlaybackState.PlayingState)
        CartwallMixin._cart_follow_deck(host, QMediaPlayer.PlaybackState.PausedState)
        CartwallMixin._cart_follow_deck(host, QMediaPlayer.PlaybackState.StoppedState)
        self.assertEqual(seen, [True, False, False])

    def test_no_pool_no_harm(self):
        from types import SimpleNamespace
        from PySide6.QtMultimedia import QMediaPlayer
        from player.window.main_cartwall import CartwallMixin
        CartwallMixin._cart_follow_deck(SimpleNamespace(_cart_voices=None),
                                        QMediaPlayer.PlaybackState.PlayingState)

    def test_it_is_one_of_the_deck_slots(self):
        from types import SimpleNamespace
        from player.window.main_xfade import CrossfadeMixin
        follow = object()
        host = SimpleNamespace(
            _on_media_status=None, _on_player_error=None,
            _audio_device=SimpleNamespace(on_playback_state=None),
            _on_playback_state=None, _taskbar=None, _cart_follow_deck=follow)
        self.assertIn(("playbackStateChanged", follow),
                      CrossfadeMixin._deck_slots(host))


class VoiceLifecycleTest(_VoiceCase):
    """The end of a sample: release, loop again, and what it reports."""

    # ── end of media ─────────────────────────────────────────────────────────
    def test_a_one_shot_releases_its_voice_when_it_ends(self):
        key = (0, 0, 0)
        self.v.fire(key, _pad())
        voice = self._voice(key)
        self._end_of_media(voice)
        self.assertIsNone(voice.key)

    def test_a_sample_that_cannot_be_decoded_frees_its_voice(self):
        """A broken file must not hold a voice (and the duck) forever."""
        from PySide6.QtMultimedia import QMediaPlayer
        for loop in (False, True):
            key = (0, 0, int(loop))
            self.v.fire(key, _pad(f"broken{int(loop)}.mp3", loop=loop, duck=True))
            voice = self._voice(key)
            stopped = []
            self.v.padStopped.connect(stopped.append)
            voice.player.mediaStatusChanged.emit(
                QMediaPlayer.MediaStatus.InvalidMedia)
            self.v.padStopped.disconnect(stopped.append)
            self.assertIsNone(voice.key)
            self.assertEqual(stopped, [key])
        self.assertEqual(self._live(), [])

    def test_a_player_error_frees_its_voice(self):
        from PySide6.QtMultimedia import QMediaPlayer
        key = (0, 0, 0)
        self.v.fire(key, _pad())
        voice = self._voice(key)
        voice.player.errorOccurred.emit(
            QMediaPlayer.Error.FormatError, "no decoder")
        self.assertIsNone(voice.key)

    def test_a_loop_pad_rewinds_and_plays_again_without_setLoops(self):
        key = (0, 0, 0)
        self.v.fire(key, _pad(loop=True))
        voice = self._voice(key)
        before = voice.player.names().count("play")
        self._end_of_media(voice)
        self.assertEqual(voice.key, key, "a bed must survive its own end")
        self.assertEqual(voice.player.names().count("play"), before + 1)
        self.assertNotIn("setLoops", voice.player.names())

    # ── signals ──────────────────────────────────────────────────────────────
    def test_active_counts_up_and_back_down(self):
        seen = []
        self.v.activeChanged.connect(seen.append)
        self.v.fire((0, 0, 0), _pad("a.mp3"))
        self.v.fire((0, 0, 1), _pad("b.mp3"))
        self.v.stop_all()
        self._drain_fades()
        self.assertEqual(seen, [1, 2, 1, 0])

    def test_padStopped_names_the_pad_that_stopped(self):
        seen = []
        self.v.padStopped.connect(seen.append)
        self.v.fire((0, 2, 3), _pad())
        self.v.stop((0, 2, 3))
        self._drain_fades()
        self.assertEqual(seen, [(0, 2, 3)])

    def test_the_tick_timer_only_runs_while_something_plays(self):
        self.assertFalse(self.v._tick.isActive())
        self.v.fire((0, 0, 0), _pad())
        self.assertTrue(self.v._tick.isActive())
        self.v.stop_all()
        self._drain_fades()
        self.v._emit_tick()
        self.assertFalse(self.v._tick.isActive())

    def test_the_tick_reports_the_time_left(self):
        seen = []
        self.v.padTick.connect(seen.append)
        self.v.fire((0, 0, 0), _pad())
        self.v._emit_tick()
        self.assertEqual(seen[0][0][0], (0, 0, 0))
        self.assertEqual(seen[0][0][1], 10_000)


class BackgroundSettingTest(unittest.TestCase):
    """⚙ Settings ▸ 🎛 Cartwall picks mute or pause, and the window hands
    the pick to the pool."""

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_dialog_starts_on_mute_and_saves_the_pick(self):
        dlg = self._dialog({})
        self.assertEqual(dlg._cart_bg_combo.currentData(), "mute")
        dlg._cart_bg_combo.setCurrentIndex(dlg._cart_bg_combo.findData("pause"))
        self.assertEqual(dlg.values()["cart_bg_mode"], "pause")
        self.assertEqual(
            self._dialog({"cart_bg_mode": "pause"})._cart_bg_combo.currentData(), "pause")
        # An old "stop" opens as pause, and saving writes the new name.
        self.assertEqual(
            self._dialog({"cart_bg_mode": "stop"})._cart_bg_combo.currentData(), "pause")

    def test_the_window_passes_it_to_the_pool(self):
        from types import SimpleNamespace
        from typing import Any, cast

        from player.window.main_cartwall import CartwallMixin
        voices = cart_voices.CartVoices(voices=1, factory=_factory)
        self.addCleanup(voices.shutdown)
        from player.audio.mix import OutputMix
        host = cast(Any, SimpleNamespace(_settings={"cart_bg_mode": "pause"},
                                         _cart_voices=voices, _mix=OutputMix()))
        CartwallMixin.apply_cart_settings(host)
        self.assertTrue(voices._bg_pauses)
        host._settings = {}
        CartwallMixin.apply_cart_settings(host)
        self.assertFalse(voices._bg_pauses)

    def test_the_window_passes_the_fade_back_in_to_the_pool(self):
        from types import SimpleNamespace
        from typing import Any, cast

        from player.audio.mix import OutputMix
        from player.window.main_cartwall import CartwallMixin
        voices = cart_voices.CartVoices(voices=1, factory=_factory)
        self.addCleanup(voices.shutdown)
        host = cast(Any, SimpleNamespace(
            _settings={"cart_bg_fade_in_ms": 4500, "cart_bg_fade_out_ms": 600},
            _cart_voices=voices, _mix=OutputMix()))
        CartwallMixin.apply_cart_settings(host)
        self.assertEqual(voices._bg_up_ms, 4500)
        self.assertEqual(voices._bg_down_ms, 600)
        host._settings = {}
        CartwallMixin.apply_cart_settings(host)
        self.assertEqual(voices._bg_up_ms, pc.DEFAULT_BG_FADE_IN_MS)
        self.assertEqual(voices._bg_down_ms, pc.DEFAULT_BG_FADE_OUT_MS)
        host._settings = {"cart_bg_fire_fade_ms": 1200, "cart_bg_hold_ms": 700}
        CartwallMixin.apply_cart_settings(host)
        self.assertEqual(voices._bg_fire_ms, 1200)
        self.assertEqual(voices._bg_hold.interval(), 700)


class CartDuckSettingDialogTest(unittest.TestCase):
    """🎛 How far a pad ducks the music: a percent spin with its dB beside it."""

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_starts_at_a_tenth_and_says_so_in_db(self):
        dlg = self._dialog({})
        self.assertEqual(dlg._cart_duck_spin.value(), 10)
        self.assertEqual(dlg._cart_duck_db.text(), "≈ −20 dB")

    def test_the_db_follows_the_spin_and_the_pick_is_saved(self):
        dlg = self._dialog({"cart_duck_pct": 30})
        self.assertEqual(dlg._cart_duck_db.text(), "≈ −10 dB")
        dlg._cart_duck_spin.setValue(50)
        self.assertEqual(dlg._cart_duck_db.text(), "≈ −6 dB")
        self.assertEqual(dlg.values()["cart_duck_pct"], 50)

    def test_the_desk_duck_shows_its_db_too(self):
        dlg = self._dialog({})
        self.assertEqual(dlg._duck_spin.value(), 20)
        self.assertEqual(dlg._duck_db.text(), "≈ −14 dB")
        dlg._duck_spin.setValue(0)
        self.assertEqual(dlg._duck_db.text(), "−∞ dB")
        self.assertEqual(self._dialog({"duck_pct": 50})._duck_db.text(), "≈ −6 dB")

    def test_a_note_under_the_ducks_spells_out_percent_against_db(self):
        from shared.audio.playback import duck_db_text
        note = self._dialog({})._duck_note.text()
        for pct in (10, 20, 30, 50):
            with self.subTest(pct=pct):
                self.assertIn("%d %% %s" % (pct, duck_db_text(pct)), note)
        self.assertIn("half as loud", note)

    def test_the_window_moves_a_running_pad_duck_to_it(self):
        from types import SimpleNamespace
        from typing import Any, cast

        from player.audio.mix import OutputMix
        from player.window.main_cartwall import CartwallMixin
        mix = OutputMix()
        mix.duck_reason("cartwall", True)
        reasons = []
        host = cast(Any, SimpleNamespace(
            _settings={"cart_duck_pct": 40}, _mix=mix,
            _set_duck_reason=lambda r, on: reasons.append((r, on))))
        CartwallMixin.apply_cart_settings(host)
        self.assertAlmostEqual(mix.duck_target, 0.4)
        self.assertEqual(reasons, [("cartwall", True)], "the ramp has to start")


if __name__ == "__main__":
    unittest.main()
