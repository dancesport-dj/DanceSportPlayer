"""🕒 Timetable dialog details from review (#66, #86)."""
import unittest
from datetime import timedelta

from PySide6.QtCore import QTime

from player.presenter.timetable import Entry, Timetable
from tests.player.presenter.test_presenter_timetable import qapp, reap_widget


def _dlg(table, offset=None):
    from player.presenter.timetable_dialog import TimetableDialog
    qapp()
    return TimetableDialog(table, None, now_offset=offset)


class TimetableDialogDetailsTest(unittest.TestCase):

    def make(self, table, offset=None):
        dlg = _dlg(table, offset)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_a_saved_empty_programme_stays_empty(self):
        """#66: it came back with the five example rows."""
        dlg = self.make(Timetable(title="Ball", entries=[]))
        self.assertEqual(dlg.table.rowCount(), 0)

    def test_no_programme_at_all_starts_from_the_examples(self):
        self.assertGreater(self.make(None).table.rowCount(), 0)

    def test_a_row_with_only_an_until_or_a_note_is_kept(self):
        """#86: they were dropped as 'blank'."""
        dlg = self.make(Timetable(entries=[Entry(time="", what="", until="20", note="n")]))
        self.assertEqual(len(dlg.timetable().entries), 1)

    def test_a_row_that_is_really_blank_is_still_dropped(self):
        dlg = self.make(Timetable(entries=[Entry(time="", what="")]))
        dlg.table.setRowCount(2)
        self.assertEqual(dlg.timetable().entries, [])

    def test_switching_the_clock_on_without_typing_a_time_adds_no_shift(self):
        """#86: the field shows whole minutes, so the shift drifted by up to 59 s."""
        dlg = self.make(Timetable(entries=[Entry(time="20:00", what="x")]))
        dlg.now_check.setChecked(True)
        self.assertEqual(dlg.now_offset(), timedelta())

    def test_toggling_the_clock_off_and_on_keeps_the_exact_shift(self):
        shift = timedelta(minutes=-45, seconds=-30)
        dlg = self.make(Timetable(entries=[Entry(time="20:00", what="x")]), shift)
        dlg.now_check.setChecked(False)
        dlg.now_check.setChecked(True)
        self.assertEqual(dlg.now_offset(), shift)

    def test_a_typed_time_still_sets_a_shift(self):
        dlg = self.make(Timetable(entries=[Entry(time="20:00", what="x")]))
        dlg.now_check.setChecked(True)
        dlg.now_time.setTime(QTime(3, 0))
        self.assertIsNotNone(dlg.now_offset())


if __name__ == "__main__":
    unittest.main()
