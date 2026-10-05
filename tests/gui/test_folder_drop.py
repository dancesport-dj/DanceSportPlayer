#!/usr/bin/env python3
"""Tests for dropping a whole FOLDER onto a playlist.

Run:  py -m unittest tests.gui.test_folder_drop -v

Music arrives by the folder — a CD ripped into one, a tournament's tracks laid
out one folder per dance. Dragging that folder in adds everything inside it,
subfolders included, instead of asking the user to open it and rubber-band the
files. The tree is read only when the folder is actually DROPPED: the checks
that run while the drag hovers count a folder without walking it, or a music
root under the cursor would stat thousands of files per mouse move.

Adding them costs real time — every track not already in the library has its
tags read — so past half a second a progress dialog appears over it, with a
Cancel that keeps whatever it had found by then.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fdrop_"))

from PySide6.QtCore import QMimeData, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui import playlist_table  # noqa: E402
from gui import table_actions  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402


class _Sig:
    """The one thing `_entries_for_paths` asks of cancel_requested."""

    def __init__(self):
        self._cbs = []

    def connect(self, cb):
        self._cbs.append(cb)

    def emit(self):
        for cb in self._cbs:
            cb()


class _RecordingBusy:
    """Stands in for BusyDialog: records that it was raised at all, and can
    answer the first progress tick with a Cancel."""

    made = []
    cancel_at_once = False

    def __init__(self, parent=None, message="", cancelable=False):
        self.message = message
        self.progress = []
        self.finished = False
        self.cancel_requested = _Sig()
        _RecordingBusy.made.append(self)

    def show_after(self, ms=500):
        pass

    def set_progress(self, done, total, detail="", eta_seconds=-1.0):
        self.progress.append((done, total))
        if _RecordingBusy.cancel_at_once:
            self.cancel_requested.emit()

    def finish(self):
        self.finished = True


class _Drop:
    """The bit of a drag event the droppable-checks read: its mime data, and a
    source that is not one of our own tables (i.e. an Explorer drag)."""

    def __init__(self, *paths):
        self._md = QMimeData()
        self._md.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])

    def mimeData(self):
        return self._md

    def source(self):
        return None


class _FolderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # root/ b.mp3 a.mp3 notes.txt list.m3u  sub/c.flac
        cls.root = Path(tempfile.mkdtemp(prefix="dp_fdrop_r_")) / "Turnier 2026"
        (cls.root / "sub").mkdir(parents=True)
        for rel in ("b.mp3", "a.mp3", "notes.txt", "list.m3u", "sub/c.flac"):
            (cls.root / rel).write_bytes(b"x")

    def setUp(self):
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)

    def names(self, paths):
        return [p.name for p in paths]


class ExpandTest(_FolderTest):

    def test_a_dropped_folder_stands_for_the_music_inside_it(self):
        got = self.table._wishlist_droppables(_Drop(self.root))
        self.assertEqual(self.names(got), ["a.mp3", "b.mp3", "c.flac"])

    def test_subfolders_come_too(self):
        """One folder per dance is how a tournament's music is laid out."""
        self.assertIn("c.flac", self.names(
            self.table._wishlist_droppables(_Drop(self.root))))

    def test_what_is_not_music_stays_out(self):
        got = self.names(self.table._wishlist_droppables(_Drop(self.root)))
        self.assertNotIn("notes.txt", got)

    def test_a_playlist_lying_in_the_folder_is_not_read(self):
        """Reading list.m3u as well would add every track it names a second
        time — the folder's own files are what was dropped."""
        self.assertNotIn("list.m3u", self.names(
            self.table._wishlist_droppables(_Drop(self.root))))

    def test_files_and_folders_can_arrive_together(self):
        extra = self.root.parent / "single.mp3"
        extra.write_bytes(b"x")
        self.addCleanup(extra.unlink)
        got = self.names(self.table._wishlist_droppables(_Drop(extra, self.root)))
        self.assertEqual(got, ["single.mp3", "a.mp3", "b.mp3", "c.flac"])

    def test_a_folder_with_no_music_yields_nothing(self):
        empty = Path(tempfile.mkdtemp(prefix="dp_fdrop_e_"))
        self.assertEqual(self.table._wishlist_droppables(_Drop(empty)), [])


class HoverIsCheapTest(_FolderTest):
    """What runs on every mouse move of a drag must not walk the tree."""

    def test_the_accept_check_leaves_the_folder_unopened(self):
        with mock.patch.object(PlaylistTable, "_files_from_dir") as walked:
            got = self.table._wishlist_droppables(_Drop(self.root),
                                                  expand_dirs=False)
        walked.assert_not_called()
        self.assertEqual(got, [self.root])

    def test_a_deck_still_accepts_the_drop(self):
        """The folder counts as droppable even though it was never opened."""
        self.assertTrue(self.table._has_droppable(_Drop(self.root)))

    def test_a_deck_refuses_what_it_cannot_use(self):
        """Guards the check above: it isn't just saying yes to everything."""
        txt = self.root / "notes.txt"
        self.assertFalse(self.table._has_droppable(_Drop(txt)))

    def test_a_folder_holding_one_m3u_is_not_a_playlist_import(self):
        """Importing an .m3u REPLACES a deck. A folder means its music, so a
        folder that happens to hold a single playlist file must not trip that."""
        one = Path(tempfile.mkdtemp(prefix="dp_fdrop_m_"))
        (one / "set.m3u").write_bytes(b"x")
        self.assertIsNone(self.table._dropped_m3u(_Drop(one)))
        # ...while the .m3u itself, dropped directly, still is one.
        self.assertIsNotNone(self.table._dropped_m3u(_Drop(one / "set.m3u")))


