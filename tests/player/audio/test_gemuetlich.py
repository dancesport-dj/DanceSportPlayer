"""🛋 Gemütlich: a party's per-dance top tempo.

Run:  py -m unittest tests.player.audio.test_gemuetlich -v

Marcel: replace the TSO button in the party set with a "gemütlich" one - per
dance a maximum speed (Jive T41 instead of T43; Quickstep, Discofox too),
default off, set like the TSO pitch targets in the settings.
"""
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_gem_"))

from PySide6.QtWidgets import QApplication

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from planner.playing.play_sets import (
    GEMUETLICH_DANCES,
    gemuetlich_max_of,
    gemuetlich_of,
)
from player.audio.tso import (
    doubtful_for_gemuetlich,
    doubtful_for_tso,
    gemuetlich_target,
)
from tests.player.audio.test_pitch_gap import _MUSIC, _Card, _Desk, _entry
from tests.qt_test_support import reap_widget


class SettingTest(unittest.TestCase):

    def test_it_is_off_in_every_set_until_switched_on(self):
        for which in ("party", "tournament", "training"):
            self.assertFalse(gemuetlich_of({}, which))

    def test_a_set_can_switch_it_on(self):
        self.assertTrue(gemuetlich_of({"party_set": {"gemuetlich": True}}, "party"))
        self.assertFalse(gemuetlich_of({"party_set": {"gemuetlich": True}}, "training"))

    def test_a_broken_settings_value_is_off(self):
        self.assertFalse(gemuetlich_of({"party_set": "oops"}, "party"))

    def test_jive_has_the_top_tempo_marcel_named(self):
        self.assertEqual(gemuetlich_max_of({}, "JI"), 41)

    def test_quickstep_viennese_waltz_and_discofox_have_theirs_too(self):
        self.assertEqual(gemuetlich_max_of({}, "QS"), 50)
        self.assertEqual(gemuetlich_max_of({}, "WW"), 58)
        self.assertEqual(gemuetlich_max_of({}, "DISCOFOX"), 30)

    def test_a_dance_without_a_limit_has_none(self):
        self.assertIsNone(gemuetlich_max_of({}, "SA"))

    def test_a_shipped_limit_can_still_be_switched_off(self):
        self.assertIsNone(gemuetlich_max_of({"gemuetlich_max": {"QS": 0}}, "QS"))

    def test_the_settings_limit_wins(self):
        s = {"gemuetlich_max": {"QS": 48, "JI": 40.5}}
        self.assertEqual(gemuetlich_max_of(s, "QS"), 48)
        self.assertEqual(gemuetlich_max_of(s, "JI"), 40.5)

    def test_zero_or_junk_means_no_limit(self):
        s = {"gemuetlich_max": {"QS": 0, "JI": "fast", "SA": -3}}
        for d in ("QS", "JI", "SA"):
            self.assertIsNone(gemuetlich_max_of(s, d))

    def test_the_settings_offer_the_dances_named(self):
        for d in ("JI", "QS", "DISCOFOX"):
            self.assertIn(d, GEMUETLICH_DANCES)


class TargetTest(unittest.TestCase):

    def test_a_title_over_the_limit_is_slowed_to_it(self):
        self.assertEqual(gemuetlich_target(43, 41), 41)

    def test_a_title_at_or_under_the_limit_is_left_alone(self):
        self.assertIsNone(gemuetlich_target(41, 41))
        self.assertIsNone(gemuetlich_target(39, 41))

    def test_no_limit_leaves_it_alone(self):
        self.assertIsNone(gemuetlich_target(60, None))

    def test_no_tempo_leaves_it_alone(self):
        self.assertIsNone(gemuetlich_target(0, 41))


class _GemCard(_Card):

    def __init__(self, log, gem: bool, tso: bool = False, tso_hidden: bool = False,
                 gem_hidden: bool = False):
        super().__init__(log, tso=tso)
        self._gem = gem
        self._tso_hidden = tso_hidden
        self._gem_hidden = gem_hidden

    def tso_applies(self) -> bool:
        return self._tso and not self._tso_hidden

    def gemuetlich_mode(self) -> bool:
        return self._gem

    def gemuetlich_applies(self) -> bool:
        return self._gem and not self._gem_hidden


