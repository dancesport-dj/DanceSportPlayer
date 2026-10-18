#!/usr/bin/env python3
"""Click-through, chapter 13: Fix paths.

Run:  py -m unittest tests.gui.test_click_13_fix_paths -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/13-export-print-paths.md
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, DropFrom, printable

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel, QPushButton, QTabWidget
from gui.table.row_buttons import BUTTON_ROLE
from shared.columns import _COL_PLAY
from tests.qt_test_support import reap_widget


class FixPathsClickTest(ClickThrough):
    """13 Fix paths."""

    def moved_list(self, to: str = r"Z:\Moved\Musik") -> tuple[Path, list[str]]:
        """A deck saved as .m3u, as another PC wrote it: the same music under
        `to`, by default a drive this one does not have. Returns the file and
        its titles; the decks are empty again."""
        self.generate(rounds="1")
        titles = self.titles()
        known = set(self.saved_files())
        self.click(self.win._cfg.save_btn)
        [saved] = [p for p in self.saved_files() if p not in known]
        self.click(self.button("Empty every playlist deck"))
        music = self.settings["library_dir"]
        text = saved.read_text(encoding="utf-8-sig")
        moved = text.replace(music, to)
        self.assertNotEqual(moved, text, "the list names no library path")
        saved.write_text(moved, encoding="utf-8")
        return saved, titles

    def reference(self, path: str):
        """⚙ Paths & search: the Reference path, and no other search folder."""
        p = mock.patch.dict(self.win._settings,
                            {"reference_path": path, "remap_paths": []})
        p.start()
        self.addCleanup(p.stop)

    def on_disk(self) -> list[bool]:
        return [Path(m.entry.path).is_file()
                for m in self.win._deckset.table._row_meta if m and m.entry]

    def test_an_import_from_another_drive_finds_the_music_here(self):
        report = []
        with self.clicking() as op:
            self.reference(self.settings["library_dir"])
            saved, titles = self.moved_list()
            op.answer(self.titled("📂  Import — track paths"),
                      lambda box: (report.append(box.text()), box.accept()))
            self.import_list(saved)
            self.assertTrue(self.wait_until(lambda: self.titles() == titles),
                            f"saved {printable(titles)}\nimported {printable(self.titles())}")
            self.assertTrue(all(self.on_disk()), self.on_disk())
        self.assertEqual(len(report), 1, "no report of the re-rooted tracks")
        self.assertIn(f"{len(titles)} tracks", report[0])

    def test_fix_paths_relocates_what_an_import_left_broken(self):
        report = []

        def read_and_close(dlg):
            report.extend(lbl.text() for lbl in dlg.findChildren(QLabel))
            dlg.accept()

        with self.clicking() as op:
            self.reference("")
            saved, titles = self.moved_list()
            self.import_list(saved)
            self.assertTrue(self.wait_until(lambda: len(self.titles()) == len(titles)))
            self.assertFalse(any(self.on_disk()), "the import found them anyway")

            self.reference(self.settings["library_dir"])
            op.pick("🧭  Fix paths")
            op.answer(self.titled("🧭  Fix paths"), read_and_close)
            self.click(self.win._check_btn)
            self.assertTrue(self.wait_until(lambda: not op.script), op.script)
            self.assertTrue(all(self.on_disk()), self.on_disk())
            self.assertEqual(sorted(self.titles()), sorted(titles))
        self.assertTrue(any(f"Relocated {len(titles)} broken" in t for t in report),
                        printable(report))

    def paths(self) -> list[str]:
        return [str(m.entry.path)
                for m in self.win._deckset.table._row_meta if m and m.entry]

    def fix_window(self, op, act):
        """🧭 Fix paths, handled by `act(dlg)` while it is open."""
        op.pick("🧭  Fix paths")
        op.answer(self.titled("🧭  Fix paths"), act)
        self.click(self.win._check_btn)
        self.assertTrue(self.wait_until(lambda: not op.script), op.script)

    @staticmethod
    def fix_button(dlg) -> QPushButton:
        return next(b for b in dlg.findChildren(QPushButton) if b.text().startswith("🧭"))

    @staticmethod
    def texts(dlg) -> list[str]:
        return [lbl.text() for lbl in dlg.findChildren(QLabel)]

    def test_a_same_named_library_file_stands_in_and_ctrl_z_undoes_it(self):
        """No search folder to re-root under: the library's file of the same
        name takes the slot. Ctrl+Z takes the fix back out and Ctrl+Y puts it
        in again. (The undone state names files that are gone, and a restored
        state drops those, so the slots come back empty, not red.)"""
        report = []

        def read_and_close(dlg):
            report.extend(self.texts(dlg))
            dlg.accept()

        with self.clicking() as op:
            self.reference("")
            saved, titles = self.moved_list()
            self.import_list(saved)
            self.assertTrue(self.wait_until(lambda: len(self.titles()) == len(titles)))
            self.assertFalse(any(self.on_disk()), "the import found them anyway")
            self.fix_window(op, read_and_close)
            self.assertTrue(all(self.on_disk()), self.on_disk())
            self.assertEqual(sorted(self.titles()), sorted(titles))
            self.assertTrue(any(f"Relocated {len(titles)} broken" in t for t in report),
                            printable(report))
            # Ctrl+Z is the window's shortcut: back in the deck first.
            self.win.activateWindow()
            self.wait_until(self.win.isActiveWindow, 1000)
            fixed = self.paths()
            self.key(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
            self.assertTrue(self.wait_until(lambda: not set(fixed) & set(self.paths())),
                            printable(self.paths()))
            self.assertIn("Moved", repr(self.win._undo_timeline.current))
            self.key(Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
            self.assertTrue(self.wait_until(lambda: self.paths() == fixed),
                            printable(self.paths()))

    def test_fix_swaps_valid_copies_onto_the_reference_path(self):
        """The deck plays a copy of the music outside the Reference path; 🧭
        Fix puts the Reference path's own file into each slot."""
        copies = Path(tempfile.mkdtemp(prefix="dp_click_copies_"))
        self.addCleanup(shutil.rmtree, copies, True)
        music = Path(self.settings["library_dir"])
        shutil.copytree(music, copies, dirs_exist_ok=True)
        seen = {}

        def swap(dlg):
            fix = self.fix_button(dlg)
            seen["before"] = (self.texts(dlg), fix.text(), fix.isEnabled())
            self.click(fix)
            seen["after"] = (self.texts(dlg), fix.isEnabled())
            dlg.accept()

        with self.clicking() as op:
            self.reference("")
            saved, titles = self.moved_list(str(copies))
            self.import_list(saved)
            self.assertTrue(self.wait_until(lambda: len(self.titles()) == len(titles)))
            self.assertTrue(all(p.startswith(str(copies)) for p in self.paths()),
                            printable(self.paths()))
            n = len(titles)
            self.reference(str(music))
            self.fix_window(op, swap)
            self.assertTrue(all(p.startswith(str(music)) for p in self.paths()),
                            printable(self.paths()))
            self.assertEqual(sorted(self.titles()), sorted(titles))
        texts, label, enabled = seen["before"]
        self.assertEqual((label, enabled), ("🧭  Fix (swap in playlists)", True))
        self.assertTrue(any(f"{n} valid tracks are not on the Reference path" in t
                            and f"{n} have a copy there" in t for t in texts),
                        printable(texts))
        texts, enabled = seen["after"]
        self.assertFalse(enabled)
        self.assertTrue(any("All track paths are valid" in t for t in texts),
                        printable(texts))

    def test_dragged_in_playlists_get_only_their_path_lines_rewritten(self):
        music = Path(self.settings["library_dir"])
        here, there = sorted(music.rglob("*.mp3"))[:2]
        moved = Path(r"Z:\Moved\Musik") / there.relative_to(music)
        ghost = Path(r"Z:\Nowhere\Ghost (SB 50).mp3")
        m3u = self.out / "old pc.m3u"
        text = "\r\n".join([
            "#EXTM3U", "# written on the old PC",
            f"#EXTINF:30,{here.stem}", str(here),
            f"#EXTINF:31,{there.stem}", str(moved),
            "#EXTINF:32,Ghost", str(ghost)]) + "\r\n"
        m3u.write_bytes(text.encode("utf-8"))
        seen = {}

        def drop_and_fix(dlg):
            tabs = dlg.findChild(QTabWidget)
            bar = tabs.tabBar()
            QTest.mouseClick(bar, Qt.MouseButton.LeftButton, pos=bar.tabRect(1).center())
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(m3u))])
            tabs.currentWidget()._zone.dropEvent(DropFrom(QPointF(20, 20), mime, None))
            QTest.qWait(5)
            fix = self.fix_button(dlg)
            seen["before"] = (self.texts(dlg), fix.text(), fix.isEnabled())
            self.click(fix)
            dlg.accept()

        with self.clicking() as op:
            self.reference(str(music))
            self.fix_window(op, drop_and_fix)
        texts, label, enabled = seen["before"]
        self.assertEqual((label, enabled), ("🧭  Fix (overwrite)", True))
        self.assertTrue(any("1 path line to fix" in t
                            and "1 valid · 1 unresolved across 1 playlist" in t
                            for t in texts), printable(texts))
        self.assertEqual(m3u.read_bytes().decode("utf-8"),
                         text.replace(str(moved), str(there)))
        self.assertEqual(m3u.with_name(m3u.name + ".bak").read_bytes().decode("utf-8"),
                         text)

    def vanish(self, row: int) -> Path:
        """The title's file goes away while the deck shows it (renamed, as a
        delete would; put back after the scenario)."""
        path = Path(self.entry_at(row).path)
        gone = path.with_name(path.name + ".gone")
        path.rename(gone)
        self.addCleanup(gone.rename, path)
        return path

    def test_a_title_gone_from_disk_turns_red_when_played(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            row = self.song_rows()[1]
            path = self.vanish(row)
            self.click_cell(table, row, _COL_PLAY)

            def glyph():
                return table.item(row, _COL_PLAY).data(BUTTON_ROLE)
            self.assertTrue(self.wait_until(lambda: glyph() == "❗"),
                            f"the ▶ reads {printable(glyph())!r}")
            self.assertIn(str(path), self.win._playback.failed)
            self.assertEqual(table._current_play_row, -1, "a dead title looks playing")

    def test_playing_mode_skips_a_title_gone_from_disk(self):
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            table = self.win._deckset.table
            first, gone, after, *_ = self.song_rows()
            self.assertTrue(table._advance_get(), "⏭ Auto is off in Playing mode")
            self.play_row(first)
            self.vanish(gone)
            self.click_cell(table, gone, _COL_PLAY)
            self.assertTrue(self.wait_until(lambda: table._current_play_row == after),
                            f"playing row {table._current_play_row}, not {after}")

    def test_a_window_gone_mid_start_takes_its_watchdog_along(self):
        # Every start arms a 2 s watchdog. A window destroyed before it fires
        # — the token not moved on, as when a start comes after the teardown
        # bumped it — must take it along, not raise on its dead player.
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            self.play_row(self.song_rows()[0])
            self.assertTrue(self.wait_until(
                lambda: self.win._player.playbackState().name == "PlayingState"))
        caught = []
        with mock.patch.object(sys, "excepthook", lambda *a: caught.append(a[1])):
            reap_widget(self.win)
            QTest.qWait(2600)
        self.assertEqual([repr(e) for e in caught], [])


if __name__ == "__main__":
    unittest.main()
