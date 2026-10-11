#!/usr/bin/env python3
"""Click-through, chapter 10: Eintanzen and party lists.

Run:  py -m unittest tests.gui.test_click_10_eintanzen -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/10-eintanzen-party.md
"""

import unittest
from pathlib import Path

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, DropFrom, printable

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QLabel, QPushButton, QSpinBox, QRadioButton, QStackedWidget)


class EintanzenClickTest(ClickThrough):
    """10 Eintanzen and party lists."""

    def build_practice(self, op, party: bool, max_tracks: int | None = None):
        """🤸 Practice / Party: pick the kind, cap the list, Generate. Returns
        the dance-order line the class page showed."""
        shown = []

        def fill(dlg):
            def find(kind, start):
                return next(w for w in dlg.findChildren(kind)
                            if w.text().startswith(start))
            shown.append(find(QLabel, "Dances (").text())
            if party:
                self.click(find(QRadioButton, "🎉"))
            if max_tracks is not None:
                page = dlg.findChild(QStackedWidget).currentWidget()
                page.findChildren(QSpinBox)[0].setValue(max_tracks)
            self.click(find(QPushButton, "Generate"))
        op.answer(self.titled("🤸  Practice / party playlist"), fill)
        self.click(self.win._warmup_gen_btn)
        self.assertTrue(self.wait_until(
            lambda: self.song_rows(self.win._deckset.warmup_table), 10000),
            "🤸 built no list")
        return shown[0]

    def dances(self, table) -> list[str]:
        from planner.warmup import warmup_code
        return [warmup_code(m.entry) for m in table._row_meta if m and m.entry]

    def test_eintanzen_for_a_class_runs_its_dances_round_robin(self):
        win = self.win
        panel = win._deckset.warmup_table
        with self.clicking() as op:
            order = self.build_practice(op, party=False, max_tracks=8)
            self.assertIn("SA → CC → RB → PD → JI", order)
            dances = self.dances(panel)
            self.assertLessEqual(len(dances), 8, "Max tracks was not the limit")
            self.assertTrue(set(dances) <= {"SA", "CC", "RB", "PD", "JI"},
                            f"not Latin S: {dances}")
            cycle = [d for d in ("SA", "CC", "RB", "PD", "JI") if d in dances]
            self.assertEqual(dances, (cycle * 8)[:len(dances)],
                             "the class's dances do not take turns")
            self.assertFalse(win._grid.warmup_box.isHidden(), "the panel stayed shut")
            self.assertIn("Latin S", panel._warmup_label)
            self.assertTrue(win._warmup_toggle_btn.isChecked())
            # 🔀 and 🩺 belong to a party list only.
            self.assertTrue(win._warmup_shuffle_btn.isHidden())
            self.assertTrue(win._warmup_check_btn.isHidden())
            self.assertEqual(self.dances(win._deckset.table), [], "a deck was overwritten")

    def test_a_party_list_shuffles_and_the_party_check_reads_it(self):
        win = self.win
        panel = win._deckset.warmup_table
        with self.clicking() as op:
            self.build_practice(op, party=True)
            dances = self.dances(panel)
            self.assertTrue({"LW", "TG", "QS"} & set(dances), f"no Standard: {dances}")
            self.assertTrue({"CC", "RB", "JI"} & set(dances), f"no Latin: {dances}")
            self.assertNotIn("WW", dances[:12], "a Viennese Waltz came early")
            # Late Paso Doble: none in the first 40 titles. This library has
            # only 30, so the Pasos are what is left when every other Latin
            # title has played: the floor never goes silent. A last Samba may
            # still follow, held back a round by its own spacing.
            latin = [i for i, d in enumerate(dances) if d in ("CC", "RB", "JI")]
            self.assertTrue(all(i > latin[-1] for i, d in enumerate(dances) if d == "PD"),
                            f"a Paso Doble came early: {dances}")
            self.assertIn("Party", panel._warmup_label)
            self.assertFalse(win._warmup_shuffle_btn.isHidden(), "no 🔀")
            self.assertFalse(win._warmup_check_btn.isHidden(), "no 🩺")

            # 🔀 the same titles in a fresh order.
            before = sorted(self.titles(panel))
            self.click(win._warmup_shuffle_btn)
            self.assertEqual(sorted(self.titles(panel)), before)

            # 🩺 changes nothing and reports the list as it stands.
            listed = self.titles(panel)
            self.click(win._warmup_check_btn)
            report = win._party_dlg
            self.assertTrue(report.isVisible(), "no 🎉 Party check window")
            self.assertTrue(report.windowTitle().startswith("🎉  Party check"))
            head = report.findChildren(QLabel)[0].text()
            self.assertIn(f"{len(listed)} titles", head)
            self.assertEqual(self.titles(panel), listed, "🩺 changed the list")
            again = next(b for b in report.findChildren(QPushButton)
                         if b.text().startswith("↻"))
            self.click(again)
            self.assertTrue(self.wait_until(lambda: win._party_dlg is not report
                                            and win._party_dlg.isVisible()),
                            "↻ Check again opened no fresh report")
            win._party_dlg.close()

    def test_an_m3u_dropped_on_the_practice_panel_loads_as_a_flat_list(self):
        from PySide6.QtCore import QMimeData, QUrl
        win = self.win
        panel = win._deckset.warmup_table
        music = sorted(Path(self.settings["library_dir"], "LateinCD").glob("*.mp3"))[:4]
        m3u = self.out / "Freitag Training.m3u"
        m3u.write_text("\n".join(["#EXTM3U", *map(str, music)]) + "\n",
                       encoding="utf-8")
        with self.clicking():
            # 🤸 ▾ opens an empty panel ready for the drop.
            self.click(win._warmup_toggle_btn)
            self.assertFalse(win._grid.warmup_box.isHidden(), "🤸 ▾ showed no panel")
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(m3u))])
            panel.dropEvent(DropFrom(QPointF(20, 20), mime, None))
            self.assertTrue(self.wait_until(lambda: len(self.titles(panel)) == 4),
                            f"loaded {printable(self.titles(panel))}")
            self.assertEqual([Path(m.entry.path).name
                              for m in panel._row_meta if m and m.entry],
                             [p.name for p in music], "the file's order was lost")
            self.assertIn("Freitag Training", panel._warmup_label,
                          "the panel is not named after the file")
            self.assertEqual(self.dances(win._deckset.table), [], "a deck was overwritten")


if __name__ == "__main__":
    unittest.main()
