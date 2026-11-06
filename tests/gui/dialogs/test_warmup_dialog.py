#!/usr/bin/env python3
"""Tests for the 🤸 Eintanzen / party dialog's answer, without a window.

Run:  py -m unittest tests.gui.dialogs.test_warmup_dialog -v

The dialog is shown with its `exec` stubbed, so what is checked is what the
generator receives: the options a click on Generate hands back.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_warmup_dlg_"))

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QRadioButton,
    QSpinBox,
)

from gui.dialogs import M3uDropDialog
from gui.dialogs.warmup_dialog import ask_warmup_options

ACCEPTED = QDialog.DialogCode.Accepted
REJECTED = QDialog.DialogCode.Rejected


def answered(exec_result, wishlists=()):
    # A plain function in the class's place, so it is called with the dialog.
    with mock.patch.object(M3uDropDialog, "exec", exec_result):
        return ask_warmup_options(None, [], "", wishlists)


def then_cancel(act):
    """`act` the first time the dialog opens; the second time (it came back
    with a message, #77) the user gives up."""
    calls = []

    def run(dlg):
        calls.append(1)
        if len(calls) > 1:
            return REJECTED
        return act(dlg) or ACCEPTED
    return run


def third_mode_then(act):
    def run(dlg):
        dlg.findChildren(QRadioButton)[2].setChecked(True)
        act(dlg)
    return run


def wish_radio(dlg):
    return next(rb for rb in dlg.findChildren(QRadioButton)
                if rb.text() == "Open wishlists")


class WarmupDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # The dialog remembers its choices; keep them in memory per test.
        self.store = {}
        for name, fn in (("load_settings", lambda: self.store),
                         ("save_settings", lambda s: self.store.update(s))):
            p = mock.patch(f"gui.dialogs.warmup_dialog.{name}", fn)
            p.start()
            self.addCleanup(p.stop)

    def test_generate_with_the_defaults(self):
        opts = answered(lambda dlg: ACCEPTED)
        self.assertEqual(
            {k: opts[k] for k in ("mode", "source", "m3u_path", "unused_only",
                                  "style", "dance_class", "max_tracks",
                                  "fresh_ratio", "relax")},
            {"mode": "class", "source": "library", "m3u_path": None,
             "unused_only": True, "style": "Latin", "dance_class": "S",
             "max_tracks": 100, "fresh_ratio": 0.25, "relax": True})
        self.assertEqual(opts["etds"]["max_tracks"], 120)
        self.assertEqual(opts["etds"]["modetaenze"], ["DISCOFOX", "SALSA"])

    def test_cancel_answers_nothing(self):
        self.assertIsNone(answered(lambda dlg: REJECTED))

    def test_a_dropped_playlist_becomes_the_source(self):
        def drop_then_generate(dlg):
            dlg.m3uDropped.emit("C:/lists/party.m3u")
            return ACCEPTED
        opts = answered(drop_then_generate)
        self.assertEqual((opts["source"], opts["m3u_path"], opts["unused_only"]),
                         ("m3u", "C:/lists/party.m3u", True))

    def test_practice_leaves_no_gap_under_the_stack(self):
        # The stack used to take the height of its tallest page (the party's,
        # also through height-for-width), so "Practice" left a big empty band.
        seen = {}

        def look(dlg):
            seen["practice"] = dlg.sizeHint().height()
            dlg.findChildren(QRadioButton)[1].setChecked(True)
            seen["party"] = dlg.sizeHint().height()
            dlg.findChildren(QRadioButton)[0].setChecked(True)
            seen["back"] = dlg.sizeHint().height()
            return ACCEPTED
        answered(look)
        self.assertLess(seen["practice"], seen["party"] - 200)
        self.assertEqual(seen["back"], seen["practice"])

    def competition(self, act=None):
        """The answer with the third mode picked; `act(dlg)` can edit first."""
        def pick(dlg):
            dlg.findChildren(QRadioButton)[2].setChecked(True)
            if act:
                act(dlg)
            return ACCEPTED
        return answered(pick)

    def test_competition_defaults_to_the_class_dances_three_heats_one_final(self):
        opts = self.competition()
        self.assertEqual(opts["mode"], "competition")
        self.assertEqual(opts["competition"], {
            "style": "Latin", "dance_class": "S",
            "dances": ["SA", "CC", "RB", "PD", "JI"],
            "heats": 3, "rounds": 2, "final_heats": 1,
        "use_timbre": True, "fresh_ratio": 0.0, "fresh_mode": "fresh"})

    def test_a_dance_can_be_unticked(self):
        opts = self.competition(
            lambda dlg: dlg.findChild(QCheckBox, "dance_PD").setChecked(False))
        self.assertEqual(opts["competition"]["dances"], ["SA", "CC", "RB", "JI"])

    def test_changing_the_class_resets_the_ticks_to_its_dances(self):
        def act(dlg):
            dlg.findChild(QComboBox, "comp_style").setCurrentText("Standard")
            dlg.findChild(QComboBox, "comp_class").setCurrentText("D")
        opts = self.competition(act)
        self.assertEqual(opts["competition"]["dances"], ["LW", "TG", "SF", "QS"])

    def test_the_rounds_and_the_final_have_their_own_heat_counts(self):
        def act(dlg):
            dlg.findChild(QSpinBox, "comp_heats").setValue(2)
            dlg.findChild(QSpinBox, "comp_rounds").setValue(3)
            dlg.findChild(QSpinBox, "comp_final").setValue(4)
        opts = self.competition(act)
        self.assertEqual((opts["competition"]["heats"],
                          opts["competition"]["rounds"],
                          opts["competition"]["final_heats"]), (2, 3, 4))

    def test_competition_needs_a_dance(self):
        def act(dlg):
            for cb in dlg.findChildren(QCheckBox):
                if cb.objectName().startswith("dance_"):
                    cb.setChecked(False)
        with mock.patch("gui.dialogs.warmup_dialog.QMessageBox.warning") as warn:
            self.assertIsNone(answered(then_cancel(third_mode_then(act))))
        warn.assert_called_once()

    def test_the_last_choices_come_back(self):
        def first(dlg):
            dlg.findChild(QCheckBox, "party_std").setChecked(False)
            dlg.findChild(QCheckBox, "party_nopaso").setChecked(True)
            dlg.findChild(QCheckBox, "source_unused").setChecked(False)
            dlg.findChild(QComboBox, "comp_class").setCurrentIndex(1)
            dlg.findChild(QCheckBox, "dance_SA").setChecked(False)
            dlg.findChild(QSpinBox, "comp_heats").setValue(5)
            for rb in dlg.findChildren(QRadioButton):
                if rb.text() == "Open wishlists":
                    rb.setChecked(True)
            return ACCEPTED
        answered(first, [("W1", 1)])
        seen = {}

        def second(dlg):
            for n in ("party_std", "party_nopaso", "source_unused", "dance_SA"):
                seen[n] = dlg.findChild(QCheckBox, n).isChecked()
            seen["heats"] = dlg.findChild(QSpinBox, "comp_heats").value()
            seen["cls"] = dlg.findChild(QComboBox, "comp_class").currentData()
            return REJECTED
        answered(second, [("W1", 1)])
        self.assertEqual(seen, dict(party_std=False, party_nopaso=True,
                                    source_unused=False, dance_SA=False,
                                    heats=5, cls="C"))

    def test_a_cancelled_dialog_remembers_nothing(self):
        def act(dlg):
            dlg.findChild(QCheckBox, "party_std").setChecked(False)
            return REJECTED
        answered(act)
        self.assertEqual(self.store, {})

    def test_a_broken_memory_leaves_the_defaults(self):
        self.store["warmup_dialog"] = dict(mode="x", source=99,
                                           fields={"party_std": "no",
                                                   "comp_heats": "many"})
        seen = {}

        def act(dlg):
            seen["std"] = dlg.findChild(QCheckBox, "party_std").isChecked()
            seen["heats"] = dlg.findChild(QSpinBox, "comp_heats").value()
            return REJECTED
        answered(act)
        self.assertEqual(seen, dict(std=True, heats=3))

    def test_only_the_wishlists_with_titles_are_offered(self):
        seen = {}

        def act(dlg):
            seen["radio"] = wish_radio(dlg).isEnabled()
            return REJECTED
        answered(act)
        self.assertFalse(seen["radio"])

    def test_the_ticked_wishlists_are_answered(self):
        def act(dlg):
            wish_radio(dlg).setChecked(True)
            boxes = [cb for cb in dlg.findChildren(QCheckBox)
                     if cb.text().startswith(("W1", "W2"))]
            self.assertEqual([cb.text() for cb in boxes], ["W1 (3)", "W2 (5)"])
            boxes[0].setChecked(False)
            return ACCEPTED
        opts = answered(act, [("W1", 3), ("W2", 5)])
        self.assertEqual((opts["source"], opts["wishlist_picks"]), ("wishlists", [1]))

    def test_the_wishlist_ticks_show_only_while_their_choice_is_picked(self):
        """Tier 3 #10: they stood there ticked under the Favorites choice."""
        seen = {}

        def act(dlg):
            boxes = [cb for cb in dlg.findChildren(QCheckBox)
                     if cb.text().startswith(("W1", "W2"))]
            seen["favorites"] = [cb.isHidden() for cb in boxes]
            wish_radio(dlg).setChecked(True)
            seen["wishlists"] = [cb.isHidden() for cb in boxes]
            return REJECTED
        answered(act, [("W1", 3), ("W2", 5)])
        self.assertEqual(seen, dict(favorites=[True, True], wishlists=[False, False]))

    def test_unticking_every_wishlist_asks_for_one(self):
        def act(dlg):
            wish_radio(dlg).setChecked(True)
            for cb in dlg.findChildren(QCheckBox):
                if cb.text().startswith(("W1", "W2")):
                    cb.setChecked(False)
            return ACCEPTED
        with mock.patch("gui.dialogs.warmup_dialog.QMessageBox.warning") as warn:
            self.assertIsNone(answered(then_cancel(act), [("W1", 3)]))
        warn.assert_called_once()

    def test_competition_heats_sound_alike_unless_unticked(self):
        def act(dlg):
            dlg.findChild(QRadioButton, "mode_competition").setChecked(True)
            return ACCEPTED
        self.assertTrue(answered(act)["competition"]["use_timbre"])

        def off(dlg):
            dlg.findChild(QRadioButton, "mode_competition").setChecked(True)
            dlg.findChild(QCheckBox, "comp_timbre").setChecked(False)
            return ACCEPTED
        self.assertFalse(answered(off)["competition"]["use_timbre"])

    def test_fresh_titles_are_new_ones_or_rarely_played_ones(self):
        def rarely(dlg):
            dlg.findChild(QRadioButton, "mode_competition").setChecked(True)
            combo = dlg.findChild(QComboBox, "comp_fresh_mode")
            combo.setCurrentIndex(combo.findData("rarely"))
            return ACCEPTED
        self.assertEqual(answered(rarely)["competition"]["fresh_mode"], "rarely")

    def test_the_fresh_share_steps_by_ten_percent(self):
        def act(dlg):
            dlg.findChild(QRadioButton, "mode_competition").setChecked(True)
            dlg.findChild(QSpinBox, "comp_fresh").stepUp()
            return ACCEPTED
        self.assertEqual(answered(act)["competition"]["fresh_ratio"], 0.1)

    def test_competition_mode_comes_back_preselected(self):
        def first(dlg):
            dlg.findChild(QRadioButton, "mode_competition").setChecked(True)
            return ACCEPTED
        answered(first)
        seen = {}

        def second(dlg):
            seen["mode"] = dlg.findChild(QRadioButton, "mode_competition").isChecked()
            return REJECTED
        answered(second)
        self.assertTrue(seen["mode"])

    def test_the_choices_go_into_the_settings_the_window_keeps(self):
        memory = {}
        with mock.patch.object(M3uDropDialog, "exec", lambda dlg: ACCEPTED):
            ask_warmup_options(None, [], "", (), memory)
        self.assertIn("warmup_dialog", memory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
