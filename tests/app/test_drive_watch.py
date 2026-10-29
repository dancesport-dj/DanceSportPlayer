#!/usr/bin/env python3
"""🔌 A stick pulled mid-evening is noticed without anybody pressing ▶.

Run:  py -m unittest tests.app.test_drive_watch -v

Every few seconds the window reads the drive list and checks the files its
decks, wishlists and 🎛 pads point at, on a thread of its own. A title that
was there and is gone now turns red at once and a toast names the likely
cause; one that comes back turns white again. Titles that were gone from the
start are red already and raise nothing.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_drive_watch_"))

from PySide6.QtWidgets import QApplication, QMainWindow

from gui.window import main_drives
from gui.window.main_drives import DriveWatchMixin
from planner.music import drives
from planner.music.drives import DriveWatch, drive_of, missing_among, warning
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

STICK = r"F:\tanzcds\lateincd\cc31.mp3"
LOCAL = r"C:\music\lw29.mp3"
ON_G = r"G:\tanzcds\lateincd\cc31.mp3"


@unittest.skipUnless(sys.platform == "win32", "drive letters are Windows'")
class DriveNameTest(unittest.TestCase):

    def test_the_drive_of_a_path(self):
        self.assertEqual(drive_of(STICK), "F:")
        self.assertEqual(drive_of("f:/x.mp3"), "F:")
        self.assertEqual(drive_of(r"\\server\share\x.mp3"), "")

    def test_this_pc_has_its_system_drive(self):
        self.assertIn(os.environ.get("SystemDrive", "C:").upper(),
                      drives.mounted_drives())


class MissingAmongTest(unittest.TestCase):

    def test_a_drive_that_errors_counts_as_gone(self):
        def exists(p):
            if p == "b":
                raise OSError("device not ready")
            return p == "a"
        self.assertEqual(missing_among(["a", "b", "c"], exists), {"b", "c"})


class DriveWatchTest(unittest.TestCase):

    def setUp(self):
        self.watch = DriveWatch()
        self.assertIsNone(self.watch.step({"C:", "F:"}, {STICK, LOCAL}, set()))

    def test_nothing_changed_is_none(self):
        self.assertIsNone(self.watch.step({"C:", "F:"}, {STICK, LOCAL}, set()))

    def test_a_pulled_stick_names_its_drive_and_titles(self):
        change = self.watch.step({"C:"}, {STICK, LOCAL}, {STICK})
        assert change is not None
        self.assertEqual(change.gone_drives, {"F:"})
        self.assertEqual(change.missing, {STICK})
        with mock.patch.object(drives, "drive_of", lambda p: "F:" if p == STICK else "C:"):
            text = warning(change)
        self.assertIn("F:", text)
        self.assertIn("USB", text)
        self.assertIn("1", text)

    def test_a_file_gone_from_a_drive_still_there_is_moved(self):
        change = self.watch.step({"C:", "F:"}, {STICK, LOCAL}, {LOCAL})
        assert change is not None
        self.assertNotIn("USB", warning(change))
        self.assertIn("moved", warning(change))

    def test_the_stick_back_brings_its_titles_back(self):
        self.watch.step({"C:"}, {STICK, LOCAL}, {STICK})
        change = self.watch.step({"C:", "F:"}, {STICK, LOCAL}, set())
        assert change is not None
        self.assertEqual(change.new_drives, {"F:"})
        self.assertEqual(change.back, {STICK})
        self.assertIn("back", warning(change))

    def test_a_title_gone_from_the_start_raises_nothing(self):
        watch = DriveWatch()
        watch.step({"C:"}, {STICK}, {STICK})
        self.assertIsNone(watch.step({"C:"}, {STICK}, {STICK}))

    def test_a_title_added_while_gone_raises_nothing(self):
        # A restored list or a drop that holds a gone file: red already.
        new = r"G:\gone.mp3"
        self.assertIsNone(self.watch.step({"C:", "F:"}, {STICK, LOCAL, new}, {new}))

    def test_a_drive_nothing_plays_from_is_only_logged(self):
        change = self.watch.step({"C:", "F:", "H:"}, {STICK, LOCAL}, set())
        assert change is not None
        self.assertEqual(change.new_drives, {"H:"})
        self.assertEqual(warning(change), "")


class RemappedDriveTest(unittest.TestCase):
    """Marcel (F7): a drive letter remapped is not noticed — no toast, and
    nothing says the titles were found on the new letter."""

    def setUp(self):
        patcher = mock.patch.object(drives, "drive_of", lambda p: str(p)[:2].upper())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.watch = DriveWatch()
        self.watch.step({"C:", "F:"}, {STICK, LOCAL}, set())

    def test_a_remapped_stick_says_where_its_titles_play_now(self):
        change = self.watch.step({"C:", "G:"}, {STICK, LOCAL}, set(), {STICK: ON_G})
        assert change is not None
        self.assertEqual(change.rehomed, {STICK: ON_G})
        self.assertEqual(change.paths(), {STICK})
        text = warning(change)
        self.assertIn("F:", text)
        self.assertIn("G:", text)
        self.assertIn("1", text)

    def test_it_is_said_once(self):
        self.watch.step({"C:", "G:"}, {STICK, LOCAL}, set(), {STICK: ON_G})
        self.assertIsNone(
            self.watch.step({"C:", "G:"}, {STICK, LOCAL}, set(), {STICK: ON_G}))

    def test_a_remap_seen_in_two_looks_ends_on_the_new_letter(self):
        """F: gone in one look, G: there in the next: the titles are back,
        and the note says from where."""
        self.watch.step({"C:"}, {STICK, LOCAL}, {STICK})
        change = self.watch.step({"C:", "G:"}, {STICK, LOCAL}, set(), {STICK: ON_G})
        assert change is not None
        self.assertIn("G:", warning(change))

    def test_the_old_letter_back_is_a_change_too(self):
        self.watch.step({"C:", "G:"}, {STICK, LOCAL}, set(), {STICK: ON_G})
        change = self.watch.step({"C:", "F:"}, {STICK, LOCAL}, set(), {})
        assert change is not None
        self.assertEqual(change.paths(), {STICK})

    def test_a_copy_on_the_same_drive_is_no_remap(self):
        """A 🧭 search folder on the stick's own drive: nothing to say."""
        moved = r"F:\elsewhere\cc31.mp3"
        self.assertIsNone(
            self.watch.step({"C:", "F:"}, {STICK, LOCAL}, set(), {STICK: moved}))


