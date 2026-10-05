#!/usr/bin/env python3
"""Tests for the GUI state files: the DANCEPLAYLIST_STATE_DIR redirect and the
rotating autosave backups.

Run:  .venv\\Scripts\\python.exe -m unittest test_state_files -v
(needs PySide6 — gui.dialogs imports Qt at module level)

DANCEPLAYLIST_STATE_DIR is set to a temp dir so nothing here can touch the real
gui_settings.json / autosave_playlist.json. It no longer has to be set before
gui.dialogs is imported: a store resolves its path when it is asked, so the
redirect holds however the import order fell out.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_STATE_DIR = Path(tempfile.mkdtemp(prefix="dp_state_"))
os.environ["DANCEPLAYLIST_STATE_DIR"] = str(_STATE_DIR)

from gui import dialogs  # noqa: E402
from shared import stores  # noqa: E402

# Belt and braces: if the redirect didn't take, skip instead of writing.
# A skipped test is a bug report; a destroyed settings file is a bad afternoon.
_REDIRECTED = stores.SETTINGS.path.parent == _STATE_DIR
_NOT_REDIRECTED_MSG = (
    f"shared.stores writes to {stores.SETTINGS.path.parent} instead of the "
    f"temp state dir")


def tearDownModule():
    shutil.rmtree(_STATE_DIR, ignore_errors=True)


@unittest.skipUnless(_REDIRECTED, _NOT_REDIRECTED_MSG)
class StateDirRedirectTest(unittest.TestCase):
    def test_settings_and_autosave_live_in_state_dir(self):
        self.assertEqual(stores.SETTINGS.path.parent, _STATE_DIR)
        self.assertEqual(dialogs.AUTOSAVE.path.parent, _STATE_DIR)
        self.assertEqual(stores.CARTWALL.path.parent, _STATE_DIR)

    def test_the_cartwall_round_trips_through_its_own_file(self):
        stores.save_cartwall_file({"version": 1, "pages": []})
        self.assertEqual(stores.load_cartwall_file()["version"], 1)

    def test_an_unreadable_cartwall_reads_as_nothing_at_all(self):
        stores.CARTWALL.path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(stores.load_cartwall_file())

    def test_save_settings_writes_redirected_file(self):
        stores.save_settings({"library_dir": "X:\\nowhere"})
        data = json.loads(stores.SETTINGS.path.read_text(encoding="utf-8"))
        self.assertEqual(data["library_dir"], "X:\\nowhere")

    def test_a_changed_play_set_survives_the_file(self):
        """🎛 Play sets are settings like any other: written on OK, read on start."""
        mine = {"secs": 45, "advance": False, "pause_off": False,
                "announce": True, "loudness": False}
        stores.save_settings({"party_set": mine})
        self.assertEqual(dialogs.load_settings()["party_set"], mine)


@unittest.skipUnless(_REDIRECTED, _NOT_REDIRECTED_MSG)
class PathFallbackTest(unittest.TestCase):
    """📁 A settings file travels between machines and between a drive being
    plugged in and not — folders that aren't there fall back to this machine's
    own Music / Documents."""

    def setUp(self):
        self.music = _STATE_DIR / "Music"
        self.docs = _STATE_DIR / "Documents"
        for p in (self.music, self.docs):
            p.mkdir(exist_ok=True)
        self._orig = dict(dialogs._PATH_FALLBACKS)
        for k in self._orig:
            target = self.docs if k in ("save_dir", "playlist_dir") else self.music
            dialogs._PATH_FALLBACKS[k] = lambda p=target: p

    def tearDown(self):
        dialogs._PATH_FALLBACKS.clear()
        dialogs._PATH_FALLBACKS.update(self._orig)

    def test_a_missing_folder_falls_back(self):
        s = dialogs.apply_path_fallbacks({"library_dir": "X:\\gone"})
        self.assertEqual(s["library_dir"], str(self.music))

    def test_an_existing_folder_is_left_alone(self):
        keep = str(_STATE_DIR)
        s = dialogs.apply_path_fallbacks({"library_dir": keep})
        self.assertEqual(s["library_dir"], keep)

    def test_an_empty_setting_falls_back_too(self):
        s = dialogs.apply_path_fallbacks({"reference_path": "   "})
        self.assertEqual(s["reference_path"], str(self.music))

    def test_playlists_and_save_as_land_in_documents(self):
        s = dialogs.apply_path_fallbacks(
            {"save_dir": "X:\\gone", "playlist_dir": "X:\\gone"})
        self.assertEqual(s["save_dir"], str(self.docs))
        self.assertEqual(s["playlist_dir"], str(self.docs))

    def test_every_path_setting_has_a_fallback(self):
        s = dialogs.apply_path_fallbacks(
            {k: "X:\\gone" for k in self._orig})
        for k in self._orig:
            self.assertTrue(Path(s[k]).is_dir(), f"{k} still points nowhere")

    def test_other_settings_are_not_touched(self):
        s = dialogs.apply_path_fallbacks({"global_search": True, "secs": 45})
        self.assertEqual(s["global_search"], True)
        self.assertEqual(s["secs"], 45)

    def test_load_settings_applies_them(self):
        stores.save_settings({"library_dir": "X:\\gone"})
        self.assertEqual(dialogs.load_settings()["library_dir"], str(self.music))

    def test_the_configured_folder_is_kept_aside(self):
        """An unplugged drive must not be lost — it is only standing aside."""
        s = dialogs.apply_path_fallbacks({"library_dir": "X:\\tanzcds"})
        self.assertEqual(s[dialogs.PATHS_OFFLINE]["library_dir"], "X:\\tanzcds")

    def test_the_drive_coming_back_puts_the_folder_back(self):
        real = _STATE_DIR / "tanzcds"
        s = dialogs.apply_path_fallbacks({"library_dir": str(real)})
        self.assertEqual(s["library_dir"], str(self.music))   # not there yet
        real.mkdir()
        self.addCleanup(real.rmdir)
        s = dialogs.apply_path_fallbacks(s)
        self.assertEqual(s["library_dir"], str(real))
        self.assertNotIn(dialogs.PATHS_OFFLINE, s)

    def test_a_folder_picked_by_hand_wins(self):
        """Choosing a folder while the drive is away is a decision — the old
        path must not come back over it later."""
        real = _STATE_DIR / "tanzcds"
        picked = _STATE_DIR / "picked"
        picked.mkdir()
        self.addCleanup(picked.rmdir)
        s = dialogs.apply_path_fallbacks({"library_dir": str(real)})
        s["library_dir"] = str(picked)               # ⚙ Settings → Browse…
        s = dialogs.apply_path_fallbacks(s)
        self.assertNotIn(dialogs.PATHS_OFFLINE, s)
        real.mkdir()
        self.addCleanup(real.rmdir)
        self.assertEqual(dialogs.apply_path_fallbacks(s)["library_dir"],
                         str(picked))

    def test_it_keeps_waiting_across_a_restart(self):
        stores.save_settings(
            dialogs.apply_path_fallbacks({"library_dir": "X:\\tanzcds"}))
        s = dialogs.load_settings()
        self.assertEqual(s["library_dir"], str(self.music))
        self.assertEqual(s[dialogs.PATHS_OFFLINE]["library_dir"], "X:\\tanzcds")

    def test_nothing_missing_means_no_note_at_all(self):
        s = dialogs.apply_path_fallbacks({"library_dir": str(_STATE_DIR)})
        self.assertNotIn(dialogs.PATHS_OFFLINE, s)

    def test_a_fallback_that_is_missing_too_changes_nothing(self):
        dialogs._PATH_FALLBACKS["library_dir"] = lambda: _STATE_DIR / "nope"
        s = dialogs.apply_path_fallbacks({"library_dir": "X:\\gone"})
        self.assertEqual(s["library_dir"], "X:\\gone")


@unittest.skipUnless(_REDIRECTED, _NOT_REDIRECTED_MSG)
class UserFolderTest(unittest.TestCase):
    """The fallback folders themselves: Qt's own Music / Documents."""

    def test_music_and_documents_are_two_absolute_folders(self):
        music, docs = dialogs._user_music_dir(), dialogs._user_docs_dir()
        self.assertTrue(music.is_absolute(), music)
        self.assertTrue(docs.is_absolute(), docs)
        self.assertNotEqual(music, docs)

    def test_qt_saying_nothing_lands_under_home(self):
        got = dialogs._home_dir(object(), "Music")   # not a real location enum
        self.assertEqual(got, Path.home() / "Music")


