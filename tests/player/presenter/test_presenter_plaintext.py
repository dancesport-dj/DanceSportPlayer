"""🛡 The hall screen shows names as text, never as markup (review #17): a file
name or a typed programme line like `<img src="file:///...">` must not be
rendered as rich text, which would fetch the image."""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_presplain_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from player.presenter.timetable import Entry, Timetable
from tests.qt_test_support import qapp, reap_widget

_EVIL = '<img src="file:///C:/x.png">'
_STATE = ("Langsamer Walzer", _EVIL, ("01:12", "− 01:48", False, 0.4),
          [("Tango", _EVIL)], ("Cha Cha Cha", _EVIL))


class PlainTextTest(unittest.TestCase):

    def test_every_label_on_the_hall_screen_is_plain_text(self):
        from player.presenter.presenter import PresenterWindow
        qapp()
        win = PresenterWindow(lambda: _STATE)
        self.addCleanup(reap_widget, win)
        win.set_timetable(Timetable(title=_EVIL, entries=[
            Entry(_EVIL, _EVIL, _EVIL), Entry("19:00", "Dinner", "Buffet")]))
        win._refresh()
        rich = [lbl.text() for lbl in win.findChildren(QLabel)
                if lbl.textFormat() != Qt.TextFormat.PlainText]
        self.assertEqual(rich, [])


if __name__ == "__main__":
    unittest.main()
