#!/usr/bin/env python3
"""🧭 Importing a playlist that was written on another machine.

Run:  py -m unittest tests.planner.test_m3u_import_remap -v

Every .m3u this app writes on the PC names `F:\\my music\\tanzcds\\…`. Carried
to the Mac (or to a PC where the library sits on another drive) not one of
those lines resolves, and 📂 Import used to hand every single track back as
missing: it matched the line against the library, tried it on disk, and gave
up. The re-rooting `PathRemapper` written for 🧭 Fix paths was never asked.

It is asked here now, and the import says what it did — which lines were
re-rooted, and which are still gone.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from planner.m3u import import_playlist_m3u
from planner.models import MusicEntry
from planner.paths import PathRemapper

FOREIGN = "Q:\\my music\\tanzcds\\lateincd\\SB\\Senorita (SB 50).mp3"
FOREIGN_2 = "Q:\\my music\\tanzcds\\lateincd\\CC\\Havana (CC 31).mp3"


def _lib(*entries):
    """Minimal stand-in for MusicLibrary — import only reads `.entries`."""
    return SimpleNamespace(entries=list(entries))


class _Base(unittest.TestCase):
    """A library root on THIS machine holding the two tracks the foreign
    playlist names, under the same subfolders."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_remap_")) / "tanzcds"
        self.here = {}
        for foreign in (FOREIGN, FOREIGN_2):
            sub = foreign.split("\\")[-2]
            local = self.root / "lateincd" / sub / foreign.split("\\")[-1]
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(b"\0" * 16)
            self.here[foreign] = local
        self.assertFalse(Path(FOREIGN).exists(),
                         "the test needs Q: to be a drive this machine has not")

    def _m3u(self, lines) -> Path:
        p = Path(tempfile.mkdtemp(prefix="dp_remap_m3u_")) / "carried.m3u"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p

    def _entry(self, foreign) -> MusicEntry:
        """The library's own entry for the local copy of a foreign track."""
        local = self.here[foreign]
        return MusicEntry(path=local, title=local.stem,
                          dance="SA" if "SB" in local.name else "CC",
                          bpm=50, duration=120)

    def _remapper(self):
        return PathRemapper([str(self.root)])


class StructuredImportTest(_Base):
    """A file this app wrote: rounds and dances come off the markers."""

    def _import(self, remapper):
        m3u = self._m3u([
            "#EXTM3U",
            "# ══════ Finale (1 Heat) ══════",
            "# ── Samba ──",
            "# Heat 1",
            "#EXTINF:120,Senorita",
            FOREIGN,
        ])
        lib = _lib(self._entry(FOREIGN))
        return import_playlist_m3u(m3u, lib, None, remapper=remapper)

    def test_a_foreign_path_is_re_rooted_under_the_search_folder(self):
        res = self._import(self._remapper())
        self.assertEqual(res["missing"], 0)
        entry = res["playlist"]["Finale"][0][0]
        self.assertEqual(Path(entry.path), self.here[FOREIGN])

    def test_the_result_says_which_lines_were_re_rooted(self):
        res = self._import(self._remapper())
        self.assertEqual([(old, Path(new)) for old, new in res["remapped"]],
                         [(FOREIGN, self.here[FOREIGN])])

    def test_without_a_remapper_the_track_is_still_missing(self):
        """The default stays what it was — planner/ knows no settings."""
        res = self._import(None)
        self.assertEqual(res["missing"], 1)
        self.assertEqual(res["remapped"], [])

    def test_a_root_that_does_not_hold_the_file_changes_nothing(self):
        empty = Path(tempfile.mkdtemp(prefix="dp_remap_empty_"))
        res = self._import(PathRemapper([str(empty)]))
        self.assertEqual(res["missing"], 1)
        self.assertEqual(res["remapped"], [])


class HeuristicImportTest(_Base):
    """A hand-made / UltraMixer list: no markers, dances detected per track.

    The two branches of `import_playlist_m3u` resolve their path lines at two
    different places, so the re-rooting has to be tested on both."""

    def _import(self, remapper):
        m3u = self._m3u([
            "#EXTM3U",
            "#EXTINF:120,Senorita",
            FOREIGN,
            "#EXTINF:120,Havana",
            FOREIGN_2,
        ])
        lib = _lib(self._entry(FOREIGN), self._entry(FOREIGN_2))
        return import_playlist_m3u(m3u, lib, None, remapper=remapper)

    def test_both_lines_are_re_rooted(self):
        res = self._import(self._remapper())
        self.assertFalse(res["structured"])
        self.assertEqual(res["missing"], 0)
        self.assertEqual([old for old, _new in res["remapped"]],
                         [FOREIGN, FOREIGN_2])

    def test_without_a_remapper_both_stay_missing(self):
        res = self._import(None)
        self.assertEqual(res["missing"], 2)
        self.assertEqual(res["remapped"], [])


class ForeignNameFallbackTest(_Base):
    """When no root holds the file, the ghost slot still has to read like a
    song — and on macOS it did not.

    `Path` only knows the separator of the system it runs on, so on macOS the
    whole `Q:\\my music\\…\\Senorita (SB 50).mp3` line is ONE filename: the
    slot took that entire string as its title and ran the dance detection over
    the folder names too. `foreign_name()` cuts both separators.

    On Windows `Path` splits the line correctly by itself, so this test cannot
    go red here — it is the guard for the Mac."""

    def test_the_title_falls_back_to_the_filename_not_the_whole_line(self):
        m3u = self._m3u(["#EXTM3U", FOREIGN])
        res = import_playlist_m3u(m3u, _lib(), None, remapper=None)
        titles = [e.title for hl in res["playlist"].values()
                  for h in hl for e in h if e is not None]
        self.assertEqual(titles, ["Senorita (SB 50)"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
