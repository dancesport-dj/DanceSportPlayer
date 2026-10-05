#!/usr/bin/env python3
"""🏆 The event plan side by side, and the last word on a slot.

Run:  py -m unittest tests.gui.test_event_compare -v

One tab per competition, the variants as columns, the slots as rows. A slot
offers the replacement "like last year" suggests, the swaps the AI did not
get, and the free titles of each tier; a title that breaks the day goes in
only when Marcel says so. The window asks the main window to ask the AI again
or to load a variant into the day decks.
"""

import os
import tempfile
import types
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_event_compare_"))

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeySequence  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QDialog, QLabel, QMessageBox, QPushButton, QWidget,
)

from gui.event_compare import TIER_NAMES, EventCompareDialog, SlotPicker  # noqa: E402
from planner import event_plan  # noqa: E402
from planner.competition import parse_competition_schedule  # noqa: E402
from tests.planner.test_event_variants import EventFixture  # noqa: E402


class _Host(QWidget):
    """The main window as far as the window sees it: the shared player's play
    callback, and `deck_path()` naming what that player is on."""

    def __init__(self):
        super().__init__()
        self.now = None
        self.calls = []
        self.seeks = []

    def play(self, path):
        self.calls.append(path)
        self.now = path

    def seek(self, delta_ms):
        self.seeks.append(delta_ms)

    def deck_path(self):
        return self.now


