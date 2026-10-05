#!/usr/bin/env python3
"""Tests for an .m3u dropped onto the 🤸 Eintanzen panel.

Run:  py -m unittest tests.gui.test_warmup_import -v

The panel is not choosy about what lands on it. An Eintanzen list is cut the
warm-up way — a fresh round wherever a dance comes round again — but a
competition running order dropped there is the evening's rounds, and it has to
read as Vorrunde / Zwischenrunde / Finale, not as "Standardrunde 1 … 6". Either
way the panel takes the file's name: it is showing that playlist now.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_warm_"))

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDropEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_STD = ("LW", "TG", "WW", "SF", "QS")


class WarmupImportTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_warm_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_warm_m3u_"))

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.lib = MusicLibrary()
        self.win._lib = self.lib
        self.table = self.win._warmup_table

    # ── fixtures ────────────────────────────────────────────────────────────
    def _m3u(self, name, dances):
        """An .m3u of `dances` (dance code per line), every track in the library."""
        paths = []
        for i, d in enumerate(dances):
            p = self.dir / f"{name}_{i:03d}_{d}.mp3"
            self.lib.entries.append(
                MusicEntry(path=p, title=f"{d} {i}", dance=d, duration=180))
            paths.append(str(p))
        f = self.dir / f"{name}.m3u"
        f.write_text("#EXTM3U\n" + "\n".join(paths), encoding="utf-8")
        return f

    def strips(self):
        """What the ─── strips are called, without their song/time summary."""
        out = []
        for r in range(self.table.rowCount()):
            if self.table._row_meta[r] is None:
                it = self.table.item(r, 0) or self.table.item(r, 3)
                text = (it.text() if it else "").strip(" ▼▶─")
                out.append(text.split("   (")[0].strip())
        return out

    def drop(self, m3u):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(m3u))])
        self.table.dropEvent(QDropEvent(
            QPointF(2, 2), Qt.DropAction.CopyAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))

    # ── the tests ───────────────────────────────────────────────────────────
    def test_a_running_order_is_cut_into_the_rounds_it_is_played_in(self):
        """The panel takes whatever is dropped on it, and a competition list is
        rounds — not a warm-up's 'new round wherever a dance repeats'."""
        self.win._load_warmup_from_m3u(self.table, str(self._m3u("HGR_D", _STD * 3)))
        self.assertEqual(self.strips(), ["Vorrunde", "Zwischenrunde", "Finale"])

    def test_the_panel_is_named_after_the_file_it_is_showing(self):
        """Not "Eintanzen HGR_D_STD": the list on screen is that playlist."""
        self.win._load_warmup_from_m3u(self.table, str(self._m3u("HGR_D_STD", _STD * 3)))
        self.assertEqual(self.win.deck(self.table).name, "🤸  HGR_D_STD")

    def test_a_warm_up_list_is_still_cut_the_warm_up_way(self):
        """A real Eintanzen list runs through the dances all evening — there are
        no rounds in that to find, and it keeps the numbered Standardrunde strips
        it always had."""
        self.win._load_warmup_from_m3u(self.table, str(self._m3u("eintanzen", _STD * 8)))
        self.assertEqual(self.strips(),
                         [f"Standardrunde {n}" for n in range(1, 9)])

    def test_a_warm_up_list_clears_the_rounds_of_the_order_before_it(self):
        """Loading over a running order must not leave the panel grouping by
        rounds the new list never had."""
        self.win._load_warmup_from_m3u(self.table, str(self._m3u("order", _STD * 3)))
        self.win._load_warmup_from_m3u(self.table, str(self._m3u("warmup", _STD * 8)))
        self.assertFalse(self.table._player_list)
        self.assertFalse(self.table._player_sections)

    def test_a_list_dropped_on_the_empty_panel_arrives(self):
        """`_warmup` is only raised once a list is loaded, so the empty panel has
        to be recognised by being the panel — the drop used to fall through to
        the deck import and leave it blank."""
        self.drop(self._m3u("dropped", _STD * 3))
        self.assertEqual(self.win.deck(self.table).name, "🤸  dropped")
        self.assertEqual(len([m for m in self.table._row_meta if m]), 15)

    def test_a_second_list_dropped_on_it_takes_over_name_and_rounds(self):
        """The panel now plays a running order, which makes it 'flat' like a
        player deck — it still has to keep its own loader, or the next file
        would arrive as a deck and lose the 🤸 title."""
        self.drop(self._m3u("first", _STD * 3))
        self.table._confirm_m3u_replaces = lambda _m3u: True
        self.drop(self._m3u("second", _STD * 2))
        self.assertEqual(self.win.deck(self.table).name, "🤸  second")
        self.assertEqual(self.strips(), ["Vorrunde", "Finale"])

    def test_the_panel_remembers_its_rounds_across_a_restart(self):
        """Saved as a warm-up list, the rounds were re-cut the warm-up way on the
        next start and the panel was back to 'Standardrunde 1 … '."""
        self.win._load_warmup_from_m3u(self.table, str(self._m3u("saved", _STD * 3)))
        before = self.strips()
        state = self.win._warmup_state()

        self.win._restore_warmup_state({})       # empty it, as a restart would
        self.assertFalse(self.table._row_meta)
        self.win._restore_warmup_state(state)
        self.assertEqual(self.strips(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
