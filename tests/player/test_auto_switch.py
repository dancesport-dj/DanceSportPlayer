#!/usr/bin/env python3
"""⏭ Auto / ✋ Manual switches the announcement with it.

Run:  py -m unittest tests.player.test_auto_switch -v

Going to Manual means the operator has taken the evening back into their own
hands: nothing starts by itself any more. An announcement that keeps firing
after that is worse than one that never fired — the hall hears "Nächster Tanz:
Langsamer Walzer" and then silence, because nobody told the desk the music was
supposed to follow.

So ✋ Manual stops the announcement too, and ⏭ Auto puts back what was
configured before — NOT simply "on". Somebody who runs the evening with
announcements off gets them left off.

The one thing this must never do is undo a click the operator made. If the
announcement is switched on by hand while in Manual, going back to Auto leaves
it on: the remembered value is what to restore, not what to enforce.

That is the PANEL's switch, which speaks for every deck. A single deck's own
⏭/✋ says the same thing for that list alone and leaves the panel untouched —
its silence is applied where the announcement is spoken, not by unticking 🔈.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_autosw_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from player.main_player import PlayerControlMixin  # noqa: E402
from player.play_mode_panel import PlayModePanel  # noqa: E402


class _Table:
    """Only what a corner switch's write-back touches."""

    def __init__(self):
        self._play_vals = None

    def refresh_advance_toggle(self):
        pass


class _Desk(PlayerControlMixin):
    """A MainWindow as far as the corner switch reaches into one."""

    def __init__(self, panel):
        self._play_panel = panel
        self._all_tables = ()

    def _autosave_playlist(self):
        pass


class AutoSwitchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self, announce: bool, advance: bool = True) -> PlayModePanel:
        p = PlayModePanel({"auto_advance": advance, "announce_next": announce})
        self.addCleanup(p.deleteLater)
        return p

    # ── the panel's own ⏭ Auto-advance switch ────────────────────────────────

    def test_manual_stops_the_announcement(self):
        p = self.panel(announce=True)
        p.advance_check.click()                     # → Manual
        self.assertFalse(p.advance_check.isChecked())
        self.assertFalse(p.announce_check.isChecked(),
                         "Manual left the announcement running")

    def test_auto_puts_back_the_announcement_that_was_configured(self):
        p = self.panel(announce=True)
        p.advance_check.click()                     # → Manual
        p.advance_check.click()                     # → Auto
        self.assertTrue(p.advance_check.isChecked())
        self.assertTrue(p.announce_check.isChecked(),
                        "Auto did not restore the announcement")

    def test_auto_does_not_switch_on_what_was_never_on(self):
        """An evening run without announcements stays without them."""
        p = self.panel(announce=False)
        p.advance_check.click()                     # → Manual
        p.advance_check.click()                     # → Auto
        self.assertFalse(p.announce_check.isChecked())

    def test_a_hand_change_while_manual_wins(self):
        """The remembered value is what to restore, not what to enforce."""
        p = self.panel(announce=False)
        p.advance_check.click()                     # → Manual, remembers "off"
        p.announce_check.setChecked(True)           # operator switches it on
        p.advance_check.click()                     # → Auto
        self.assertTrue(p.announce_check.isChecked(),
                        "Auto overwrote a setting the operator had just made")

    # ── the switch in a deck's corner ────────────────────────────────────────

    def test_the_deck_corner_switch_leaves_the_panel_alone(self):
        """⏭ Auto / ✋ Manual under a deck answers for THAT deck (see
        tests/gui/test_deck_advance.py), so it must not reach the panel's
        🔈 tick — the other lists are still being announced. The deck's own
        silence is not stored here but applied where it is spoken."""
        p = self.panel(announce=True)
        desk = _Desk(p)
        table = _Table()
        desk._set_deck_advance(table, False)
        self.assertFalse(desk._deck_advance(table))
        self.assertTrue(p.announce_check.isChecked(),
                        "one deck going Manual switched the announcement off "
                        "for the whole evening")
        self.assertTrue(p.advance_check.isChecked())

    # ── what must NOT change ─────────────────────────────────────────────────

    def test_a_play_set_keeps_its_own_announce_value(self):
        """A stored play set carries both switches. Applying one is not a
        click on Auto, so its announce value stands as stored."""
        p = self.panel(announce=True)
        p.apply_play_set(secs=0, advance=False, pause_off=False, announce=True)
        self.assertFalse(p.advance_check.isChecked())
        self.assertTrue(p.announce_check.isChecked(),
                        "applying a play set was treated as a click on Auto")


if __name__ == "__main__":
    unittest.main()