class MediaBackendTest(unittest.TestCase):
    """🔊 ⚙ Settings → Audio backend: which engine Qt plays through. Only ever
    read at startup, into QT_MEDIA_BACKEND."""

    def setUp(self):
        self._orig = os.environ.get("QT_MEDIA_BACKEND")

    def tearDown(self):
        if self._orig is None:
            os.environ.pop("QT_MEDIA_BACKEND", None)
        else:
            os.environ["QT_MEDIA_BACKEND"] = self._orig

    @property
    def _default(self) -> str:
        return "ffmpeg" if sys.platform == "win32" else "auto"

    def test_an_older_settings_file_keeps_this_platform_default(self):
        self.assertEqual(dialogs.media_backend_of({}), self._default)

    def test_garbage_reads_as_the_default_too(self):
        for bad in ("wmf", "", None, 7):
            self.assertEqual(dialogs.media_backend_of({"media_backend": bad}),
                             self._default)

    def test_a_configured_backend_wins(self):
        """Named with something OTHER than the platform default, or the test
        would pass on the fallback alone."""
        other = "auto" if sys.platform == "win32" else "ffmpeg"
        self.assertEqual(
            dialogs.media_backend_of({"media_backend": other}), other)
        self.assertNotEqual(other, self._default)

    def test_automatic_means_qt_is_not_told_anything(self):
        self.assertEqual(dialogs.media_backend_env({"media_backend": "auto"}), "")

    def test_applying_it_sets_the_variable_qt_reads(self):
        dialogs.apply_media_backend({"media_backend": "ffmpeg"})
        self.assertEqual(os.environ["QT_MEDIA_BACKEND"], "ffmpeg")

    def test_automatic_clears_a_variable_that_was_already_there(self):
        """Otherwise 'let Qt choose' would quietly keep the last choice."""
        os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"
        dialogs.apply_media_backend({"media_backend": "auto"})
        self.assertNotIn("QT_MEDIA_BACKEND", os.environ)

    def test_only_this_platform_backends_are_offered(self):
        keys = [k for k, _caption in dialogs.MEDIA_BACKEND_CHOICES]
        self.assertIn("ffmpeg", keys)
        self.assertIn(self._default, keys)
        if sys.platform != "win32":
            # Naming it where it does not exist leaves the app with no audio.
            self.assertNotIn("windows", keys)