class _Meta:
    def __init__(self, path):
        self.path_str = path


class _Table:
    def __init__(self, paths):
        self.rows = [_Meta(p) for p in paths]
        self.refreshed = []
        self._row_meta = SimpleNamespace(numbered=lambda: list(enumerate(self.rows)))

    def refresh_paths(self, paths):
        self.refreshed.append(set(paths))
        return len(paths)


class _Wall:
    def __init__(self, paths):
        self.page = SimpleNamespace(pads={(0, i): SimpleNamespace(path=p)
                                          for i, p in enumerate(paths)})
        self.refreshed = 0

    def pages(self):
        return [self.page]

    def refresh_missing(self):
        self.refreshed += 1


class _Win(DriveWatchMixin, QMainWindow):
    def __init__(self, tables, wall, settings):
        super().__init__()
        me: Any = self
        me._deckset = SimpleNamespace(all_tables=tables)
        me._cartwall = wall
        me._settings = settings
        self._init_drive_watch()
        self._drive_hub.timer.stop()    # the test ticks by hand


class WindowTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dp_drives_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.track = self.tmp / "song.mp3"
        self.track.write_bytes(b"ID3")
        self.pad = self.tmp / "tusch.mp3"
        self.pad.write_bytes(b"ID3")
        self.table = _Table([str(self.track)])
        self.wall = _Wall([str(self.pad)])
        self.win = _Win([self.table], self.wall, {})
        self.addCleanup(reap_widget, self.win)
        self.toasts = []
        self.red = []
        def toast(_w, text, _ms=0, error=False):
            self.toasts.append(text)
            self.red.append(error)
        patcher = mock.patch.object(main_drives, "show_toast", toast)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tick(self):
        self.win._drive_tick()
        probe = self.win._drive_hub.probe
        assert probe is not None
        probe.join(5)
        QApplication.processEvents()

    def test_a_title_that_vanishes_turns_red_and_says_so(self):
        self.tick()     # the baseline
        self.assertEqual(self.table.refreshed, [])
        self.track.unlink()
        self.tick()
        self.assertEqual(self.table.refreshed, [{str(self.track)}])
        self.assertEqual(self.wall.refreshed, 1)
        self.assertEqual(len(self.toasts), 1)
        self.assertEqual(self.win.statusBar().currentMessage(), self.toasts[0])
        self.assertEqual(self.red, [True])

    def test_a_pad_found_under_the_search_folders_is_not_gone(self):
        self.tick()
        moved = self.tmp / "elsewhere" / "tusch.mp3"
        moved.parent.mkdir()
        self.pad.rename(moved)
        self.win._settings["remap_paths"] = [str(moved.parent)]
        self.tick()
        self.assertEqual(self.toasts, [])

    def test_a_title_found_on_another_drive_says_so(self):
        self.tick()
        on_g = r"G:\music\song.mp3"
        with mock.patch.object(main_drives, "resolve_file",
                               lambda p, _s: Path(on_g) if p == str(self.track) else Path(p)), \
                mock.patch.object(drives, "drive_of",
                                  lambda p: "G:" if str(p) == on_g else "F:"):
            self.tick()
        self.assertEqual(self.table.refreshed, [{str(self.track)}])
        self.assertEqual(len(self.toasts), 1)
        self.assertIn("G:", self.toasts[0])

    def test_a_vanished_pad_says_so(self):
        self.tick()
        self.pad.unlink()
        self.tick()
        self.assertEqual(self.wall.refreshed, 1)
        self.assertEqual(len(self.toasts), 1)

    def test_a_title_that_comes_back_turns_white_again(self):
        self.tick()
        gone = self.track.with_suffix(".gone")
        self.track.rename(gone)
        self.tick()
        gone.rename(self.track)
        self.tick()
        self.assertEqual(self.table.refreshed, [{str(self.track)}] * 2)
        self.assertIn("back", self.toasts[-1])
        # Good news, not an error: the plain toast, not the red one (Marcel).
        self.assertEqual(self.red, [True, False])

    def test_a_slow_look_is_not_stacked(self):
        hub = self.win._drive_hub
        hub.probe = SimpleNamespace(is_alive=lambda: True)  # pyright: ignore[reportAttributeAccessIssue]
        self.win._drive_tick()
        self.assertIsInstance(hub.probe, SimpleNamespace)

    def test_a_drive_change_from_windows_looks_at_once(self):
        """WM_DEVICECHANGE: a stick in or out, a letter remapped — looked at
        in a second, not on the next 10 s tick."""
        hub = self.win._drive_hub
        hub.soon.stop()
        fields = {1: (0, 0x0219, 0x8000), 2: (0, 0x0219, 0x0007), 3: (0, 0x0200, 0x8000)}
        flt = main_drives._DeviceFilter(hub.soon.start, fields.get)
        self.assertEqual(flt.nativeEventFilter(b"windows_generic_MSG", 3), (False, 0))
        self.assertFalse(hub.soon.isActive(), "a mouse move")
        flt.nativeEventFilter(b"windows_generic_MSG", 2)
        self.assertFalse(hub.soon.isActive(), "a device change that is no volume")
        flt.nativeEventFilter(b"windows_generic_MSG", 1)
        self.assertTrue(hub.soon.isActive())
        self.assertLess(hub.soon.interval(), main_drives.DRIVE_CHECK_MS)

    def test_closing_stops_the_watch(self):
        self.win._drive_hub.timer.start()
        self.win._drive_watch_shutdown()
        self.assertFalse(self.win._drive_hub.timer.isActive())

    def test_a_window_without_the_watch_closes_too(self):
        # The quit tests build a bare window that never ran _init_drive_watch.
        bare = _Win.__new__(_Win)
        QMainWindow.__init__(bare)
        self.addCleanup(reap_widget, bare)
        bare._drive_watch_shutdown()


if __name__ == "__main__":
    unittest.main()
