#!/usr/bin/env python3
"""Labels that take outside text show it as typed (review 7.C / 4.C).

Run:  py -m unittest tests.gui.test_outside_text_plain -v

A default QLabel is AutoText: a pad label, a key name or a raw ID3 value
that starts like markup is rendered as rich text, `<img src=…>` included.
The key-clash warnings and the Extended tab's value tooltip now show the
text as it is, like the message boxes and toasts already did.
"""
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_outside_plain_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem

from planner.playing import controller as pctl
from shared.plain_text import plain_tip
from tests.qt_test_support import qapp, reap_widget

MARKUP = '<b>Jingle</b><img src="http://10.255.255.1/x.png">'


class OutsideTextPlainTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapp()

    def test_the_pad_key_warning_is_plain(self):
        from player.widgets import cart_keys
        warn = cart_keys._warning_label()
        self.addCleanup(reap_widget, warn)
        self.assertEqual(warn.textFormat(), Qt.TextFormat.PlainText)

    def test_the_desk_key_warnings_are_plain(self):
        from player.dialogs.desk_keys_dialog import DeskKeysPanel
        panel = DeskKeysPanel(pctl.desk_keys({}))
        self.addCleanup(reap_widget, panel)
        warns = [lbl for lbl in panel.findChildren(QLabel)
                 if "#b26a00" in lbl.styleSheet()]
        self.assertTrue(warns)
        for warn in warns:
            self.assertEqual(warn.textFormat(), Qt.TextFormat.PlainText)

    def test_a_raw_tag_value_tooltip_is_plain(self):
        from gui.dialogs import tag_edit_dialog as ted
        value = QTableWidgetItem(MARKUP)
        value.setData(ted._EDITABLE_ROLE, True)
        host = SimpleNamespace(_raw_form={}, _raw_custom=None)
        ted.TagEditDialog._raw_lock(host, value, "TIT2")
        self.assertEqual(value.toolTip(), plain_tip(MARKUP))
        self.assertNotEqual(value.toolTip(), MARKUP)


if __name__ == "__main__":
    unittest.main()
