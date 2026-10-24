"""📦 Venue pack: the desk of one PC carried to another in one file."""
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path, PureWindowsPath
from unittest import mock

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

    def test_remote_and_guest_access_stay_local(self):
        """S3: an older pack still carries the other PC's PIN and modes; the
        import must neither take them nor switch the remote on."""
        local = {"remote_pin": "1111", "remote_mode": "off", "guest_mode": "off"}
        imported = {"remote_pin": "9999", "remote_mode": "tunnel",
                    "remote_port": 8765, "guest_mode": "lan", "guest_port": 8766}
        self.assertEqual(vp.merge_settings(local, imported), local)

    def test_the_pack_does_not_carry_remote_or_guest_access(self):
        settings = {"remote_pin": "9999", "remote_mode": "tunnel",
                    "remote_port": 8765, "guest_mode": "lan",
                    "guest_port": 8766, "zoom": 3}
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "v.dpvenue"
            vp.write_pack(dest, {vp.SETTINGS_FILE: settings}, include_music=False)
            self.assertEqual(vp.read_pack(dest).docs[vp.SETTINGS_FILE], {"zoom": 3})
            with zipfile.ZipFile(dest) as z:
                self.assertNotIn(b"9999", z.read(vp.SETTINGS_FILE))
        self.assertIn("remote_pin", settings)       # the caller's dict untouched


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

    def test_a_different_track_of_the_same_size_is_not_taken_for_it(self):
        dest = self.root / "venue.dpvenue"
        vp.write_pack(dest, self.docs, include_music=True)
        target = self.root / "venue_music"
        mine = _mp3(target / "LW" / "Moon.mp3", b"Z" * 100)   # same size as A
        mapping = vp.extract_music(dest, target)
        self.assertEqual(Path(mapping[self.a]).read_bytes(), b"A" * 100)
        self.assertEqual(Path(mine).read_bytes(), b"Z" * 100)

    def test_a_different_track_of_another_size_is_not_overwritten(self):
        dest = self.root / "venue.dpvenue"
        vp.write_pack(dest, self.docs, include_music=True)
        target = self.root / "venue_music"
        mine = _mp3(target / "LW" / "Moon.mp3", b"Z" * 7)
        mapping = vp.extract_music(dest, target)
        self.assertEqual(Path(mapping[self.a]).read_bytes(), b"A" * 100)
        self.assertEqual(Path(mine).read_bytes(), b"Z" * 7)

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


