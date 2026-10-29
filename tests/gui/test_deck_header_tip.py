#!/usr/bin/env python3
"""The tooltip of a deck header (and of the badge under a deck) looks like any
other tooltip, not like the header it belongs to.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_deck_header_tip -v

Marcel: the playlist header tooltip was too big. The header carries a
selector-less stylesheet (bold 11 px, 2 px 8 px padding, border, the blue
face when focused), and Qt draws a widget's tooltip with that widget's sheet,
so the tip came out bold, padded and — on the focused deck — blue.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_header_tip_"))

from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication, QLabel, QToolTip

from tests.qt_test_support import reap_widget, stub_window_startup


class DeckHeaderTipTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_header_tip_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.win.show()
        self.win._on_table_focused(self.win._deckset.tableA)
        self.addCleanup(QToolTip.hideText)

    def tip_of(self, widget):
        """Hover `widget` and return the tooltip label Qt shows for it."""
        QToolTip.hideText()
        self.app.processEvents()
        pos = QPoint(4, 4)
        QApplication.sendEvent(widget, QHelpEvent(
            QEvent.Type.ToolTip, pos, widget.mapToGlobal(pos)))
        self.app.processEvents()
        tips = [w for w in QApplication.topLevelWidgets()
                if w.metaObject().className() == "QTipLabel" and w.isVisible()]
        self.assertEqual(len(tips), 1, "no tooltip shown")
        return tips[0]

    def plain_tip(self, text):
        lbl = QLabel("plain", self.win)
        lbl.setToolTip(text)
        lbl.show()
        return self.tip_of(lbl)

    def assertLooksPlain(self, widget):
        plain = self.plain_tip(widget.toolTip())
        font, height = plain.font(), plain.sizeHint().height()
        tip = self.tip_of(widget)
        self.assertFalse(tip.font().bold())
        self.assertEqual(tip.font().pixelSize(), font.pixelSize())
        self.assertEqual(tip.font().pointSizeF(), font.pointSizeF())
        self.assertEqual(tip.sizeHint().height(), height)

    def test_the_focused_header_tip(self):
        self.assertLooksPlain(self.win.deck(self.win._deckset.tableA).header)

    def test_an_idle_header_tip(self):
        self.assertLooksPlain(self.win.deck(self.win._deckset.tableB).header)

    def test_the_total_badge_tip(self):
        tot = self.win.deck(self.win._deckset.tableA).total_lbl
        tot.setVisible(True)
        self.assertLooksPlain(tot)

    def test_the_wishlist_count_tip(self):
        cnt = self.win.deck(self.win._deckset.wishlists[0]).count_lbl
        cnt.setVisible(True)
        self.assertLooksPlain(cnt)


if __name__ == "__main__":
    unittest.main()