class BigFolderTest(_FolderTest):
    """A music root dragged in by accident costs minutes — every file's tags are
    read on the way in. So past a hundred tracks the folder drop asks first."""

    def _question(self, answer):
        return mock.patch.object(playlist_table.QMessageBox, "question",
                                 return_value=answer)

    def test_a_big_folder_asks(self):
        self.table._DIR_DROP_ASK = 1
        with self._question(QMessageBox.StandardButton.Yes) as q:
            got = self.table._wishlist_droppables(_Drop(self.root))
        q.assert_called_once()
        self.assertEqual(self.names(got), ["a.mp3", "b.mp3", "c.flac"])

    def test_no_means_nothing_is_added(self):
        self.table._DIR_DROP_ASK = 1
        with self._question(QMessageBox.StandardButton.No):
            self.assertEqual(self.table._wishlist_droppables(_Drop(self.root)), [])

    def test_an_ordinary_folder_is_not_worth_a_dialog(self):
        with self._question(QMessageBox.StandardButton.No) as q:
            self.table._wishlist_droppables(_Drop(self.root))
        q.assert_not_called()

    def test_the_threshold_is_a_hundred(self):
        self.assertEqual(PlaylistTable._DIR_DROP_ASK, 100)


class ProgressTest(_FolderTest):
    """The dialog over a long add. It is deferred, so a drop of two or three
    tracks — the everyday case — never sees a window at all."""

    def setUp(self):
        super().setUp()
        _RecordingBusy.made = []
        _RecordingBusy.cancel_at_once = False
        self.table._entry_for = lambda p: MusicEntry(
            path=p, title=p.stem, dance="WW", bpm=None)
        patch = mock.patch.object(table_actions, "BusyDialog", _RecordingBusy)
        patch.start()
        self.addCleanup(patch.stop)

    def paths(self, n):
        return [self.root / f"{i}.mp3" for i in range(n)]

    def test_a_quick_add_shows_nothing(self):
        got = self.table._entries_for_paths(self.paths(3))
        self.assertEqual(len(got), 3)
        self.assertEqual(_RecordingBusy.made, [], "a window flashed up for 3 files")

    def test_a_long_add_gets_a_dialog_and_closes_it(self):
        self.table._DROP_PROGRESS_AFTER = 0   # "it has already taken too long"
        self.table._entries_for_paths(self.paths(5))
        self.assertEqual(len(_RecordingBusy.made), 1)
        self.assertTrue(_RecordingBusy.made[0].progress, "the bar never moved")
        self.assertTrue(_RecordingBusy.made[0].finished, "the dialog was left open")

    def test_it_says_how_many_are_coming(self):
        self.table._DROP_PROGRESS_AFTER = 0
        self.table._entries_for_paths(self.paths(250))
        self.assertIn("250", _RecordingBusy.made[0].message)

    def test_half_a_second_is_the_wait(self):
        self.assertEqual(PlaylistTable._DROP_PROGRESS_AFTER, 0.5)

    def test_the_last_file_is_never_worth_a_window(self):
        """It would appear and close in the same breath."""
        self.table._DROP_PROGRESS_AFTER = 0
        self.table._entries_for_paths(self.paths(1))
        self.assertEqual(_RecordingBusy.made, [])

    def test_cancelling_stops_it_and_keeps_what_was_found(self):
        self.table._DROP_PROGRESS_AFTER = 0
        _RecordingBusy.cancel_at_once = True
        got = self.table._entries_for_paths(self.paths(50))
        self.assertLess(len(got), 50, "Cancel didn't stop the resolve")
        self.assertTrue(got, "what had already been found was thrown away")
        self.assertTrue(all(e is not None for e in got))

    def test_a_result_per_path_so_callers_can_pair_them_up(self):
        """_fill_empty_slots_with zips the two together to know which track goes
        where — a path that resolves to nothing has to hold its place."""
        self.table._entry_for = lambda p: (
            None if p.name == "1.mp3" else MusicEntry(path=p, title=p.stem,
                                                      dance="WW", bpm=None))
        got = self.table._entries_for_paths(self.paths(3))
        self.assertEqual([e is None for e in got], [False, True, False])


class UnreadableReportTest(_FolderTest):
    """A folder can hold a hundred files that aren't music. A hundred modal
    boxes is not a report — one is."""

    def _information(self):
        return mock.patch.object(table_actions.QMessageBox, "information")

    def test_one_message_for_the_lot(self):
        # Nothing resolves: the table has no library behind it.
        with self._information() as box:
            got = self.table._resolve_drop_entries(
                [self.root / f"{i}.mp3" for i in range(5)])
        self.assertEqual(got, [])
        box.assert_called_once()
        self.assertIn("0.mp3", box.call_args.args[2])

    def test_a_long_list_is_trimmed(self):
        with self._information() as box:
            self.table._resolve_drop_entries(
                [self.root / f"{i}.mp3" for i in range(20)])
        self.assertIn("plus 12 more", box.call_args.args[2])

    def test_a_dead_line_in_an_m3u_stays_silent(self):
        """A playlist naming a track that has moved is not the user's doing."""
        m3u = self.root / "gone.m3u"
        m3u.write_text("#EXTM3U\nC:\\nowhere\\ghost.mp3\n", encoding="utf-8")
        self.addCleanup(m3u.unlink)
        with self._information() as box:
            self.assertEqual(self.table._resolve_drop_entries([m3u]), [])
        box.assert_not_called()


if __name__ == "__main__":
    unittest.main()
