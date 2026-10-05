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

from PySide6.QtCore import QCoreApplication, QObject, QUrl, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from planner import cartwall as pc  # noqa: E402
from player import cartwall as gc  # noqa: E402

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
        self.v = gc.CartVoices(voices=4, factory=_factory)
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
        self.assertGreater(len(levels), 4, "0.4 s at 25 ms is many steps")
        self.assertTrue(all(b <= a for a, b in zip(levels, levels[1:])),
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

    # ── rate limiting ────────────────────────────────────────────────────────
    def test_a_double_click_is_one_tap(self):
        key = (0, 0, 0)
        self.assertTrue(self.v.fire(key, _pad()))
        self.assertFalse(self.v.fire(key, _pad()))
        self.assertEqual(len(self._live()), 1)


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


if __name__ == "__main__":
    unittest.main()
