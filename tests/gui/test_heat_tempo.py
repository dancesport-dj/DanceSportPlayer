"""Tests for the Check-Music round-structure checks (heat tempo evenness,
final/semifinal taper) and the report's slot-jump resolution: within a round
every heat should dance the same dance at (nearly) the same takt — a spread
over 1 takt (e.g. a WW round with T58 / T59 / T60 heats) is flagged."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from gui.deck import Deck
from gui.running_order import Row, RunningOrder
from planner.models import MusicEntry


# gui.main_import pulls in gui.dialogs, which resolves the state files at
# import time — keep the import at TEST time (see test_silence.py) so during
# discovery test_state_files still claims DANCEPLAYLIST_STATE_DIR first.
def _import_mixin():
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_heat_"))
    from gui.main_import import ImportMixin
    return ImportMixin


class _FakeWindow:
    _BEATS_PER_BAR = {"LW": 3, "WW": 3, "QS": 4}

    def deck(self, table):
        """A bare Deck is enough here: the checks only read name and folded."""
        return Deck(table)


def _e(dance, takt=None, measured=None):
    feats = SimpleNamespace(bpm=float(measured)) if measured else None
    return MusicEntry(path=Path(rf"C:\music\{dance}{takt or measured}.mp3"),
                      title=f"{dance} {takt}", dance=dance, bpm=takt,
                      features=feats)


def _table(playlist, dances):
    return SimpleNamespace(_playlist=playlist,
                           current_dances=lambda: list(dances))


class HeatTempoSpreadTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _import_mixin()):
            pass
        cls.win = Win()

    def _warns(self, playlist, dances=("WW",)):
        return self.win._playlist_structure_issues(_table(playlist, dances))

    def test_spread_over_one_takt_warns(self):
        pl = {"Vorrunde": [[_e("WW", 58)], [_e("WW", 59)], [_e("WW", 60)]]}
        warns = self._warns(pl)
        self.assertEqual(len(warns), 1)
        self.assertIn("differ by 2 takte", warns[0])
        # Each offender is named with its heat position, takt and title.
        self.assertIn("heat 1: T58 “WW 58”", warns[0])
        self.assertIn("heat 2: T59 “WW 59”", warns[0])
        self.assertIn("heat 3: T60 “WW 60”", warns[0])

    def test_one_takt_spread_is_fine(self):
        pl = {"Vorrunde": [[_e("WW", 58)], [_e("WW", 59)], [_e("WW", 59)]]}
        self.assertEqual(self._warns(pl), [])

    def test_single_heat_round_is_skipped(self):
        pl = {"Final": [[_e("WW", 58)]]}
        self.assertEqual(self._warns(pl), [])

    def test_unknown_takt_is_ignored(self):
        pl = {"Vorrunde": [[_e("WW", 58)], [_e("WW", None)], [_e("WW", 59)]]}
        self.assertEqual(self._warns(pl), [])

    def test_measured_tempo_fallback(self):
        # No filename label, but a measured 180 bpm WW (3/4) reads T60.
        pl = {"Vorrunde": [[_e("WW", 58)], [_e("WW", None, measured=180.0)]]}
        warns = self._warns(pl)
        self.assertEqual(len(warns), 1)
        self.assertIn("heat 1: T58", warns[0])
        self.assertIn("heat 2: T60", warns[0])

    def test_findings_carry_slot_targets(self):
        # The findings variant marks each offender with its grid slot so the
        # Music-check report can render it as a jump link into the deck.
        pl = {"Vorrunde": [[_e("WW", 58)], [_e("WW", 59)], [_e("WW", 60)]]}
        finds = self.win._playlist_structure_findings(_table(pl, ("WW",)))
        self.assertEqual(len(finds), 1)
        slots = [s for _, s in finds[0] if s is not None]
        self.assertEqual(slots, [("Vorrunde", 0, 0), ("Vorrunde", 1, 0),
                                 ("Vorrunde", 2, 0)])
        # The plain-string view stays the concatenation of the segments.
        self.assertEqual("".join(t for t, _ in finds[0]), self._warns(pl)[0])

    def test_missing_heat_findings_target_the_gap(self):
        pl = {"Vorrunde": [
            [_e("LW", 29), _e("WW", 58)],
            [_e("LW", 29), None],
        ]}
        finds = self.win._playlist_structure_findings(_table(pl, ("LW", "WW")))
        self.assertEqual(len(finds), 1)
        slots = [s for _, s in finds[0] if s is not None]
        self.assertEqual(slots, [("Vorrunde", 1, 1)])   # heat 2, WW column

    def test_uneven_counts_name_missing_heats(self):
        # WW is missing from heat 2 — the warning should say exactly where.
        pl = {"Vorrunde": [
            [_e("LW", 29), _e("WW", 58)],
            [_e("LW", 29), None],
        ]}
        warns = self._warns(pl, dances=("LW", "WW"))
        self.assertEqual(len(warns), 1)
        self.assertIn("uneven dance counts", warns[0])
        self.assertIn("Wiener Walzer 1/2 (missing in heat 2)", warns[0])

    def test_dances_checked_independently(self):
        # LW is even, WW is spread — only WW warns.
        pl = {"Vorrunde": [
            [_e("LW", 29), _e("WW", 58)],
            [_e("LW", 29), _e("WW", 60)],
        ]}
        warns = self._warns(pl, dances=("LW", "WW"))
        self.assertEqual(len(warns), 1)
        self.assertIn("Wiener Walzer", warns[0])


class TaperTest(unittest.TestCase):
    """Section B: a multi-round field must taper to 2 semifinal / 1 final heats."""

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _import_mixin()):
            pass
        cls.win = Win()

    def _warns(self, playlist, dances=("WW",)):
        return self.win._playlist_structure_issues(_table(playlist, dances))

    def test_wrong_taper_warns(self):
        pl = {"Semifinale": [[_e("WW", 58)]],
              "Finale": [[_e("WW", 58)], [_e("WW", 58)]]}
        warns = self._warns(pl)
        self.assertIn("Final “Finale” has 2 heats, expected 1.", warns)
        self.assertIn("Semifinal “Semifinale” has 1 heats, expected 2.", warns)

    def test_correct_taper_is_silent(self):
        pl = {"Semifinale": [[_e("WW", 58)], [_e("WW", 58)]],
              "Finale": [[_e("WW", 58)]]}
        self.assertEqual(self._warns(pl), [])

    def test_single_round_field_is_skipped(self):
        pl = {"Finale": [[_e("WW", 58)], [_e("WW", 58)]]}
        self.assertEqual(self._warns(pl), [])


class SuspectProgressTest(unittest.TestCase):
    """_compute_music_suspects ticks progress_cb once per UNIQUE track (cross-
    deck duplicates don't tick twice) — feeds the 🎵 BusyDialog."""

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _import_mixin()):
            def __init__(self, tables):
                self._tables = tables

            def _checkable_deck_tables(self):
                return self._tables

            def _track_issues(self, e, probe_silence=True, in_final=False):
                return []

            def _playlist_structure_findings(self, table):
                return []
        cls.Win = Win

    def test_ticks_once_per_unique_track(self):
        class T:
            def __init__(self, row_meta):
                self._row_meta = row_meta
        e1, e2 = _e("WW", 58), _e("WW", 59)
        t1 = T(RunningOrder([None, Row(entry=e1), Row(entry=e2)]))
        t2 = T(RunningOrder([Row(entry=e1)]))   # same track, a second deck
        win = self.Win([t1, t2])
        ticks = []
        res = win._compute_music_suspects(
            progress_cb=lambda d, t, name="": ticks.append((d, t)))
        self.assertEqual(ticks, [(1, 2), (2, 2)])
        self.assertEqual(res[1], 2)   # checked == unique tracks

    def test_the_same_track_is_checked_again_for_the_final(self):
        """⏱ too short only bites in the final. A Paso danced in a Vorrunde AND
        in the Finale must therefore be checked twice — deduping on the path
        alone froze the verdict on whichever deck happened to be scanned first,
        and the final's warning never appeared."""
        class T:
            def __init__(self, row_meta):
                self._row_meta = row_meta
        seen_finals = []

        class Win(self.Win):
            def _track_issues(self, e, probe_silence=True, in_final=False):
                seen_finals.append(in_final)
                return []

        e = _e("PD", 60)
        early = T(RunningOrder([Row(entry=e, round_name="Vorrunde")]))
        final = T(RunningOrder([Row(entry=e, round_name="Finale",
                                    tier="final")]))
        res = Win([early, final])._compute_music_suspects()
        self.assertEqual(sorted(seen_finals), [False, True])
        self.assertEqual(res[1], 2)