class RestartCommandTest(unittest.TestCase):
    """🔄 Changing the backend offers a restart — this is what gets started."""

    def setUp(self):
        self._argv = list(sys.argv)
        self._frozen = getattr(sys, "frozen", None)

    def tearDown(self):
        sys.argv = self._argv
        if self._frozen is None:
            if hasattr(sys, "frozen"):
                del sys.frozen
        else:
            sys.frozen = self._frozen

    def test_from_source_the_interpreter_runs_the_script_again(self):
        sys.argv = ["dancesport_gui.py", "--player"]
        prog, args = dialogs.restart_command()
        self.assertEqual(prog, sys.executable)
        self.assertEqual(args, ["dancesport_gui.py", "--player"])

    def test_a_frozen_build_is_the_program_itself(self):
        """argv[0] is the .exe there — passing it on would make it its own
        first argument, and the app would try to open itself as a playlist."""
        sys.frozen = True
        sys.argv = ["Danceplaylist.exe", "--player"]
        prog, args = dialogs.restart_command()
        self.assertEqual(prog, sys.executable)
        self.assertEqual(args, ["--player"])

    def test_a_restart_that_cannot_start_says_so(self):
        with mock.patch.object(dialogs.QProcess, "startDetached",
                               side_effect=OSError("no")):
            self.assertFalse(dialogs.restart_app())

    def test_a_started_restart_reports_success(self):
        with mock.patch.object(dialogs.QProcess, "startDetached",
                               return_value=True) as start:
            self.assertTrue(dialogs.restart_app())
        self.assertEqual(start.call_args[0][0], sys.executable)


@unittest.skipUnless(_REDIRECTED, _NOT_REDIRECTED_MSG)
class AutosaveRotationTest(unittest.TestCase):
    def setUp(self):
        self._orig_age = dialogs._AUTOSAVE_BACKUP_MIN_AGE
        dialogs._AUTOSAVE_BACKUP_MIN_AGE = 0   # rotate on every save
        dialogs.AUTOSAVE.remove()
        for n in range(1, dialogs.AUTOSAVE_BACKUPS + 2):
            dialogs._autosave_backup_path(n).unlink(missing_ok=True)

    def tearDown(self):
        dialogs._AUTOSAVE_BACKUP_MIN_AGE = self._orig_age

    @staticmethod
    def _saved(n: int) -> dict:
        return {"version": dialogs.AUTOSAVE_VERSION, "n": n}

    @staticmethod
    def _read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_backups_shift_oldest_out(self):
        total = dialogs.AUTOSAVE_BACKUPS + 2   # 2 more saves than slots
        for i in range(1, total + 1):
            dialogs.save_autosave(self._saved(i))
        # Current file holds the newest state …
        self.assertEqual(self._read(dialogs.AUTOSAVE.path)["n"], total)
        # … slot k holds the state from k saves ago …
        for k in range(1, dialogs.AUTOSAVE_BACKUPS + 1):
            self.assertEqual(
                self._read(dialogs._autosave_backup_path(k))["n"], total - k)
        # … and nothing spills past the last slot.
        self.assertFalse(
            dialogs._autosave_backup_path(dialogs.AUTOSAVE_BACKUPS + 1).exists())

    def test_fresh_backup_throttles_rotation(self):
        dialogs.save_autosave(self._saved(1))
        dialogs.save_autosave(self._saved(2))   # cuts backup .1 (n=1)
        dialogs._AUTOSAVE_BACKUP_MIN_AGE = 3600
        dialogs.save_autosave(self._saved(3))   # .1 too fresh → no rotation
        self.assertEqual(self._read(dialogs._autosave_backup_path(1))["n"], 1)
        self.assertEqual(self._read(dialogs.AUTOSAVE.path)["n"], 3)

    def test_first_save_creates_no_backup(self):
        dialogs.save_autosave(self._saved(1))
        self.assertTrue(dialogs.AUTOSAVE.exists())
        self.assertFalse(dialogs._autosave_backup_path(1).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
