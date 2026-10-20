#!/usr/bin/env python3
"""⌨ Desk keys: every Playing-side action on a key of its own.

Run:  .venv/Scripts/python.exe -m unittest tests.player.dialogs.test_desk_keys -v

The 📱 phone and a 🎛 MIDI controller already drive the desk through one list
of actions (planner.playing.controller.ACTIONS). The keyboard is a third way into the
same list: a Stream Deck or a macro keypad sends keys, so with a key per
action it needs no MIDI driver at all. Ctrl+Shift+←/→ were the only two keys
the player had; they stay the defaults of ⏮ / ⏭. An action takes more than
one key (Marcel: "make it generally possible to give more than one
shortcut"): a ＋ in its row adds another.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_desk_keys_"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog,
                               QDialogButtonBox, QPushButton, QToolButton)

from planner.playing import controller as pctl
from planner import i18n
from tests.qt_test_support import reap_widget, stub_window_startup


class RegistryTest(unittest.TestCase):

    def test_every_button_action_but_the_pads_can_have_a_key(self):
        self.assertIn("toggle", pctl.KEY_ACTIONS)
        self.assertIn("stop_pads", pctl.KEY_ACTIONS)
        self.assertNotIn("volume", pctl.KEY_ACTIONS, "a fader is no key")
        self.assertFalse([a for a in pctl.KEY_ACTIONS if a.startswith("pad:")],
                         "the pads have their own keys on the 🎛 wall")

    def test_the_volume_can_be_stepped(self):
        """A keypad has no fader: up and down a step instead."""
        for action in ("vol_up", "vol_down"):
            self.assertIn(action, pctl.KEY_ACTIONS)
            self.assertIn(action, pctl.ACTION_IDS, "MIDI buttons may step it too")
            self.assertNotIn(action, pctl.CONTINUOUS)

    def test_the_defaults_are_the_keys_the_player_always_had(self):
        keys = pctl.desk_keys({})
        self.assertEqual(keys["next"], ["Ctrl+Shift+Right"])
        self.assertEqual(keys["prev"], ["Ctrl+Shift+Left"])
        self.assertEqual(set(keys), set(pctl.KEY_ACTIONS))

    def test_every_action_has_a_key_of_its_own_from_the_start(self):
        keys = pctl.desk_keys({})
        self.assertEqual([a for a, k in keys.items() if not k], [])
        every = [k for ks in keys.values() for k in ks]
        self.assertEqual(len(set(every)), len(keys))
        self.assertEqual(pctl.key_clashes(keys), {},
                         "no default takes a key the app answers to")

    def test_the_warm_up_lists_swap_key_is_the_apps(self):
        """Alt+S swaps two titles in the warm-up list; a desk key on it would
        take it from the list (⭐ to the wishlist had it at first)."""
        self.assertIn("Alt+S", pctl.RESERVED_KEYS)

    def test_enter_plays_the_selection_in_the_lists(self):
        """Both Enter keys: the main one and the keypad's."""
        self.assertIn("Return", pctl.RESERVED_KEYS)
        self.assertIn("Enter", pctl.RESERVED_KEYS)

    def test_a_saved_key_wins_and_an_empty_one_unbinds(self):
        keys = pctl.desk_keys({"fade": "F13", "next": ""})
        self.assertEqual(keys["fade"], ["F13"])
        self.assertEqual(keys["next"], [])
        self.assertEqual(keys["prev"], ["Ctrl+Shift+Left"])

    def test_an_action_can_have_more_than_one_key(self):
        keys = pctl.desk_keys({"fade": ["F13", "Ctrl+Shift+F"], "next": []})
        self.assertEqual(keys["fade"], ["F13", "Ctrl+Shift+F"])
        self.assertEqual(keys["next"], [])

    def test_the_same_key_twice_counts_once(self):
        self.assertEqual(pctl.desk_keys({"fade": ["F13", "F13", ""]})["fade"], ["F13"])

    def test_rubbish_is_ignored(self):
        keys = pctl.desk_keys({"fade": 7, "hold": ["F13", 8],
                               "nonsense": "F2", "pad:1": "F3"})
        self.assertEqual(keys, pctl.desk_keys({}))
        self.assertEqual(pctl.desk_keys("not a dict"), pctl.desk_keys({}))

    def test_a_key_answers_to_one_action(self):
        """Two shortcuts on one key are ambiguous to Qt: neither fires."""
        keys = pctl.desk_keys({"toggle": "F13", "fade": ["F14", "F13"]})
        self.assertEqual(keys["toggle"], ["F13"])
        self.assertEqual(keys["fade"], ["F14"])

    def test_clashes_are_named(self):
        clash = pctl.key_clashes({"toggle": ["Ctrl+S"], "fade": ["F13"],
                                  "hold": ["F15", "F13"], "duck": ["F14"]})
        self.assertEqual(set(clash), {("toggle", 0), ("hold", 1)})
        self.assertEqual(clash[("hold", 1)], dict(pctl.ACTIONS)["fade"])

    def test_the_same_key_twice_on_one_action_is_named_once(self):
        clash = pctl.key_clashes({"fade": ["F13", "", "F13"]})
        self.assertEqual(clash, {("fade", 2): dict(pctl.ACTIONS)["fade"]})
        self.assertIn("Ctrl+S", pctl.RESERVED_KEYS)

    def test_a_key_someone_else_has_is_named(self):
        clash = pctl.key_clashes({"fade": ["F13"], "hold": ["F14"]},
                                 {"F13": "🎛  Tusch (p1)"})
        self.assertEqual(clash, {("fade", 0): "🎛  Tusch (p1)"})

    def test_the_wall_names_its_slot_better_than_the_app_does(self):
        clash = pctl.key_clashes({"fade": ["Ctrl+2"]}, {"Ctrl+2": "🎛  Slot 2"})
        self.assertEqual(clash, {("fade", 0): "🎛  Slot 2"})

    def test_the_wall_must_not_take_the_app_or_desk_keys(self):
        taken = pctl.keys_outside_wall(pctl.desk_keys({"fade": ["F13", "F14"]}))
        self.assertEqual(taken["F13"], dict(pctl.ACTIONS)["fade"])
        self.assertEqual(taken["F14"], dict(pctl.ACTIONS)["fade"])
        self.assertEqual(taken["Ctrl+S"], pctl.RESERVED_KEYS["Ctrl+S"])
        self.assertIn("Esc", taken, "the wall's own stop-all")
        self.assertNotIn("Ctrl+1", taken, "the wall's own slot keys")

    def test_a_key_reads_like_the_cheat_sheet(self):
        self.assertEqual(pctl.key_text("Ctrl+Shift+Right"), "Ctrl + Shift + →")
        self.assertEqual(pctl.key_text("Ctrl++"), "Ctrl + +")
        self.assertEqual(pctl.key_text("F13"), "F13")


