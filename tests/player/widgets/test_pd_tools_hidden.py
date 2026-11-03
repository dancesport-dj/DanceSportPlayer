"""🎯 ✖ ✏️ are only on the panel while a Paso Doble is on the deck.

Run:  py -m unittest tests.player.widgets.test_pd_tools_hidden -v

Marcel's list, 5.8: "If no Paso Doble is selected, do not show the "edit" and
"mark PD highlight" menu options, which are currently greyed out." They used
to stay as grey buttons, in a column that is read in the middle of a round.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from player.widgets.play_mode_panel import PlayModePanel
from tests.qt_test_support import reap_widget


class PdToolsHiddenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self):
        p = PlayModePanel({"pd_highlight_stop": True, "pd_highlight_n": 2})
        self.addCleanup(reap_widget, p)
        p.show()
        self.app.processEvents()
        return p

    def tools(self, p):
        return (p.pd_learn_btn, p.pd_clear_btn, p.pd_edit_btn)

    def test_nothing_on_the_deck_shows_none_of_them(self):
        p = self.panel()
        self.assertEqual([w.isVisible() for w in self.tools(p)], [False] * 3)

    def test_a_paso_doble_on_the_deck_shows_them_all(self):
        p = self.panel()
        p.set_pd_loaded(True)
        self.assertEqual([w.isVisible() for w in self.tools(p)], [True] * 3)
        self.assertTrue(all(w.isEnabled() for w in self.tools(p)))

    def test_another_title_takes_them_away_again(self):
        p = self.panel()
        p.set_pd_loaded(True)
        p.set_pd_loaded(False)
        self.assertEqual([w.isVisible() for w in self.tools(p)], [False] * 3)

    def test_their_rows_give_their_room_back(self):
        """Hiding only the buttons would leave an empty line in the column."""
        p = self.panel()
        without = p.pd_sub_box.sizeHint().height()
        p.set_pd_loaded(True)
        self.assertGreaterEqual(p.pd_sub_box.sizeHint().height() - without, 2 * 26)

    def test_the_settings_of_the_stop_stay(self):
        """They are the round's settings, not tools for the title on the deck."""
        p = self.panel()
        self.assertTrue(p.pd_spin.isVisible())
        self.assertTrue(p.pd_sub_box.isVisible())

    def test_the_paso_doble_switch_does_not_bring_them_back(self):
        p = self.panel()
        p.pd_check.setChecked(False)
        p.pd_check.setChecked(True)
        self.assertEqual([w.isVisible() for w in self.tools(p)], [False] * 3)

    def test_the_strip_layout_keeps_them_hidden(self):
        p = self.panel()
        p.set_wide(True)
        self.app.processEvents()
        self.assertEqual([w.isVisible() for w in self.tools(p)], [False] * 3)
        p.set_pd_loaded(True)
        self.assertEqual([w.isVisible() for w in self.tools(p)], [True] * 3)

    def test_edit_mode_does_not_go_on_behind_the_hidden_button(self):
        """It would keep the highlight stop suspended with nothing on screen
        saying so; the same reason the Paso Doble switch ends it."""
        p = self.panel()
        p.set_pd_loaded(True)
        p.pd_edit_btn.setChecked(True)
        p.set_pd_loaded(False)
        self.assertFalse(p.pd_edit_btn.isChecked())
        self.assertFalse(p.pd_marks_box.isVisible())


if __name__ == "__main__":
    unittest.main(verbosity=2)