class HostileMusicNamesTest(unittest.TestCase):
    """S1: the arc names come from the pack's own manifest, so a crafted pack
    must not get a file written anywhere but under the chosen music folder."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.dest = self.root / "venue_music"
        # A drive-relative name resolves against the drive's current folder;
        # pointing that at the temp root keeps a failing run inside it.
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)

    def _pack(self, arcs):
        src = self.root / "evil.dpvenue"
        with zipfile.ZipFile(src, "w") as z:
            for arc in arcs:
                z.writestr(arc, b"payload")
            z.writestr(vp.MANIFEST, json.dumps(
                {"format": vp.FORMAT, "version": vp.VERSION, "files": [],
                 "music": {f"F:\\orig\\{i}.mp3": arc for i, arc in enumerate(arcs)}}))
        return src

    def _written(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")
                      if p.is_file() and p.name != "evil.dpvenue")

    @unittest.skipUnless(os.name == "nt", "drive letters are a Windows path form")
    def test_a_drive_relative_name_does_not_escape(self):
        drive = PureWindowsPath(self.root).drive
        mapping = vp.extract_music(self._pack([f"music/x/{drive}outside/a.mp3"]),
                                   self.dest)
        self.assertEqual(mapping, {})
        self.assertEqual(self._written(), [])

    def test_only_audio_files_are_unpacked(self):
        mapping = vp.extract_music(
            self._pack(["music/x/run.bat", "music/x/song.mp3"]), self.dest)
        self.assertEqual(list(mapping.values()), [str(self.dest / "x" / "song.mp3")])
        self.assertEqual(self._written(), [str(Path("venue_music/x/song.mp3"))])

    def test_a_name_without_a_file_part_is_skipped(self):
        """L-VP1: `music` alone made the target the folder itself, and
        opening a folder for writing unwound the whole import."""
        mapping = vp.extract_music(self._pack(["music", "music/x/song.mp3"]),
                                   self.dest)
        self.assertEqual(list(mapping.values()), [str(self.dest / "x" / "song.mp3")])


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

    def test_only_the_desk_files_are_taken_from_a_pack(self):
        """S2: the file list comes from the pack, so a crafted one could
        overwrite any JSON in the app folder (the AI key, the planner config)."""
        evil = self.root / "evil.dpvenue"
        with zipfile.ZipFile(evil, "w") as z:
            for name in ("cartwall.json", "openrouter_config.json"):
                z.writestr(name, json.dumps({"pads": []}))
            z.writestr(vp.MANIFEST, json.dumps(
                {"format": vp.FORMAT, "version": vp.VERSION,
                 "files": ["cartwall.json", "openrouter_config.json"]}))
        pack = vp.stage_import(evil, self.state, music_dir=None)
        self.assertEqual(list(pack.docs), ["cartwall.json"])
        # A file that reached the stage folder some other way is not applied.
        (self.state / vp.STAGE_DIR / "planner_config.json").write_text(
            "{}", encoding="utf-8")
        self.assertEqual(vp.apply_pending(self.state), ["cartwall.json"])
        self.assertFalse((self.state / "openrouter_config.json").exists())
        self.assertFalse((self.state / "planner_config.json").exists())

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

    def _assert_untouched(self):
        self.assertEqual(self._read("gui_settings.json"),
                         {"library_dir": r"C:\here", "zoom": 1})
        self.assertEqual(self._read("autosave_playlist.json"), {})
        self.assertFalse((self.state / "cartwall.json").exists())
        self.assertTrue(vp.has_pending(self.state), "tried again next start")

    def test_a_file_that_cannot_be_backed_up_applies_nothing(self):
        """L-VP4: a locked live file stopped the loop half way — some docs
        replaced, the rest old, and no backup of the ones still to come."""
        vp.stage_import(self.pack, self.state, music_dir=None)
        real = vp.shutil.copy2

        def copy2(src, dst, *a, **k):
            if Path(src).name == "gui_settings.json":
                raise PermissionError("locked")
            return real(src, dst, *a, **k)
        with mock.patch.object(vp.shutil, "copy2", side_effect=copy2):
            self.assertEqual(vp.apply_pending(self.state), [])
        self._assert_untouched()

    def test_a_write_that_fails_puts_the_earlier_files_back(self):
        vp.stage_import(self.pack, self.state, music_dir=None)
        real = vp.write_json_atomic

        def write(path, obj):
            if path.name == "gui_settings.json":
                raise PermissionError("locked")
            return real(path, obj)
        with mock.patch.object(vp, "write_json_atomic", side_effect=write):
            self.assertEqual(vp.apply_pending(self.state), [])
        self._assert_untouched()

    def test_with_music_the_imported_docs_point_at_the_copies(self):
        music = self.root / "venue_music"
        vp.stage_import(self.pack, self.state, music_dir=music)
        vp.apply_pending(self.state)
        rows = self._read("autosave_playlist.json")["rows"]
        self.assertTrue(Path(rows[0]).is_relative_to(music))
        self.assertTrue(Path(rows[0]).exists())

    def test_without_music_the_paths_find_this_machines_copies(self):
        """The pack names the other PC's paths. Left as they were, the 🎛 pads
        and decks pointed at files this machine does not have; this machine's
        own folders (Reference path, search folders, library) hold them."""
        here = self.root / "here" / "my music"
        moon = _mp3(here / "standardcd" / "LW" / "Moon (LW 29).mp3")
        tusch = _mp3(self.root / "jingles" / "Tusch.mp3")
        far_moon = r"F:\my music\standardcd\LW\Moon (LW 29).mp3"
        far_tusch = r"E:\jingles\Tusch.mp3"
        gone = r"F:\my music\standardcd\LW\Gone.mp3"
        docs = {"gui_settings.json": {"library_dir": r"F:\my music", "zoom": 3,
                                      "per_title": {far_moon: 5}},
                "autosave_playlist.json": {"rows": [far_moon, gone, self.a]},
                "cartwall.json": {"pads": [{"path": far_tusch}, {"path": far_moon}]}}
        pack = self.root / "far.dpvenue"
        vp.write_pack(pack, docs, include_music=False)
        (self.state / "gui_settings.json").write_text(json.dumps(
            {"library_dir": str(here), "remap_paths": [str(self.root / "jingles")]}),
            encoding="utf-8")
        vp.stage_import(pack, self.state, music_dir=None)
        vp.apply_pending(self.state)
        self.assertEqual(self._read("cartwall.json")["pads"],
                         [{"path": tusch}, {"path": moon}])
        self.assertEqual(self._read("autosave_playlist.json")["rows"],
                         [moon, gone, self.a])     # no copy: left as it was
        s = self._read("gui_settings.json")
        self.assertEqual(s["per_title"], {moon: 5})
        self.assertEqual(s["library_dir"], str(here))

    def test_settings_that_are_no_object_are_skipped_not_retried(self):
        """P11: merge_settings raised on them outside the apply's try, so the
        stage was never cleared and every start failed on it again."""
        vp.stage_import(self.pack, self.state, music_dir=None)
        (self.state / vp.STAGE_DIR / "gui_settings.json").write_text(
            "[1, 2]", encoding="utf-8")
        with self.assertLogs(vp.log, "WARNING"):
            applied = vp.apply_pending(self.state)
        self.assertEqual(sorted(applied), ["autosave_playlist.json", "cartwall.json"])
        self.assertEqual(self._read("gui_settings.json"),
                         {"library_dir": r"C:\here", "zoom": 1})
        self.assertFalse(vp.has_pending(self.state))

    def test_a_pack_with_such_settings_is_refused_at_import(self):
        bad = self.root / "bad.dpvenue"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("gui_settings.json", "[1, 2]")
            z.writestr(vp.MANIFEST, json.dumps(
                {"format": vp.FORMAT, "version": vp.VERSION,
                 "files": ["gui_settings.json"]}))
        with self.assertRaises(vp.VenuePackError):
            vp.stage_import(bad, self.state, music_dir=None)
        self.assertFalse(vp.has_pending(self.state))

    def test_nothing_pending_applies_nothing(self):
        self.assertEqual(vp.apply_pending(self.state), [])
        self.assertEqual(list(self.state.glob("before-venue-import-*")), [])


if __name__ == "__main__":
    unittest.main()
