#!/usr/bin/env python3
"""▶ Picking the evening up after a crash or a restart.

Run:  py -m unittest tests.player.audio.test_evening_pick_up -v

Each title that greys writes the evening's played titles down, off the GUI
thread; at start the window offers them. Picked up, they grey again — and
nothing starts. With a title on air the crash question carries this along
(tests/gui/window/test_crash_resume.py); here it is asked on its own.
"""
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QMessageBox

from planner.playing import play_session
from planner.store import JsonStore
from player.audio.on_air_note import OnAirNote
from player.window import main_resume
from tests.player.audio.test_repeat_list import _Desk, _Fixture
from tests.qt_test_support import reap_widget


class EveningPickUpTest(_Fixture):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = JsonStore.at(Path(tmp.name) / "play_session.json")
        self.writer = OnAirNote(self.store)
        for patcher in (mock.patch.object(play_session, "STORE", self.store),
                        mock.patch.object(main_resume, "EVENING", self.writer)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def desk(self) -> _Desk:
        self.deck()   # builds self.table
        desk = _Desk(self.table)
        self.addCleanup(reap_widget, desk)
        self.table.set_play_highlight_enabled(True)
        return desk

    def paths(self) -> list[str]:
        return [m.path_str for r, m in self.table._row_meta.numbered()
                if m.entry is not None]

    def saved(self, minutes_ago: int, played: list[str]):
        self.store.write(play_session.to_json(play_session.Session(
            datetime.now() - timedelta(minutes=minutes_ago), played)))

    # ----- writing it down ----------------------------------------------------

    def test_a_greyed_title_writes_down_what_was_heard(self):
        desk = self.desk()
        p = self.paths()
        self.table.mark_path_played(p[1])
        self.table.mark_path_played(p[0])
        desk._note_session()
        self.assertTrue(self.writer.flush())
        s = play_session.load(datetime.now())
        assert s is not None
        self.assertEqual(s.played, sorted([p[0], p[1]]))

    def test_the_write_is_off_the_gui_thread(self):
        desk = self.desk()
        with mock.patch.object(self.writer, "write") as write, \
                mock.patch.object(self.store, "write") as on_disk:
            desk._note_session()
        write.assert_called_once()
        on_disk.assert_not_called()

    # ----- the offer ----------------------------------------------------------

    def test_without_a_saved_evening_there_is_nothing_to_offer(self):
        self.assertIsNone(self.desk()._evening_to_offer())

    def test_the_offer_does_not_block_and_start_fresh_forgets_it(self):
        desk = self.desk()
        p = self.paths()
        self.saved(12, [p[0], p[1]])
        session = desk._evening_to_offer()
        assert session is not None
        desk._offer_evening(session)
        box = desk.findChild(QMessageBox)
        assert box is not None
        self.assertTrue(box.isVisible())   # open, and the test went on
        self.assertIn("12", box.text())
        self.assertIn("2", box.text())
        fresh = next(b for b in box.buttons()
                     if box.buttonRole(b) == QMessageBox.ButtonRole.RejectRole)
        fresh.click()
        self.assertIsNone(play_session.load(datetime.now()))
        self.assertEqual(self.table._played_paths, set())

    # ----- picking it up ------------------------------------------------------

    def test_picked_up_the_played_grey_again(self):
        desk = self.desk()
        p = self.paths()
        self.saved(3, [p[0], p[1]])
        session = desk._evening_to_offer()
        assert session is not None
        desk._offer_evening(session)
        box = desk.findChild(QMessageBox)
        assert box is not None
        pick = next(b for b in box.buttons()
                    if box.buttonRole(b) == QMessageBox.ButtonRole.AcceptRole)
        pick.click()
        self.assertEqual(self.table._played_paths, {p[0], p[1]})
        self.assertIsNotNone(play_session.load(datetime.now()))   # still this evening's
