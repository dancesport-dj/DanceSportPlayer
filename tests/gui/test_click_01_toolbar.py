#!/usr/bin/env python3
"""Click-through, chapter 01: The toolbar.

Run:  py -m unittest tests.gui.test_click_01_toolbar -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/01-getting-started.md
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, _silent_mp3

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox
import gui.dialogs
from shared import stores


class ToolbarClickTest(ClickThrough):
    """01 The toolbar."""

    # ── First start ─────────────────────────────────────────────────────────

    def test_the_first_start_asks_for_the_mode_once_and_planner_hides_the_floor(self):
        ok = QDialogButtonBox.StandardButton.Ok

        def planner_only(dlg):
            radio = dlg._radios["planner"]   # stretched: aim at the dot
            QTest.mouseClick(radio, Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier,
                             QPoint(8, radio.height() // 2))
            self.click(dlg.findChild(QDialogButtonBox).button(ok))

        with self.clicking() as op,                 mock.patch.object(gui.dialogs, "warn_if_ffmpeg_missing") as ffmpeg:
            op.answer(self.titled("Welcome to DanceSport"), planner_only)
            self.assertEqual(gui.dialogs.ensure_app_mode(), "planner")
            self.assertEqual(stores.SETTINGS.read().get("app_mode"), "planner")
            ffmpeg.assert_called_once()
            # Asked once: the second start reads the answer.
            self.assertEqual(gui.dialogs.ensure_app_mode(), "planner")
            self.assertEqual(ffmpeg.call_count, 1)

        with mock.patch.dict(self.settings, {"app_mode": "planner"}):
            self.restart()
            win = self.win
            with self.clicking():
                title = win.windowTitle()
                self.assertTrue(title.startswith("DanceSport Planner"), title)
                self.assertNotIn("Player", title)
                self.assertTrue(win._mode_row_w.isHidden(), "the 📝 / ▶ switch shows")
                self.assertTrue(win._cart_btn.isHidden(), "the 🎛 cartwall shows")
                self.assertTrue(all(b.isVisible() for b in win._planner_btns))
                self.generate(rounds="1")

    def test_a_new_favorites_library_is_scanned_on_the_next_start(self):
        new = Path(tempfile.mkdtemp(prefix="dp_click_lib_"))
        samba = new / "LateinCD" / "Samba"
        samba.mkdir(parents=True)
        _silent_mp3(samba / "Senorita.mp3", 3)          # no code: the folder says
        _silent_mp3(new / "LateinCD" / "Night (RB 25).mp3", 3)
        before = len(self.win._library.lib.entries)
        told = []

        def info(_parent, title, text, *_a, **_kw):
            told.append((title, text))
            return QMessageBox.StandardButton.Ok

        def point_at_new(dlg):
            dlg._lib_edit.setText(str(new))
            self.click(dlg.findChild(QDialogButtonBox).button(
                QDialogButtonBox.StandardButton.Ok))

        with self.clicking() as op, mock.patch.object(QMessageBox, "information", info):
            op.answer(self.titled("⚙  Settings"), point_at_new)
            self.click(self.win._cfg.settings_btn)
            self.assertTrue(self.wait_until(lambda: not op.script), op.script)
        self.assertEqual(told, [("Settings saved", "The favorites library path changed.\n"
                                 "Restart the app to load the new library.")])
        self.assertEqual(stores.SETTINGS.read().get("library_dir"), str(new))
        self.assertEqual(len(self.win._library.lib.entries), before, "rescanned at once")

        with mock.patch.dict(self.settings, {"library_dir": str(new)}):
            self.restart()
            entries = self.win._library.lib.entries
            self.assertEqual(sorted(Path(e.path).name for e in entries),
                             ["Night (RB 25).mp3", "Senorita.mp3"])
            by_name = {Path(e.path).name: e.dance for e in entries}
            self.assertEqual(by_name["Senorita.mp3"], "SA")
            self.assertEqual(by_name["Night (RB 25).mp3"], "RB")
            status = self.win._cfg.status_lbl.text()
            self.assertIn("Library: 2 files", status)
            self.assertIn("— Indexes (analyzed / total) —", status)
            # Nothing analysed yet: 🧱 offers itself.
            self.assertTrue(self.win._cfg.build_all_btn.isVisible())

    def test_collapse_all_hides_the_titles_and_opens_them_again(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            rows = self.song_rows()
            collapse = self.button("Collapse every round")
            self.click(collapse)
            self.assertTrue(all(table.isRowHidden(r) for r in rows), "⊟ left titles open")
            self.click(collapse)
            self.assertFalse(any(table.isRowHidden(r) for r in rows), "⊞ left titles shut")

    def test_fold_decks_folds_the_deck_to_a_tab_and_back(self):
        with self.clicking():
            self.generate(rounds="1")
            deck = self.win.deck(self.win._deckset.table)
            fold = self.button("Fold every visible playlist")
            self.click(fold)
            self.assertTrue(deck.folded)
            self.click(fold)
            self.assertFalse(deck.folded)

    def test_the_deck_count_cycles_through_its_views(self):
        with self.clicking():
            win = self.win
            ring = [2, 4, 8, 0, 1] if win._max_decks() >= 8 else [2, 4, 0, 1]
            self.assertEqual(win._deckset.deck_count, 1)
            views = []
            for _ in ring:
                self.click(self.button("Cycle 1 "))
                views.append(win._deckset.deck_count)
            self.assertEqual(views, ring)
            self.assertTrue(win._deckset.table.isVisible(), "deck 1 hidden in the 1-deck view")

    def test_compact_cycles_the_headers_and_keeps_the_titles(self):
        with self.clicking():
            self.generate(rounds="2-1")
            table = self.win._deckset.table
            titles = self.titles()
            full = table.rowCount()
            states = []
            for _ in range(4):
                self.click(self.button("Cycle the playlist headers"))
                states.append(self.win._compact_state)
                self.assertEqual(sorted(self.titles()), sorted(titles))
                if self.win._compact_state in (2, 3):     # 🚫 no grouping, 🔢 numbers
                    shown = [r for r in range(table.rowCount()) if not table.isRowHidden(r)]
                    self.assertEqual(len(shown), len(titles), "header rows left")
            self.assertEqual(states, [1, 2, 3, 0])
            self.assertEqual(table.rowCount(), full)

    def test_the_wishlist_area_cycles_through_its_views(self):
        with self.clicking():
            win = self.win
            self.assertEqual((win._wish_state, win._wish_grid), (1, False))
            views = []
            for _ in range(6):
                self.click(self.button("Cycle the wishlist area"))
                views.append((win._wish_state, win._wish_grid))
            self.assertEqual(views, [(2, False), (3, False), (4, False),
                                     (4, True), (0, False), (1, False)])

    def test_a_title_parked_in_a_wishlist_goes_back_and_all_survive_a_restart(self):
        with self.clicking():
            self.generate(rounds="1")
            # One deck on screen hides the single wishlist: ⭐ shows two.
            self.click(self.button("Cycle the wishlist area"))
            deck, wish = self.win._deckset.table, self.win._deckset.wishlists[0]
            self.assertTrue(wish.isVisible())
            first, second, *_ = self.song_rows()
            parked = self.entry_at(first).title
            self.drag(deck, first, wish)
            self.assertEqual(self.titles(wish), [parked])
            self.assertNotIn(parked, self.titles(), "the deck kept the dragged title")
            self.drag(wish, 0, deck, first)
            self.assertEqual(self.entry_at(first).title, parked)
            self.assertEqual(self.titles(wish), [], "the wishlist kept the dragged title")
            kept = self.entry_at(second).title
            self.drag(deck, second, wish)
            planned = self.titles()
            self.key(Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier
                     | Qt.KeyboardModifier.ShiftModifier)
            self.restart()
            self.assertEqual(self.titles(), planned)
            self.assertEqual(self.titles(self.win._deckset.wishlists[0]), [kept])

    def test_print_writes_a_pdf_of_the_focused_deck(self):
        with self.clicking() as op:
            self.generate(rounds="1")
            op.answer(self.titled("Print / Export"), lambda dlg: self.click(dlg._ok))
            self.click(self.button("Export the focused playlist as a printable PDF"))
            pdfs = list(self.out.glob("*.pdf"))
            self.assertEqual(len(pdfs), 1, pdfs)
            self.assertTrue(pdfs[0].read_bytes().startswith(b"%PDF"))

    def test_usb_export_copies_the_titles_in_play_order(self):
        with self.clicking() as op:
            self.generate(rounds="1")
            titles = self.titles()
            usb = self.out / "usb"
            usb.mkdir()
            op.answer(self.titled("🧳"), lambda dlg: self.click(dlg._ok))
            with mock.patch.object(QFileDialog, "getExistingDirectory",
                                   lambda *_a, **_kw: str(usb)):
                self.click(self.button("Export playlists as a self-contained"))
            self.assertTrue(self.wait_until(
                lambda: len(list(usb.rglob("*.mp3"))) == len(titles)),
                f"copied {len(list(usb.rglob('*.mp3')))} of {len(titles)}")
            copies = sorted(p.name for p in usb.rglob("*.mp3"))
            for title, copy in zip(titles, copies, strict=True):
                self.assertIn(title, copy)
            self.assertEqual(len(list(usb.rglob("*.m3u*"))), 1)

    def test_save_state_writes_the_session(self):
        from gui.dialogs import AUTOSAVE
        with self.clicking():
            self.generate(rounds="1")
            AUTOSAVE.remove()
            self.click(self.button("Save the whole working session"))
            text = AUTOSAVE.path.read_text(encoding="utf-8")
            for title in self.titles():
                self.assertIn(title, text)

    def test_ctrl_shift_s_saves_the_session_too(self):
        from gui.dialogs import AUTOSAVE
        with self.clicking():
            self.generate(rounds="1")
            AUTOSAVE.remove()
            self.key(Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier
                     | Qt.KeyboardModifier.ShiftModifier)
            self.assertTrue(AUTOSAVE.path.exists())

    def test_a_cleared_desk_stays_cleared_after_a_restart(self):
        from gui.dialogs import AUTOSAVE
        AUTOSAVE.remove()
        self.restart()   # an empty desk: no wishlist or panel left from before
        yes = lambda *_a, **_kw: QMessageBox.StandardButton.Yes  # noqa: E731
        with self.clicking(), mock.patch.object(QMessageBox, "question", yes):
            self.generate(rounds="1")
            titles = self.titles()
            self.click(self.button("Empty every playlist deck"))
            self.assertEqual(self.titles(), [], "🧹 left titles")
            text = AUTOSAVE.path.read_text(encoding="utf-8")
            self.assertFalse([t for t in titles if t in text], "the autosave kept the list")
            self.restart()
            self.assertEqual(self.titles(), [], "the cleared list came back")

    def test_the_day_plan_opens_its_dialog(self):
        with self.clicking() as op:
            self.click(self.button("Plan a whole tournament day"))
            self.assertTrue(op.opened, "📅 opened nothing")


if __name__ == "__main__":
    unittest.main()
