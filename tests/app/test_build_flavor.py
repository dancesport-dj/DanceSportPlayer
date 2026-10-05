"""Tests for planner.config: build_flavor() (dev / lite / full detection via the
build_flavor.txt marker), the writable data dir, and write_json_atomic."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner import config


class BuildFlavorTest(unittest.TestCase):
    """build_flavor() reads the marker only when frozen; source runs are 'dev'.

    The marker is a SHIPPED file, so it is read from INSTALL_DIR — the data dir
    may have moved out from under it (see DataDirTest) — and from the bundle
    folder (sys._MEIPASS), which is where PyInstaller actually puts shipped
    data: `_internal`, not next to the .exe."""

    def setUp(self):
        self._base = config.INSTALL_DIR
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_flavor_"))
        self._bundle = Path(tempfile.mkdtemp(prefix="dp_flavor_internal_"))
        config.INSTALL_DIR = self._tmp

    def tearDown(self):
        config.INSTALL_DIR = self._base
        for attr in ("frozen", "_MEIPASS"):
            if hasattr(sys, attr):
                delattr(sys, attr)

    def _freeze(self, marker=None, bundled=None):
        """Freeze the app, with a marker beside the .exe and/or in the bundle."""
        sys.frozen = True
        if marker is not None:
            (self._tmp / "build_flavor.txt").write_text(marker, encoding="utf-8")
        if bundled is not None:
            sys._MEIPASS = str(self._bundle)
            (self._bundle / "build_flavor.txt").write_text(bundled, encoding="utf-8")

    def test_source_run_is_dev(self):
        self.assertEqual(config.build_flavor(), "dev")

    def test_frozen_reads_marker(self):
        self._freeze("full")
        self.assertEqual(config.build_flavor(), "full")

    def test_marker_is_normalized(self):
        self._freeze("  LITE \n")
        self.assertEqual(config.build_flavor(), "lite")

    def test_missing_marker_defaults_to_lite(self):
        self._freeze()
        self.assertEqual(config.build_flavor(), "lite")

    def test_junk_marker_defaults_to_lite(self):
        self._freeze("banana")
        self.assertEqual(config.build_flavor(), "lite")

    def test_the_marker_is_found_where_pyinstaller_puts_it(self):
        """The real layout of a build: the marker is data, so it lands in
        `_internal`. Reading only beside the .exe found nothing and answered
        'lite' — for a full build, the wrong answer with no error to show."""
        self._freeze(bundled="full")
        self.assertEqual(config.build_flavor(), "full")

    def test_frozen_reads_the_player_marker(self):
        """The third flavor: no librosa stack, planning UI locked away."""
        self._freeze("player")
        self.assertEqual(config.build_flavor(), "player")
        self.assertTrue(config.player_build())

    def test_only_the_player_marker_is_a_player_build(self):
        self.assertFalse(config.player_build())      # source run = dev
        for marker in ("lite", "full"):
            with self.subTest(marker=marker):
                self._freeze(marker)
                self.assertFalse(config.player_build())

    def test_a_marker_beside_the_exe_wins_over_the_bundled_one(self):
        """Hand-placed beats shipped: it is how a build gets re-labelled without
        being rebuilt, and the bundle is replaced wholesale by the next one."""
        self._freeze("lite", bundled="full")
        self.assertEqual(config.build_flavor(), "lite")


class SpecLanguagesTest(unittest.TestCase):
    """Every language ⚙ Settings offers is packaged. planner.i18n loads a
    catalog by name (importlib), which PyInstaller cannot see — so a module
    the spec does not name is missing from every .exe, and the app says
    "No catalog for de, staying English" on a machine set to German."""

    def test_every_offered_language_is_named_in_the_spec(self):
        from planner.i18n import DEFAULT_LANGUAGE, LANGUAGES
        spec = (Path(config.__file__).resolve().parent.parent
                / "dancesport.spec").read_text(encoding="utf-8")
        for code, _caption, _blurb in LANGUAGES:
            if code == DEFAULT_LANGUAGE:
                continue
            with self.subTest(language=code):
                self.assertTrue(f'"planner.lang_{code}"' in spec,
                                f"planner.lang_{code} is not in dancesport.spec")


class BuildNamesTest(unittest.TestCase):
    """The spec names the build; the scripts then copy ffmpeg into it
    (build_exe.bat) and sign it (build_app.sh) by that same name. A script
    left on an old name signs or fills a folder that is not there."""

    NAMES = ("DanceSport-Planner-Player", "DanceSport-Planner-Player-Full",
             "DanceSport-Player")

    def _read(self, name):
        root = Path(config.__file__).resolve().parent.parent
        return (root / name).read_text(encoding="utf-8")

    def test_spec_and_scripts_build_under_the_same_names(self):
        for file in ("dancesport.spec", "build_exe.bat", "build_app.sh"):
            text = self._read(file)
            for name in self.NAMES:
                with self.subTest(file=file, name=name):
                    self.assertIn(name, text)

    def test_nothing_is_built_under_the_old_name(self):
        for file in ("dancesport.spec", "build_exe.bat", "build_app.sh"):
            with self.subTest(file=file):
                self.assertNotIn("DancePlaylist", self._read(file))


class DataDirTest(unittest.TestCase):
    """Everything the app writes goes next to it — unless it cannot."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_datadir_"))

    def test_a_writable_folder_is_writable(self):
        self.assertTrue(config._is_writable(self._tmp))

    def test_a_folder_that_is_not_there_is_not_writable(self):
        self.assertFalse(config._is_writable(self._tmp / "nope"))

    def test_the_probe_leaves_nothing_behind(self):
        config._is_writable(self._tmp)
        self.assertEqual(list(self._tmp.iterdir()), [])

    def test_a_writable_app_folder_stays_the_data_folder(self):
        """The portable-folder property: nothing moves, no migration."""
        self.assertEqual(config._data_dir(self._tmp), self._tmp)

    def test_a_folder_inside_a_dot_app_is_never_the_data_folder(self):
        """A writable bundle is still a bundle: the next version replaces it whole."""
        inside = Path("/Applications/DancePlaylist.app/Contents/MacOS")
        self.assertTrue(config._in_app_bundle(inside))
        user = self._tmp / "user"
        with mock.patch.object(config, "_is_writable", return_value=True), \
             mock.patch.object(config, "_user_data_dir", return_value=user):
            self.assertEqual(config._data_dir(inside), user)

    def test_an_ordinary_folder_is_not_a_bundle(self):
        self.assertFalse(config._in_app_bundle(self._tmp))
        self.assertFalse(config._in_app_bundle(
            Path("/Users/me/Contents/MacOS")))       # no .app above it

    def test_a_read_only_app_folder_falls_back_to_the_user_folder(self):
        user = self._tmp / "user data"
        with mock.patch.object(config, "_is_writable", return_value=False), \
             mock.patch.object(config, "_user_data_dir", return_value=user):
            self.assertEqual(config._data_dir(self._tmp / "app"), user)
        self.assertTrue(user.is_dir())          # created, ready to be written to

    def test_an_unusable_fallback_keeps_the_app_folder(self):
        """Nothing works — fail exactly the way the app failed before, not worse."""
        app = self._tmp / "app"
        with mock.patch.object(config, "_is_writable", return_value=False), \
             mock.patch.object(config, "_user_data_dir",
                               return_value=self._tmp / "user"), \
             mock.patch.object(Path, "mkdir", side_effect=OSError("read-only fs")):
            self.assertEqual(config._data_dir(app), app)

    def test_the_user_folder_is_the_one_the_os_expects(self):
        name = "DanceSport-Planner-Player"
        cases = {
            "darwin": ("HOME", Path("Library") / "Application Support" / name),
            "win32": ("LOCALAPPDATA", Path(name)),
            "linux": ("XDG_DATA_HOME", Path(name)),
        }
        for platform, (env_key, tail) in cases.items():
            with self.subTest(platform=platform):
                env = {env_key: str(self._tmp)}
                with mock.patch.object(sys, "platform", platform), \
                     mock.patch.dict(config.os.environ, env, clear=False), \
                     mock.patch.object(Path, "home", return_value=self._tmp):
                    self.assertEqual(config._user_data_dir(), self._tmp / tail)


