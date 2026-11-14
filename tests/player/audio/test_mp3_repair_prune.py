"""🔧 Repaired mp3 copies do not pile up, and the damaged file is named.

Review 2026-11-12, F3 and suggestion 5: every repaired copy stayed in
<temp>/danceplaylist_repaired for good. Copies unused for a week now go at
the start, and so do .part files a crash left behind. A copy in use keeps
its place: reusing it refreshes its time. The first time a title plays
from a copy in a session, the window says which file is damaged, so it
can be replaced at its source.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_repair_prune_"))

from player.audio import mp3_repair

DAY = 86400


class PruneTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dp_prune_"))
        patcher = mock.patch.object(mp3_repair.tempfile, "gettempdir",
                                    return_value=str(self.tmp))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = mp3_repair.copies_dir()
        self.dir.mkdir(parents=True)
        self.now = time.time()

    def _file(self, name, age_s):
        p = self.dir / name
        p.write_bytes(b"x")
        os.utime(p, (self.now - age_s, self.now - age_s))
        return p

    def test_a_copy_unused_for_a_week_goes(self):
        old = self._file("aaaa.mp3", 8 * DAY)
        fresh = self._file("bbbb.mp3", 2 * DAY)
        self.assertEqual(mp3_repair.prune_copies(now=self.now), 1)
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())

    def test_a_part_left_by_a_crash_goes_but_one_being_written_stays(self):
        stale = self._file("cccc.part", 2 * 3600)
        writing = self._file("dddd.part", 5)
        mp3_repair.prune_copies(now=self.now)
        self.assertFalse(stale.exists())
        self.assertTrue(writing.exists(), "another instance may be writing it")

    def test_nothing_else_in_the_folder_is_touched(self):
        other = self._file("notes.txt", 30 * DAY)
        mp3_repair.prune_copies(now=self.now)
        self.assertTrue(other.exists())

    def test_no_folder_is_no_error(self):
        self.dir.rmdir()
        self.assertEqual(mp3_repair.prune_copies(now=self.now), 0)

    def test_a_copy_in_use_is_kept(self):
        src = self.tmp / "title.mp3"
        src.write_bytes(b"\xff\xfb\x90\x00" * 10)
        copy = mp3_repair._copy_path(src)
        copy.write_bytes(b"copy")
        os.utime(copy, (self.now - 8 * DAY, self.now - 8 * DAY))
        self.assertEqual(mp3_repair.cached_copy(src), copy)
        mp3_repair.prune_copies()
        self.assertTrue(copy.exists(), "reused this session, so not stale")


class TellTheDamagedFileTest(unittest.TestCase):

    def _host(self):
        from player.window import main_load
        host = SimpleNamespace(_playback=SimpleNamespace(repaired={}), _settings={})
        host._keep_repaired = lambda path, copy: main_load.TrackLoadMixin._keep_repaired(
            host, path, copy)
        return host, main_load

    def test_a_cached_copy_is_named_once_a_session(self):
        host, main_load = self._host()
        path = Path("C:/music/Waltz.mp3")
        with mock.patch.object(main_load, "resolve_file", return_value=path), \
                mock.patch.object(main_load, "cached_copy", return_value=Path("C:/t/x.mp3")), \
                mock.patch.object(main_load, "show_toast") as toast:
            main_load.TrackLoadMixin._source_url(host, path)
            main_load.TrackLoadMixin._source_url(host, path)
        toast.assert_called_once()
        self.assertIn("Waltz", toast.call_args.args[1])

    def test_a_title_without_a_copy_says_nothing(self):
        host, main_load = self._host()
        path = Path("C:/music/Tango.mp3")
        with mock.patch.object(main_load, "resolve_file", return_value=path), \
                mock.patch.object(main_load, "cached_copy", return_value=None), \
                mock.patch.object(main_load, "show_toast") as toast:
            main_load.TrackLoadMixin._source_url(host, path)
        toast.assert_not_called()


class PruneAtStartTest(unittest.TestCase):

    def test_the_window_prunes_as_it_opens(self):
        from PySide6.QtWidgets import QApplication

        from tests.qt_test_support import reap_widget, stub_window_startup
        self.app = QApplication.instance() or QApplication([])
        gui = stub_window_startup(self, {"app_mode": "both"})
        import threading
        ran = threading.Event()
        where = []

        def prune():
            where.append(threading.current_thread())
            ran.set()
        with mock.patch.object(gui, "prune_copies", side_effect=prune):
            win = gui.MainWindow()
            win._loading_dlg.accept()
            self.addCleanup(reap_widget, win)
            self.assertTrue(ran.wait(5), "the prune never ran")
        # Review: a temp folder full of copies (or a slow disk) held up the
        # window's start; the prune now runs beside it.
        self.assertIsNot(where[0], threading.main_thread())


if __name__ == "__main__":
    unittest.main()