class _WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_desk_keys_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(
            cls, {"app_mode": "both", "desk_keys": {"fade": "F13"}})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)


class WindowKeysTest(_WindowTest):

    def test_one_shortcut_per_action(self):
        self.assertEqual(set(self.win._desk_keys), set(pctl.KEY_ACTIONS))

    def test_the_saved_keys_are_on_them(self):
        self.assertEqual(self.win._desk_keys["fade"].key(), QKeySequence("F13"))
        self.assertEqual(self.win._desk_keys["next"].key(),
                         QKeySequence("Ctrl+Shift+Right"))
        self.assertEqual(self.win._desk_keys["hold"].key(),
                         QKeySequence(pctl.KEY_DEFAULTS["hold"]))

    def test_every_key_of_an_action_is_on_its_shortcut(self):
        self.win.set_desk_keys({"fade": ["F13", "F14"]})
        self.assertEqual(self.win._desk_keys["fade"].keys(),
                         [QKeySequence("F13"), QKeySequence("F14")])

    def test_a_key_runs_the_action_the_phone_runs(self):
        done = []
        self.win._fade_out_now = lambda: done.append("fade")
        self.win._desk_keys["fade"].activated.emit()
        self.assertEqual(done, ["fade"])

    def test_a_focus_key_brings_its_list_in_front(self):
        self.assertEqual(self.win._desk_keys["deck:3"].key(), QKeySequence("Alt+3"))
        self.win._focus_list = mock.Mock()
        self.win._desk_keys["wish:2"].activated.emit()
        self.win._focus_list.assert_called_once_with("wish", 2)

    def test_only_the_volume_and_tempo_steps_repeat(self):
        """A held ⏭ throws titles away; a held volume or tempo key is a glide."""
        for action, sc in self.win._desk_keys.items():
            with self.subTest(action=action):
                self.assertEqual(sc.autoRepeat(),
                                 action in ("vol_up", "vol_down", "tempo_up", "tempo_down"))

    def test_the_volume_keys_step_the_master(self):
        self.win._set_base_volume(0.5)
        self.win._desk_keys["vol_up"].activated.emit()
        self.assertAlmostEqual(self.win._mix.base, 0.5 + pctl.VOLUME_STEP)
        self.win._desk_keys["vol_down"].activated.emit()
        self.win._desk_keys["vol_down"].activated.emit()
        self.assertAlmostEqual(self.win._mix.base, 0.5 - pctl.VOLUME_STEP)

    def _open(self, opener, answer=None):
        """Open the ⌨ Keys window through `opener`. `answer(dlg)` plays the
        user and says whether they pressed OK; without one they cancel."""
        import player.dialogs.desk_keys_dialog as dkd
        seen = {}

        class _Spy(dkd.KeysDialog):
            def exec(self):
                seen["dlg"] = self
                ok = answer(self) if answer else False
                return (QDialog.DialogCode.Accepted if ok
                        else QDialog.DialogCode.Rejected)

        with mock.patch.object(dkd, "KeysDialog", _Spy):
            opener()
        return seen["dlg"]

    def test_the_desk_entry_opens_on_the_desk_tab(self):
        dlg = self._open(self.win.open_desk_keys_window)
        self.assertIs(dlg.tabs.currentWidget(), dlg.desk)

    def test_the_wall_opens_the_same_window_on_its_own_tab(self):
        dlg = self._open(self.win._cartwall._on_shortcuts)
        self.assertIs(dlg.tabs.currentWidget(), dlg.wall)

    def test_the_wall_tab_shows_the_wall(self):
        from planner.playing import cartwall as pc
        self.win._cartwall.set_wall((4, 4), [pc.Page(pads={
            (0, 0): pc.CartPad(path="t.mp3", label="Tusch", shortcut="F20")})])
        dlg = self._open(self.win.open_desk_keys_window)
        self.assertEqual(dlg.wall.pad_keys(), {(0, 0, 0): "F20"})
        self.assertEqual(dlg.desk._taken["F20"], "🎛  Tusch (p1)")

    def test_the_wall_tab_hears_of_the_desk_keys(self):
        dlg = self._open(self.win._cartwall._on_shortcuts)
        self.assertEqual(dlg.wall._taken["F13"], dict(pctl.ACTIONS)["fade"])

    def test_one_ok_saves_both(self):
        def answer(dlg):
            dlg.desk._pickers["toggle"][0].set_sequence("F14")
            dlg.wall._slot_pickers[0].set_sequence("F5")
            return True
        self._open(self.win.open_desk_keys_window, answer)
        self.assertEqual(self.win._settings["desk_keys"]["toggle"], ["F14"])
        self.assertEqual(self.win._desk_keys["toggle"].key(), QKeySequence("F14"))
        self.assertEqual(self.win._cartwall.slot_keys()[0], "F5")

    def test_cancel_changes_neither(self):
        def answer(dlg):
            dlg.desk._pickers["toggle"][0].set_sequence("F14")
            dlg.wall._slot_pickers[0].set_sequence("F5")
            return False
        self._open(self.win._cartwall._on_shortcuts, answer)
        self.assertNotIn("toggle", self.win._settings["desk_keys"])
        self.assertEqual(self.win._cartwall.slot_keys()[0], "Ctrl+1")

    def test_new_keys_are_saved_and_applied(self):
        self.win.set_desk_keys({"toggle": ["F14"], "next": []})
        self.assertEqual(self.win._settings["desk_keys"]["toggle"], ["F14"])
        self.assertEqual(self.win._desk_keys["toggle"].key(), QKeySequence("F14"))
        self.assertTrue(self.win._desk_keys["next"].key().isEmpty())


class DialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, keys):
        from player.dialogs.desk_keys_dialog import DeskKeysPanel
        dlg = DeskKeysPanel(pctl.desk_keys(keys))
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_hands_back_what_it_was_given(self):
        keys = pctl.desk_keys({"fade": "F13"})
        self.assertEqual(self._dialog({"fade": "F13"}).keys(), keys)

    def test_a_row_per_action(self):
        self.assertEqual(set(self._dialog({})._pickers), set(pctl.KEY_ACTIONS))

    def test_the_list_scrolls_rather_than_outgrow_a_laptop_screen(self):
        """Twenty-five rows would ask for ~800 px before the tabs and the
        buttons; a 768 px screen has to hold the whole window."""
        self.assertLessEqual(self._dialog({}).minimumSizeHint().height(), 520)

    def test_restore_defaults(self):
        dlg = self._dialog({"fade": "F13", "next": ""})
        btn = next(b for b in dlg.findChildren(QPushButton)
                   if b.text() == "↺  Restore defaults")
        btn.click()
        self.assertEqual(dlg.keys(), pctl.desk_keys({}))
        self.assertEqual(len(dlg._pickers["fade"]), 1)

    def test_plus_adds_another_key(self):
        dlg = self._dialog({"fade": "F13"})
        dlg._add_buttons["fade"].click()
        self.assertEqual(len(dlg._pickers["fade"]), 2)
        self.assertEqual(dlg.keys()["fade"], ["F13"], "an empty one is no key")
        dlg._pickers["fade"][1].set_sequence("F14")
        self.assertEqual(dlg.keys()["fade"], ["F13", "F14"])

    def _minus(self, dlg):
        return [b for b in dlg.findChildren(QToolButton) if b.text() == "−"]

    def test_minus_takes_an_added_key_away(self):
        # Marcel: "a - to remove the second key is missing totally"
        dlg = self._dialog({"fade": "F13"})
        self.assertEqual(self._minus(dlg), [], "the first field has a ＋, no −")
        dlg._add_buttons["fade"].click()
        dlg._pickers["fade"][1].set_sequence("F14")
        changed = []
        dlg.changed.connect(lambda: changed.append(1))
        minus = self._minus(dlg)
        self.assertEqual(len(minus), 1)
        minus[0].click()
        self.assertEqual(len(dlg._pickers["fade"]), 1)
        self.assertEqual(len(dlg._warnings["fade"]), 1)
        self.assertEqual(dlg.keys()["fade"], ["F13"])
        self.assertEqual(changed, [1])
        self.assertEqual(self._minus(dlg), [])

    def test_minus_takes_the_field_it_stands_beside(self):
        dlg = self._dialog({"fade": ["F13", "F14", "F15"]})
        self._minus(dlg)[0].click()     # beside F14
        self.assertEqual(dlg.keys()["fade"], ["F13", "F15"])

    def test_it_opens_with_every_saved_key(self):
        dlg = self._dialog({"fade": ["F13", "F14"]})
        self.assertEqual([p.sequence() for p in dlg._pickers["fade"]], ["F13", "F14"])

    def test_a_clash_on_the_second_key_is_shown_beside_it(self):
        dlg = self._dialog({"fade": ["F13", "Ctrl+S"]})
        self.assertEqual(dlg._warnings["fade"][0].text(), "")
        self.assertIn(pctl.RESERVED_KEYS["Ctrl+S"], dlg._warnings["fade"][1].text())

    def test_a_clash_is_shown_on_its_row(self):
        dlg = self._dialog({})
        dlg._pickers["toggle"][0].set_sequence("Ctrl+S")
        dlg._refresh()
        self.assertTrue(dlg._warnings["toggle"][0].text())
        self.assertFalse(dlg._warnings["fade"][0].text())

    def test_the_clash_says_what_the_app_does_with_the_key(self):
        dlg = self._dialog({})
        dlg._pickers["toggle"][0].set_sequence("Ctrl+S")
        dlg._refresh()
        self.assertIn(pctl.RESERVED_KEYS["Ctrl+S"],
                      dlg._warnings["toggle"][0].text())

    def test_a_wall_key_is_named_on_its_row(self):
        from player.dialogs.desk_keys_dialog import DeskKeysPanel
        dlg = DeskKeysPanel(pctl.desk_keys({"fade": "F13"}),
                            taken={"F13": "🎛  Tusch (p1)"})
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg._warnings["fade"][0].text(),
                         "⚠ The app uses this key: 🎛  Tusch (p1)")
        self.assertEqual(dlg._warnings["hold"][0].text(), "")

    def test_in_german_too(self):
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        dlg = self._dialog({})
        dlg._pickers["toggle"][0].set_sequence("Ctrl+S")
        dlg._refresh()
        self.assertIn(i18n.t(pctl.RESERVED_KEYS["Ctrl+S"]),
                      dlg._warnings["toggle"][0].text())
        self.assertIn("Die App nutzt diese Taste",
                      dlg._warnings["toggle"][0].text())


