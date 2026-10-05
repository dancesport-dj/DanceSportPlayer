#!/usr/bin/env python3
"""A party list's foreign paths get re-rooted like a deck's.

Run:  py -m unittest tests.gui.test_party_path_fix -v

A list carried over from another machine — or written before the library moved
— names the library at ITS drive. Importing one into a deck re-roots those
lines under the search folders (Settings), and 🔗 Fix paths repairs whatever is
left. The 🤸 Eintanzen panel got neither: it is not a deck and not a wishlist,
so the import kept the dead `C:\\…` path as an external entry and the fix dialog
never looked at the panel at all — it reported every track it DID check as
valid while the party list pointed at files that are not there.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_party_paths_"))

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_TMP = Path(tempfile.mkdtemp(prefix="dp_party_paths_files_"))
_LIB = _TMP / "F" / "my music" / "tanzcds"          # where the music really is
# Where the list says it is: the old library location, on a drive of its own.
_OLD = r"C:\Users\me\Documents\datein\my music\tanzcds"

_TRACKS = [("lateincd", "CC", "cc1.mp3"), ("lateincd", "RB", "rb1.mp3"),
           ("standardcd", "LW", "lw1.mp3")]


def _real(sub: str, name: str) -> Path:
    p = _LIB / sub / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def _foreign(sub: str, name: str) -> str:
    return rf"{_OLD}\{sub}\{name}"


class PartyPathFixTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_party_paths_qs_"))
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._settings["reference_path"] = str(_LIB)
        self.real = [_real(sub, name) for sub, _d, name in _TRACKS]
        self.win._lib = MusicLibrary()
        self.win._lib.entries = [
            MusicEntry(path=p, title=p.stem, dance=d, duration=180)
            for p, (_s, d, _n) in zip(self.real, _TRACKS)]
        self.table = self.win._warmup_table

    def _m3u(self, name: str) -> Path:
        """A party list naming every track at the OLD library location."""
        out = _TMP / name
        lines = ["#EXTM3U"]
        for sub, _d, fname in _TRACKS:
            lines += [f"#EXTINF:180,{fname}", _foreign(sub, fname)]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    def _load_party(self):
        """The panel, holding the list exactly as the import leaves it."""
        entries = self.win._entries_from_m3u_file(self._m3u("party.m3u"))
        self.table.load_warmup(entries, "Party", style="", dance_class="S",
                               relax=True, play_cb=None, suggester=None)
        return entries

    # ── the import re-roots, like a deck import does ──────────────────────────
    def test_the_import_finds_the_tracks_at_their_real_place(self):
        entries = self.win._entries_from_m3u_file(self._m3u("import.m3u"))
        self.assertEqual([str(e.path) for e in entries],
                         [str(p) for p in self.real])

    def test_no_track_is_lost_in_the_re_rooting(self):
        entries = self.win._entries_from_m3u_file(self._m3u("count.m3u"))
        self.assertEqual(len(entries), len(_TRACKS))

    def test_a_path_that_resolves_as_written_is_left_alone(self):
        out = _TMP / "asis.m3u"
        out.write_text("#EXTM3U\n" + "\n".join(str(p) for p in self.real) + "\n",
                       encoding="utf-8")
        entries = self.win._entries_from_m3u_file(out)
        self.assertEqual([str(e.path) for e in entries],
                         [str(p) for p in self.real])

    # ── 🔗 Fix paths looks at the panel ───────────────────────────────────────
    def test_fix_paths_checks_the_party_list(self):
        """It used to report on the decks only — and say nothing was wrong."""
        entries = [MusicEntry(path=Path(_foreign(s, n)), title=n, dance=d,
                              duration=180) for s, d, n in _TRACKS]
        self.table.load_warmup(entries, "Party", style="", dance_class="S",
                               relax=True, play_cb=None, suggester=None)
        msg = self.win._run_deck_path_fix()
        self.assertIn(f"Checked {len(_TRACKS)} tracks", msg)
        self.assertIn("Relocated", msg)
        self.assertEqual([str(e.path) for e in self.table._row_meta.entries()],
                         [str(p) for p in self.real])

    def test_an_already_valid_party_list_is_reported_as_valid(self):
        self._load_party()
        msg = self.win._run_deck_path_fix()
        self.assertIn(f"{len(_TRACKS)} already valid", msg)
        self.assertNotIn("unresolved", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
