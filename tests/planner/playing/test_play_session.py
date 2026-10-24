#!/usr/bin/env python3
"""▶ Which titles the evening played, kept for picking it up after a crash.

Run:  py -m unittest tests.planner.playing.test_play_session -v

Only an evening still running is offered: state older than the play log's
evening gap is another night, and a party past midnight is still the same one.
"""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from planner.playing import play_session
from planner.playing.play_session import Session
from planner.store import JsonStore

T0 = datetime(2026, 10, 24, 23, 40)


class PlaySessionTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = JsonStore.at(Path(tmp.name) / "play_session.json")
        patcher = mock.patch.object(play_session, "STORE", store)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = store

    def session(self, **kw) -> Session:
        base = {"saved_at": T0, "played": [r"C:\m\a.mp3", r"C:\m\b.mp3"]}
        base.update(kw)
        return Session(**base)

    def save(self, session: Session) -> bool:
        return self.store.write(play_session.to_json(session))

    def test_what_is_saved_comes_back(self):
        self.assertTrue(self.save(self.session()))
        got = play_session.load(T0 + timedelta(minutes=3))
        self.assertEqual(got, self.session())

    def test_no_file_no_evening(self):
        self.assertIsNone(play_session.load(T0))

    def test_a_broken_file_is_no_evening(self):
        self.store.path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(play_session.load(T0))
        self.store.path.write_text('{"played": []}', encoding="utf-8")
        self.assertIsNone(play_session.load(T0))

    def test_past_midnight_it_is_the_same_evening(self):
        self.save(self.session())
        self.assertIsNotNone(play_session.load(T0 + timedelta(hours=1)))

    def test_another_evening_is_never_offered(self):
        self.save(self.session())
        self.assertIsNone(play_session.load(T0 + timedelta(hours=play_session.GAP_HOURS, minutes=1)))

    def test_a_clock_set_back_offers_nothing(self):
        self.save(self.session())
        self.assertIsNone(play_session.load(T0 - timedelta(minutes=5)))

    def test_an_evening_with_nothing_in_it_is_not_offered(self):
        self.save(self.session(played=[]))
        self.assertIsNone(play_session.load(T0))

    def test_clear_forgets_it(self):
        self.save(self.session())
        play_session.clear()
        self.assertIsNone(play_session.load(T0))
        play_session.clear()   # twice is fine


if __name__ == "__main__":
    unittest.main()
