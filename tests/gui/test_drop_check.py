"""Tests for the live Check-Music marks: dropping / importing tracks runs the
per-track checks plus the round's heat-tempo evenness instantly, offending
rows stay red until the issue is resolved (re-evaluated on every grid edit)."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from gui.running_order import Row, RunningOrder


# The gui modules pull in gui.dialogs, which resolves the state files at import
# time — keep the import at TEST time (see test_heat_tempo.py) so during
# discovery test_state_files still claims DANCEPLAYLIST_STATE_DIR first.
def _import_gui():
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_drop_"))
    from gui import playlist_table
    from gui import table_dnd
    return playlist_table, table_dnd


class _FakeWin:
    """Stands in for the MainWindow: per-track issues and takte are read
    straight off the fake entries; probe flags are recorded per title."""

    def __init__(self):
        self.probed = []
        self.in_final = []

    def _track_issues(self, e, probe_silence=True, in_final=False):
        self.in_final.append(in_final)
        if probe_silence:
            self.probed.append(e.title)
        return list(getattr(e, "issues", []))

    def _entry_takt(self, e):
        return getattr(e, "takt", 0)


def _entry(title, takt=0, issues=()):
    return SimpleNamespace(title=title, takt=takt, issues=list(issues),
                           path=Path(rf"C:\m\{title}.mp3"))


def _slot(entry, rname="Vorrunde", h=0, d=0, backup=False):
    return Row(round_name=rname, h_idx=h, d_idx=d, dance="WW", entry=entry,
               backup=backup)


class IssueMarksTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pt, _dnd = _import_gui()

        class FakeTable:
            _compute_issue_marks = pt.PlaylistTable._compute_issue_marks
            refresh_issue_marks = pt.PlaylistTable.refresh_issue_marks
            host = pt.PlaylistTable.host

            def __init__(self, row_meta):
                self._playlist = {"Vorrunde": []}
                self._row_meta = RunningOrder(row_meta)
                self._issue_paths = {}
                self._current_play_row = -1   # nothing playing
                self._win = _FakeWin()
                self.repainted = []

            def window(self):
                return self._win

            def _fill_song_row(self, r, m, bg):
                self.repainted.append(r)
        cls.FakeTable = FakeTable

    def test_track_issue_is_reported_with_its_title(self):
        t = self.FakeTable([None, _slot(_entry("WW A", 58,
                                               issues=["⏱ Short: 1:30"]))])
        issues = t._compute_issue_marks()
        self.assertEqual(issues, {1: ["“WW A” — ⏱ Short: 1:30"]})

    def test_the_grid_says_which_slots_are_in_the_final(self):
        """The short-Paso-Doble rule needs to know: the row carries the round,
        the window is told per track."""
        t = self.FakeTable([_slot(_entry("PD early", 60)),
                            _slot(_entry("PD final", 60), rname="Finale")])
        t._compute_issue_marks()
        self.assertEqual(t._win.in_final, [False, True])

    def test_takte_spread_marks_the_whole_column(self):
        # T58 vs T60 in the same round+dance spreads by 2 — BOTH heats are
        # flagged, not just the freshly dropped one.
        t = self.FakeTable([_slot(_entry("WW A", 58), h=0),
                            _slot(_entry("WW B", 60), h=1)])
        issues = t._compute_issue_marks()
        self.assertEqual(sorted(issues), [0, 1])
        self.assertIn("differ by 2 takte", issues[0][0])
        self.assertIn("Wiener Walzer", issues[0][0])

    def test_the_marks_read_german_on_a_german_floor(self):
        from planner import i18n
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        t = self.FakeTable([_slot(_entry("WW A", 58, issues=["⏱ Kurz: 1:30"]), h=0),
                            _slot(_entry("WW B", 60), h=1)])
        issues = t._compute_issue_marks()
        self.assertEqual(issues[0], [
            "„WW A“ — ⏱ Kurz: 1:30",
            "🧩 „Vorrunde“: Die Wiener Walzer-Gruppen weichen um 2 Takte ab (erlaubt: 1)"])

    def test_backup_rows_do_not_count_for_the_spread(self):
        t = self.FakeTable([_slot(_entry("WW A", 58), h=0),
                            _slot(_entry("WW alt", 61), h=0, backup=True),
                            _slot(_entry("WW B", 59), h=1)])
        self.assertEqual(t._compute_issue_marks(), {})

    def test_probe_only_the_dropped_rows(self):
        t = self.FakeTable([_slot(_entry("WW A", 58), h=0),
                            _slot(_entry("WW B", 59), h=1)])
        t.refresh_issue_marks(probe_rows={1})
        self.assertEqual(t._win.probed, ["WW B"])

    def test_marks_stay_until_resolved(self):
        bad = _entry("WW B", 60)
        t = self.FakeTable([_slot(_entry("WW A", 58), h=0), _slot(bad, h=1)])
        t.refresh_issue_marks()
        self.assertEqual(sorted(t._issue_paths),
                         [str(_entry("WW A").path), str(bad.path)])
        self.assertEqual(sorted(t.repainted), [0, 1])
        # Nothing changed → no repaint churn.
        t.repainted.clear()
        t.refresh_issue_marks()
        self.assertEqual(t.repainted, [])
        # Fixing the tempo resolves the issue: marks clear, rows repaint.
        bad.takt = 59
        t.refresh_issue_marks()
        self.assertEqual(t._issue_paths, {})
        self.assertEqual(sorted(t.repainted), [0, 1])


class MarkDropIssuesToastTest(unittest.TestCase):
    """_mark_drop_issues toasts the landed rows' problems (spread message
    deduplicated — it spans several rows)."""

    @classmethod
    def setUpClass(cls):
        _pt, dnd = _import_gui()
        cls.dnd = dnd

        class Table(dnd.TableDragDropMixin):
            def __init__(self, canned):
                self._canned = canned
                self.probed = None

            def refresh_issue_marks(self, probe_rows=()):
                self.probed = set(probe_rows)
                return self._canned
        cls.Table = Table

    def _toast(self, canned, rows):
        t = self.Table(canned)
        toasts = []
        orig = self.dnd._show_toast
        self.dnd._show_toast = lambda anchor, text, msec=0: toasts.append(text)
        try:
            t._mark_drop_issues(rows)
        finally:
            self.dnd._show_toast = orig
        return t, toasts

    def test_spread_message_is_deduplicated(self):
        spread = "🧩 “Vorrunde” Wiener Walzer heats differ by 2 takte (allowed: 1)"
        t, toasts = self._toast({0: [spread], 1: ["“WW B” — 🐇 Too fast", spread]},
                                [0, 1])
        self.assertEqual(t.probed, {0, 1})
        self.assertEqual(len(toasts), 1)
        self.assertEqual(toasts[0].count("🧩"), 1)
        self.assertIn("🐇 Too fast", toasts[0])

    def test_clean_drop_stays_silent(self):
        _t, toasts = self._toast({}, [0])
        self.assertEqual(toasts, [])

    def test_only_landed_rows_are_toasted(self):
        _t, toasts = self._toast({0: ["“WW A” — ⏱ Short"],
                                  3: ["“TG X” — ⚡ Tempo"]}, [0])
        self.assertIn("WW A", toasts[0])
        self.assertNotIn("TG X", toasts[0])


if __name__ == "__main__":
    unittest.main()
