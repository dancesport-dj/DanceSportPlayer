"""Text from files, tags and packs reaches Qt as text, never as rich text.

Run:  py -m unittest tests.shared.test_plain_text -v

Qt turns a string that "might be rich text" into HTML, and an `<img src>` in it
opens that path (an SMB login for a UNC path). The probe uses a LOCAL png: it
goes through the same resource loader, and a loaded image makes the widget
taller. Security audit run-2 #3.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_plain_text_"))

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtGui import QColor, QHelpEvent, QImage
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QTableWidget, QTableWidgetItem

from shared import plain_text
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_TMP = tempfile.mkdtemp(prefix="dp_plain_png_")
PNG = os.path.join(_TMP, "probe.png").replace("\\", "/")
_img = QImage(300, 400, QImage.Format.Format_RGB32)
_img.fill(QColor("red"))
_img.save(PNG)

BAIT = f'Cha Cha <img src="{PNG}"> (Remix)'
# The image is 400 high; wrapped text stays well under the limit, a loaded image
# lands well over IMAGE_MIN.
PLAIN_HEIGHT_LIMIT = 200
IMAGE_MIN = 300


def _tip_labels():
    return [w for w in QApplication.topLevelWidgets()
            if w.metaObject().className() == "QTipLabel"]


class HelperTest(unittest.TestCase):

    def test_plain_html_escapes_everything_and_keeps_line_breaks(self):
        out = plain_text.plain_html('a <b>&"x"\nb')
        self.assertNotIn("<b>", out)
        self.assertIn("&lt;b&gt;&amp;", out)
        self.assertIn("white-space:pre-wrap", out)

    def test_a_tip_qt_shows_as_plain_is_left_alone(self):
        # "a < b and c > d": markup to Qt 6.11's guess, plain to 6.12's.
        for text in ("C:/music/x.mp3", "Tom & Jerry <3", "line1" + chr(10) + "<img src=y>",
                     "a < b and c > d"):
            with self.subTest(text=text):
                self.assertEqual(plain_text.plain_tip(text), text)

    def test_a_tip_qt_would_read_as_markup_is_escaped(self):
        for text in ("<b>x</b>", "x <img src=y>", "a <b and c> d"):
            with self.subTest(text=text):
                tip = plain_text.plain_tip(text)
                self.assertNotIn("<img", tip)
                self.assertNotIn("<b>", tip)
                self.assertIn("white-space:pre-wrap", tip)

    def test_an_empty_tip_stays_empty(self):
        self.assertEqual(plain_text.plain_tip(""), "")
        self.assertEqual(plain_text.plain_tip(None), "")

    def test_plain_label_is_plain_text(self):
        lbl = plain_text.plain_label(BAIT)
        self.addCleanup(reap_widget, lbl)
        self.assertEqual(lbl.text(), BAIT)
        lbl.adjustSize()
        self.assertLess(lbl.sizeHint().height(), PLAIN_HEIGHT_LIMIT)


class TooltipTest(unittest.TestCase):

    def _shown_tip_height(self, tip):
        table = QTableWidget(1, 1)
        self.addCleanup(reap_widget, table)
        item = QTableWidgetItem("cell")
        item.setToolTip(tip)
        table.setItem(0, 0, item)
        table.resize(300, 100)
        table.show()
        _app.processEvents()
        pos = table.visualItemRect(item).center()
        _app.sendEvent(table.viewport(), QHelpEvent(
            QEvent.Type.ToolTip, pos, table.viewport().mapToGlobal(pos)))
        _app.processEvents()
        tips = _tip_labels()
        self.assertTrue(tips, "no tooltip was shown")
        return tips[0].height()

    def test_the_bait_loads_an_image_without_the_helper(self):
        # The canary: if this ever stops being tall, the tests below prove nothing.
        self.assertGreater(self._shown_tip_height(BAIT), IMAGE_MIN)

    def test_the_helper_keeps_it_text(self):
        self.assertLess(self._shown_tip_height(plain_text.plain_tip(BAIT)),
                        PLAIN_HEIGHT_LIMIT)


class MessageBoxTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(plain_text.restore_message_boxes)

    def _label_height_of(self, call):
        seen = []

        def peek():
            box = QApplication.activeModalWidget()
            lbl = box.findChild(QLabel, "qt_msgbox_label")
            lbl.adjustSize()
            seen.append((lbl.sizeHint().height(), lbl.text()))
            box.close()

        QTimer.singleShot(50, peek)
        call()
        self.assertTrue(seen, "no message box appeared")
        return seen[0]

    def test_the_bait_loads_an_image_without_the_hook(self):
        height, _ = self._label_height_of(
            lambda: QMessageBox.warning(None, "t", BAIT))
        self.assertGreater(height, IMAGE_MIN)

    def test_every_static_shows_it_as_text(self):
        plain_text.install_message_boxes()
        for name in ("information", "warning", "critical", "question", "about"):
            with self.subTest(name=name):
                height, shown = self._label_height_of(
                    lambda n=name: getattr(QMessageBox, n)(None, "t", BAIT))
                self.assertLess(height, PLAIN_HEIGHT_LIMIT)
                self.assertIn("Cha Cha", shown)

    def test_a_box_built_by_hand_is_plain_by_default(self):
        plain_text.install_message_boxes()
        box = QMessageBox(None)
        self.addCleanup(reap_widget, box)
        box.setText(BAIT)
        lbl = box.findChild(QLabel, "qt_msgbox_label")
        lbl.adjustSize()
        self.assertLess(lbl.sizeHint().height(), PLAIN_HEIGHT_LIMIT)

    def test_a_box_can_still_ask_for_rich_text(self):
        plain_text.install_message_boxes()
        box = QMessageBox(None)
        self.addCleanup(reap_widget, box)
        box.setTextFormat(plain_text.RICH)
        box.setText("<b>bold</b>")
        self.assertEqual(box.textFormat(), plain_text.RICH)

    def test_install_twice_wraps_once(self):
        plain_text.install_message_boxes()
        plain_text.install_message_boxes()
        plain_text.restore_message_boxes()
        height, _ = self._label_height_of(
            lambda: QMessageBox.warning(None, "t", BAIT))
        self.assertGreater(height, IMAGE_MIN)   # fully restored


if __name__ == "__main__":
    unittest.main()