class LearnTest(unittest.TestCase):
    """🎓 Learn takes whatever key is pressed next — F13–F24 from a Stream
    Deck, any chord — where a ▼ list could only offer the keys it knew."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from player.dialogs.desk_keys_dialog import DeskKeysPanel
        self.dlg = DeskKeysPanel(pctl.desk_keys({"fade": "F13"}))
        self.addCleanup(reap_widget, self.dlg)
        self.dlg.show()
        self.picker = self.dlg._pickers["fade"][0]

    def test_a_learn_button_not_a_list(self):
        self.assertFalse(self.picker._learn.isHidden())
        self.assertEqual(self.picker.findChildren(QComboBox), [])
        self.assertEqual(self.picker._learn.text(), "Learn")

    def test_learn_takes_the_next_key_pressed(self):
        self.picker._learn.click()
        self.assertEqual(self.picker._learn.text(), "Cancel")
        QTest.keyClick(self.picker._edit, Qt.Key.Key_F20)
        self.assertEqual(self.picker.sequence(), "F20")
        self.assertEqual(self.dlg.keys()["fade"], ["F20"])
        self.assertEqual(self.picker._learn.text(), "Learn")

    def test_a_chord_too(self):
        self.picker._learn.click()
        QTest.keyClick(self.picker._edit, Qt.Key.Key_K,
                       Qt.KeyboardModifier.ControlModifier
                       | Qt.KeyboardModifier.AltModifier)
        self.assertEqual(self.picker.sequence(), "Ctrl+Alt+K")

    def test_learn_again_cancels_and_keeps_the_old_key(self):
        self.picker._learn.click()
        self.picker._learn.click()
        self.assertEqual(self.picker.sequence(), "F13")
        self.assertEqual(self.picker._learn.text(), "Learn")

    def test_the_cross_stops_learning_with_no_key(self):
        self.picker._learn.click()
        self.picker._on_clear()
        self.assertEqual(self.picker.sequence(), "")
        self.assertEqual(self.picker._learn.text(), "Learn")

    def test_the_cartwall_learns_too(self):
        from planner.playing import cartwall as pc
        from player.widgets.cart_keys import CartKeysPanel
        dlg = CartKeysPanel((2, 2), [pc.blank_page()], pc.SLOT_KEYS)
        self.addCleanup(reap_widget, dlg)
        picker = dlg._slot_pickers[0]
        self.assertFalse(picker._learn.isHidden())
        self.assertEqual(dlg.findChildren(QComboBox), [])


class KeysDialogTest(unittest.TestCase):
    """⌨ One window for every key: the desk's and the 🎛 wall's, each tab
    warning about what the other one has — saved or not yet."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from planner.playing import cartwall as pc
        from player.dialogs.desk_keys_dialog import KeysDialog
        self.dlg = KeysDialog(pctl.desk_keys({"fade": "F13"}),
                              ((4, 4), [pc.Page(pads={(0, 0): pc.CartPad(
                                  path="t.mp3", label="Tusch")})], pc.SLOT_KEYS))
        self.addCleanup(reap_widget, self.dlg)
        self.pad = self.dlg.wall._pad_pickers[0][1]
        self.pad_warn = self.dlg.wall._pad_pickers[0][2]

    def _press(self, picker, key):
        picker.set_sequence(key)
        picker.changed.emit()

    def test_an_added_key_gets_a_full_row(self):
        # Marcel: "i can add a new one, but then not enough space to show it
        # fully" — the fields were squeezed instead of the window growing.
        self.dlg.show()
        self.app.processEvents()
        for action in ("toggle", "next", "prev", "fade", "hold"):
            self.dlg.desk._add_buttons[action].click()
        for _ in range(5):          # layout requests post further ones
            self.app.processEvents()
        for action, pickers in self.dlg.desk._pickers.items():
            for picker in pickers:
                self.assertGreaterEqual(picker.height(), picker.sizeHint().height(),
                                        action)

    def test_two_tabs_one_ok(self):
        self.assertEqual(self.dlg.tabs.count(), 2)
        self.assertIs(self.dlg.tabs.currentWidget(), self.dlg.desk)
        self.assertEqual(len(self.dlg.findChildren(QDialogButtonBox)), 1)

    def test_it_can_open_on_the_wall_tab(self):
        from planner.playing import cartwall as pc
        from player.dialogs.desk_keys_dialog import KeysDialog
        dlg = KeysDialog({}, ((2, 2), [pc.blank_page()], pc.SLOT_KEYS),
                         tab=KeysDialog.WALL)
        self.addCleanup(reap_widget, dlg)
        self.assertIs(dlg.tabs.currentWidget(), dlg.wall)

    def test_it_hands_back_both(self):
        from planner.playing import cartwall as pc
        self.assertEqual(self.dlg.desk_keys(), pctl.desk_keys({"fade": "F13"}))
        self.assertEqual(self.dlg.pad_keys(), {(0, 0, 0): ""})
        self.assertEqual(self.dlg.slot_keys(), pc.SLOT_KEYS)

    def test_a_wall_key_not_yet_saved_is_named_on_the_desk_tab(self):
        self._press(self.pad, "F13")
        self.assertEqual(self.dlg.desk._warnings["fade"][0].text(),
                         "⚠ The app uses this key: 🎛  Tusch (p1)")
        self.assertEqual(self.pad_warn.text(), "⚠ The app uses this key: "
                         + dict(pctl.ACTIONS)["fade"])

    def test_a_desk_key_not_yet_saved_is_named_on_the_wall_tab(self):
        self._press(self.dlg.desk._pickers["toggle"][0], "Ctrl+2")
        self.assertEqual(self.dlg.wall._slot_warnings[1].text(),
                         "⚠ The app uses this key: "
                         + dict(pctl.ACTIONS)["toggle"])
        self.assertEqual(self.dlg.desk._warnings["toggle"][0].text(),
                         "⚠ The app uses this key: 🎛  Slot 2")

    def test_moving_the_key_away_clears_both_tabs(self):
        self._press(self.pad, "F13")
        self._press(self.pad, "F20")
        self.assertEqual(self.dlg.desk._warnings["fade"][0].text(), "")
        self.assertEqual(self.pad_warn.text(), "")


