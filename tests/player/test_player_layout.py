"""Tests for ▤ where the master player is docked — at the head of the ▶ panel
on the left, or as one wide strip above the decks."""
import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication, state files into a temp dir (the gui
# modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_playerpos_"))

from PySide6.QtCore import QPoint          # noqa: E402
from shared.stores import player_layout_of  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_BLOCKS = ("_head_box", "_time_box", "_slider", "_btn_box", "_aux_box",
           "_vol_box", "_tempo_box")


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class PlayerLayoutSettingTest(unittest.TestCase):

    def test_anything_unrecognised_reads_as_the_panel(self):
        """A settings file written before the option existed simply keeps the
        player where it has always been."""
        self.assertEqual(player_layout_of({}), "panel")
        self.assertEqual(player_layout_of({"player_layout": "sideways"}),
                         "panel")
        self.assertEqual(player_layout_of({"player_layout": "wide"}), "wide")


class WideCardTest(unittest.TestCase):
    """The card itself, laid out along the width."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _card(self):
        from PySide6.QtMultimedia import QMediaPlayer
        from player.player import BigPlayerWidget
        card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, card)
        card.show()
        self.app.processEvents()
        return card

    def test_wide_is_the_same_card_lying_down(self):
        """Every block is still there and still shown — only the shape changes:
        a strip that fits over a playlist, not a column beside it."""
        card = self._card()
        tall = card.sizeHint()
        card.set_wide(True)
        self.app.processEvents()
        wide = card.sizeHint()
        # Not quite half the height — but nothing like a column, and far
        # wider than it is deep.
        self.assertLess(wide.height(), tall.height() * 0.6)
        self.assertGreater(wide.width(), tall.width() * 2)
        for name in _BLOCKS:
            block = getattr(card, name)
            self.assertIsNotNone(block.parent(), name)
            if name != "_aux_box":   # …only shown while a song plays
                self.assertTrue(block.isVisible(), name)

    def test_the_player_hugs_the_left_and_the_settings_the_right(self):
        """What is watched and hit while a song runs — the title, the clock,
        the transport, the seek bar — stands together at the left edge; the
        faders and switches that are dialled in between songs sit at the
        right. Neither half is stretched to fill the monitor."""
        card = self._card()
        card.set_wide(True)
        card.resize(1200, card.sizeHint().height())
        self.app.processEvents()
        mid = card.width() / 2
        for name in ("_head_box", "_time_box", "_btn_box", "_slider"):
            block = getattr(card, name)
            self.assertLess(block.x(), mid, name)
        for name in ("_vol_box", "_tempo_box"):   # _aux_box hides when empty
            block = getattr(card, name)
            self.assertGreater(block.x(), mid, name)
            self.assertGreater(block.x() + block.width(), card.width() - 30,
                               name)
        # The play button belongs beside the clock it drives — a widening card
        # must not push it off towards the middle.
        gap = card._btn_box.x() - (card._time_box.x() + card._time_box.width())
        self.assertLess(gap, 40)
        self.assertGreater(card._slider.y(), card._head_box.y())

    def test_it_goes_back_exactly_as_it_stood(self):
        """The operator may try the strip and change their mind."""
        card = self._card()
        before = card.sizeHint()
        for _ in range(2):
            card.set_wide(True)
            card.set_wide(False)
        self.app.processEvents()
        self.assertEqual(card.sizeHint(), before)
        self.assertFalse(card.is_wide())
        for name in _BLOCKS:
            self.assertIsNotNone(getattr(card, name).parent(), name)


class WidePanelTest(unittest.TestCase):
    """The ▶ Playing panel, dealt into columns to ride in the strip."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _panel(self, **settings):
        from player.play_mode_panel import PlayModePanel
        panel = PlayModePanel(dict(settings))
        self.addCleanup(reap_widget, panel)
        panel.show()
        self.app.processEvents()
        return panel

    def test_the_groups_go_side_by_side(self):
        """Down a column the panel is 900 px of settings; across the strip it
        is a few lines and a fraction of that height — which is the whole
        point, height being what the decks are short of."""
        panel = self._panel()
        tall = panel.sizeHint()
        panel.set_wide(True)
        panel.resize(2200, 200)
        self.app.processEvents()
        deep = panel._body.layout().heightForWidth(2200)
        self.assertLess(deep, tall.height() / 3)
        # Groups that stood one under the other now share a line.
        first = panel.fade_spin.mapTo(panel, QPoint(0, 0))
        later = panel.pd_check.mapTo(panel, QPoint(0, 0))
        self.assertGreater(later.x(), first.x())
        self.assertLess(abs(later.y() - first.y()), 40)

    def test_no_row_is_laid_wider_than_the_strip(self):
        """A row that asks for more width than the strip has used to be drawn
        at its full width anyway — off the right edge, its last control cut in
        half. The line stops at the edge whatever it wants."""
        panel = self._panel()
        panel.set_wide(True)
        panel.resize(700, 400)
        self.app.processEvents()
        flow = panel._body.layout()
        for i in range(flow.count()):
            item = flow.itemAt(i)
            if item.isEmpty():
                continue
            self.assertLessEqual(item.geometry().right(), 700)

    def test_a_wider_strip_takes_fewer_lines(self):
        """No column plan survives contact with the window: what fits on one
        line at a desk monitor is two on a laptop. The flow finds its own
        breaks, so the strip is only ever as deep as the width forces."""
        panel = self._panel()
        panel.set_wide(True)
        self.app.processEvents()
        flow = panel._body.layout()
        self.assertLess(flow.heightForWidth(2000), flow.heightForWidth(1000))

    def test_the_sub_groups_lie_down_with_the_panel(self):
        """The Paso Doble block is four rows deep in the column. Left standing
        it would set the depth of the whole strip on its own."""
        panel = self._panel()
        panel.pd_check.setChecked(True)
        panel.set_wide(True)
        panel.resize(1400, 200)
        self.app.processEvents()
        box = panel.pd_sub_box
        self.assertLess(box.sizeHint().height(), 40)
        self.assertGreater(box.sizeHint().width(), 300)

    def test_the_strip_is_dark_like_the_player(self):
        """A pale board bolted to the side of a black deck reads as two
        devices. In the strip the panel wears the player's own chrome — and
        gives it back at the door when it goes down the side again."""
        panel = self._panel()
        self.assertEqual(panel.styleSheet(), "")
        self.assertIsNone(panel.awake_check._ink)
        panel.set_wide(True)
        self.app.processEvents()
        self.assertIn("#PlayModePanel { background:transparent; }",
                      panel.styleSheet())
        # The pill paints its own caption — a style sheet never reaches it.
        self.assertIsNotNone(panel.awake_check._ink)
        panel.set_wide(False)
        self.app.processEvents()
        self.assertEqual(panel.styleSheet(), "")
        self.assertIsNone(panel.awake_check._ink)

    def test_the_strip_does_not_say_it_twice(self):
        """The heading names a mode the strip announces itself, and the panel's
        countdown is the player's own clock a hand's width to the left."""
        panel = self._panel()
        for w in (panel._title_row, panel.countdown_lbl):
            self.assertTrue(w.isVisibleTo(panel), w)
        panel.set_wide(True)
        for w in (panel._title_row, panel.countdown_lbl):
            self.assertFalse(w.isVisibleTo(panel), w)
        panel.set_wide(False)
        for w in (panel._title_row, panel.countdown_lbl):
            self.assertTrue(w.isVisibleTo(panel), w)

    def test_the_heading_stays_behind_in_the_strip(self):
        """"▶ Playing mode" over a panel that IS the mode says something; over
        a strip that fills the top of the window it is a row of wasted height."""
        panel = self._panel()
        title = panel._title_row
        self.assertTrue(title.isVisibleTo(panel))
        panel.set_wide(True)
        self.assertFalse(title.isVisibleTo(panel))
        panel.set_wide(False)
        self.assertTrue(title.isVisibleTo(panel))

    def test_nothing_is_lost_on_the_way_over_and_back(self):
        """The panel is re-dealt, never rebuilt — every control keeps its
        place in the window and its wiring."""
        panel = self._panel(fade_secs=4.5)
        seen = []
        panel.settingsChanged.connect(lambda: seen.append(panel.fade_secs()))
        for _ in range(2):
            panel.set_wide(True)
            panel.set_wide(False)
        self.app.processEvents()
        self.assertEqual(panel.fade_secs(), 4.5)
        for w in (panel.len_plus, panel.fade_spin, panel.pd_check,
                  panel.advance_check, panel.announce_check,
                  panel.loudness_check, panel.tournament_btn,
                  panel.presenter_btn, panel.awake_check,
                  panel.countdown_lbl):
            self.assertTrue(w.isVisibleTo(panel), w)
        panel.fade_spin.setValue(2.0)
        self.assertEqual(seen, [2.0])


class StripDepthTest(unittest.TestCase):
    """How deep the strip says it is — which is a question about its width.

    The rows wrap, so the depth is a function of the width. The panel used to
    answer with one number: the depth at its own preferred width, right there
    and wrong everywhere else. Narrower than that it is short by a line, and
    the last line of switches is cut off — which is what a Mac does at any
    width, its fallback for a missing Consolas being wider than the PC font
    the number was measured on.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _panel(self, wide=True):
        from player.play_mode_panel import PlayModePanel
        panel = PlayModePanel({"pause_secs": 15, "auto_advance": True})
        self.addCleanup(reap_widget, panel)
        panel.show()
        panel.set_wide(wide)
        self.app.processEvents()
        return panel

    def _at(self, panel, width):
        panel.resize(width, 200)
        self.app.processEvents()
        return panel

    def test_the_depth_it_reports_follows_the_width_it_is_given(self):
        panel = self._panel()
        deep = self._at(panel, 600).sizeHint().height()
        shallow = self._at(panel, 2000).sizeHint().height()
        self.assertGreater(deep, shallow)

    def test_the_hint_is_the_depth_the_rows_really_need(self):
        for width in (2000, 1400, 900, 600):
            with self.subTest(strip=width):
                panel = self._at(self._panel(), width)
                self.assertEqual(panel.sizeHint().height(),
                                 panel.heightForWidth(width))

    def test_it_tells_a_container_that_asks_the_policy(self):
        """A layout reads it off the widget's own layout, but a splitter or a
        scroll area asks the size policy — and was told 'fixed depth'."""
        panel = self._panel()
        self.assertTrue(panel.sizePolicy().hasHeightForWidth())

    def test_down_the_side_the_depth_is_its_own_business(self):
        """In the column the panel is a stack of rows that scrolls; nothing
        there wraps, and the hint must stay the plain one."""
        panel = self._panel(wide=False)
        self.assertFalse(panel.sizePolicy().hasHeightForWidth())
        tall = panel.sizeHint().height()
        self.assertEqual(self._at(panel, 300).sizeHint().height(), tall)

    def test_no_row_falls_below_the_depth_it_asked_for(self):
        panel = self._panel()
        for width in (1800, 1100, 700):
            with self.subTest(strip=width):
                self._at(panel, width)
                panel.resize(width, panel.sizeHint().height())
                self.app.processEvents()
                flow = panel._body.layout()
                rows = [flow.itemAt(i) for i in range(flow.count())]
                bottom = max(r.geometry().bottom()
                             for r in rows if not r.isEmpty())
                self.assertLessEqual(bottom, panel.height())


class DockedPlayerTest(unittest.TestCase):
    """…and where the window puts it."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        cls._qs_dir = tempfile.mkdtemp(prefix="dp_playerpos_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = _app()
        cls.gui = stub_window_startup(cls)

    def _win(self):
        win = self.gui.MainWindow()
        win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        return win

    def test_the_wide_player_stands_over_the_decks(self):
        win = self._win()
        if not win._big_player:
            self.skipTest("no multimedia backend in this environment")
        win._settings["player_layout"] = "wide"
        win._apply_player_layout()
        self.app.processEvents()
        self.assertTrue(win._big_player.is_wide())
        # Under the toolbar, above the deck area — in the right column, not
        # in the left panel any more.
        self.assertLess(win._right_col.indexOf(win._big_player),
                        win._right_col.indexOf(win._right_split))
        self.assertGreater(win._right_col.indexOf(win._big_player), 0)

    def test_it_is_the_same_card_that_moves(self):
        """Moved, never rebuilt: a card built fresh would drop the running
        title, the tempo the operator dialled in and the fade in progress."""
        win = self._win()
        if not win._big_player:
            self.skipTest("no multimedia backend in this environment")
        card = win._big_player
        win._settings["player_layout"] = "wide"
        win._apply_player_layout()
        win._settings["player_layout"] = "panel"
        win._apply_player_layout()
        self.app.processEvents()
        self.assertIs(win._big_player, card)
        self.assertFalse(card.is_wide())

    def test_over_the_decks_it_comes_and_goes_with_the_mode(self):
        """Planning mode has its own player — the mini overlay over the deck.
        The strip would stand there showing the same thing twice."""
        win = self._win()
        if not win._big_player:
            self.skipTest("no multimedia backend in this environment")
        win._settings["player_layout"] = "wide"
        win._apply_player_layout()
        win._set_play_mode(True)
        self.assertFalse(win._big_player.isHidden())
        win._set_play_mode(False)
        self.assertTrue(win._big_player.isHidden())
        # …while in the panel it is the panel that comes and goes, not the card.
        win._settings["player_layout"] = "panel"
        win._apply_player_layout()
        self.assertFalse(win._big_player.isHidden())


class StripHoldsTheModeTest(unittest.TestCase):
    """Wide, the strip is the whole of Playing mode: the panel rides in it and
    the left column steps aside."""

    @classmethod
    def setUpClass(cls):
        DockedPlayerTest.setUpClass.__func__(cls)

    def _playing(self):
        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        if not win._big_player:
            self.skipTest("no multimedia backend in this environment")
        win._settings["player_layout"] = "wide"
        win._apply_player_layout()
        win._set_play_mode(True)
        self.app.processEvents()
        return win

    def test_the_panel_rides_in_the_strip_and_the_column_goes(self):
        win = self._playing()
        self.assertTrue(win._big_player.isAncestorOf(win._play_panel))
        self.assertTrue(win._play_panel.is_wide())
        self.assertTrue(win._left_box.isHidden())
        # …and the mode switch goes with it, or there would be no way back.
        self.assertTrue(win._big_player.isAncestorOf(win._mode_row_w))
        self.assertFalse(win._mode_row_w.isHidden())

    def test_the_panel_takes_the_right_end_of_the_strip(self):
        """A pale board with dark on both sides is a hole in the middle of the
        strip. The card closes up on the left — player, then its own faders —
        and the panel runs from there to the right edge."""
        win = self._playing()
        card = win._big_player
        win.show()
        self.addCleanup(win.hide)
        win.resize(1900, 900)
        self.app.processEvents()
        panel = win._play_panel
        left = panel.mapTo(card, panel.pos()).x()
        for name in ("_time_box", "_btn_box", "_vol_box", "_tempo_box"):
            block = getattr(card, name)
            self.assertLess(block.x() + block.width(), left, name)
        self.assertGreater(left + panel.width(), card.width() - 30)

    def test_the_switch_sits_in_the_bottom_right_corner(self):
        """Beside the transport the switch was 240 px of the player's own
        column — and that column decides how much width is left for the mode
        panel, which paid for it a whole line deep. The corner is space the
        strip has anyway."""
        win = self._playing()
        card = win._big_player
        win.show()
        self.addCleanup(win.hide)
        win.resize(1900, 900)
        self.app.processEvents()
        sw = win._mode_row_w
        far = sw.mapTo(card, QPoint(0, 0))
        self.assertGreater(far.x() + sw.width(), card.width() - 30)
        self.assertGreater(far.y() + sw.height(), card.height() - 30)
        # Under the panel, not beside the transport.
        self.assertGreater(far.y(), card._btn_box.y())

    def test_planning_gets_its_column_back(self):
        """Planning mode is the panel's column — the switch has to be in it."""
        win = self._playing()
        win._set_play_mode(False)
        self.app.processEvents()
        self.assertFalse(win._left_box.isHidden())
        self.assertFalse(win._big_player.isAncestorOf(win._mode_row_w))
        self.assertGreaterEqual(win._left_col.indexOf(win._mode_row_w), 0)
        self.assertFalse(win._mode_row_w.isHidden())

    def test_a_player_only_desk_keeps_its_switch_hidden(self):
        """With one side installed there is nothing to switch to — the strip
        must not smuggle the switch back in."""
        win = self._playing()
        win._settings["app_mode"] = "player"
        win._apply_app_mode()
        win._set_play_mode(True)
        self.app.processEvents()
        self.assertFalse(win._mode_row_w.isVisibleTo(win._big_player))

    def test_the_panel_goes_home_when_the_strip_does(self):
        win = self._playing()
        win._settings["player_layout"] = "panel"
        win._apply_player_layout()
        self.app.processEvents()
        self.assertIs(win._play_scroll.widget(), win._play_panel)
        self.assertFalse(win._play_panel.is_wide())
        self.assertTrue(win._play_panel.isAncestorOf(win._big_player))
        self.assertFalse(win._left_box.isHidden())


if __name__ == "__main__":
    unittest.main()
