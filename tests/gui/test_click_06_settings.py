#!/usr/bin/env python3
"""Click-through, chapter 06: Settings.

Run:  py -m unittest tests.gui.test_click_06_settings -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/06-settings.md
"""

import os
import unittest
from pathlib import Path
from unittest import mock

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, printable

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QAbstractButton, QDialogButtonBox, QGroupBox, QMessageBox, QTableWidget)


class SettingsClickTest(ClickThrough):
    """06 Settings."""

    def settings_dialog(self, op, gear, mode: str, language: str | None = None,
                        party_secs: int | None = None):
        """⚙ on `gear`, a new app mode (and language, 🎉 play length), OK."""
        def act(dlg):
            for combo, value in ((dlg._app_mode_combo, mode),
                                 (dlg._language_combo, language),
                                 (dlg._set_widgets["party"]["length"], party_secs)):
                if value is not None:
                    combo.setCurrentIndex(combo.findData(value))
            self.click(dlg.findChild(QDialogButtonBox).button(
                QDialogButtonBox.StandardButton.Ok))
        op.answer(self.titled("⚙  Settings"), act)
        self.click(gear)
        self.assertTrue(self.wait_until(lambda: not op.script), op.script)

    def check_music(self, op):
        """🎵 Check Music: (length in s, issues) per suspect, and the report."""
        op.pick("🎵  Check music")
        self.click(self.win._check_btn)
        report = self.win._bpm_dlg
        self.assertTrue(report.isVisible())
        [suspects] = report.findChildren(QTableWidget)
        rows = []
        for r in range(suspects.rowCount()):
            m, s = suspects.item(r, 5).text().split(":")
            rows.append((int(m) * 60 + int(s), suspects.item(r, 6).text()))
        return rows, report

    def test_the_checks_thresholds_change_what_check_music_flags(self):
        from shared.stores import SETTINGS
        with self.clicking() as op:
            self.analysed()
            self.generate(rounds="2-1")
            rows, report = self.check_music(op)
            # Every fixture title is under 1:45; the measured 120 is off the
            # label by more than 10 % for some.
            self.assertTrue(all("⏱" in issues for _, issues in rows), rows)
            self.assertTrue(any(secs > 35 for secs, _ in rows), rows)
            self.assertTrue(any("⚡" in issues for _, issues in rows), rows)
            report.close()

            def loosen(dlg):
                dlg._min_time.setTime(QTime(0, 0, 35))
                dlg._dev_spin.setValue(25)
            self.edit_settings(op, loosen)
            saved = SETTINGS.read() or {}
            self.assertEqual((saved.get("check_min_play_secs"),
                              saved.get("check_tempo_dev_pct")), (35, 25))
            rows, report = self.check_music(op)
            self.assertTrue(rows, "nothing at or below 0:35 left to flag")
            for secs, issues in rows:
                self.assertNotIn("⚡", issues)
                self.assertLessEqual(secs, 35, issues)
                self.assertIn("⏱", issues)
            self.assertIn("off > 25%", report._info.text())
            report.close()

    def test_library_gaps_double_click_opens_the_library_on_that_row(self):
        from shared.stores import SETTINGS
        win = self.win
        picked = []

        def gaps(dlg):
            table = dlg.findChild(QTableWidget)
            row = next(r for r in range(table.rowCount())
                       if table.item(r, 2).text().endswith("(SF)"))
            picked.append(("SF", table.item(row, 1).text()))
            self.click_cell(table, row, 3)
            self.click_cell(table, row, 3, double=True)
        with self.clicking() as op:
            if win._lib_btn.isChecked():
                self.click(win._lib_btn)
            self.assertFalse(win._lib_btn.isChecked())
            op.answer(self.titled("📊 Library gaps"), gaps)
            def edit_then_gaps(dlg):
                dlg._dev_spin.setValue(20)
                self.click(dlg._gaps_btn)
            self.edit_settings(op, edit_then_gaps, ok=False)
            # The double-click closed both dialogs, kept what was edited…
            self.assertIsNone(win._settings_dlg)
            self.assertEqual((SETTINGS.read() or {}).get("check_tempo_dev_pct"), 20)
            # …and opened 📚 on that row.
            self.assertTrue(self.wait_until(win._lib_btn.isChecked))
            browser = win._lib_browser
            [(dance, cls)] = picked
            self.assertEqual((browser._dance_combo.currentData(),
                              browser._class_combo.classes(),
                              browser._plays_combo.currentData()),
                             (dance, [cls], "never"))
            self.assertIs(win._lib_tabs.currentWidget(), browser)

    def test_the_play_sets_are_what_the_two_buttons_apply(self):
        from shared.stores import SETTINGS
        win, panel = self.win, self.win._play_panel

        def sets(dlg):
            t = dlg._set_widgets["tournament"]
            t["length"].setCurrentIndex(t["length"].findData(135))
            t["fade"].setValue(3.5)
            t["boxes"]["announce"].setChecked(True)
            dlg._set_widgets["party"]["fade"].setValue(1.0)
        with self.clicking() as op:
            self.edit_settings(op, sets)
            saved = (SETTINGS.read() or {}).get("tournament_set") or {}
            self.assertEqual((saved.get("secs"), saved.get("fade"), saved.get("announce")),
                             (135, 3.5, True))
            self.click(win._mode_play_btn)
            panel.pd_check.setChecked(True)
            self.click(panel.tournament_btn)
            self.assertEqual((panel.play_secs(), panel.fade_spin.value(),
                              panel.announce_check.isChecked()), (135, 3.5, True))
            self.assertTrue(panel.tournament_btn.isChecked())
            self.assertFalse(panel.pd_check.isChecked(), "🏆 left the 🐂 stop on")
            # 🎉 leaves the 🐂 stop wherever it stands.
            panel.pd_check.setChecked(True)
            self.click(panel.party_btn)
            self.assertEqual((panel.play_secs(), panel.fade_spin.value()), (0, 1.0))
            self.assertTrue(panel.pd_check.isChecked(), "🎉 switched the 🐂 stop")

    def test_the_tso_pitch_target_puts_a_dance_on_its_upper_takt(self):
        win = self.win

        def upper(dlg):
            combo = dlg._band_combos["CC"]
            combo.setCurrentIndex(combo.findData("upper"))
        with self.clicking() as op:
            self.edit_settings(op, upper)
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            row = next(r for r in self.song_rows() if self.entry_at(r).dance == "CC")
            self.assertEqual(self.entry_at(row).bpm, 30)
            self.play_row(row)
            card = win._big_player
            if not card._tso_btn.isChecked():
                self.click(card._tso_btn)
            # T30 → T32, the top of the 30–32 band: +6.7 %, 67 fader steps.
            # The round's own takt (Middle of the round) would leave it at 0.
            self.assertTrue(self.wait_until(lambda: card._tempo.value() == 67),
                            card._tempo.value())
            table = win._deckset.table
            win._on_stop_btn()
            self.assertTrue(self.wait_until(lambda: table._current_play_row < 0),
                            "■ did not stop the pitched title")

    def test_clean_up_refuses_when_the_music_drive_looks_unmounted(self):
        from planner.music.db import _db
        conn = _db()
        # The guard wants most of the library gone, and earlier tests in the
        # same process leave their own (present) files registered.
        known = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        gone = [(f"Z:/unmounted/Song {i:05d}.mp3",)
                for i in range(max(150, known + 1))]
        conn.executemany("INSERT OR IGNORE INTO files (path) VALUES (?)", gone)
        conn.commit()

        def forget():
            conn.executemany("DELETE FROM files WHERE path = ?", gone)
            conn.commit()
        self.addCleanup(forget)
        warned = []

        def warning(_parent, title, text, *_a, **_kw):
            warned.append((title, text))
            return QMessageBox.StandardButton.Ok
        with self.clicking() as op, mock.patch.object(QMessageBox, "warning", warning):
            self.edit_settings(op, lambda dlg: self.click(dlg._maint_btn), ok=False)
            self.assertTrue(self.wait_until(lambda: warned, 10000), "no answer")
            [(title, text)] = warned
            self.assertEqual(title, "Clean up database")
            self.assertIn("is the music drive mounted?", text)
            # …and the cached rows are all still there.
            left = conn.execute("SELECT COUNT(*) FROM files WHERE path LIKE "
                                "'Z:/unmounted/%'").fetchone()[0]
            self.assertEqual(left, len(gone))

    def test_heavy_shows_only_with_the_ai_models(self):
        """In a built .exe: no 🐘 box without the models, one with them."""
        import planner.config
        import planner.music.embeddings
        import planner.music.vocals
        seen = []

        def heavy_boxes(dlg):
            seen.append(sum(b.title().startswith("🐘")
                            for b in dlg.findChildren(QGroupBox)))
        with self.clicking() as op:
            for models in (False, True):
                with mock.patch.object(planner.config, "build_flavor", lambda: "full"), \
                        mock.patch.object(planner.music.embeddings, "mert_available",
                                          lambda m=models: m), \
                        mock.patch.object(planner.music.vocals, "demucs_available",
                                          lambda m=models: m):
                    self.edit_settings(op, heavy_boxes)
        self.assertEqual(seen, [0, 1])

    def test_a_venue_pack_takes_the_deck_and_its_music_to_another_pc(self):
        """📦 Export with the music, 📥 import it unpacked into a folder of
        its own, restart: the deck is back and plays from that folder."""
        from PySide6.QtMultimedia import QMediaPlayer
        from PySide6.QtWidgets import QFileDialog
        from planner.event import venue_pack
        from planner.store import state_dir
        pack = self.out / f"venue{venue_pack.SUFFIX}"
        music = self.out / "venue-music"
        asked = []

        def answer(_parent, title, text, *_a, **_kw):
            asked.append(title)
            # The music goes along and is unpacked; the test restarts itself.
            if "Restart now?" in text:
                return QMessageBox.StandardButton.No
            return QMessageBox.StandardButton.Yes
        with self.clicking() as op, mock.patch.object(QMessageBox, "question", answer):
            self.generate()
            planned = self.titles()
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   lambda *_a, **_kw: (str(pack), "")):
                self.edit_settings(op, lambda dlg: self.click(dlg._venue_export_btn), ok=False)
            self.assertTrue(self.wait_until(pack.is_file), "no venue pack written")
            with mock.patch.object(QFileDialog, "getOpenFileName",
                                   lambda *_a, **_kw: (str(pack), "")), \
                    mock.patch.object(QFileDialog, "getExistingDirectory",
                                      lambda *_a, **_kw: str(music)):
                self.edit_settings(op, lambda dlg: self.click(dlg._venue_import_btn), ok=False)
            self.assertTrue(self.wait_until(
                lambda: venue_pack.has_pending(state_dir()) and "Import venue pack" in asked[-1:]),
                f"nothing staged, asked {printable(asked)}")
            self.restart(at_start=lambda: venue_pack.apply_pending(state_dir()))
            self.assertEqual(self.titles(), planned)
            paths = [self.entry_at(r).path for r in self.song_rows()]
            self.assertTrue(paths and all(Path(p).is_relative_to(music) and Path(p).is_file()
                                          for p in paths),
                            f"not played from the unpacked music: {printable(paths[:3])}")
            self.play_row(self.song_rows()[0])
            self.assertTrue(self.wait_until(
                lambda: self.win._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState), "the first title did not play")
            self.win._on_stop_btn()

    def test_settings_switch_the_mode_at_once_and_the_language_after_a_restart(self):
        from planner import i18n
        from shared.stores import SETTINGS
        win, play = self.win, self.win._play_panel
        asked = []

        def later(_parent, title, *_a, **_kw):
            asked.append(title)
            return QMessageBox.StandardButton.No
        with self.clicking() as op, mock.patch.object(QMessageBox, "question", later):
            self.settings_dialog(op, win._cfg.settings_btn, "player",
                                 language="de", party_secs=120)
            self.assertTrue(SETTINGS.path.is_relative_to(
                os.environ["DANCEPLAYLIST_STATE_DIR"]), "the real settings file")
            saved = SETTINGS.read() or {}
            self.assertEqual((saved.get("app_mode"), saved.get("language"),
                              (saved.get("party_set") or {}).get("secs")),
                             ("player", "de", 120))
            # The language waits for a restart, and says so.
            self.assertEqual([printable(t) for t in asked], [printable("🎨 Look")])
            self.assertEqual(i18n.active_language(), "en")
            self.assertTrue(win.statusBar().currentMessage().startswith(
                "Saved — it takes effect"), printable(win.statusBar().currentMessage()))
            # The mode does not: player only, now.
            self.assertTrue(win.windowTitle().startswith("DanceSport Player"))
            self.assertTrue(win._mode_play_btn.isChecked())
            self.assertTrue(win._mode_row_w.isHidden(), "the 📝 / ▶ switch shows")
            for b in win._planner_btns:
                self.assertTrue(b.isHidden(), f"{printable(b.text())} shows")
            self.assertFalse(play._gear_box.isHidden(), "no ⚙ on the Playing panel")
            # 🎉 plays the party set at its new length.
            self.assertFalse(play.party_btn.isChecked())
            self.click(play.party_btn)
            self.assertEqual(play._secs, 120)
            # …and from the Playing panel's ⚙ back to both sides, no restart.
            self.settings_dialog(op, play._gear_box.findChild(QAbstractButton), "both")
            self.assertEqual(len(asked), 1, "a mode change asked for a restart")
            self.assertTrue(win.windowTitle().startswith("DanceSport Planner & Player"))
            self.assertFalse(win._mode_row_w.isHidden(), "no 📝 / ▶ switch")
            for b in win._planner_btns:
                self.assertFalse(b.isHidden(), f"{printable(b.text())} stays hidden")
            self.click(win._mode_plan_btn)
            self.generate(rounds="1")

    def test_a_german_start_plans_plays_and_saves(self):
        """The language is read at start: a window built in German, worked
        through plan, play, stop and save without a translation tripping."""
        from planner import i18n
        p = mock.patch.dict(self.settings, {"language": "de"})
        p.start()
        self.addCleanup(p.stop)
        i18n.apply_settings(self.settings)
        i18n.install_text_hook()
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.addCleanup(i18n._restore_text_hook)
        self.restart()
        win = self.win
        with self.clicking():
            for btn, text in ((win._cfg.generate_btn, "⚡  Playlist erzeugen"),
                              (win._cfg.save_btn, "💾  M3U speichern"),
                              (win._mode_plan_btn, "📝  Planung"),
                              (win._mode_play_btn, "▶  Wiedergabe")):
                self.assertEqual(btn.text(), text)
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            row = self.song_rows()[0]
            self.play_row(row)
            win._on_stop_btn()
            self.assertTrue(self.wait_until(lambda: win._deckset.table._current_play_row < 0),
                            "the title kept playing")
            self.click(win._mode_plan_btn)
            known = set(self.saved_files())
            self.click(win._cfg.save_btn)
            self.assertEqual(len(set(self.saved_files()) - known), 1, "nothing saved")
            self.assertTrue(win.statusBar().currentMessage().startswith("Gespeichert → "),
                            printable(win.statusBar().currentMessage()))


if __name__ == "__main__":
    unittest.main()
