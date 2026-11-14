"""📜 A pad that ran for 10 s goes into the play log under "Cartwall".

Songs are logged once they have been heard for 10 s; a pad is held to the same
rule, so a Tusch does not clutter the report but a birthday track does.

Run:  py -m unittest tests.player.test_cartwall_play_log -v
"""
import datetime as dt
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from planner.playing import play_log
from planner.playing.cartwall import CartPad
from player.window.main_cartwall import CartwallMixin
from tests.db_support import use_scratch_db


class _Desk(CartwallMixin):
    def __init__(self, playing=True, with_db=True):
        self._playing = playing
        self._library = SimpleNamespace(cache=object() if with_db else None)
        self._PLAYED_AFTER_MS = 10_000

    def _is_playing_mode(self):
        return self._playing


class PadPlayLogTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_pad_log_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")

    def logged(self):
        return [p for e in play_log.evenings() for p in play_log.plays(e)]

    def pad(self, label="Happy Birthday"):
        return CartPad(path=r"C:\samples\birthday.mp3", label=label)

    def test_a_pad_heard_for_ten_seconds_is_logged_as_cartwall(self):
        before = dt.datetime.now()
        _Desk()._on_cart_pad_played(self.pad(), 31.0)
        after = dt.datetime.now()
        (p,) = self.logged()
        self.assertEqual((p.title, p.list_name, p.length, p.dance),
                         ("Happy Birthday", play_log.CARTWALL_LIST, 31.0, ""))
        # It started when the sound did, not when it ended.
        gap = dt.timedelta(seconds=31)
        self.assertLessEqual(before - gap - dt.timedelta(seconds=1), p.started_at)
        self.assertLessEqual(p.started_at, after - gap)

    def test_a_pad_without_a_label_is_named_after_its_file(self):
        _Desk()._on_cart_pad_played(self.pad(label=""), 20.0)
        self.assertEqual(self.logged()[0].title, "birthday")

    def test_a_short_pad_is_not_logged(self):
        _Desk()._on_cart_pad_played(self.pad(), 9.9)
        self.assertEqual(self.logged(), [])

    def test_planning_mode_logs_nothing(self):
        _Desk(playing=False)._on_cart_pad_played(self.pad(), 31.0)
        self.assertEqual(self.logged(), [])

    def test_a_desk_without_a_database_logs_nothing(self):
        _Desk(with_db=False)._on_cart_pad_played(self.pad(), 31.0)
        self.assertEqual(self.logged(), [])


if __name__ == "__main__":
    unittest.main()
