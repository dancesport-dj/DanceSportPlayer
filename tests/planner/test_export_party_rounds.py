#!/usr/bin/env python3
"""A party list exports with its ROUNDS written into the .m3u.

Run:  py -m unittest tests.planner.test_export_party_rounds -v

An Eintanzen / party list is one flat running order, and what an operator wants
to read off the printed file is where each round starts — Standardrunde 1,
Lateinrunde 1, Socialrunde 1 — not the "# ══ (1 Heat) ══" / "# ── Tango ──"
scaffolding a competition draw is exported with. Those heat comments say
nothing here: a party list has no heats and no draw.

A list that is NOT a party list keeps a bare flat export, so a theme list or a
wishlist is unchanged.
"""

import tempfile
import unittest
from pathlib import Path

from planner.m3u import export_flat_m3u
from planner.models import MusicEntry

_DIR = Path(tempfile.mkdtemp(prefix="dp_export_party_"))

# One evening's worth of rounds: Standard, Latin, social, Standard again.
_PARTY = (["LW", "TG", "QS"] + ["SA", "CC", "RB"] + ["DISCOFOX"]
          + ["LW", "SF", "QS"] + ["CC", "RB", "JI"])


def _entry(dance: str, i: int) -> MusicEntry:
    if dance == "DISCOFOX":
        return MusicEntry(path=Path(rf"C:\music\others\df{i}.mp3"),
                          title=f"Social {i}", dance=None,
                          other_genre="Discofox", duration=180)
    return MusicEntry(path=Path(rf"C:\music\{dance}\{dance}{i}.mp3"),
                      title=f"{dance} {i}", dance=dance, duration=180)


def _party_entries():
    return [_entry(d, i) for i, d in enumerate(_PARTY)]


def _lines(m3u: Path) -> list[str]:
    return m3u.read_text(encoding="utf-8").splitlines()


def _headers(m3u: Path) -> list[str]:
    """Every comment line that is not an #EXT tag, stripped of its rule."""
    return [ln.strip("# ─═").strip() for ln in _lines(m3u)
            if ln.startswith("#") and not ln.upper().startswith("#EXT")]


def _tracks(m3u: Path) -> list[str]:
    return [ln for ln in _lines(m3u) if ln.strip() and not ln.startswith("#")]


class PartyExportTest(unittest.TestCase):

    def test_the_rounds_are_written_as_headers(self):
        out = export_flat_m3u(_party_entries(), "party",
                              out_path=_DIR / "party.m3u")
        self.assertEqual(_headers(out),
                         ["Standardrunde 1", "Lateinrunde 1", "Socialrunde 1",
                          "Standardrunde 2", "Lateinrunde 2"])

    def test_no_heat_comments_anywhere(self):
        """The competition scaffolding has no meaning on a party list."""
        out = export_flat_m3u(_party_entries(), "party",
                              out_path=_DIR / "noheats.m3u")
        text = out.read_text(encoding="utf-8")
        self.assertNotIn("Heat", text)
        self.assertNotIn("(no song found)", text)

    def test_every_track_still_gets_out_in_order(self):
        """The headers are added around the list, never instead of part of it."""
        entries = _party_entries()
        out = export_flat_m3u(entries, "party", out_path=_DIR / "order.m3u")
        self.assertEqual(_tracks(out), [str(e.path) for e in entries])

    def test_a_flat_list_that_is_no_party_gets_no_headers(self):
        """A theme list or a wishlist exports exactly as it did before."""
        entries = [_entry("LW", 0), _entry("TG", 1), _entry("QS", 2)]
        out = export_flat_m3u(entries, "theme", out_path=_DIR / "theme.m3u")
        self.assertEqual(_headers(out), [])
        self.assertEqual(_tracks(out), [str(e.path) for e in entries])


if __name__ == "__main__":
    unittest.main(verbosity=2)