class EventCompareTest(EventFixture, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def open(self, schedule="HGR S STD 2-1\nSEN I S STD 1", *, host=None,
             profiles=("like_last_year", "variety"), twins=False, **extra):
        _vr, er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/HGR_S_STD.m3u", "KR")
        if twins:           # a new title that sounds like each of the final's
            for anchor in er:
                new = self.entry(f"New {anchor.dance}", anchor.dance)
                self.sounds_like[new.title] = (new, anchor, 0.9)
        editions = event_plan.past_editions("danceconvention", root=self.root)
        self.cands = [event_plan.gather_candidates(self.lib, s, editions,
                                                   similar=self.similar)
                      for s in parse_competition_schedule(schedule)]
        variants = {p: event_plan.plan_variant(self.cands, p) for p in profiles}
        self.result = event_plan.RefineResult(variants, **extra)
        dlg = EventCompareDialog(self.result, self.cands, host,
                                 play_cb=host.play if host else None,
                                 seek_cb=host.seek if host else None)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_a_tab_per_competition_a_column_per_variant(self):
        dlg = self.open()
        self.assertEqual(dlg._tabs.count(), 2)
        table = dlg._tables[0]
        self.assertEqual(table.columnCount(), 2)
        self.assertEqual(table.rowCount(), 3 * 5)
        self.assertEqual(table.verticalHeaderItem(0).text()[-2:], "LW")

    def test_a_round_of_heats_runs_dance_by_dance(self):
        """Like the playlist: both heats' Slow Waltz, then both Tangos — not
        every dance of heat 1 before heat 2."""
        dlg = self.open()
        heads = [dlg._tables[0].verticalHeaderItem(r).text() for r in range(4)]
        self.assertEqual([h[-2:] for h in heads], ["LW", "LW", "TG", "TG"])
        self.assertEqual([dlg._slots[0][r] for r in range(4)],
                         [(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1)])

    def test_jack_and_jill_keeps_its_ampersand(self):
        """Qt reads '&' in a tab text as a shortcut marker: 'J&J' showed 'J J'."""
        dlg = self.open("HGR S STD 2-1\nJ&J (LW; CC) 1")
        self.assertTrue(dlg._tabs.tabText(1).endswith(" J&&J"))

    def test_a_competition_the_event_never_had_says_so(self):
        """Marcel: Jug A showed 'like last year' titles, though DanceConvention
        2025 had no Jug A STD. Without a list of its own at the event, the tab
        and the note under the table say the class lists stand in."""
        dlg = self.open()                   # SEN I S STD: no list at DC
        notes = lambda i: dlg._tabs.widget(i).findChild(QLabel).text()  # noqa: E731
        self.assertTrue(dlg._tabs.tabText(1).startswith("∅ "))
        self.assertIn("no list of this competition", notes(1))
        self.assertIn("class lists", notes(1))
        self.assertFalse(dlg._tabs.tabText(0).startswith("∅ "))
        self.assertNotIn("no list of this competition", notes(0))

    def test_without_a_list_of_its_own_the_reference_is_like_similar_competitions(self):
        """Marcel: if there is no list from last year, label it like similar
        competitions — the class lists fill it."""
        dlg = self.open()                   # SEN I S STD: no list at DC
        head = lambda i: dlg._tables[i].horizontalHeaderItem(0).text()  # noqa: E731
        self.assertEqual(head(1), "✔ Like similar competitions")
        self.assertEqual(head(0), "✔ Like last year")
        self.assertEqual(dlg._tables[1].horizontalHeaderItem(1).text(), "Variety")

    def test_the_tab_of_a_competition_the_event_never_had_is_orange(self):
        """Marcel: the ∅ alone is too inconspicuous, make the tab orange too."""
        dlg = self.open()                   # SEN I S STD: no list at DC
        bar = dlg._tabs.tabBar()
        bar.resize(bar.sizeHint())
        image = bar.grab().toImage()
        orange = lambda k: (lambda c: c.red() > 200 and c.blue() < 150)(  # noqa: E731
            image.pixelColor(bar.tabRect(k).center().x(), bar.tabRect(k).bottom() - 2))
        self.assertTrue(orange(1))
        self.assertFalse(orange(0))

    def test_the_window_opens_wide_enough_for_every_variant(self):
        """Marcel: the default width must show all 4 tables."""
        dlg = self.open(profiles=event_plan.PROFILE_ORDER)
        screen = dlg.screen().availableGeometry().width()
        self.assertEqual(dlg.width(), min(max(dlg.fit_width(), 1100), screen))
        dlg.resize(dlg.fit_width(), 720)
        dlg.show()
        QApplication.processEvents()
        self.assertEqual(dlg._tables[0].horizontalScrollBar().maximum(), 0)

    RENEWED = ("like_last_year", "last_year_renewed")

    def test_renewed_colours_the_titles_it_changed(self):
        """Marcel: mark in 'last year, renewed' what changed."""
        dlg = self.open(profiles=self.RENEWED, twins=True)
        table = dlg._tables[0]
        changed = [r for r in range(15) if table.item(r, 1).background().style()
                   != Qt.BrushStyle.NoBrush]
        swapped = [r for r in range(15) if table.item(r, 1).text().endswith("↺")]
        self.assertTrue(swapped)
        self.assertEqual(changed, swapped)
        self.assertEqual([r for r in range(15) if table.item(r, 0).background().style()
                          != Qt.BrushStyle.NoBrush], [])

    def test_a_title_chosen_in_renewed_is_coloured_too(self):
        dlg = self.open(profiles=self.RENEWED, twins=True)
        table = dlg._tables[0]
        row = next(r for r in range(15) if not table.item(r, 1).text().endswith("↺"))
        key = (0, *dlg._slots[0][row])
        comps = self.result.variants["last_year_renewed"]
        pick = next(p for group, _text, p in dlg.slot_choices(0, row, 1)
                    if group and not event_plan.slot_conflict(comps, key, p))
        with mock.patch("gui.event_compare.QMessageBox") as box:
            box.StandardButton = QMessageBox.StandardButton
            box.question.return_value = QMessageBox.StandardButton.Yes
            self.assertTrue(dlg.choose(0, row, 1, pick))
        self.assertNotEqual(table.item(row, 1).background().style(), Qt.BrushStyle.NoBrush)

    def test_renewed_without_a_change_is_not_shown_twice(self):
        """Marcel: at the first test both were 1:1 the same — where nothing
        could be replaced, don't show the column twice."""
        dlg = self.open(profiles=self.RENEWED, twins=True)
        notes = lambda i: dlg._tabs.widget(i).findChild(QLabel).text()  # noqa: E731
        self.assertFalse(dlg._tables[0].isColumnHidden(1))
        self.assertTrue(dlg._tables[1].isColumnHidden(1))     # SEN I S: no list
        self.assertIn("the same as 'Like last year'", notes(1))
        self.assertNotIn("the same as 'Like last year'", notes(0))

    def test_a_cell_shows_where_its_title_comes_from(self):
        dlg = self.open()
        text = dlg._tables[0].item(14, 0).text()        # the final's Quickstep
        self.assertTrue(text.startswith("🟦 DC ER QS"))
        self.assertIn("DanceConvention 2025", dlg._tables[0].item(14, 0).toolTip())

    def test_the_tooltip_also_tells_what_a_playlist_row_tells(self):
        """Marcel: on the tooltip with info where it comes from I want also
        the infos the tooltip in a normal playlist shows."""
        dlg = self.open()
        key = (0, *dlg._slots[0][14])
        entry = event_plan.slot_pick(self.result.variants["like_last_year"], key).entry
        entry.popularity = 3
        entry.class_plays = {"S": 2, "C": 1}
        dlg.set_result(self.result, self.cands)
        tip = dlg._tables[0].item(14, 0).toolTip()
        self.assertIn("DanceConvention 2025", tip)
        self.assertIn("In 3 of your playlists", tip)
        self.assertIn("Played in: S×2 · C×1", tip)
        self.assertIn(str(entry.path), tip)
        self.assertLess(tip.index("DanceConvention 2025"), tip.index("In 3 of your"))

    def test_a_title_in_the_tooltip_is_text_not_markup(self):
        dlg = self.open()
        key = (0, *dlg._slots[0][14])
        comps = self.result.variants["like_last_year"]
        pick = event_plan.slot_pick(comps, key)
        comps[0].grid[comps[0].rounds[key[1]].name][key[2]][key[3]] = replace(
            pick, source="Jack & Jill <2025>")
        dlg.set_result(self.result, self.cands)
        self.assertIn("Jack &amp; Jill &lt;2025&gt;", dlg._tables[0].item(14, 0).toolTip())

    def test_a_later_heat_says_what_it_sounds_like_in_the_first(self):
        dlg = self.open()
        key = (0, *dlg._slots[0][1])                     # Vorrunde heat 2, LW
        comps = self.result.variants["variety"]
        pick = event_plan.slot_pick(comps, key)
        comps[0].grid[comps[0].rounds[key[1]].name][key[2]][key[3]] = replace(
            pick, like_heat="sounds like 'DC VR1 LW' of the first heat (timbre top 5 %)")
        dlg.set_result(self.result, self.cands)
        self.assertIn("≈ sounds like 'DC VR1 LW' of the first heat",
                      dlg._tables[0].item(1, 1).toolTip())

    def test_like_last_year_offers_but_puts_nothing_in(self):
        dlg = self.open(twins=True)
        texts = [dlg._tables[0].item(r, 0).text() for r in range(15)]
        self.assertTrue([t for t in texts if t.endswith("↻")])
        self.assertEqual([t for t in texts if "↺" in t], [])

    def test_renewed_shows_its_suggestion(self):
        dlg = self.open(profiles=("last_year_renewed", "variety"))
        rows = [r for r in range(15) if dlg._tables[0].item(r, 0).text().endswith("↻")]
        self.assertTrue(rows)
        self.assertIn("↻", dlg._tables[0].item(rows[0], 0).toolTip())
        group, _text, pick = dlg.slot_choices(0, rows[0], 0)[0]
        self.assertEqual(group, "")
        key = (0, *dlg._slots[0][rows[0]])
        comps = self.result.variants["last_year_renewed"]
        self.assertIs(pick, event_plan.slot_pick(comps, key).suggestion)

    def test_a_swapped_slot_names_last_years_title_and_goes_back(self):
        dlg = self.open(profiles=("last_year_renewed", "variety"), twins=True)
        table = dlg._tables[0]
        row = next(r for r in range(15) if table.item(r, 0).text().endswith("↺"))
        key = (0, *dlg._slots[0][row])
        last_year = event_plan.slot_pick(
            self.result.variants["last_year_renewed"], key).replaces
        self.assertIn("↺ Replaces '%s' of last year" % last_year.entry.title,
                      table.item(row, 0).toolTip())
        group, text, pick = dlg.slot_choices(0, row, 0)[0]
        self.assertEqual((group, pick), ("", last_year))
        self.assertIn(last_year.entry.title, text)
        self.assertTrue(dlg.choose(0, row, 0, pick))
        self.assertTrue(table.item(row, 0).text().startswith(
            "🟦 " + last_year.entry.title))

    def test_a_suggestion_taken_goes_in(self):
        dlg = self.open(profiles=("last_year_renewed", "variety"))
        row = next(r for r in range(15) if dlg._tables[0].item(r, 0).text().endswith("↻"))
        _group, _text, pick = dlg.slot_choices(0, row, 0)[0]
        self.assertTrue(dlg.choose(0, row, 0, pick))
        self.assertIn(pick.entry.title, dlg._tables[0].item(row, 0).text())
        self.assertFalse(dlg._tables[0].item(row, 0).text().endswith("↻"))

    def test_the_swaps_the_ai_did_not_get_are_offered(self):
        dlg = self.open()
        comps = self.result.variants["variety"]
        alt = dlg.slot_choices(0, 0, 1)[-1][2]
        comps[0].refused.append(event_plan.RefusedSwap(
            comps[0].rounds[0].name, 0, 0, alt, "already plays that day"))
        dlg.set_result(self.result, self.cands)
        self.assertIn("✋1", dlg._tables[0].item(0, 1).text())
        group, text, pick = dlg.slot_choices(0, 0, 1)[0]
        self.assertEqual((group, pick), ("", alt))
        self.assertIn("already plays that day", text)

    def test_the_tiers_come_after(self):
        dlg = self.open()
        groups = [g for g, _t, _p in dlg.slot_choices(0, 0, 1)]
        self.assertTrue(set(groups) <= {"event", "class", "new", "rare", "library"})
        self.assertTrue(groups)

    def test_a_rarely_played_title_has_its_badge(self):
        for n in range(3):
            self.entry(f"Rare {n} LW", "LW", s_plays=1, months_ago=60)
        dlg = self.open()
        rare = next(p for g, _t, p in dlg.slot_choices(0, 0, 1) if g == "rare")
        self.assertTrue(dlg.choose(0, 0, 1, rare))
        cell = dlg._tables[0].item(0, 1)
        self.assertTrue(cell.text().startswith("🟧 Rare"))
        self.assertIn("Rarely played", cell.toolTip())
        self.assertIn("played 1× at the class", cell.toolTip())

    def test_a_title_that_breaks_the_day_needs_a_yes(self):
        dlg = self.open()
        comps = self.result.variants["variety"]
        other = event_plan.slot_pick(comps, (0, 0, 1, 0))     # VR heat 2, LW
        before = dlg._tables[0].item(0, 1).text()
        with mock.patch("gui.event_compare.QMessageBox") as box:
            box.StandardButton = QMessageBox.StandardButton
            box.question.return_value = QMessageBox.StandardButton.No
            self.assertFalse(dlg.choose(0, 0, 1, other))
            self.assertIn("already plays that day", box.question.call_args.args[2])
            self.assertEqual(dlg._tables[0].item(0, 1).text(), before)
            box.question.return_value = QMessageBox.StandardButton.Yes
            self.assertTrue(dlg.choose(0, 0, 1, other))
        self.assertIs(event_plan.slot_pick(comps, (0, 0, 0, 0)).entry, other.entry)

    def test_ask_again_buttons_only_when_there_is_something_to_ask(self):
        dlg = self.open()
        self.assertTrue(dlg._later_btn.isHidden())
        self.assertTrue(dlg._second_btn.isHidden())

    def test_the_held_back_are_asked_again(self):
        dlg = self.open(pending=[1], limit="usage limit reached", second_round=[0])
        self.assertFalse(dlg._later_btn.isHidden())
        self.assertEqual(dlg._tabs.tabText(1)[:1], "⏳")
        self.assertIn("usage limit reached", dlg._status.text())
        asked = []
        dlg.continueRequested.connect(asked.append)
        dlg._later_btn.click()
        dlg._second_btn.click()
        self.assertEqual(asked, [[1], [0]])

    def test_while_the_ai_is_asked_nothing_is_edited(self):
        dlg = self.open(pending=[1])
        dlg.set_busy(True)
        self.assertFalse(dlg._later_btn.isEnabled())
        self.assertFalse(dlg._apply_btn.isEnabled())
        asked = []
        dlg.continueRequested.connect(asked.append)
        dlg._ask_again([1])
        self.assertEqual(asked, [])

    def test_each_competition_goes_to_the_day_decks_as_its_tab_chose(self):
        """Marcel: choose the variant per tab, then copy everything into the decks."""
        dlg = self.open()
        taken = []
        dlg.applyRequested.connect(taken.append)
        dlg._tabs.setCurrentIndex(0)
        dlg._variant.setCurrentIndex(1)
        dlg._tabs.setCurrentIndex(1)
        self.assertEqual(dlg._variant.currentData(), "like_last_year")
        dlg._tabs.setCurrentIndex(0)
        self.assertEqual(dlg._variant.currentData(), "variety")
        dlg._apply_btn.click()
        self.assertEqual(taken, [["variety", "like_last_year"]])

    def test_the_tabs_variant_is_ticked_in_its_header(self):
        dlg = self.open()
        head = lambda i, col: dlg._tables[i].horizontalHeaderItem(col).text()  # noqa: E731
        dlg._tabs.setCurrentIndex(0)
        dlg._variant.setCurrentIndex(1)
        self.assertEqual([head(0, 0), head(0, 1)], ["Like last year", "✔ Variety"])
        self.assertEqual([head(1, 0), head(1, 1)],
                         ["✔ Like similar competitions", "Variety"])

    # ── prehearing ─────────────────────────────────────────────────────────

    def with_host(self):
        host = _Host()
        self.addCleanup(host.deleteLater)
        return host, self.open(host=host)

    def slot_path(self, dlg, row, col):
        comps = self.result.variants[dlg._profiles[col]]
        return event_plan.slot_pick(comps, (0, *dlg._slots[0][row])).entry.path

    def test_space_prehears_the_chosen_title_and_stops_it(self):
        host, dlg = self.with_host()
        table = dlg._tables[0]
        table.setCurrentCell(14, 1)
        QTest.keyClick(table, Qt.Key.Key_Space)
        self.assertEqual(host.calls, [self.slot_path(dlg, 14, 1)])
        QTest.keyClick(table, Qt.Key.Key_Space)
        self.assertEqual(host.calls[-1], None)

    def test_no_prehear_button_next_to_the_cells_play_icons(self):
        """Marcel: remove the prehear button, the cells have their play icons."""
        host, dlg = self.with_host()
        self.assertEqual([b.text() for b in dlg.findChildren(QPushButton)
                          if "Prehear" in b.text()], [])
        self.assertNotIn("Prehear", dlg._status.text())

    def test_another_title_follows_the_first(self):
        host, dlg = self.with_host()
        table = dlg._tables[0]
        table.setCurrentCell(0, 0)
        QTest.keyClick(table, Qt.Key.Key_Space)
        table.setCurrentCell(1, 0)
        QTest.keyClick(table, Qt.Key.Key_Space)
        self.assertEqual(host.calls, [self.slot_path(dlg, 0, 0),
                                      self.slot_path(dlg, 1, 0)])

    def test_closing_stops_its_own_prehearing(self):
        host, dlg = self.with_host()
        dlg._tables[0].setCurrentCell(0, 0)
        QTest.keyClick(dlg._tables[0], Qt.Key.Key_Space)
        dlg.close()
        self.assertEqual(host.calls[-1], None)

    def test_closing_leaves_a_deck_title_playing(self):
        host, dlg = self.with_host()
        dlg._tables[0].setCurrentCell(0, 0)
        QTest.keyClick(dlg._tables[0], Qt.Key.Key_Space)
        host.now = "the deck's title"          # the operator started a deck
        host.calls.clear()
        dlg.close()
        self.assertEqual(host.calls, [])

    def test_ctrl_click_in_the_menu_prehears_without_choosing(self):
        host, dlg = self.with_host()
        before = dlg._tables[0].item(0, 1).text()
        menu, actions = dlg._slot_menu(0, 0, 1)
        self.addCleanup(menu.deleteLater)
        action, pick = next((a, p) for a, p in actions.items()
                            if a.parent() is not menu)      # in a tier's submenu
        sub = action.parent()
        sub.popup(sub.pos())
        QTest.mouseClick(sub, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.ControlModifier,
                         sub.actionGeometry(action).center())
        self.assertEqual(host.calls, [pick.entry.path])
        self.assertEqual(dlg._tables[0].item(0, 1).text(), before)
        sub.hide()

    # ── the picker: hear first, then choose ───────────────────────────────

    def picker(self, dlg, row=0, col=1):
        picker = dlg.slot_picker(0, row, col)
        self.addCleanup(picker.deleteLater)
        return picker

    def test_the_picker_lists_everything_the_slot_offers(self):
        """Marcel: only names are not good enough, I need to hear them — a
        window on top with the choices, grouped by tier."""
        _host, dlg = self.with_host()
        picker = self.picker(dlg)
        choices = dlg.slot_choices(0, 0, 1)
        self.assertEqual(picker.picks(), [p for _g, _t, p in choices])
        groups = {g for g, _t, _p in choices if g}
        self.assertEqual(picker.headings()[-len(groups):],
                         [TIER_NAMES[g] for g in dict.fromkeys(
                             g for g, _t, _p in choices if g)])
        now = event_plan.slot_pick(self.result.variants["variety"], (0, *dlg._slots[0][0]))
        self.assertIn(now.entry.title, picker.now_text())

    def test_each_title_in_the_picker_plays_and_stops(self):
        host, dlg = self.with_host()
        picker = self.picker(dlg)
        picks = picker.picks()
        picker.play_button(0).click()
        self.assertEqual(host.calls, [picks[0].entry.path])
        self.assertEqual(picker.play_button(0).text(), "■")
        picker.play_button(1).click()
        self.assertEqual(host.calls[-1], picks[1].entry.path)
        self.assertEqual([picker.play_button(k).text() for k in (0, 1)], ["▶", "■"])
        picker.play_button(1).click()
        self.assertEqual(host.calls[-1], None)
        self.assertEqual(picker.play_button(1).text(), "▶")

    def test_the_slots_own_title_plays_in_the_picker_too(self):
        host, dlg = self.with_host()
        picker = self.picker(dlg)
        picker.now_button().click()
        self.assertEqual(host.calls, [self.slot_path(dlg, 0, 1)])

    def test_space_in_the_picker_plays_the_selected_title(self):
        host, dlg = self.with_host()
        picker = self.picker(dlg)
        picker.select(2)
        QTest.keyClick(picker.table(), Qt.Key.Key_Space)
        self.assertEqual(host.calls, [picker.picks()[2].entry.path])

    def test_ctrl_shift_arrows_in_the_picker_skip_a_title(self):
        """Marcel: in the hear and choose dialog a key should skip a title —
        the next one down (or up) is selected and plays. Ctrl+Shift, as the
        player's ⏭/⏮ from the main window."""
        host, dlg = self.with_host()
        picker = self.picker(dlg)
        picks = picker.picks()
        picker.select(1)
        ctrl = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        QTest.keyClick(picker.table(), Qt.Key.Key_Right, ctrl)
        self.assertEqual(host.calls, [picks[2].entry.path])
        self.assertEqual(picker.play_button(2).text(), "■")
        QTest.keyClick(picker.table(), Qt.Key.Key_Left, ctrl)
        QTest.keyClick(picker.table(), Qt.Key.Key_Left, ctrl)
        self.assertEqual(host.calls[1:], [picks[1].entry.path, picks[0].entry.path])
        QTest.keyClick(picker.table(), Qt.Key.Key_Left, ctrl)    # the list's top
        self.assertEqual(len(host.calls), 3)
        self.assertEqual(picker.picks()[picker._selected()], picks[0])

    def test_the_picker_skips_over_its_headings(self):
        host, dlg = self.with_host()
        (_g, a, pa), (_g, b, pb) = dlg.slot_choices(0, 0, 1)[:2]
        picker = SlotPicker(dlg, "slot", None, [("event", a, pa), ("class", b, pb)],
                            host.play)
        self.addCleanup(picker.deleteLater)
        self.assertEqual(picker._rows, [1, 3])
        picker.select(0)
        QTest.keyClick(picker.table(), Qt.Key.Key_Right,
                       Qt.KeyboardModifier.ControlModifier
                       | Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(host.calls, [pb.entry.path])

    def test_ctrl_arrows_in_the_picker_seek(self):
        """Ctrl+←/→ seeks ∓30 s, as everywhere else in the app."""
        host, dlg = self.with_host()
        picker = self.picker(dlg)
        picker.select(1)
        ctrl = Qt.KeyboardModifier.ControlModifier
        QTest.keyClick(picker.table(), Qt.Key.Key_Right, ctrl)
        QTest.keyClick(picker.table(), Qt.Key.Key_Left, ctrl)
        self.assertEqual(host.seeks, [30000, -30000])
        self.assertEqual(host.calls, [])                  # no other title
        self.assertEqual(picker._selected(), 1)

    def test_the_title_taken_in_the_picker_goes_in(self):
        _host, dlg = self.with_host()
        pick = None

        def take(picker):
            nonlocal pick
            pick = picker.picks()[-1]
            picker.select(len(picker.picks()) - 1)
            picker.take()
            return QDialog.DialogCode.Accepted

        dlg.open_picker(0, 0, 1)
        take(dlg.shown_picker())
        self.assertIn(pick.entry.title, dlg._tables[0].item(0, 1).text())
        self.assertIsNone(dlg.shown_picker())

    def test_a_cancelled_picker_changes_nothing(self):
        _host, dlg = self.with_host()
        before = dlg._tables[0].item(0, 1).text()
        dlg.open_picker(0, 0, 1)
        dlg.shown_picker().reject()
        self.assertEqual(dlg._tables[0].item(0, 1).text(), before)
        self.assertIsNone(dlg.shown_picker())

    def test_a_title_dragged_out_of_the_picker_carries_its_file(self):
        """Marcel: "i cant drag music from hear and choose ... to playlist 2".
        A picker row drags its file into a deck as from Explorer."""
        from gui.table_dnd import TableDragDropMixin

        class _Deck(TableDragDropMixin):
            pass

        _host, dlg = self.with_host()
        picker = self.picker(dlg)
        table = picker.table()
        self.assertTrue(table.dragEnabled())
        path = picker.picks()[1].entry.path
        mime = table.row_mime(picker._rows[1])
        self.assertEqual([u.toLocalFile() for u in mime.urls()],
                         [Path(path).as_posix()])
        drop = types.SimpleNamespace(mimeData=lambda: mime)
        with mock.patch.object(Path, "is_file", return_value=True):
            self.assertEqual(_Deck()._droppable_path(drop), Path(path))
        self.assertIsNone(table.row_mime(0))              # a heading

    def test_the_picker_leaves_the_playlists_open_for_a_drop(self):
        """Qt refuses a drop onto a window a modal one blocks — run modal,
        the picker would lock every playlist. It is shown instead."""
        _host, dlg = self.with_host()
        with mock.patch.object(SlotPicker, "exec",
                               side_effect=AssertionError("run modal")):
            dlg.open_picker(0, 0, 1)
        picker = dlg.shown_picker()
        self.addCleanup(picker.close)
        self.assertTrue(picker.isVisible())
        self.assertFalse(picker.isModal())
        self.assertIsNone(QApplication.activeModalWidget())

    def test_one_picker_at_a_time_and_none_over_new_tables(self):
        _host, dlg = self.with_host()
        dlg.open_picker(0, 0, 1)
        first = dlg.shown_picker()
        dlg.open_picker(0, 1, 1)
        self.assertFalse(first.isVisible())
        self.assertIsNot(dlg.shown_picker(), first)
        second = dlg.shown_picker()
        dlg.set_result(self.result, self.cands)           # its slot is gone
        self.assertFalse(second.isVisible())
        self.assertIsNone(dlg.shown_picker())

    def test_a_double_click_and_the_menu_open_the_picker(self):
        _host, dlg = self.with_host()
        with mock.patch.object(dlg, "open_picker") as opened:
            dlg._tables[0].cellDoubleClicked.emit(0, 1)
        opened.assert_called_once_with(0, 0, 1)
        menu, _actions = dlg._slot_menu(0, 0, 1)
        self.addCleanup(menu.deleteLater)
        self.assertEqual(menu.actions()[0], dlg._picker_action)

    def test_without_a_player_the_picker_only_chooses(self):
        dlg = self.open()
        picker = self.picker(dlg)
        self.assertTrue(picker.play_button(0).isHidden())
        self.assertTrue(picker.now_button().isHidden())

    def test_without_a_player_there_is_nothing_to_prehear(self):
        dlg = self.open()
        dlg._tables[0].setCurrentCell(0, 0)
        QTest.keyClick(dlg._tables[0], Qt.Key.Key_Space)      # no crash

    # ── ▶/■ in the cells ──────────────────────────────────────────────────

    def click_cell(self, dlg, row, col, *, on_icon=True, double=False):
        table = dlg._tables[0]
        rect = table.visualRect(table.model().index(row, col))
        point = rect.center()
        if on_icon:
            point.setX(rect.left() + 8)
        click = QTest.mouseDClick if double else QTest.mouseClick
        click(table.viewport(), Qt.MouseButton.LeftButton,
              Qt.KeyboardModifier.NoModifier, point)

    def icon_of(self, dlg, row, col):
        """'play', 'stop' or None — the icon a cell shows."""
        key = dlg._tables[0].item(row, col).icon().cacheKey()
        return {dlg._icons[False].cacheKey(): "play",
                dlg._icons[True].cacheKey(): "stop"}.get(key)

    def test_every_title_has_its_play_icon(self):
        """Marcel: not only Space — play icons in it to press and stop."""
        _host, dlg = self.with_host()
        self.assertEqual({self.icon_of(dlg, r, c) for r in range(15) for c in (0, 1)},
                         {"play"})

    def test_without_a_player_the_cells_have_no_icon(self):
        dlg = self.open()
        self.assertTrue(dlg._tables[0].item(0, 1).icon().isNull())

    def test_the_icon_plays_the_cell_and_stops_it(self):
        host, dlg = self.with_host()
        self.click_cell(dlg, 3, 1)
        self.assertEqual(host.calls, [self.slot_path(dlg, 3, 1)])
        self.assertEqual(self.icon_of(dlg, 3, 1), "stop")
        self.click_cell(dlg, 5, 0)
        self.assertEqual(host.calls[-1], self.slot_path(dlg, 5, 0))
        self.assertEqual([self.icon_of(dlg, 3, 1), self.icon_of(dlg, 5, 0)],
                         ["play", "stop"])
        self.click_cell(dlg, 5, 0)
        self.assertEqual(host.calls[-1], None)
        self.assertEqual(self.icon_of(dlg, 5, 0), "play")

    def test_a_click_on_the_title_only_selects_it(self):
        host, dlg = self.with_host()
        self.click_cell(dlg, 3, 1, on_icon=False)
        self.assertEqual(host.calls, [])
        self.assertEqual((dlg._tables[0].currentRow(), dlg._tables[0].currentColumn()),
                         (3, 1))

    def test_a_double_click_on_the_icon_does_not_open_the_picker(self):
        host, dlg = self.with_host()
        with mock.patch.object(dlg, "open_picker") as opened:
            self.click_cell(dlg, 3, 1)
            self.click_cell(dlg, 3, 1, double=True)
        opened.assert_not_called()
        self.assertEqual(host.calls, [self.slot_path(dlg, 3, 1)])

    def test_space_marks_the_cell_it_plays(self):
        _host, dlg = self.with_host()
        dlg._tables[0].setCurrentCell(2, 0)
        QTest.keyClick(dlg._tables[0], Qt.Key.Key_Space)
        self.assertEqual(self.icon_of(dlg, 2, 0), "stop")

    def test_a_cell_asks_for_the_mini_player(self):
        """…with the mini player coming up: the main window anchors it to
        the row — a title heard from the menu or the picker has no row."""
        _host, dlg = self.with_host()
        seen = []
        dlg.prehearing.connect(lambda table, row, title: seen.append((table, row, title)))
        self.click_cell(dlg, 3, 1)
        self.assertEqual(seen, [(dlg._tables[0], 3, self.slot_path(dlg, 3, 1).stem)])
        dlg.prehear(self.slot_path(dlg, 4, 1))
        self.assertEqual(len(seen), 1)
        self.assertEqual(self.icon_of(dlg, 3, 1), "play")

    def test_another_player_start_clears_the_mark(self):
        _host, dlg = self.with_host()
        self.click_cell(dlg, 3, 1)
        dlg.on_playback_stopped()
        self.assertEqual(self.icon_of(dlg, 3, 1), "play")

    def test_the_mini_players_skip_walks_the_column(self):
        host, dlg = self.with_host()
        self.assertFalse(dlg.skip_prehear(1))
        self.click_cell(dlg, 3, 1)
        self.assertTrue(dlg.skip_prehear(1))
        self.assertEqual(host.calls[-1], self.slot_path(dlg, 4, 1))
        self.assertEqual(self.icon_of(dlg, 4, 1), "stop")
        self.assertTrue(dlg.skip_prehear(-1))
        self.assertEqual(host.calls[-1], self.slot_path(dlg, 3, 1))
        self.click_cell(dlg, 0, 1)
        self.assertFalse(dlg.skip_prehear(-1))

    def test_a_new_result_says_its_tables_go(self):
        """The mini player sits in a table's viewport — it has to move out
        before the table is deleted, or it goes with it."""
        _host, dlg = self.with_host()
        self.click_cell(dlg, 3, 1)
        gone = []
        dlg.tablesReplaced.connect(lambda: gone.append(len(dlg._tables)))
        dlg.set_result(self.result, self.cands)
        self.assertEqual(gone, [2])
        self.assertEqual(self.icon_of(dlg, 3, 1), "play")

    # ── dragging between variants ──────────────────────────────────────────

    def free_row(self, dlg):
        """A slot whose like-last-year title can go into variety without a warning."""
        last, variety = (self.result.variants[p] for p in ("like_last_year", "variety"))
        for row, slot in enumerate(dlg._slots[0]):
            pick = event_plan.slot_pick(last, (0, *slot))
            if (pick.entry is not event_plan.slot_pick(variety, (0, *slot)).entry
                    and not event_plan.slot_conflict(variety, (0, *slot), pick)):
                return row, pick
        self.fail("no slot takes the other variant's title")

    def test_a_title_dragged_to_another_variant_goes_in(self):
        dlg = self.open()
        row, pick = self.free_row(dlg)
        before = dlg._tables[0].item(row, 0).text()
        self.assertTrue(dlg.drop_slot(0, (row, 0), (row, 1)))
        self.assertIn(pick.entry.title, dlg._tables[0].item(row, 1).text())
        self.assertEqual(dlg._tables[0].item(row, 0).text(), before)
        variety = self.result.variants["variety"]
        self.assertIs(event_plan.slot_pick(variety, (0, *dlg._slots[0][row])).entry,
                      pick.entry)

    def test_a_title_goes_only_to_the_same_dance_of_another_variant(self):
        dlg = self.open()
        self.assertTrue(dlg.can_drop(0, (0, 0), (1, 1)))     # LW heat 1 → LW heat 2
        self.assertTrue(dlg.can_drop(0, (0, 0), (1, 0)))     # a swap in the variant
        self.assertFalse(dlg.can_drop(0, (0, 0), (0, 0)))    # onto itself
        self.assertFalse(dlg.can_drop(0, (0, 0), (2, 1)))    # LW → TG
        dlg.set_busy(True)
        self.assertFalse(dlg.can_drop(0, (0, 0), (1, 1)))
        self.assertFalse(dlg.drop_slot(0, (0, 0), (1, 1)))

    def test_a_dragged_title_that_breaks_the_day_needs_a_yes(self):
        dlg = self.open()
        last, variety = (self.result.variants[p] for p in ("like_last_year", "variety"))
        other = event_plan.slot_pick(variety, (0, 0, 1, 0))     # VR heat 2, LW
        event_plan.put_slot(last, (0, 0, 0, 0), other)
        before = dlg._tables[0].item(0, 1).text()
        with mock.patch("gui.event_compare.QMessageBox") as box:
            box.StandardButton = QMessageBox.StandardButton
            box.question.return_value = QMessageBox.StandardButton.No
            self.assertFalse(dlg.drop_slot(0, (0, 0), (0, 1)))
            self.assertEqual(dlg._tables[0].item(0, 1).text(), before)
            box.question.return_value = QMessageBox.StandardButton.Yes
            self.assertTrue(dlg.drop_slot(0, (0, 0), (0, 1)))
        self.assertIs(event_plan.slot_pick(variety, (0, 0, 0, 0)).entry, other.entry)

    def test_a_title_dragged_within_its_variant_swaps_the_two(self):
        """Marcel: VR LW onto the final's LW of the same variant swaps them."""
        dlg = self.open()
        table = dlg._tables[0]
        first, last = table.item(0, 0).text(), table.item(10, 0).text()
        self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))     # VR heat 1 ⇄ final
        self.assertEqual(table.item(0, 0).text(), last)
        self.assertEqual(table.item(10, 0).text(), first)

    def test_a_swap_that_breaks_the_day_needs_a_yes(self):
        dlg = self.open()
        table = dlg._tables[0]
        first = table.item(0, 0).text()
        with mock.patch.object(event_plan, "swap_conflict",
                               return_value="already plays in that round"), \
                mock.patch("gui.event_compare.QMessageBox") as box:
            box.StandardButton = QMessageBox.StandardButton
            box.question.return_value = QMessageBox.StandardButton.No
            self.assertFalse(dlg.drop_slot(0, (0, 0), (10, 0)))
            self.assertIn("already plays in that round", box.question.call_args.args[2])
            self.assertEqual(table.item(0, 0).text(), first)
            box.question.return_value = QMessageBox.StandardButton.Yes
            self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))
        self.assertEqual(table.item(10, 0).text(), first)

    # ── Ctrl+Z ────────────────────────────────────────────────────────────

    def texts(self, dlg):
        table = dlg._tables[0]
        return [[table.item(r, c).text() for c in range(table.columnCount())]
                for r in range(table.rowCount())]

    def test_ctrl_z_takes_a_choice_back(self):
        """Marcel: Ctrl+Z should work for undo in the event plan table — the
        title comes back, and so does the AI's swap the choice settled."""
        dlg = self.open()
        self.assertEqual(dlg._undo_sc.key(), QKeySequence(QKeySequence.StandardKey.Undo))
        comps = self.result.variants["variety"]
        alt = dlg.slot_choices(0, 0, 1)[-1][2]
        comps[0].refused.append(event_plan.RefusedSwap(
            comps[0].rounds[0].name, 0, 0, alt, "already plays that day"))
        dlg.set_result(self.result, self.cands)
        was, before = event_plan.slot_pick(comps, (0, 0, 0, 0)), self.texts(dlg)
        with mock.patch("gui.event_compare.QMessageBox") as box:
            box.StandardButton = QMessageBox.StandardButton
            box.question.return_value = QMessageBox.StandardButton.Yes
            self.assertTrue(dlg.choose(0, 0, 1, alt))
        self.assertEqual(comps[0].refused, [])
        dlg._undo_sc.activated.emit()
        self.assertIs(event_plan.slot_pick(comps, (0, 0, 0, 0)), was)
        self.assertEqual(len(comps[0].refused), 1)
        self.assertEqual(self.texts(dlg), before)

    def test_ctrl_z_takes_back_one_step_after_the_other(self):
        dlg = self.open()
        start = self.texts(dlg)
        self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))       # a swap
        swapped = self.texts(dlg)
        row, _pick = self.free_row(dlg)
        self.assertTrue(dlg.drop_slot(0, (row, 0), (row, 1)))   # into variety
        self.assertNotEqual(self.texts(dlg), swapped)
        dlg.undo()
        self.assertEqual(self.texts(dlg), swapped)
        dlg.undo()
        self.assertEqual(self.texts(dlg), start)
        dlg.undo()                                               # nothing left
        self.assertEqual(self.texts(dlg), start)

    def test_ctrl_y_puts_back_what_ctrl_z_took(self):
        """Redo, with the main window's keys: Ctrl+Y and Ctrl+Shift+Z."""
        dlg = self.open()
        self.assertEqual(dlg._redo_sc.key(), QKeySequence(QKeySequence.StandardKey.Redo))
        self.assertEqual(dlg._redo_sc2.key(), QKeySequence("Ctrl+Shift+Z"))
        comps = self.result.variants["variety"]
        start = self.texts(dlg)
        self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))       # a swap
        swapped = self.texts(dlg)
        row, pick = self.free_row(dlg)
        self.assertTrue(dlg.drop_slot(0, (row, 0), (row, 1)))   # into variety
        dropped = self.texts(dlg)
        dlg.undo()
        dlg.undo()
        self.assertEqual(self.texts(dlg), start)
        dlg._redo_sc.activated.emit()
        self.assertEqual(self.texts(dlg), swapped)
        dlg._redo_sc2.activated.emit()
        self.assertEqual(self.texts(dlg), dropped)
        self.assertIs(event_plan.slot_pick(comps, (0, *dlg._slots[0][row])).entry,
                      pick.entry)
        dlg.redo()                                               # nothing left
        self.assertEqual(self.texts(dlg), dropped)
        dlg.undo()
        self.assertEqual(self.texts(dlg), swapped)

    def test_a_new_step_ends_the_redo(self):
        dlg = self.open()
        self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))
        dlg.undo()
        start = self.texts(dlg)
        row, _pick = self.free_row(dlg)
        self.assertTrue(dlg.drop_slot(0, (row, 0), (row, 1)))
        dropped = self.texts(dlg)
        dlg.redo()
        self.assertEqual(self.texts(dlg), dropped)
        dlg.undo()
        self.assertEqual(self.texts(dlg), start)

    def test_no_redo_while_the_ai_is_asked_or_after_its_answer(self):
        dlg = self.open()
        self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))
        dlg.undo()
        start = self.texts(dlg)
        dlg.set_busy(True)
        dlg.redo()
        self.assertEqual(self.texts(dlg), start)
        dlg.set_busy(False)
        dlg.set_result(event_plan.RefineResult(self.result.variants), self.cands)
        dlg.redo()
        self.assertEqual(self.texts(dlg), start)

    def test_ctrl_z_shows_what_it_took_back(self):
        dlg = self.open("HGR S STD 2-1\nJ&J (LW; CC) 1")
        self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))
        dlg._tabs.setCurrentIndex(1)
        dlg.undo()
        self.assertEqual(dlg._tabs.currentIndex(), 0)
        self.assertEqual((dlg._tables[0].currentRow(), dlg._tables[0].currentColumn()),
                         (0, 0))

    def test_no_ctrl_z_while_the_ai_is_asked_or_after_its_answer(self):
        dlg = self.open()
        self.assertTrue(dlg.drop_slot(0, (0, 0), (10, 0)))
        swapped = self.texts(dlg)
        dlg.set_busy(True)
        dlg.undo()
        self.assertEqual(self.texts(dlg), swapped)
        dlg.set_busy(False)
        dlg.set_result(event_plan.RefineResult(self.result.variants), self.cands)
        dlg.undo()
        self.assertEqual(self.texts(dlg), swapped)

    def drag_event(self, cls, table, mime, row, col):
        pos = table.visualItemRect(table.item(row, col)).center()
        if cls is QDropEvent:
            pos = QPointF(pos)
        return cls(pos, Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton,
                   Qt.KeyboardModifier.NoModifier)

    def test_the_table_takes_a_drop_from_another_variant(self):
        dlg = self.open()
        row, pick = self.free_row(dlg)
        table = dlg._tables[0]
        mime = table.slot_mime(row, 0)
        over = self.drag_event(QDragMoveEvent, table, mime, row, 1)
        table.dragMoveEvent(over)
        self.assertTrue(over.isAccepted())
        same = self.drag_event(QDragMoveEvent, table, mime, row, 0)
        table.dragMoveEvent(same)
        self.assertFalse(same.isAccepted())
        table.dropEvent(self.drag_event(QDropEvent, table, mime, row, 1))
        QApplication.processEvents()
        self.assertIn(pick.entry.title, table.item(row, 1).text())

    def test_a_title_dragged_out_carries_its_file_for_the_playlists(self):
        """Marcel: drag a title from the event plan into the normal playlists.
        A deck takes a drop by the audio file it carries, as from Explorer."""
        from gui.table_dnd import TableDragDropMixin

        class _Deck(TableDragDropMixin):
            pass

        dlg = self.open()
        path = self.slot_path(dlg, 0, 1)
        mime = dlg._tables[0].slot_mime(0, 1)
        self.assertEqual([u.toLocalFile() for u in mime.urls()],
                         [Path(path).as_posix()])
        drop = types.SimpleNamespace(mimeData=lambda: mime)
        with mock.patch.object(Path, "is_file", return_value=True):
            self.assertEqual(_Deck()._droppable_path(drop), Path(path))

    def test_the_cell_a_title_would_go_into_is_coloured(self):
        """Marcel: when we drag and drop there highlight where it will be
        dropped, color the cell."""
        dlg = self.open()
        row, _pick = self.free_row(dlg)
        table = dlg._tables[0]
        mime = table.slot_mime(row, 0)
        table.viewport().grab()                          # lays the table out
        rect = table.visualItemRect(table.item(row, 1))
        spot = rect.bottomLeft() + QPoint(rect.width() // 2, -3)
        plain = table.viewport().grab().toImage().pixelColor(spot)
        self.assertTrue(plain.isValid())
        table.dragMoveEvent(self.drag_event(QDragMoveEvent, table, mime, row, 1))
        self.assertEqual(table.drop_cell(), (row, 1))
        self.assertNotEqual(table.viewport().grab().toImage().pixelColor(spot), plain)
        table.dragMoveEvent(self.drag_event(QDragMoveEvent, table, mime, row, 0))
        self.assertIsNone(table.drop_cell())             # it cannot go there
        self.assertEqual(table.viewport().grab().toImage().pixelColor(spot), plain)

    def test_the_colour_goes_when_the_drag_leaves_or_drops(self):
        dlg = self.open()
        row, _pick = self.free_row(dlg)
        table = dlg._tables[0]
        mime = table.slot_mime(row, 0)
        table.dragMoveEvent(self.drag_event(QDragMoveEvent, table, mime, row, 1))
        table.dragLeaveEvent(QDragLeaveEvent())
        self.assertIsNone(table.drop_cell())
        table.dragMoveEvent(self.drag_event(QDragMoveEvent, table, mime, row, 1))
        table.dropEvent(self.drag_event(QDropEvent, table, mime, row, 1))
        self.assertIsNone(table.drop_cell())

    def test_another_competitions_title_is_not_taken(self):
        dlg = self.open()
        table = dlg._tables[0]
        mime = dlg._tables[1].slot_mime(0, 0)
        before = table.item(0, 1).text()
        drop = self.drag_event(QDropEvent, table, mime, 0, 1)
        table.dropEvent(drop)
        QApplication.processEvents()
        self.assertFalse(drop.isAccepted())
        self.assertEqual(table.item(0, 1).text(), before)

    def test_a_click_on_a_column_header_chooses_that_variant(self):
        """Marcel: choose the tab's variant by a click on its column header."""
        dlg = self.open()
        dlg._tabs.setCurrentIndex(1)
        table = dlg._tables[1]
        table.viewport().grab()                          # lays the table out
        header = table.horizontalHeader()
        spot = QPoint(header.sectionViewportPosition(1) + 10, header.height() // 2)
        QTest.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=spot)
        self.assertEqual(dlg.chosen(1), "variety")
        self.assertEqual(dlg.chosen(0), "like_last_year")
        self.assertEqual(dlg._variant.currentData(), "variety")
        self.assertEqual(table.horizontalHeaderItem(1).text(), "✔ Variety")

    def test_a_new_result_keeps_the_tab_and_variant(self):
        dlg = self.open()
        dlg._tabs.setCurrentIndex(1)
        dlg._variant.setCurrentIndex(1)
        dlg.set_result(self.result, self.cands)
        self.assertEqual(dlg._tabs.currentIndex(), 1)
        self.assertEqual(dlg._variant.currentData(), "variety")
        dlg._tabs.setCurrentIndex(0)
        self.assertEqual(dlg._variant.currentData(), "like_last_year")


if __name__ == "__main__":
    unittest.main(verbosity=2)
