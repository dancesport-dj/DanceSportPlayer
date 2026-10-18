#!/usr/bin/env python3
"""Click-through, chapter 08 / 09: Checks and similar tracks.

Run:  py -m unittest tests.gui.test_click_08_checks -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/08-checks.md
    docs/manual-planner/09-similar-tracks.md
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, DropFrom, printable

import numpy as np
import shiboken6
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QFileDialog, QLabel, QMessageBox,
                               QTableWidget)
from planner.music.analysis import AudioFeatures
from shared.columns import _COL_TITLE


class ChecksClickTest(ClickThrough):
    """08 / 09 Checks and similar tracks."""

    def test_find_similar_lists_titles_of_the_same_dance(self):
        from gui.dialogs.similar_dialog import SimilarTracksDialog
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="1")
            row = self.song_rows()[0]
            dance = self.entry_at(row).dance
            op.pick("🔎  Find similar tracks")
            self.right_click(op, self.win._deckset.table, row)
            [dlg] = [w for w in self._roots() if isinstance(w, SimilarTracksDialog)]
            found = [e for e in dlg._row_entries if e is not None]
            self.assertTrue(found, "no similar titles listed")
            self.assertEqual({e.dance for e in found}, {dance})
            dlg.close()

    def similar_window(self, op, row: int):
        """Right-click ▸ 🔎 Find similar tracks on a deck slot: its window."""
        from gui.dialogs.similar_dialog import SimilarTracksDialog
        op.pick("🔎  Find similar tracks")
        self.right_click(op, self.win._deckset.table, row)
        [dlg] = [w for w in self._roots() if isinstance(w, SimilarTracksDialog)]
        return dlg

    def test_the_method_choice_reranks_the_matches(self):
        """Gaussian/KL and librosa each find their own sound-alike: one title
        shares the base's timbre distribution, the other its feature vector."""
        def feats(mfcc, centroid, mean):
            return AudioFeatures(bpm=120.0, mfcc=mfcc, centroid=centroid, rms=0.1,
                                 mfcc_mean=np.full(20, mean, dtype=np.float32),
                                 mfcc_cov=np.eye(20, dtype=np.float32).ravel())
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="1")
            row = self.song_rows()[0]
            source = self.entry_at(row)
            same = {e.path: e for e in self.win._library.lib.by_dance(source.dance)}
            kl_twin, vec_twin = [e for p, e in sorted(same.items()) if p != source.path]
            v = np.linspace(-3.0, 4.0, 84, dtype=np.float32)
            same[source.path].features = source.features = feats(v, 1500.0, 0.0)
            kl_twin.features = feats(-v, 3000.0, 0.0)
            vec_twin.features = feats(v, 1500.0, 5.0)
            dlg = self.similar_window(op, row)
            combo = dlg._method_combo
            self.assertEqual(combo.currentData(), "combined")

            def listed():
                return [e.path for e in dlg._row_entries if e is not None]
            combo.setCurrentIndex(combo.findData("gaussian_kl"))
            self.assertEqual(listed(), [kl_twin.path])
            combo.setCurrentIndex(combo.findData("librosa"))
            self.assertEqual(listed(), [vec_twin.path])
            dlg.close()

    def test_a_match_plays_seeks_and_opens_in_the_systems_player(self):
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="1")
            dlg = self.similar_window(op, self.song_rows()[0])
            t = dlg._table
            r = max((i for i, e in enumerate(dlg._row_entries) if e is not None),
                    key=lambda i: dlg._row_entries[i].duration)
            path = dlg._paths[r]
            self.assertGreaterEqual(dlg._row_entries[r].duration, 35)
            self.click_cell(t, r, 3)
            self.key(Qt.Key.Key_Space, widget=t)
            pb, player = self.win._playback, self.win._player
            self.assertTrue(self.wait_until(
                lambda: pb.path == Path(path) and player.duration() > 0),
                "Space did not play the match")
            self.assertEqual(dlg._cur_row, r)
            self.key(Qt.Key.Key_Right, Qt.KeyboardModifier.ControlModifier, widget=t)
            self.assertTrue(self.wait_until(lambda: player.position() > 25000),
                            f"Ctrl+→ left the player at {player.position()} ms")
            self.key(Qt.Key.Key_Space, widget=t)
            self.assertEqual(dlg._cur_row, -1)
            self.assertTrue(self.wait_until(lambda: pb.path is None),
                            "Space again did not stop it")
            opened = []
            with mock.patch("os.startfile", opened.append, create=True):
                self.click_cell(t, r, 3, double=True)
            self.assertEqual(opened, [str(path)])
            dlg.close()

    def test_a_match_dragged_onto_a_slot_replaces_its_title(self):
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="1")
            row = self.song_rows()[0]
            before = self.entry_at(row)
            dlg = self.similar_window(op, row)
            last = len(dlg._row_entries) - 1
            self.assertGreater(last, 0, "one match only: any row would pass")
            match = dlg._row_entries[last]
            self.drag(dlg._table, last, self.win._deckset.table, row)
            self.assertTrue(self.wait_until(
                lambda: self.entry_at(row).path == match.path),
                "the dropped match did not take the slot")
            self.assertNotEqual(match.path, before.path)
            dlg.close()

    def test_check_music_replaces_a_suspect_with_a_similar_title(self):
        from gui.dialogs.similar_dialog import SimilarTracksDialog
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="1")
            before = {r: self.entry_at(r) for r in self.song_rows()}
            op.pick("🎵  Check music")
            self.click(self.win._check_btn)
            report = self.win._bpm_dlg
            self.assertTrue(report.isVisible())

            def use_first(dlg):
                self.click_cell(dlg._table, 0, 0)
                self.click(dlg._pick_btn)
            op.answer(lambda w: isinstance(w, SimilarTracksDialog), use_first)
            self.click(self.button("Replace via the similar-tracks picker", report))
            changed = {r: self.entry_at(r) for r, e in before.items()
                       if self.entry_at(r) is not e}
            self.assertEqual(len(changed), 1, "one suspect, one slot replaced")
            [(row, new)] = changed.items()
            self.assertEqual(new.dance, before[row].dance)
            report.close()

    def test_enter_or_a_double_click_also_picks_the_replacement(self):
        from gui.dialogs.similar_dialog import SimilarTracksDialog
        for how in ("double-click", "enter"):
            with self.subTest(how), self.clicking() as op:
                self.analysed()
                self.generate(rounds="1")
                before = {r: self.entry_at(r) for r in self.song_rows()}
                op.pick("🎵  Check music")
                self.click(self.win._check_btn)
                report = self.win._bpm_dlg
                picked = []

                def use_last(dlg):
                    last = len(dlg._row_entries) - 1
                    picked.append(dlg._row_entries[last])
                    if how == "enter":
                        self.click_cell(dlg._table, last, 3)
                        self.key(Qt.Key.Key_Return, widget=dlg._table)
                    else:
                        self.click_cell(dlg._table, last, 3)
                        self.click_cell(dlg._table, last, 3, double=True)
                op.answer(lambda w: isinstance(w, SimilarTracksDialog), use_last)
                self.click(self.button("Replace via the similar-tracks picker", report))
                changed = [self.entry_at(r) for r, e in before.items()
                           if self.entry_at(r) is not e]
                self.assertEqual([e.path for e in changed], [picked[0].path])
                report.close()

    def check_music(self, op):
        """🎵 Check Music: the report and its table of suspects."""
        op.pick("🎵  Check music")
        self.click(self.win._check_btn)
        report = self.win._bpm_dlg
        self.assertTrue(report.isVisible())
        [suspects] = report.findChildren(QTableWidget)
        return report, suspects

    def test_check_music_plays_a_suspect_and_ctrl_arrow_seeks(self):
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="2-1")
            report, suspects = self.check_music(op)
            # The longest suspect: a 30 s seek has to stay inside it.
            secs = [sum(int(p) * f for p, f in zip(
                suspects.item(r, 5).text().split(":"), (60, 1), strict=True))
                for r in range(suspects.rowCount())]
            row = secs.index(max(secs))
            self.assertGreater(secs[row], 40)
            title = suspects.item(row, 3).text()
            play = suspects.cellWidget(row, 0)
            self.click(play)
            win = self.win
            self.assertTrue(self.wait_until(
                lambda: win._playback.path is not None
                and win._playback.path.stem.startswith(title)
                and win._player.position() > 0, 3000), "▶ did not play the title")
            self.assertEqual(play.text(), "■")
            before = win._player.position()
            QTest.keyClick(report, Qt.Key.Key_Right, Qt.KeyboardModifier.ControlModifier)
            self.assertTrue(self.wait_until(
                lambda: win._player.position() >= before + 25000, 2000),
                f"Ctrl+→ did not seek 30 s: {before} → {win._player.position()}")
            QTest.keyClick(report, Qt.Key.Key_Left, Qt.KeyboardModifier.ControlModifier)
            self.assertTrue(self.wait_until(
                lambda: win._player.position() < before + 25000, 2000), "Ctrl+← did not seek back")
            self.click(play)
            self.assertEqual(play.text(), "▶")
            self.assertTrue(self.wait_until(lambda: win._playback.path is None),
                            "a second ▶ did not stop it")
            report.close()

    def test_a_check_slow_enough_for_its_progress_window_still_reports(self):
        """On a loaded machine the scan outlasts the 250 ms before its progress
        window shows. The operator waits it out; pressing Cancel (its reject)
        aborted the check and no report opened."""
        from gui.common import BusyDialog
        show_after = BusyDialog.show_after
        with mock.patch.object(BusyDialog, "show_after",
                               lambda dlg, _ms=500: show_after(dlg, 0)), \
                self.clicking() as op:
            self.analysed()
            self.generate(rounds="2-1")
            report, _suspects = self.check_music(op)
            report.close()

    def test_check_music_remove_empties_the_slots_and_ctrl_z_undoes(self):
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="2-1")
            table = self.win._deckset.table
            rows = len(table._row_meta)
            report, suspects = self.check_music(op)
            title = suspects.item(0, 3).text()
            held = [r for r in self.song_rows() if self.entry_at(r).title == title]
            self.assertTrue(held)
            self.click(self.button("Remove from the playlist(s)", report))
            self.assertNotIn(title, self.titles())
            self.assertEqual(len(table._row_meta), rows, "the slot did not stay")
            self.assertTrue(suspects.item(0, 3).font().strikeOut())
            self.assertFalse(suspects.cellWidget(0, 7).isEnabled())
            report.close()
            # Ctrl+Z is the window's shortcut: back in the deck first.
            self.win.activateWindow()
            self.wait_until(self.win.isActiveWindow, 1000)
            self.key(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual([r for r in self.song_rows()
                              if self.entry_at(r).title == title], held)

    def test_check_music_double_click_and_structure_links_jump_to_the_deck(self):
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="2-1")
            table = self.win._deckset.table
            # Not the heat's first dance: the jump has to find the dance too.
            gone = next(r for r in self.song_rows()
                        if table._row_meta[r].h_idx == 1 and table._row_meta[r].d_idx == 2)
            slot = (table._row_meta[gone].round_name, table._row_meta[gone].h_idx,
                    table._row_meta[gone].d_idx)
            table.selectRow(gone)
            self.key(Qt.Key.Key_Delete)
            self.assertIsNone(table._row_meta[gone].entry)
            report, suspects = self.check_music(op)

            row = suspects.rowCount() - 1
            title = suspects.item(row, 3).text()
            table.setCurrentCell(0, _COL_TITLE)
            # A real double-click: the view takes it only after a press there.
            self.click_cell(suspects, row, 3)
            self.click_cell(suspects, row, 3, double=True)
            self.assertEqual(self.entry_at(table.currentRow()).title, title)

            [box] = [lbl for lbl in report.findChildren(QLabel)
                     if "Round structure" in lbl.text()]
            self.assertIn("missing in heat", box.text())
            table.setCurrentCell(0, _COL_TITLE)
            self.click_link(box, "0")
            m = table._row_meta[table.currentRow()]
            self.assertEqual((m.round_name, m.h_idx, m.d_idx), slot)
            self.assertIsNone(m.entry)
            report.close()

    def click_link(self, label: QLabel, href: str):
        """Click the link `href` of a rich-text label: the mouse is moved over
        it until the label reports hovering that link, then pressed there."""
        label.window().activateWindow()
        self.wait_until(label.window().isActiveWindow, 1000)
        hovered = []
        label.linkHovered.connect(hovered.append)
        try:
            for y in range(3, label.height(), 4):
                for x in range(3, label.width(), 3):
                    QTest.mouseMove(label, QPoint(x, y))
                    if hovered and hovered[-1] == href:
                        QTest.mouseClick(label, Qt.MouseButton.LeftButton,
                                         Qt.KeyboardModifier.NoModifier, QPoint(x, y))
                        QTest.qWait(5)
                        return
        finally:
            label.linkHovered.disconnect(hovered.append)
        self.fail(f"no link '{href}' found under the mouse")

    def test_check_duplicates_opens_its_report(self):
        from gui.dialogs.duplicate_dialog import DuplicateResolveDialog
        with self.clicking() as op:
            self.generate()              # 6-3-2-1 on three titles a dance repeats
            # On its decks tab the report is application-modal: the operator
            # gets it, so the look at it is scripted, not raced against him.
            seen = []

            def look(dlg):
                seen.append(dlg is self.win._dup_dlg and dlg.isVisible())
                dlg.reject()
            op.answer(lambda w: isinstance(w, DuplicateResolveDialog), look)
            op.pick("🔁  Check duplicates")
            self.click(self.win._check_btn)
            self.assertTrue(self.wait_until(lambda: seen), "the report never opened")
            self.assertEqual(seen, [True])
            self.assertTrue(self.wait_until(lambda: self.win._dup_dlg is None))

    def _open_duplicates(self, op, act):
        """🔁 Check duplicates, its window handed to `act`; returns the window."""
        from gui.dialogs.duplicate_dialog import DuplicateResolveDialog
        seen = []

        def take(dlg):
            seen.append(dlg)
            act(dlg)
        op.answer(lambda w: isinstance(w, DuplicateResolveDialog), take)
        op.pick("🔁  Check duplicates")
        self.click(self.win._check_btn)
        self.assertTrue(self.wait_until(lambda: seen), "the report never opened")
        return seen[0]

    def _m3u(self, name: str, *tracks: Path) -> Path:
        path = self.out / name
        path.write_text("\n".join(["#EXTM3U", *map(str, tracks)]) + "\n", encoding="utf-8")
        return path

    def _drop(self, zone, *files: Path):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(f)) for f in files])
        zone.dropEvent(DropFrom(QPointF(20, 20), mime, None))
        QTest.qWait(5)

    def test_check_duplicates_removes_the_copy_set_to_remove(self):
        removed = []

        def remove_one(dlg):
            st = next(s for s in dlg._occ_state if s["kind"] == "single")
            removed.append(st["occ"]["entry"].title)
            st["combo"].setCurrentIndex(2)            # 🗑 Remove
            st["combo"].activated.emit(2)
            self.click(dlg._action_btn)               # ✅ Apply
        with self.clicking() as op:
            self.generate()              # 6-3-2-1 on three titles a dance repeats
            before = self.titles()
            self._open_duplicates(op, remove_one)
            self.assertTrue(self.wait_until(lambda: self.win._dup_dlg is None))
        [title] = removed
        # A deck empties the heat slot: one copy fewer, the others stay.
        self.assertEqual(len(self.titles()), len(before) - 1)
        self.assertEqual(self.titles().count(title), before.count(title) - 1)

    def test_dragged_in_playlists_report_the_titles_they_share(self):
        latin = sorted(Path(self.settings["library_dir"], "LateinCD").glob("*.mp3"))
        shared, only_a, only_b = latin[:3]
        lists = (self._m3u("Turnier A.m3u", shared, only_a),
                 self._m3u("Turnier B.m3u", only_b, shared))
        with self.clicking() as op:
            dlg = self._open_duplicates(
                op, lambda d: d._tabs.setCurrentWidget(d._drop_tab_w))
            # This tab leaves the decks usable beside the window.
            self.assertEqual(dlg.windowModality(), Qt.WindowModality.NonModal)
            self._drop(dlg._drop_zone, *lists)
            text = " | ".join(lbl.text() for lbl in
                              dlg._drop_results.widget().findChildren(QLabel))
            self.assertIn("Shared between playlists", text, printable(text))
            self.assertIn(shared.name, text)
            self.assertNotIn(only_a.name, text)
            self.assertNotIn(only_b.name, text)
            self.click(dlg._action_btn)               # OK
            self.assertTrue(self.wait_until(lambda: self.win._dup_dlg is None))

    def test_reference_base_exports_what_the_tournament_did_not_use(self):
        latin = sorted(Path(self.settings["library_dir"], "LateinCD").glob("*.mp3"))
        used, unused = [f for f in latin if "(PD " not in f.name][:2]
        paso = next(f for f in latin if "(PD " in f.name)
        reference = self._m3u("Referenz.m3u", used, unused, paso)
        tournament = self._m3u("Turnier.m3u", used, paso)
        out = self.out / "Referenz_cleaned.m3u"
        with self.clicking() as op:
            dlg = self._open_duplicates(
                op, lambda d: d._tabs.setCurrentWidget(d._ref_tab_w))
            self._drop(dlg._ref_zone, reference)
            self._drop(dlg._ref_tour_zone, tournament)
            self.assertTrue(dlg._ref_compare_btn.isEnabled())
            self.click(dlg._ref_compare_btn)
            self.assertTrue(self.wait_until(lambda: dlg._ref_result is not None, 10000),
                            "the comparison never finished")
            self.assertEqual(dlg._action_btn.text(), "🧹  Export unused")
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   lambda *_a, **_kw: (str(out), "")):
                self.click(dlg._action_btn)
            dlg.close()
        written = out.read_text(encoding="utf-8")
        self.assertNotIn(used.name, written)
        self.assertIn(unused.name, written)
        # Left out of the comparison: kept though the tournament played it.
        self.assertIn(paso.name, written)

    def test_remove_duplicate_titles_asks_and_keeps_the_last_copy(self):
        latin = sorted(Path(self.settings["library_dir"], "LateinCD").glob("*.mp3"))
        cc = next(f for f in latin if "(CC " in f.name)
        rb = next(f for f in latin if "(RB " in f.name)
        sb = QMessageBox.StandardButton
        replies = [sb.No, sb.Yes]
        asked = []

        def question(_parent, title, text, *_a, **_kw):
            asked.append(title)
            return replies[len(asked) - 1]

        def copies():
            return [r for r in self.song_rows() if Path(self.entry_at(r).path) == cc]
        with self.clicking() as op, mock.patch.object(QMessageBox, "question", question):
            self.import_list(self._m3u("Doppelt.m3u", cc, rb, cc))
            # A list that arrives is checked at once: No keeps both, for now.
            self.assertEqual(asked, ["Duplicate titles"])
            rows = copies()
            self.assertEqual(len(rows), 2)
            op.pick("♊  Remove duplicate titles in this list")
            self.right_click(op, self.win._deckset.table, rows[0])
        # Only identical copies: it asks, and the last copy stays.
        self.assertEqual(asked, ["Duplicate titles"] * 2)
        self.assertEqual(copies(), rows[-1:])

    def test_wishlist_cleanup_drops_what_a_deck_already_plans(self):
        with self.clicking() as op:
            self.generate()
            self.click(self.button("Cycle the wishlist area"))
            deck, wish = self.win._deckset.table, self.win._deckset.wishlists[0]
            self.assertTrue(wish.isVisible())
            # A Paso Doble may come round again: the cleanup leaves it alone.
            x, y = [r for r in self.song_rows() if self.entry_at(r).dance != "PD"][:2]
            tx, ty = self.entry_at(x).title, self.entry_at(y).title
            self.drag(deck, x, wish, mods=Qt.KeyboardModifier.ControlModifier)
            self.drag(deck, y, wish)         # a move: the deck lets it go
            self.assertEqual(self.titles(wish), [tx, ty])
            self.assertNotIn(ty, self.titles())
            op.pick("🧹  Remove tracks already in a playlist")
            self.right_click(op, wish, 0)
        self.assertEqual(self.titles(wish), [ty])
        self.assertIn(tx, self.titles(), "the deck lost its copy too")

    def test_check_music_speed_compares_the_name_with_the_measurement(self):
        texts = []

        def read(dlg):
            texts.append(" | ".join(lbl.text() for lbl in dlg.findChildren(QLabel)))
            dlg.reject()
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="1")
            row = next(r for r in self.song_rows() if self.entry_at(r).dance == "CC")
            entry = self.entry_at(row)
            # Measured 120 beats/min: T30 in the name, four beats a bar.
            for bpm in (120.0, 100.0):
                entry.features = AudioFeatures(
                    bpm=bpm, mfcc=np.zeros(84, dtype=np.float32),
                    centroid=1500.0, rms=0.1)
                op.pick("🎵  Check music speed")
                op.answer(self.titled("🎵 Music speed"), read)
                self.right_click(op, self.win._deckset.table, row)
                self.assertTrue(self.wait_until(lambda: not op.script), op.script)
        agree, differ = texts
        self.assertIn("T30 = 30 bars/min", agree)
        self.assertIn("~120 beats/min", agree)
        self.assertIn("✅", agree, printable(agree))
        self.assertIn("⚠️", differ, printable(differ))
        self.assertIn("off 17%", differ)

    def test_find_planned_before_lists_what_a_past_final_played(self):
        import planner.config
        history = Path(tempfile.mkdtemp(prefix="dp_click_history_"))
        p = mock.patch.object(planner.config, "PLAYLIST_DIR", history)
        p.start()
        self.addCleanup(p.stop)
        latin = sorted(Path(self.settings["library_dir"], "LateinCD").glob("*.mp3"))
        past_cc = next(f for f in latin if "(CC " in f.name)
        with self.clicking() as op:
            self.generate(rounds="1")
            table = self.win._deckset.table
            cls = table._dance_class
            # A final of the same class, from another year: its last five
            # titles are the final, one per dance.
            final = [next(f for f in latin if f"({d} " in f.name and f != past_cc)
                     if d != "CC" else past_cc for d in ("SB", "CC", "RB", "PD", "JV")]
            past = history / f"Hgr {cls} Latein 2024.m3u"
            past.write_text("\n".join(["#EXTM3U", *map(str, final)]) + "\n",
                            encoding="utf-8")
            row = next(r for r in self.song_rows() if self.entry_at(r).dance == "CC")
            op.pick("📜  Find planned before")
            self.right_click(op, table, row)
            self.assertTrue(self.wait_until(lambda: not op.script), op.script)
            dlg = next((w for w in QApplication.topLevelWidgets()
                        if w.isVisible() and w.windowTitle().startswith("📜  Planned before")),
                       None)
            self.assertIsNotNone(dlg, "no 📜 Planned before window")
            self.addCleanup(lambda: shiboken6.isValid(dlg) and dlg.close())
            self.assertIn("Cha", dlg.windowTitle())
            self.assertEqual([Path(x).name for x in dlg._paths], [past_cc.name])
            self.assertEqual(dlg._table.horizontalHeaderItem(1).text(), "Class")
            self.assertEqual(dlg._table.item(0, 1).text(), cls)


if __name__ == "__main__":
    unittest.main()
