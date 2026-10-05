#!/usr/bin/env python3
"""An imported .m3u finds its relative and quoted lines.

Run:  py -m unittest tests.planner.test_m3u_import_relative -v

The 🧳 USB bundle writes bare filenames next to the playlist — that is what
makes the folder self-contained. The import resolved such a line against the
app's working directory instead of the playlist's folder, so the app could not
re-import its own bundle: every track came back missing. A line wrapped in
quotes (some players write them) kept the quotes and matched nothing either.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from planner.m3u import import_playlist_m3u, numbered_folder_m3u
from planner.models import MusicEntry


class RelativeImportTest(unittest.TestCase):

    def setUp(self):
        self.src = Path(tempfile.mkdtemp(prefix="dp_rel_src_"))
        self.out = Path(tempfile.mkdtemp(prefix="dp_rel_out_"))
        self.addCleanup(shutil.rmtree, self.src, True)
        self.addCleanup(shutil.rmtree, self.out, True)

    def _mp3(self, name) -> Path:
        p = self.src / name
        p.write_bytes(b"ID3fake")
        return p

    def _lib_at(self, *paths):
        return SimpleNamespace(entries=[
            MusicEntry(path=p, title=p.stem, dance="CC", bpm=30) for p in paths])

    def test_the_app_re_imports_its_own_usb_bundle(self):
        a = self._mp3("Song A (CC 30).mp3")
        b = self._mp3("Song B (CC 30).mp3")
        m3u = self.out / "comp.m3u"
        m3u.write_text("\n".join([
            "#EXTM3U", "#EXTINF:120,Song A", str(a),
            "#EXTINF:110,Song B", str(b)]) + "\n", encoding="utf-8")
        copied, _missing = numbered_folder_m3u(m3u)
        self.assertNotIn(str(self.out), m3u.read_text(encoding="utf-8"),
                         "the bundle's lines are bare filenames")

        res = import_playlist_m3u(m3u, self._lib_at(*copied), None)
        self.assertEqual(res["missing"], 0)
        got = [e.path for heats in res["playlist"].values()
               for heat in heats for e in heat if e is not None]
        self.assertEqual(sorted(got), sorted(copied))

    def test_a_quoted_line_is_the_path_inside_the_quotes(self):
        a = self._mp3("Song A (CC 30).mp3")
        m3u = self.out / "quoted.m3u"
        m3u.write_text(f'#EXTM3U\n"{a}"\n', encoding="utf-8")
        res = import_playlist_m3u(m3u, self._lib_at(a), None)
        self.assertEqual(res["missing"], 0)

    def test_a_missing_relative_track_is_a_ghost_in_the_playlist_folder(self):
        m3u = self.out / "gone.m3u"
        m3u.write_text("#EXTM3U\nGone (CC 30).mp3\n", encoding="utf-8")
        res = import_playlist_m3u(m3u, self._lib_at(), None)
        self.assertEqual(res["missing"], 1)
        ghost = [e for heats in res["playlist"].values()
                 for heat in heats for e in heat if e is not None][0]
        self.assertEqual(ghost.path, self.out / "Gone (CC 30).mp3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
