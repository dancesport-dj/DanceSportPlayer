#!/usr/bin/env python3
"""Tests for the ⏭/✋ auto-advance switch in a deck's badge bar.

Run:  py -m unittest tests.gui.test_advance_corner -v

Auto-advance decides whether a round runs by itself or every title is started
by hand, and it gets flipped between heats — so it sits on every deck and not
only on the play panel. What these tests pin is the button itself: that it
reads a setting instead of holding one, that a click reaches that setting, and
that it lays out in the badge bar without covering the rows.

WHICH setting it reads is one per deck, with the panel's switch as the default
— that is tests/gui/test_deck_advance.py.

It used to float in the bottom-right of the viewport, where it covered the rows
and sat across the middle of the list while scrolling. It now goes into the
same bar as the Σ song counter under the deck, so it covers nothing — which is
what `advance_toggle()` is for: the deck box takes the button and lays it out.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists (see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_corner_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (QApplication, QHBoxLayout,  # noqa: E402
                               QLabel, QWidget)

from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.main_decks import DeckLayoutMixin  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _Setting:
    """The one place the value lives — stands in for the play panel."""

    def __init__(self, on=True):
        self.on = on
        self.on_change = None   # stands for the panel's toggled signal

    def get(self):
        return self.on

    def set(self, value):
        self.on = value
        if self.on_change is not None:
            self.on_change()


class AdvanceCornerTest(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.table = PlaylistTable()
        self.table.resize(500, 300)
        self.addCleanup(reap_widget, self.table)
        self.setting = _Setting()

    def _wire(self, visible=True):
        self.table.set_advance_toggle(self.setting.get, self.setting.set)
        self.table.set_advance_toggle_visible(visible)
        return self.table.advance_toggle()

    def _shown(self, btn):
        # NOT isVisible(): that is False for as long as the top-level window is
        # unmapped, which it always is in an offscreen test — and a deck built
        # on a folded tab is in the same state in the real app.
        return btn.isVisibleTo(btn.parentWidget())

    def test_the_bar_is_empty_until_a_deck_is_told_what_it_switches(self):
        btn = self.table.advance_toggle()
        self.assertFalse(self._shown(btn))
        # Asking for it without a setting behind it changes nothing.
        self.table.set_advance_toggle_visible(True)
        self.assertFalse(self._shown(btn))

    def test_it_reads_the_setting_rather_than_a_copy_of_it(self):
        btn = self._wire()
        self.assertTrue(self._shown(btn))
        self.assertIn("Auto", btn.text())

        self.setting.on = False
        self.table.refresh_advance_toggle()
        self.assertIn("Manual", btn.text())

    def test_a_click_flips_the_setting_itself(self):
        """The deck writes to the setting and then waits to be told — exactly
        the round trip the real app makes through the panel's toggled signal."""
        btn = self._wire()
        self.setting.on_change = self.table.refresh_advance_toggle
        btn.click()
        self.assertFalse(self.setting.on, "the click never reached the setting")
        self.assertIn("Manual", btn.text())

    def test_it_never_floats_over_the_rows(self):
        """The whole reason it moved: as a child of the viewport it lay on top
        of the playlist, and a scroll left it sitting across the middle of it."""
        btn = self._wire()
        self.assertIsNot(btn.parentWidget(), self.table.viewport())

    def test_the_deck_box_can_take_it_into_its_own_badge_bar(self):
        """What the Σ bar does: ask for the button and lay it out. It keeps
        working afterwards — it is the same button, only somewhere else."""
        btn = self._wire()
        bar = QWidget()
        self.addCleanup(reap_widget, bar)
        row = QHBoxLayout(bar)
        row.addWidget(QLabel("▸  Σ  12 songs"))
        row.addStretch(1)
        row.addWidget(btn)

        self.assertIs(btn.parentWidget(), bar)
        self.assertTrue(self._shown(btn))
        self.setting.on_change = self.table.refresh_advance_toggle
        btn.click()
        self.assertFalse(self.setting.on, "the click never reached the setting")
        self.assertIn("Manual", btn.text())

    def _real_bar(self, badge_visible=True):
        """The arrangement `_make_deck_box` builds: the badge takes the width,
        the switch is added after it right-aligned. Built here rather than
        called, because the real builder needs a whole MainWindow — so this
        pins what the arrangement *does*, not that production still uses it."""
        btn = self._wire()
        bar = QWidget()
        self.addCleanup(reap_widget, bar)
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        badge = QLabel("▸  Σ  12 songs · 00:42")
        badge.setVisible(badge_visible)
        row.addWidget(badge, 1)
        row.addWidget(btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        bar.resize(400, 30)
        bar.show()
        self.app.processEvents()
        row.activate()
        return badge, btn, bar, row

    def test_the_counter_fills_the_bar_up_to_the_switch(self):
        """What Marcel asked for: the highlight runs the length of the bar
        instead of stopping after the text with a stripe of bare background
        between it and the switch. Measured as the gap, because at a wide
        enough text the badge is large either way — a spacer shows up as a gap
        of 56px where the layout's own spacing is 6."""
        badge, btn, bar, row = self._real_bar()
        self.assertEqual(btn.x() - (badge.x() + badge.width()), row.spacing(),
                         "bare background between the counter and the switch")
        self.assertEqual(btn.x() + btn.width(), bar.width(),
                         "the switch is not on the right edge")

    def test_the_switch_keeps_the_right_edge_while_the_badge_is_hidden(self):
        """An empty deck holds the Σ badge hidden. Without the right-align the
        switch takes the whole empty row and slides to the left edge."""
        _badge, btn, bar, _row = self._real_bar(badge_visible=False)
        self.assertEqual(btn.x() + btn.width(), bar.width())
        self.assertGreater(btn.x(), 0, "the switch slid to the left edge")

    def test_resizing_the_deck_no_longer_moves_it(self):
        """It is laid out by whoever owns the bar now, so the table must not
        reach in and place it — that is what put it over the rows."""
        btn = self._wire()
        bar = QWidget()
        self.addCleanup(reap_widget, bar)
        row = QHBoxLayout(bar)
        row.addWidget(btn)
        bar.resize(400, 30)
        where = btn.pos()

        self.table.resize(700, 480)
        self.assertEqual(btn.pos(), where)

    def test_leaving_playing_mode_takes_it_away(self):
        btn = self._wire()
        self.table.set_advance_toggle_visible(False)
        self.assertFalse(self._shown(btn))


class _Table:
    """Only what _refresh_advance_toggles touches."""

    def __init__(self):
        self.refreshed = 0
        self._play_vals = None

    def refresh_advance_toggle(self):
        self.refreshed += 1


class _Panel:
    """The play panel as far as the repaint reaches: what the tick says."""

    def auto_advance(self) -> bool:
        return True


class _Window(PlayerControlMixin):

    deck = DeckLayoutMixin.deck

    def __init__(self, tables=()):
        self._play_panel = _Panel()
        self._deck_of = {}
        if tables:
            self._all_tables = tables


class AdvanceRepaintTest(unittest.TestCase):
    """Whatever moved the setting, every corner has to be repainted from it."""

    def test_every_deck_is_repainted_after_a_flip(self):
        tables = (_Table(), _Table(), _Table())
        _Window(tables)._refresh_advance_toggles()
        self.assertEqual([t.refreshed for t in tables], [1, 1, 1])

    def test_a_flip_before_the_decks_exist_is_harmless(self):
        """A play set applied during start-up flips auto-advance while the
        panel is built and the decks are not."""
        _Window()._refresh_advance_toggles()     # must not raise


if __name__ == "__main__":
    unittest.main()
