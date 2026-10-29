#!/usr/bin/env python3
"""Click-through, chapter 11: Theme and Past Competitions.

Run:  py -m unittest tests.gui.test_click_11_theme -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/11-theme-and-past-competitions.md
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QPushButton

from shared.columns import _COL_TITLE

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, printable


class ThemeClickTest(ClickThrough):
    """11 Theme and Past Competitions."""

    def song(self, number: int) -> Path:
        """The fixture title "Song NN (…).mp3"."""
        [path] = Path(self.settings["library_dir"]).rglob(f"Song {number:02d} (*.mp3")
        return path

    def past_list(self, name: str, songs: list[Path]) -> Path:
        """A list played before, in the playlist folder."""
        path = self.out / f"{name}.m3u"
        path.write_text("\n".join(["#EXTM3U", *map(str, songs)]) + "\n",
                        encoding="utf-8")
        return path

    def own_themes(self, data: dict | None = None):
        """themes.json from a folder of this scenario's own. The app's data
        folder is the real one, and a file of the user's there adds themes."""
        import planner.store
        folder = Path(tempfile.mkdtemp(prefix="dp_click_themes_"))
        if data is not None:
            (folder / "themes.json").write_text(json.dumps(data), encoding="utf-8")
        p = mock.patch.object(planner.store.USER_THEMES, "_root", lambda: folder)
        p.start()
        self.addCleanup(p.stop)

    def mode(self, mode: str, button: str):
        cfg = self.win._cfg
        cfg.mode_combo.setCurrentIndex(cfg.mode_combo.findData(mode))
        self.assertEqual(cfg.generate_btn.text(), button)

    def theme(self, label: str) -> list:
        """Mode Theme, the theme `label`, ⚡ Generate Theme Playlist: the
        titles of the list."""
        cfg = self.win._cfg
        self.mode("Theme", "⚡  Generate Theme Playlist")
        cfg.theme_combo.setCurrentIndex(cfg.theme_combo.findText(label))
        self.assertEqual(cfg.theme_combo.currentText(), label)
        self.click(cfg.generate_btn)
        return [self.entry_at(r) for r in self.song_rows()]

    def test_a_party_theme_takes_its_dances_and_spreads_them(self):
        self.own_themes()
        cfg = self.win._cfg
        with self.clicking():
            self.assertEqual(cfg.theme_count.value(), 30)
            self.type_into(cfg.theme_count, "5")
            entries = self.theme("Party")
            self.assertEqual(len(entries), 5)
            self.type_into(cfg.theme_count, "30")
            entries = self.theme("Party")
        # Three titles of each of its five dances in the library: all fifteen.
        dances = [e.dance for e in entries]
        self.assertEqual(len({e.path for e in entries}), 15)
        self.assertEqual(set(dances), {"CC", "SA", "JI", "QS", "TG"})
        self.assertEqual([d for d, nxt in zip(dances, dances[1:], strict=False) if d == nxt], [],
                         dances)
        self.assertIn("Party: 15 tracks", printable(self.win._hints_lbl.text()))

    def test_wedding_and_gala_take_only_titles_played_before(self):
        self.own_themes()
        # LW WW QS CC RB SF JV, in a list of the playlist folder.
        played = [self.song(n) for n in (0, 2, 4, 6, 7, 13, 19)]
        self.past_list("Abschlussball 2024", played)
        self.restart()   # the library learns what was played as it loads
        with self.clicking():
            wedding = self.theme("Hochzeit (Wedding)")
            gala = self.theme("Galaball / Ballnacht")
        # Hochzeit: its dances, slow ones only — Cha-Cha is in its list but
        # is a fast dance, so the slow rule leaves it out.
        self.assertEqual(sorted(e.path.name for e in wedding),
                         sorted(self.song(n).name for n in (0, 2, 7, 13)))
        self.assertEqual(sorted(e.path.name for e in gala),
                         sorted(p.name for p in played))

    def test_a_decade_theme_reads_the_year_tag(self):
        from mutagen.id3 import ID3, TDRC
        self.own_themes()
        years = {5: "1995", 16: "1998", 21: "1987"}
        for n, year in years.items():
            path = self.song(n)
            tags = ID3()
            tags.add(TDRC(encoding=3, text=[year]))
            tags.save(path)
            # The library cache goes by whole-second mtimes.
            st = path.stat()
            os.utime(path, (st.st_atime, st.st_mtime + 2))

            def untag(path=path):
                ID3(path).delete()
                st = path.stat()
                os.utime(path, (st.st_atime, st.st_mtime + 2))
            self.addCleanup(untag)
        self.restart()
        with self.clicking():
            nineties = self.theme("90er")
            eighties = self.theme("80er")
            self.theme("2010er")
            self.assertEqual(self.win._deckset.table.rowCount(), 0)
            self.assertEqual(self.win.statusBar().currentMessage(),
                             "No tracks matched '2010er'.")
        self.assertEqual(sorted(e.path.name for e in nineties),
                         sorted(self.song(n).name for n in (5, 16)))
        self.assertEqual([e.path.name for e in eighties], [self.song(21).name])

    def test_a_theme_without_matches_leaves_nothing_to_save(self):
        self.own_themes()
        target = self.out / "empty.m3u8"
        with self.clicking():
            self.assertTrue(self.theme("Party"))
            self.theme("2010er")   # no title of the library carries a year
            self.assertEqual(self.win._deckset.table.rowCount(), 0)
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   lambda *_a, **_kw: (str(target), "")):
                self.key(Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        # The deck shows nothing, so Ctrl+S has nothing of the old list to write.
        text = target.read_text(encoding="utf-8-sig") if target.exists() else ""
        self.assertNotIn("Song ", text)

    def test_an_own_theme_from_themes_json_joins_the_theme_box(self):
        # A title must meet every rule: Rumba and Cha-Cha, but slow — so the
        # Cha-Chas drop out. Song 00 is a Slow Waltz, listed by hand.
        self.own_themes({
            "custom_themes": {"Abend": {"label": "Rumba-Abend",
                                        "dances": ["RB", "CC"], "mood": "slow"}},
            "track_themes": {self.song(0).stem: ["Abend"]},
        })
        self.restart()   # the Theme box is filled as the window opens
        with self.clicking():
            entries = self.theme("Rumba-Abend")
        self.assertEqual(sorted(e.path.name for e in entries),
                         sorted(self.song(n).name for n in (0, 7, 17, 27)))

    def schedule(self, *lines: str):
        """Mode Past Competitions, `lines` pasted, Parse schedule."""
        cfg = self.win._cfg
        self.mode("Past Competitions", "⚡  Generate from History")
        cfg.replay_text.setFocus()
        cfg.replay_text.selectAll()
        for i, line in enumerate(lines):
            if i:
                QTest.keyClick(cfg.replay_text, Qt.Key.Key_Return)
            QTest.keyClicks(cfg.replay_text, line)
        [parse] = [b for b in cfg.findChildren(QPushButton)
                   if b.text() == "Parse schedule"]
        self.click(parse)

    def sen_history(self) -> tuple[list[Path], list[Path]]:
        """Last year's SEN I LAT, 2-1: two heats of every dance, then the
        final. A list without round names is cut from the bottom up."""
        early = [self.song(n) for n in (5, 6, 7, 8, 9, 15, 16, 17, 18, 19)]
        final = [self.song(n) for n in (25, 26, 27, 28, 29)]
        self.past_list("SEN I LAT 2024", early + final)
        return early, final

    def round_titles(self) -> list[set[str]]:
        return [{e.path.name for heat in heats for e in heat if e}
                for heats in self.win._playlist.values()]

    def test_past_competitions_fill_each_round_from_the_old_list(self):
        early, final = self.sen_history()
        cfg = self.win._cfg
        with self.clicking():
            self.schedule("Fr: SEN I LAT (38) 2 - 1", "    U21 STD (50) 2 - 1")
            self.assertEqual([cfg.replay_combo.itemText(i)
                              for i in range(cfg.replay_combo.count())],
                             ["SEN I LAT  (2-1)", "U21 STD  (2-1)"])
            self.assertEqual(cfg.rounds_edit.text(), "2-1")
            self.click(cfg.generate_btn)
            self.assertEqual(self.round_titles(),
                             [{p.name for p in early}, {p.name for p in final}])
            self.assertEqual(self.win.deck(self.win._deckset.table).name, "SEN I LAT")
            hint = self.win._hints_lbl.text()
            self.assertIn("Seeded from 1 past", hint)
            self.assertIn("round pool sizes", hint)
            tip = self.win._deckset.table.item(self.song_rows()[0], _COL_TITLE).toolTip()
            self.assertIn("In these matching past lists:", tip)
            self.assertIn("SEN I LAT 2024", tip)

            # 🎯 off: the final draws from all playlists; on again: from this
            # competition's list, which holds one title per dance.
            final_round = list(self.win._playlist)[-1]
            scope = cfg._scope_checks[final_round]
            self.tick(cfg.auto_reroll_check)
            self.tick(scope)
            self.assertFalse(scope.isChecked())
            msg = self.win.statusBar().currentMessage()
            self.assertTrue(msg.startswith(f"↻ {final_round} re-rolled"), printable(msg))
            self.assertTrue(msg.endswith("all playlists"), printable(msg))
            self.tick(scope)
            self.assertTrue(self.win.statusBar().currentMessage().endswith("this comp"))
            self.assertEqual(self.round_titles()[-1], {p.name for p in final})

    def test_each_competition_keeps_its_own_work(self):
        self.sen_history()
        cfg = self.win._cfg
        with self.clicking():
            self.schedule("Fr: SEN I LAT (38) 2 - 1", "    U21 STD (50) 2 - 1")
            self.click(cfg.generate_btn)
            senior = self.titles()
            cfg.replay_combo.setCurrentIndex(1)
            self.assertEqual(self.titles(), [])
            self.assertTrue(self.win.statusBar().currentMessage().startswith(
                "🆕 This competition has no saved work yet"))
            self.click(cfg.generate_btn)
            under21 = self.titles()
            self.assertIn("No past “U21 STD” lists found", self.win._hints_lbl.text())
            self.assertEqual({m.dance for m in self.win._deckset.table._row_meta if m and m.dance},
                             {"LW", "TG", "WW", "SF", "QS"})
            cfg.replay_combo.setCurrentIndex(0)
            self.assertEqual(self.titles(), senior)
            cfg.replay_combo.setCurrentIndex(1)
            self.assertEqual(self.titles(), under21)
            # A new schedule drops what was kept.
            self.schedule("Fr: SEN I LAT (38) 2 - 1", "    U21 STD (50) 2 - 1")
            self.assertEqual(cfg.replay_combo.currentIndex(), 0)
            self.assertEqual(self.titles(), [])


if __name__ == "__main__":
    unittest.main()
