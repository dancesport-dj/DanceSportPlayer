#!/usr/bin/env python3
"""Tests for the ♪ Takt tap-tempo overlay (`player.takt_meter`).

Run:  py -m unittest tests.player.test_takt_meter -v

A TopTurnier-style manual cross-check: tap along to a track's beat and read
its live tempo back next to a target and the % it is off by. Display only —
none of this touches the playback-rate fader.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_takt_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.player import BigPlayerWidget  # noqa: E402
from player.takt_meter import (  # noqa: E402
    TaktMeterOverlay,
    TapTempoMeter,
    default_sollwert,
    _BAD,
    _DIM,
    _GAIN,
)

_app = QApplication.instance() or QApplication([])


class TapTempoMeterTest(unittest.TestCase):

    def test_two_taps_give_the_interval_as_a_rate(self):
        m = TapTempoMeter()
        m.tap(0.0)
        got = m.tap(2.0)                    # one bar every 2 s → 30 / min
        self.assertAlmostEqual(got, 30.0)

    def test_it_averages_over_the_whole_tapped_span_not_just_the_last_gap(self):
        m = TapTempoMeter()
        for t in (0.0, 2.0, 4.0, 5.0):      # 3 bars over 5 s → 36 / min
            m.tap(t)
        self.assertAlmostEqual(m.takte_per_minute(), 36.0)

    def test_a_pause_in_the_tapping_starts_a_new_reading(self):
        """Tapping stopped for a while, then picked up again: the silent gap
        is no bar, and averaging over it would halve the tempo."""
        m = TapTempoMeter()
        for t in (0.0, 2.0, 4.0):           # 30 / min …
            m.tap(t)
        self.assertIsNone(m.tap(20.0), "the first tap after the pause")
        self.assertAlmostEqual(m.tap(22.0), 30.0)

    def test_one_tap_is_not_a_rate_yet(self):
        m = TapTempoMeter()
        self.assertIsNone(m.tap(0.0))

    def test_reset_clears_it(self):
        m = TapTempoMeter()
        m.tap(0.0)
        m.tap(2.0)
        m.reset()
        self.assertIsNone(m.takte_per_minute())


class DefaultSollwertTest(unittest.TestCase):

    def test_a_known_dance_gives_the_range_midpoint(self):
        self.assertAlmostEqual(default_sollwert("WW"), 59.0)    # (58, 60)

    def test_an_unknown_dance_gives_nothing(self):
        self.assertIsNone(default_sollwert("XX"))

    def test_no_dance_gives_nothing(self):
        self.assertIsNone(default_sollwert(None))


class TaktMeterOverlayTest(unittest.TestCase):

    def setUp(self):
        self.w = TaktMeterOverlay()
        self.addCleanup(reap_widget, self.w)

    def _tap_at(self, *times):
        for t in times:
            self.w._meter._taps.append(t)
        self.w._refresh()

    def test_a_single_tap_still_gives_visible_feedback(self):
        self.assertEqual(self.w._taktzahl_lbl.text(), "—")
        self.w._on_tap()
        self.assertEqual(self.w._taktzahl_lbl.text(), "—")   # no rate from one tap
        self.assertEqual(self.w._tap_btn.styleSheet(), self.w._TAP_FLASH_QSS)
        self.w._end_tap_flash()
        self.assertEqual(self.w._tap_btn.styleSheet(), self.w._TAP_QSS)

    def test_tapping_updates_the_taktzahl_label(self):
        self.w._on_tap()
        self.w._on_tap()
        self.assertIn("Takte / Minute", self.w._taktzahl_lbl.text())

    def test_reset_clears_taktzahl_but_not_sollwert(self):
        self.w._sollwert_spin.setValue(50.0)
        self.w._on_tap()
        self.w._on_tap()
        self.w.reset()
        self.assertEqual(self.w._taktzahl_lbl.text(), "—")
        self.assertAlmostEqual(self.w._sollwert_spin.value(), 50.0)

    def test_closing_the_card_ends_the_measurement(self):
        """Taps belong to the title that was playing — a card reopened later
        must not average new taps against a span from minutes ago."""
        _anchor, _outside = self._open_in_container()
        self._tap_at(0.0, 2.0)
        self.assertIn("Takte / Minute", self.w._taktzahl_lbl.text())
        self.w.hide()
        self.assertEqual(self.w._taktzahl_lbl.text(), "—")
        self.assertEqual(self.w._meter._taps, [])

    def test_the_sollwert_survives_the_close(self):
        """Only the measurement is thrown away; the target is a setting."""
        self._open_in_container()
        self.w._sollwert_spin.setValue(50.0)
        self._tap_at(0.0, 2.0)
        self.w.hide()
        self.assertAlmostEqual(self.w._sollwert_spin.value(), 50.0)

    def test_set_dance_fills_sollwert_until_the_user_edits_it(self):
        self.w.set_dance("WW")
        self.assertAlmostEqual(self.w._sollwert_spin.value(), 59.0)
        self.w.set_dance("QS")                       # still auto → follows
        self.assertAlmostEqual(self.w._sollwert_spin.value(), 51.0)
        self.w._sollwert_spin.setValue(40.0)          # user overrides
        self.w.set_dance("WW")                        # auto stays off
        self.assertAlmostEqual(self.w._sollwert_spin.value(), 40.0)

    def test_korrektur_matches_the_formula(self):
        self._tap_at(0.0, 2.0)                        # 30 / min
        self.w._sollwert_spin.setValue(33.0)           # +10 % needed
        self.w._refresh()
        self.assertEqual(self.w._korrektur_lbl.text(), "+10.0%")

    def test_korrektur_is_zero_with_no_measurement_yet(self):
        self.w._sollwert_spin.setValue(33.0)
        self.w._refresh()
        self.assertEqual(self.w._korrektur_lbl.text(), "0.0%")

    def test_apply_is_disabled_until_there_is_a_real_correction(self):
        self.assertFalse(self.w._apply_btn.isEnabled())
        self._tap_at(0.0, 2.0)                        # 30 / min, no Sollwert yet
        self.assertFalse(self.w._apply_btn.isEnabled())
        self.w._sollwert_spin.setValue(30.0)           # matches exactly: 0.0%
        self.w._refresh()
        self.assertFalse(self.w._apply_btn.isEnabled())
        self.w._sollwert_spin.setValue(33.0)
        self.w._refresh()
        self.assertTrue(self.w._apply_btn.isEnabled())

    def test_it_opens_to_the_right_of_its_anchor(self):
        # A container standing in for the app window, with a small anchor
        # (like the ♪ button) placed well clear of its right edge.
        container = QWidget()
        container.resize(900, 500)
        anchor = QWidget(container)
        anchor.setGeometry(50, 50, 30, 20)
        container.show()
        self.addCleanup(reap_widget, container)
        self.w.show_near(anchor)
        anchor_top_left = self.w.parentWidget().mapFromGlobal(
            anchor.mapToGlobal(QPoint(0, 0)))
        self.assertGreaterEqual(self.w.pos().x(),
                                 anchor_top_left.x() + anchor.width())
        self.assertEqual(self.w.pos().y(), anchor_top_left.y())

    def test_clicking_apply_emits_the_correction(self):
        self._tap_at(0.0, 2.0)                        # 30 / min
        self.w._sollwert_spin.setValue(33.0)           # +10 % needed
        self.w._refresh()
        got = []
        self.w.applyRequested.connect(got.append)
        self.w._apply_btn.click()
        self.assertEqual(len(got), 1)
        self.assertAlmostEqual(got[0], 10.0)

    def test_clicking_apply_resets_the_measurement_for_a_clean_second_reading(self):
        self._tap_at(0.0, 2.0)                        # 30 / min
        self.w._sollwert_spin.setValue(33.0)           # +10 % needed
        self.w._refresh()
        self.w._apply_btn.click()
        self.assertIsNone(self.w._meter.takte_per_minute())
        self.assertEqual(self.w._taktzahl_lbl.text(), "—")
        self.assertFalse(self.w._apply_btn.isEnabled())
        # A fresh tap sequence, long after the first one — if the old taps had
        # survived, this would average against that stale gap and read wrong.
        self._tap_at(1000.0, 1002.0)                  # 30 / min again
        self.assertAlmostEqual(self.w._meter.takte_per_minute(), 30.0)

    def test_korrektur_label_is_orange_bold_within_the_warn_threshold(self):
        self._tap_at(0.0, 2.0)                        # 30 / min
        self.w._sollwert_spin.setValue(30.6)           # +2.0 % — under 2.5 %
        self.w._refresh()
        style = self.w._korrektur_lbl.styleSheet()
        self.assertIn("font-weight:bold", style)
        self.assertIn(_GAIN, style)
        self.assertNotIn(_BAD, style)

    def test_korrektur_label_turns_red_bold_past_the_warn_threshold(self):
        self._tap_at(0.0, 2.0)                        # 30 / min
        self.w._sollwert_spin.setValue(33.0)           # +10 % — past 2.5 %
        self.w._refresh()
        style = self.w._korrektur_lbl.styleSheet()
        self.assertIn("font-weight:bold", style)
        self.assertIn(_BAD, style)

    def _open_in_container(self):
        """The card shown inside a stand-in app window, with a small anchor
        button beside it and one unrelated widget to click on."""
        container = QWidget()
        container.resize(900, 500)
        anchor = QWidget(container)
        anchor.setGeometry(50, 50, 30, 20)
        outside = QWidget(container)
        outside.setGeometry(50, 400, 200, 60)
        container.show()
        self.addCleanup(reap_widget, container)
        self.w.show_near(anchor)
        return anchor, outside

    def test_a_click_outside_asks_the_card_to_close(self):
        _anchor, outside = self._open_in_container()
        got = []
        self.w.closeRequested.connect(lambda: got.append(1))
        QTest.mousePress(outside, Qt.MouseButton.LeftButton)
        self.assertEqual(len(got), 1)

    def test_a_click_on_the_card_itself_keeps_it_open(self):
        self._open_in_container()
        got = []
        self.w.closeRequested.connect(lambda: got.append(1))
        QTest.mousePress(self.w._tap_btn, Qt.MouseButton.LeftButton)
        QTest.mousePress(self.w, Qt.MouseButton.LeftButton)
        self.assertEqual(got, [])

    def test_a_click_on_the_anchor_button_keeps_it_open(self):
        # The anchor toggles the card off by itself; closing here too would
        # let that toggle reopen it on the very same click.
        anchor, _outside = self._open_in_container()
        got = []
        self.w.closeRequested.connect(lambda: got.append(1))
        QTest.mousePress(anchor, Qt.MouseButton.LeftButton)
        self.assertEqual(got, [])

    def test_a_hidden_card_no_longer_listens_for_clicks(self):
        _anchor, outside = self._open_in_container()
        self.w.hide()
        got = []
        self.w.closeRequested.connect(lambda: got.append(1))
        QTest.mousePress(outside, Qt.MouseButton.LeftButton)
        self.assertEqual(got, [])

    def test_korrektur_label_is_dim_and_not_bold_with_no_correction(self):
        self.w._sollwert_spin.setValue(33.0)
        self.w._refresh()                              # no taps yet → 0.0%
        style = self.w._korrektur_lbl.styleSheet()
        self.assertIn(_DIM, style)
        self.assertNotIn("font-weight:bold", style)


class BigPlayerTaktToggleTest(unittest.TestCase):

    def setUp(self):
        self.w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.w.resize(900, 500)   # room for the overlay beside the button, unclamped
        self.w.show()
        self.addCleanup(reap_widget, self.w)

    def test_toggling_creates_and_shows_the_overlay_lazily(self):
        self.assertIsNone(self.w._takt_overlay)
        self.w._takt_btn.setChecked(True)
        self.assertIsNotNone(self.w._takt_overlay)
        self.assertTrue(self.w._takt_overlay.isVisible())
        overlay = self.w._takt_overlay
        self.w._takt_btn.setChecked(False)
        self.assertFalse(overlay.isVisible())
        self.w._takt_btn.setChecked(True)
        self.assertIs(self.w._takt_overlay, overlay)   # not recreated

    def test_set_current_dance_forwards_once_the_overlay_exists(self):
        self.w.set_current_dance("WW")                 # no overlay yet, just stored
        self.w._takt_btn.setChecked(True)
        self.assertEqual(self.w._takt_overlay._dance, "WW")  # picked up on creation
        self.w.set_current_dance("QS")                 # now forwarded live
        self.assertEqual(self.w._takt_overlay._dance, "QS")
        self.assertAlmostEqual(self.w._takt_overlay._sollwert_spin.value(), 51.0)

    def test_the_overlay_closing_itself_unchecks_the_button(self):
        self.w._takt_btn.setChecked(True)
        self.w._takt_overlay.closeRequested.emit()
        self.assertFalse(self.w._takt_btn.isChecked())

    def test_clicking_elsewhere_in_the_player_closes_the_overlay(self):
        self.w._takt_btn.setChecked(True)
        overlay = self.w._takt_overlay
        QTest.mousePress(self.w._title, Qt.MouseButton.LeftButton)  # clear of the card
        self.assertFalse(self.w._takt_btn.isChecked())
        self.assertFalse(overlay.isVisible())

    def test_applying_a_correction_pushes_the_fader_onto_the_current_rate(self):
        self.w._tempo.setValue(50)                    # +5 % already on the fader
        self.w.apply_takt_correction(10.0)             # +10 % more, compounding
        # (1 + 0.05) * (1 + 0.10) = 1.155 → +15.5 % on the fader
        self.assertEqual(self.w._tempo.value(), 155)

    def test_applying_a_correction_clamps_to_the_faders_range(self):
        self.w._tempo.setValue(150)
        self.w.apply_takt_correction(10.0)
        self.assertEqual(self.w._tempo.value(), 160)

    def test_the_overlays_apply_button_reaches_the_fader(self):
        self.w._takt_btn.setChecked(True)
        overlay = self.w._takt_overlay
        overlay._meter._taps = [0.0, 2.0]              # 30 / min
        overlay._sollwert_spin.setValue(33.0)           # +10 % needed
        overlay._refresh()
        overlay._apply_btn.click()
        self.assertEqual(self.w._tempo.value(), 100)    # 0 % fader → +10 %


    def test_a_new_title_ends_the_standing_measurement(self):
        """on_new_track fires once per load — the taps tapped along to the
        title that just went would drag the next reading off."""
        self.w._takt_btn.setChecked(True)
        overlay = self.w._takt_overlay
        overlay._meter._taps = [0.0, 2.0]
        overlay._refresh()
        self.w.on_new_track()
        self.assertEqual(overlay._meter._taps, [])
        self.assertEqual(overlay._taktzahl_lbl.text(), "—")

    def test_a_new_title_leaves_a_card_that_was_never_opened_alone(self):
        self.assertIsNone(self.w._takt_overlay)
        self.w.on_new_track()                          # must not build one
        self.assertIsNone(self.w._takt_overlay)


if __name__ == "__main__":
    unittest.main()