class RenamedDataDirTest(unittest.TestCase):
    """The app was DancePlaylist; its user folder moves along with the name.

    A Mac that ran the old build has its database, settings and playlists in
    …/Application Support/DancePlaylist. The first start under the new name
    moves that folder over whole, so nothing is left behind or copied twice."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_rename_"))
        self.new = self._tmp / "DanceSport-Planner-Player"
        self.old = self._tmp / "DancePlaylist"
        self._bundle = Path("/Applications/DanceSport Planner & Player.app"
                            "/Contents/MacOS")

    def _data_dir(self):
        with mock.patch.object(config, "_user_data_dir", return_value=self.new):
            return config._data_dir(self._bundle)

    def test_the_old_folder_moves_to_the_new_name(self):
        self.old.mkdir()
        (self.old / "audio_features.db").write_bytes(b"db")
        self.assertEqual(self._data_dir(), self.new)
        self.assertEqual((self.new / "audio_features.db").read_bytes(), b"db")
        self.assertFalse(self.old.exists())

    def test_a_new_folder_that_is_there_already_wins(self):
        """Moved before, or started fresh: the old folder is left alone."""
        self.old.mkdir()
        self.new.mkdir()
        (self.new / "gui_settings.json").write_text("{}")
        self.assertEqual(self._data_dir(), self.new)
        self.assertTrue(self.old.is_dir())

    def test_no_old_folder_starts_a_new_one(self):
        self.assertEqual(self._data_dir(), self.new)
        self.assertTrue(self.new.is_dir())

    def test_a_move_that_fails_keeps_using_the_old_folder(self):
        """Never start empty next to the user's real data."""
        self.old.mkdir()
        with mock.patch.object(Path, "rename", side_effect=OSError("busy")):
            self.assertEqual(self._data_dir(), self.old)
        self.assertFalse(self.new.exists())

    def test_a_writable_app_folder_is_not_touched_by_the_move(self):
        """The portable folder next to the .exe is not a user folder."""
        self.old.mkdir()
        app = self._tmp / "app"
        app.mkdir()
        with mock.patch.object(config, "_user_data_dir", return_value=self.new):
            self.assertEqual(config._data_dir(app), app)
        self.assertTrue(self.old.is_dir())