class FocusSlotTest(unittest.TestCase):
    """_focus_slot_in_deck resolves a (round, heat, dance) slot to its table row
    — including empty slots — and skips backup rows stacked under a slot."""

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _import_mixin()):
            def __init__(self):
                self.revealed = []

            def _reveal_deck_row(self, table, r):
                self.revealed.append(r)
        cls.Win = Win

    @staticmethod
    def _slot_meta(rname, h, d, entry="x", backup=False):
        return Row(round_name=rname, h_idx=h, d_idx=d, entry=entry,
                   backup=backup)

    def test_finds_the_slot_row(self):
        table = SimpleNamespace(_row_meta=RunningOrder([
            None,                                     # header span row
            self._slot_meta("Finale", 0, 0),          # row 1
            self._slot_meta("Finale", 0, 0, backup=True),
            self._slot_meta("Finale", 0, 1, entry=None),   # row 3, empty slot
        ]))
        win = self.Win()
        self.assertTrue(win._focus_slot_in_deck(table, "Finale", 0, 0))
        self.assertTrue(win._focus_slot_in_deck(table, "Finale", 0, 1))
        self.assertEqual(win.revealed, [1, 3])

    def test_unknown_slot_returns_false(self):
        table = SimpleNamespace(
            _row_meta=RunningOrder([self._slot_meta("Finale", 0, 0)]))
        win = self.Win()
        self.assertFalse(win._focus_slot_in_deck(table, "Vorrunde", 0, 0))
        self.assertEqual(win.revealed, [])


if __name__ == "__main__":
    unittest.main()