class LoadPathTest(unittest.TestCase):
    """The real `_load_track`: a title over the top is slowed before play."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def play(self, entries, gem=True, settings=None, tso=False, tso_hidden=False,
             gem_hidden=False):
        table = PlaylistTable()
        self.addCleanup(reap_widget, table)
        table.load_warmup(entries, "🤸 Eintanzen", "both", "S", False,
                          lambda *a: None, None, running_order=False)
        rows = [r for r, m in enumerate(table._row_meta)
                if m and m.entry is not None]
        desk = _Desk(table, False, settings)
        self.addCleanup(reap_widget, desk)
        desk._big_player = _GemCard(desk.log, gem, tso, tso_hidden, gem_hidden)
        table._current_play_row = rows[0]
        desk._load_track(table._row_meta[rows[0]].entry.path)
        return desk

    def test_a_jive_over_the_top_is_slowed_to_it_before_play(self):
        desk = self.play([_entry("JI", 1, 43)])
        self.assertEqual(desk._big_player.target, 41)
        self.assertLess(desk.log.index("pitch"), desk.log.index("play"))

    def test_a_jive_under_the_top_is_not_touched(self):
        desk = self.play([_entry("JI", 1, 40)])
        self.assertNotIn("pitch", desk.log)

    def test_a_dance_without_a_limit_is_not_touched(self):
        desk = self.play([_entry("SA", 1, 60)])
        self.assertNotIn("pitch", desk.log)

    def test_the_shipped_quickstep_limit_applies(self):
        desk = self.play([_entry("QS", 1, 52)])
        self.assertEqual(desk._big_player.target, 50)

    def test_the_settings_limit_applies(self):
        desk = self.play([_entry("QS", 1, 52)],
                         settings={"gemuetlich_max": {"QS": 48}})
        self.assertEqual(desk._big_player.target, 48)

    def test_with_the_button_off_nothing_is_pitched(self):
        desk = self.play([_entry("JI", 1, 43)], gem=False)
        self.assertNotIn("pitch", desk.log)

    def test_gemuetlich_wins_over_a_tso_pitch_that_is_still_on(self):
        # The party list hides the TSO button but keeps its stored value; with
        # both on, the round's mean (T43) was pitched instead of the top (T41).
        desk = self.play([_entry("JI", 1, 43), _entry("JI", 2, 43)], tso=True)
        self.assertEqual(desk._big_player.target, 41)

    def test_a_t42_jive_in_a_t43_list_is_slowed_not_raised(self):
        # The reported case: T42 went to T43 (the list's mean) instead of T41.
        desk = self.play([_entry("JI", 1, 42), _entry("JI", 2, 43),
                          _entry("JI", 3, 43)], tso=True)
        self.assertEqual(desk._big_player.target, 41)

    def test_a_hidden_tso_never_pitches_on_the_party_list(self):
        # Marcel: the party list shows gemuetlich IN PLACE of TSO, so the logic of
        # the button that is not there must not run, not even as a fallback.
        desk = self.play([_entry("JI", 1, 43), _entry("JI", 2, 43)],
                         gem=False, tso=True, tso_hidden=True)
        self.assertNotIn("pitch", desk.log)

    def test_a_hidden_gemuetlich_never_pitches_on_a_tournament_list(self):
        # The mirror: a tournament list hides the 🛋 button but keeps its stored
        # value; the logic of the button that is not there must not run, so TSO
        # (whose button is on show) pitches to the round's mean, not to the top.
        desk = self.play([_entry("JI", 1, 43), _entry("JI", 2, 43)],
                         gem=True, gem_hidden=True, tso=True)
        self.assertEqual(desk._big_player.target, 43)

    def test_a_hidden_gemuetlich_with_tso_off_pitches_nothing(self):
        desk = self.play([_entry("JI", 1, 43)], gem=True, gem_hidden=True)
        self.assertNotIn("pitch", desk.log)

    def test_without_gemuetlich_tso_still_pitches(self):
        desk = self.play([_entry("JI", 1, 43), _entry("JI", 2, 43)],
                         gem=False, tso=True)
        self.assertEqual(desk._big_player.target, 43)


def _unlabelled(dance: str, i: int, measured: float | None):
    """A title whose file name carries no takt ("?" in the list), with the
    tempo librosa measured for it, in beats/min."""
    e = _entry(dance, i, None)
    e.features = SimpleNamespace(bpm=measured) if measured else None
    return e


class MeasuredTaktTest(unittest.TestCase):
    """A "?" title has no takt in its name; the measured tempo ÷ the dance's
    beats per bar stands in for it, so gemütlich and TSO can still pitch it."""

    setUpClass = classmethod(lambda cls: LoadPathTest.setUpClass.__func__(cls))
    play = LoadPathTest.play

    def test_a_jive_without_a_label_is_slowed_from_what_was_measured(self):
        desk = self.play([_unlabelled("JI", 1, 172)])    # 172 / 4 = T43
        self.assertEqual(desk._big_player.target, 41)

    def test_the_card_is_told_the_takt_the_measure_gave(self):
        desk = self.play([_unlabelled("JI", 1, 172)])
        self.assertEqual(desk._big_player.takt, 43)

    def test_a_measured_tempo_under_the_top_is_left_alone(self):
        desk = self.play([_unlabelled("JI", 1, 160)])    # T40
        self.assertNotIn("pitch", desk.log)

    def test_a_discofox_without_a_label_is_slowed_from_what_was_measured(self):
        # The reported case: "Party Mix I" (a Discofox, no takt in its name) was
        # measured at 129 bpm and played as it was. Discofox is 4/4, so 129 / 4
        # is T32, over the T30 top.
        desk = self.play([_unlabelled("DISCOFOX", 1, 129)])
        self.assertEqual(desk._big_player.takt, 32)
        self.assertEqual(desk._big_player.target, 30)

    def test_a_discofox_known_only_by_its_folder_is_slowed_too(self):
        # The reported case: "Udo Jürgens - Erste Sahne Mix" sits in a discofox
        # folder with no dance in its name or tags, so the library leaves
        # .dance empty and keeps the Discofox in other_genre. The party row is a
        # Discofox (it was announced as one), but 🛋 read the title's own empty
        # dance: no top, no meter, played as recorded at 129 bpm.
        e = MusicEntry(path=_MUSIC / "discofox" / "Erste Sahne Mix.mp3",
                       title="Erste Sahne Mix", dance=None,
                       other_genre="Discofox", duration=180, bpm=None)
        e.features = SimpleNamespace(bpm=129.2)
        desk = self.play([e])
        self.assertEqual(desk._big_player.takt, 32)
        self.assertEqual(desk._big_player.target, 30)

    def test_every_dance_gemuetlich_can_limit_has_a_meter(self):
        # Gemütlich is not TSO: its limit is set per dance for all of these, so
        # a title without a label in any of them must get a takt from its tempo.
        from player.audio.tso import PITCH_BEATS_PER_BAR
        for dance in GEMUETLICH_DANCES:
            with self.subTest(dance=dance):
                self.assertIn(dance, PITCH_BEATS_PER_BAR)

    def test_the_social_dances_are_slowed_from_what_was_measured(self):
        # Limit T45, measured 192 bpm = T48 in four: slowed to the limit, with
        # TSO off (these dances have no TSO band).
        for dance in ("SALSA", "DISCOFOX", "BACHATA", "WCS", "KIZOMBA",
                      "FORRO", "BW", "LD"):
            with self.subTest(dance=dance):
                desk = self.play([_unlabelled(dance, 1, 192)],
                                 settings={"gemuetlich_max": {dance: 45}})
                self.assertEqual(desk._big_player.takt, 48)
                self.assertEqual(desk._big_player.target, 45)

    def test_nothing_measured_leaves_it_alone(self):
        desk = self.play([_unlabelled("JI", 1, None)])
        self.assertNotIn("pitch", desk.log)
        self.assertIsNone(desk._big_player.takt)

    def test_a_labelled_title_still_uses_its_label(self):
        e = _entry("JI", 1, 43)
        e.features = SimpleNamespace(bpm=120)            # the label wins
        desk = self.play([e])
        self.assertEqual(desk._big_player.target, 41)
        self.assertEqual(desk._big_player.takt, 43)

    def test_tso_pitches_a_title_without_a_label_into_its_round(self):
        # Round T43 + T43, the third title measured T44: one takt off, so TSO
        # brings it to the round's 43.
        desk = self.play([_unlabelled("JI", 1, 176), _entry("JI", 2, 43),
                          _entry("JI", 3, 43)], gem=False, tso=True)
        self.assertEqual(desk._big_player.target, 43)

    def test_tso_leaves_a_title_without_a_label_or_a_measure_alone(self):
        desk = self.play([_unlabelled("JI", 1, None)], gem=False, tso=True)
        self.assertNotIn("pitch", desk.log)


class DoubtfulMeasureTest(unittest.TestCase):
    """A measured tempo far from where the dance lives is probably a wrong
    measure (half or double time). The title is left as it is and the user
    is told, once, in a toast."""

    setUpClass = classmethod(lambda cls: LoadPathTest.setUpClass.__func__(cls))
    play = LoadPathTest.play

    def play_toasted(self, entries, **kw):
        with mock.patch("player.window.main_player.show_toast") as toast:
            desk = self.play(entries, **kw)
        return desk, toast

    def test_gemuetlich_slows_a_measure_three_takte_over_the_top(self):
        desk, toast = self.play_toasted([_unlabelled("JI", 1, 176)])  # T44
        self.assertEqual(desk._big_player.target, 41)
        toast.assert_not_called()

    def test_gemuetlich_leaves_a_measure_more_than_three_over_alone(self):
        desk, toast = self.play_toasted([_unlabelled("JI", 1, 180)])  # T45
        self.assertNotIn("pitch", desk.log)
        self.assertEqual(toast.call_count, 1)
        text = toast.call_args.args[1]
        self.assertIn("T45", text)
        self.assertIn("T41", text)

    def test_the_toast_comes_once_although_the_load_asks_twice(self):
        # `_pitch_before_play` and `_show_big_now` both try when nothing was set.
        desk, toast = self.play_toasted([_unlabelled("JI", 1, 180)])
        self.assertEqual(toast.call_count, 1)

    def test_a_label_is_trusted_however_far_over_the_top(self):
        desk, toast = self.play_toasted([_entry("JI", 1, 50)])
        self.assertEqual(desk._big_player.target, 41)
        toast.assert_not_called()

    def test_tso_pitches_a_measure_two_takte_outside_the_range(self):
        desk, toast = self.play_toasted([_unlabelled("JI", 1, 184)],   # T46
                                        gem=False, tso=True)           # 42-44
        self.assertEqual(desk._big_player.target, 44)
        toast.assert_not_called()

    def test_a_rumba_measured_two_takte_under_its_band_is_pitched(self):
        desk, toast = self.play_toasted([_unlabelled("RB", 1, 88)],    # T22
                                        gem=False, tso=True)           # 24-26
        self.assertEqual(desk._big_player.target, 24)
        toast.assert_not_called()

    def test_tso_leaves_a_measure_more_than_two_takte_outside_alone(self):
        for measured in (188, 156):                                    # T47, T39
            with self.subTest(measured=measured):
                desk, toast = self.play_toasted(
                    [_unlabelled("JI", 1, measured)], gem=False, tso=True)
                self.assertNotIn("pitch", desk.log)
                self.assertEqual(toast.call_count, 1)
                self.assertIn("T%d" % (measured // 4), toast.call_args.args[1])

    def test_tso_trusts_a_label_outside_the_range(self):
        desk, toast = self.play_toasted([_entry("JI", 1, 50)],
                                        gem=False, tso=True)
        self.assertIsNotNone(desk._big_player.target)
        toast.assert_not_called()

    def test_tso_counts_a_measured_title_in_the_round(self):
        # Playing the T42 of [T42, measured T44]: the round is on 42 and 44,
        # so it is pitched to the middle, 43. Counting labels only left it on 42.
        desk, toast = self.play_toasted(
            [_entry("JI", 1, 42), _unlabelled("JI", 2, 176)], gem=False, tso=True)
        self.assertEqual(desk._big_player.target, 43)

    def test_tso_does_not_count_a_measure_it_does_not_trust(self):
        desk, toast = self.play_toasted(
            [_entry("JI", 1, 42), _unlabelled("JI", 2, 188)], gem=False, tso=True)
        self.assertEqual(desk._big_player.target, 42)

    def test_a_dance_without_a_band_is_not_judged(self):
        self.assertFalse(doubtful_for_tso("DISCOFOX", 99))

    def test_the_limits_are_two_takte_for_tso_and_three_for_gemuetlich(self):
        self.assertFalse(doubtful_for_tso("JI", 46))     # band 42-44
        self.assertTrue(doubtful_for_tso("JI", 47))
        self.assertFalse(doubtful_for_tso("JI", 40))
        self.assertTrue(doubtful_for_tso("JI", 39))
        self.assertFalse(doubtful_for_gemuetlich(44, 41))
        self.assertTrue(doubtful_for_gemuetlich(45, 41))


if __name__ == "__main__":
    unittest.main()