class WriteJsonAtomicTest(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_json_"))

    def test_round_trip(self):
        target = self._tmp / "out.json"
        config.write_json_atomic(target, {"a": 1, "täkte": [58, 59]})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")),
                         {"a": 1, "täkte": [58, 59]})
        self.assertFalse(target.with_suffix(".json.tmp").exists())

    def test_overwrites_existing(self):
        target = self._tmp / "out.json"
        target.write_text('{"old": true}', encoding="utf-8")
        config.write_json_atomic(target, {"new": True})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")),
                         {"new": True})

    def test_the_bytes_are_on_disk_before_the_file_is_swapped_in(self):
        """NTFS journals the rename, not the data: a power cut right after it
        left a settings file of zeros where the old one had been."""
        target = self._tmp / "out.json"
        calls = []
        real_fsync, real_replace = config.os.fsync, config.os.replace
        with mock.patch.object(config.os, "fsync",
                               side_effect=lambda fd: (calls.append("fsync"),
                                                       real_fsync(fd))), \
             mock.patch.object(config.os, "replace",
                               side_effect=lambda a, b: (calls.append("replace"),
                                                         real_replace(a, b))):
            config.write_json_atomic(target, {"a": 1})
        self.assertEqual(calls, ["fsync", "replace"])

    def test_two_writers_of_one_file_do_not_share_a_temp_file(self):
        """The autosave and a worker thread can save the same store at once;
        with one fixed .tmp name the second truncated the first one's half-
        written file and the first one's swap then found nothing to move."""
        target = self._tmp / "out.json"
        real_replace = config.os.replace
        state = {"first": True}

        def replace(src, dst):
            if state.pop("first", False):
                config.write_json_atomic(target, {"writer": "B"})   # B runs whole
            real_replace(src, dst)

        with mock.patch.object(config.os, "replace", side_effect=replace):
            config.write_json_atomic(target, {"writer": "A"})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")),
                         {"writer": "A"})
        self.assertEqual([p.name for p in self._tmp.iterdir()], ["out.json"])

    def test_a_write_that_fails_leaves_no_temp_file(self):
        target = self._tmp / "out.json"
        with mock.patch.object(config.os, "replace", side_effect=OSError("locked")):
            with self.assertRaises(OSError):
                config.write_json_atomic(target, {"a": 1})
        self.assertEqual(list(self._tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