class CheatSheetTest(unittest.TestCase):

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_the_sheet_lists_the_keys_as_bound(self):
        from gui.dialogs.shortcuts import shortcut_rows
        rows = shortcut_rows({"fade": "F13", "next": ""})
        self.assertIn(("F13", dict(pctl.ACTIONS)["fade"]), rows)
        self.assertIn(("Ctrl + Shift + ←", dict(pctl.ACTIONS)["prev"]), rows)
        self.assertNotIn(dict(pctl.ACTIONS)["next"], [r for _l, r in rows])

    def test_more_than_one_key_shares_a_row(self):
        from gui.dialogs.shortcuts import shortcut_rows
        rows = shortcut_rows({"fade": ["F13", "Ctrl+Shift+F"]})
        self.assertIn(("F13  /  Ctrl + Shift + F", dict(pctl.ACTIONS)["fade"]), rows)

    def test_each_of_them_is_spelt_the_german_way(self):
        from gui.dialogs.shortcuts import shortcut_sheet_html
        i18n.set_active("de")
        html = shortcut_sheet_html({"fade": ["Ctrl+F5", "Ctrl+Shift+F6"]})
        self.assertIn("Strg + F5  /  Strg + Umschalt + F6", html)

    def test_a_custom_key_is_spelt_the_german_way(self):
        from gui.dialogs.shortcuts import shortcut_sheet_html
        i18n.set_active("de")
        html = shortcut_sheet_html({"fade": "Ctrl+Shift+F5"})
        self.assertIn("Strg + Umschalt + F5", html)


class SettingsButtonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_settings_opens_the_desk_keys(self):
        from gui.dialogs import settings_dialog
        opened = []
        dlg = settings_dialog.SettingsDialog({}, controller_cb=lambda over: None,
                                             desk_keys_cb=opened.append)
        self.addCleanup(reap_widget, dlg)
        btn = next(b for b in dlg.findChildren(QPushButton)
                   if b.text() == "⌨  Keys…")
        btn.click()
        self.assertEqual(opened, [dlg])


if __name__ == "__main__":
    unittest.main(verbosity=2)
