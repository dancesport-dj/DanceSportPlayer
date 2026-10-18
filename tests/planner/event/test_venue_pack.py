"""📦 Venue pack: the desk of one PC carried to another in one file."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from planner.event import venue_pack as vp


def _mp3(path: Path, data: bytes = b"ID3fake") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


class TrackPathsTest(unittest.TestCase):
    def test_collects_audio_paths_from_values_and_keys_once(self):
        a = r"F:\music\standardcd\LW\Moon (LW 29).mp3"
        b = r"F:\music\lateincd\CC\Cha (CC 32).flac"
        doc = {"decks": [{"rows": [{"path": a}, {"path": b}, {"path": a}]}],
               "player_sections": {b: [1, 2]},
               "title": "not a path.mp3",          # relative: not a track
               "notes": r"F:\music\cover.jpg"}     # not audio
        self.assertEqual(vp.track_paths(doc), [a, b])

    def test_several_docs_merge_in_order(self):
        a, b = "/m/a.mp3", "/m/b.mp3"
        self.assertEqual(vp.track_paths({"x": a}, [b, a]), [a, b])


class RemapTest(unittest.TestCase):
    def test_values_and_keys_are_remapped_rest_untouched(self):
        a = r"F:\m\a.mp3"
        doc = {"rows": [{"path": a, "n": 3}], "sections": {a: [1]}, "k": "x"}
        out = vp.remap(doc, {a: r"E:\venue\a.mp3"})
        self.assertEqual(out, {"rows": [{"path": r"E:\venue\a.mp3", "n": 3}],
                               "sections": {r"E:\venue\a.mp3": [1]}, "k": "x"})
        self.assertEqual(doc["rows"][0]["path"], a)     # the input is not changed


class MergeSettingsTest(unittest.TestCase):
    def test_machine_keys_stay_local_the_rest_comes_along(self):
        local = {"library_dir": r"C:\lib", "save_dir": r"C:\out",
                 "presenter_screen_name": "DELL", "media_backend": "ffmpeg",
                 "check_min_play_secs": 105, "only_here": 1}
        imported = {"library_dir": r"F:\lib", "save_dir": r"F:\out",
                    "presenter_screen_name": "BENQ", "media_backend": "windows",
                    "check_min_play_secs": 90, "only_there": 2}
        out = vp.merge_settings(local, imported)
        self.assertEqual(out["library_dir"], r"C:\lib")
        self.assertEqual(out["save_dir"], r"C:\out")
        self.assertEqual(out["presenter_screen_name"], "DELL")
        self.assertEqual(out["media_backend"], "ffmpeg")
        self.assertEqual(out["check_min_play_secs"], 90)
        self.assertEqual(out["only_here"], 1)
        self.assertEqual(out["only_there"], 2)

    def test_a_machine_key_missing_locally_is_not_imported(self):
        out = vp.merge_settings({}, {"library_dir": r"F:\lib", "a": 1})
        self.assertNotIn("library_dir", out)
        self.assertEqual(out["a"], 1)


class PackRoundTripTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.a = _mp3(self.root / "lib" / "LW" / "Moon.mp3", b"A" * 100)
        self.b = _mp3(self.root / "lib" / "CC" / "Moon.mp3", b"B" * 50)
        self.gone = str(self.root / "lib" / "SB" / "Gone.mp3")
        self.docs = {
            "gui_settings.json": {"library_dir": "x", "zoom": 2},
            "autosave_playlist.json": {"decks": [{"path": self.a},
                                                 {"path": self.b},
                                                 {"path": self.gone}]},
            "cartwall.json": {"pads": [{"file": self.a, "shortcut": "Ctrl+1"}]},
        }

    def tearDown(self):
        self._tmp.cleanup()

    def test_without_music_only_the_documents_travel(self):
        dest = self.root / "venue.dpvenue"
        res = vp.write_pack(dest, self.docs, include_music=False)
        self.assertEqual(res.tracks, 0)
        with zipfile.ZipFile(dest) as z:
            self.assertFalse([n for n in z.namelist() if n.startswith("music/")])
        pack = vp.read_pack(dest)
        self.assertEqual(pack.docs, self.docs)
        self.assertEqual(pack.music, {})

    def test_with_music_every_existing_track_travels_once(self):
        dest = self.root / "venue.dpvenue"
        seen = []
        res = vp.write_pack(dest, self.docs, include_music=True,
                            progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(res.tracks, 2)
        self.assertEqual(res.missing, [self.gone])
        self.assertEqual(seen[-1], (2, 2))
        pack = vp.read_pack(dest)
        self.assertEqual(set(pack.music), {self.a, self.b})
        # Same file name in two folders: both survive, under their folder.
        self.assertEqual(len(set(pack.music.values())), 2)
        self.assertIn("LW/Moon.mp3", pack.music[self.a])

    def test_music_extracts_and_the_docs_point_at_it(self):
        dest = self.root / "venue.dpvenue"
        vp.write_pack(dest, self.docs, include_music=True)
        target = self.root / "venue_music"
        mapping = vp.extract_music(dest, target)
        self.assertEqual(Path(mapping[self.a]).read_bytes(), b"A" * 100)
        self.assertEqual(Path(mapping[self.b]).read_bytes(), b"B" * 50)
        self.assertTrue(Path(mapping[self.a]).is_relative_to(target))
        # A second import of the same pack reuses what is already there.
        self.assertEqual(vp.extract_music(dest, target), mapping)

    def test_cancel_leaves_no_pack_behind(self):
        dest = self.root / "venue.dpvenue"
        with self.assertRaises(vp.VenuePackCancelled):
            vp.write_pack(dest, self.docs, include_music=True,
                          cancelled=lambda: True)
        self.assertFalse(dest.exists())
        self.assertEqual(list(self.root.glob("venue.dpvenue*")), [])

    def test_not_a_venue_pack_is_refused(self):
        bad = self.root / "other.zip"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("readme.txt", "hi")
        with self.assertRaises(vp.VenuePackError):
            vp.read_pack(bad)
        junk = self.root / "junk.dpvenue"
        junk.write_bytes(b"not a zip")
        with self.assertRaises(vp.VenuePackError):
            vp.read_pack(junk)

    def test_a_newer_pack_version_is_refused(self):
        dest = self.root / "venue.dpvenue"
        with zipfile.ZipFile(dest, "w") as z:
            z.writestr(vp.MANIFEST, json.dumps(
                {"format": vp.FORMAT, "version": vp.VERSION + 1}))
        with self.assertRaises(vp.VenuePackError):
            vp.read_pack(dest)


class StagedImportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.a = _mp3(self.root / "lib" / "LW" / "Moon.mp3")
        docs = {"gui_settings.json": {"library_dir": r"F:\there", "zoom": 3},
                "autosave_playlist.json": {"rows": [self.a]},
                "cartwall.json": {"pads": []}}
        self.pack = self.root / "v.dpvenue"
        vp.write_pack(self.pack, docs, include_music=True)
        (self.state / "gui_settings.json").write_text(
            json.dumps({"library_dir": r"C:\here", "zoom": 1}), encoding="utf-8")
        (self.state / "autosave_playlist.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _read(self, name):
        return json.loads((self.state / name).read_text(encoding="utf-8"))

    def test_stage_changes_nothing_live_until_applied(self):
        vp.stage_import(self.pack, self.state, music_dir=None)
        self.assertTrue(vp.has_pending(self.state))
        self.assertEqual(self._read("gui_settings.json")["zoom"], 1)
        self.assertEqual(self._read("autosave_playlist.json"), {})

    def test_apply_replaces_merges_and_keeps_a_backup(self):
        vp.stage_import(self.pack, self.state, music_dir=None)
        applied = vp.apply_pending(self.state)
        self.assertEqual(sorted(applied), ["autosave_playlist.json",
                                           "cartwall.json", "gui_settings.json"])
        self.assertFalse(vp.has_pending(self.state))
        s = self._read("gui_settings.json")
        self.assertEqual(s, {"library_dir": r"C:\here", "zoom": 3})
        self.assertEqual(self._read("autosave_playlist.json"), {"rows": [self.a]})
        backups = list(self.state.glob("before-venue-import-*"))
        self.assertEqual(len(backups), 1)
        old = json.loads((backups[0] / "gui_settings.json").read_text("utf-8"))
        self.assertEqual(old["zoom"], 1)

    def test_with_music_the_imported_docs_point_at_the_copies(self):
        music = self.root / "venue_music"
        vp.stage_import(self.pack, self.state, music_dir=music)
        vp.apply_pending(self.state)
        rows = self._read("autosave_playlist.json")["rows"]
        self.assertTrue(Path(rows[0]).is_relative_to(music))
        self.assertTrue(Path(rows[0]).exists())

    def test_nothing_pending_applies_nothing(self):
        self.assertEqual(vp.apply_pending(self.state), [])
        self.assertEqual(list(self.state.glob("before-venue-import-*")), [])


if __name__ == "__main__":
    unittest.main()
