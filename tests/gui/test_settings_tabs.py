"""⚙ Settings: one tab per kind of setting, not one "Paths & search" for all.

Run:  py -m unittest tests.gui.test_settings_tabs -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_tabs_"))

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QScrollArea, QTabWidget

from gui.dialogs.settings_dialog import SettingsDialog
from planner.playing import equalizer as eqs
from shared.audio.eq_question import MusicEqQuestion


class SettingsTabsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dlg = SettingsDialog({}, None)
        self.addCleanup(self.dlg.deleteLater)
        self.tabs = self.dlg.findChild(QTabWidget)

    def page(self, caption):
        captions = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        return self.tabs.widget(captions.index(caption))

    def assertOn(self, caption, *widgets):
        page = self.page(caption)
        for w in widgets:
            self.assertTrue(page.isAncestorOf(w), (caption, w))

    def test_the_tabs_and_their_order(self):
        captions = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        self.assertEqual(captions[:4], ["⚙ General", "📁 Paths",
                                        "🎨 Look", "🔊 Sound && player"])
        # One checkbox made a tab of its own too small to be worth a click.
        self.assertNotIn("🔎 Search", captions)

    def test_general(self):
        self.assertOn("⚙ General", self.dlg._app_mode_combo, self.dlg._remote_box,
                      self.dlg._global_chk)

    def test_paths(self):
        self.assertOn("📁 Paths", self.dlg._lib_edit, self.dlg._glob_edit,
                      self.dlg._save_edit, self.dlg._m3u_format_combo,
                      self.dlg._pl_edit, self.dlg._relearn_btn,
                      self.dlg._ref_edit, self.dlg._remap_edit,
                      self.dlg._hidden_edit)

    def test_hidden_folders_round_trip_one_per_line(self):
        dlg = SettingsDialog({"hidden_folders": ["F:\\m\\Party", "F:\\m\\Talk"]}, None)
        self.addCleanup(dlg.deleteLater)
        self.assertEqual(dlg._hidden_edit.toPlainText(), "F:\\m\\Party\nF:\\m\\Talk")
        dlg._hidden_edit.setPlainText("F:\\m\\Party\n\n  F:\\m\\party\\ \nF:\\m\\Kids")
        self.assertEqual(dlg.values()["hidden_folders"], ["F:\\m\\Party", "F:\\m\\Kids"])

    def test_the_folder_list_is_called_excluded_folders(self):
        # Marcel asked for "Excluded folders": the titles are left out of
        # the library, not merely hidden from view.
        texts = [lbl.text() for lbl in self.dlg.findChildren(QLabel)]
        self.assertTrue(any("<b>Excluded folders</b>" in t for t in texts))
        self.assertFalse(any("Hidden folders" in t for t in texts))

    def test_sound_and_player(self):
        self.assertOn("🔊 Sound && player", self.dlg._backend_combo,
                      self.dlg._release_audio_chk, self.dlg._mute_sys_chk)

    def test_the_tempo_engine_sits_with_the_sound(self):
        self.assertOn("🔊 Sound && player", self.dlg._tempo_engine_combo)

    def test_the_tempo_engine_round_trips(self):
        dlg = SettingsDialog({"tapped_tempo_engine": "rubberband"}, None)
        self.addCleanup(dlg.deleteLater)
        self.assertEqual(dlg.values()["tapped_tempo_engine"], "rubberband")
        self.assertEqual(self.dlg.values()["tapped_tempo_engine"], "qt")

    def test_rubber_band_is_greyed_without_its_filter(self):
        with mock.patch("shared.audio.audio_probes.ffmpeg_has_filter",
                        return_value=False):
            dlg = SettingsDialog({}, None)
        self.addCleanup(dlg.deleteLater)
        combo = dlg._tempo_engine_combo
        item = combo.model().item(combo.findData("rubberband"))
        self.assertFalse(item.isEnabled())

    def test_the_player_rows_sit_with_the_sound(self):
        self.assertOn("🔊 Sound && player", self.dlg._preview_chk,
                      self.dlg._player_layout_combo, self.dlg._voice_combo,
                      self.dlg._heat_chk, self.dlg._voice_test_btn)

    def test_the_venue_intro_wraps_to_the_tab_width(self):
        # A hard line break inside a word-wrapped label pins it to a narrow
        # column however wide the dialog is.
        intro = [lbl.text() for lbl in self.page("📦 Venue pack").findChildren(QLabel)
                 if "PC" in lbl.text()]
        self.assertTrue(intro)
        self.assertNotIn("\n", intro[0])

    def test_every_page_scrolls(self):
        for i in range(self.tabs.count()):
            self.assertIsInstance(self.tabs.widget(i), QScrollArea, self.tabs.tabText(i))

    def test_the_buttons_stay_on_a_small_screen(self):
        """A laptop screen shorter than the tallest page: the page scrolls,
        and OK / Cancel below it stay where they can be pressed."""
        avail = self.dlg.screen().availableGeometry()
        for hint in (self.dlg.minimumSizeHint(), self.dlg.size()):
            self.assertLessEqual(hint.height(), avail.height())
            self.assertLessEqual(hint.width(), avail.width())

    def test_the_per_dance_lengths_keep_their_own_size(self):
        """Marcel: "the per dance input fields are now too long make them as
        before but make sure in the height they are visible on small
        screens" — as wide as a length needs, however wide the dialog is,
        and full height on a laptop screen: the page scrolls instead."""
        self.tabs.setCurrentWidget(self.page("🎛 Playsets"))
        for size in ((1600, 1000), (700, 450)):
            self.dlg.resize(*size)
            self.dlg.show()
            QApplication.processEvents()
            for dance, (combo, _secs) in self.dlg._dance_len_combos.items():
                self.assertEqual(combo.width(), combo.sizeHint().width(), (size, dance))
                self.assertGreaterEqual(combo.height(), combo.sizeHint().height(),
                                        (size, dance))

    def test_the_tso_pitch_targets_keep_their_own_size(self):
        """Marcel: "tso pitch target also need not to be so wide" — and then
        "a little bit wider ... I miss the last border edge of the combobox":
        on a Mac the popup button's frame reaches past its size hint, so a
        few pixels of room on top, not the dialog's whole width."""
        combos = self.dlg._band_combos
        self.tabs.setCurrentWidget(
            next(self.tabs.widget(i) for i in range(self.tabs.count())
                 if self.tabs.widget(i).isAncestorOf(combos["LW"])))
        for size in ((1600, 1000), (700, 450)):
            self.dlg.resize(*size)
            self.dlg.show()
            QApplication.processEvents()
            for dance, combo in combos.items():
                extra = combo.width() - combo.sizeHint().width()
                self.assertTrue(6 <= extra <= 20, (size, dance, extra))
                self.assertGreaterEqual(combo.height(), combo.sizeHint().height(),
                                        (size, dance))


class LastTabTest(unittest.TestCase):
    """Marcel: "setting screen should remeber last tab that was opened in
    current session" — for this run of the app, not in the settings file."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.addCleanup(setattr, SettingsDialog, "_last_tab",
                        SettingsDialog._last_tab)
        SettingsDialog._last_tab = None

    def open(self, settings=None, **kw):
        dlg = SettingsDialog(settings or {}, None, **kw)
        self.addCleanup(dlg.deleteLater)
        return dlg, dlg.findChild(QTabWidget)

    def caption(self, tabs):
        return tabs.tabText(tabs.currentIndex())

    def test_the_first_settings_of_a_session_open_on_general(self):
        _, tabs = self.open()
        self.assertEqual(self.caption(tabs), "⚙ General")

    def test_it_reopens_on_the_tab_it_closed_on(self):
        for close in ("accept", "reject"):
            with self.subTest(close=close):
                dlg, tabs = self.open()
                tabs.setCurrentIndex(2)
                getattr(dlg, close)()
                _, tabs = self.open()
                self.assertEqual(self.caption(tabs), "🎨 Look")

    def test_choose_outputs_still_opens_on_sound(self):
        dlg, tabs = self.open()
        tabs.setCurrentIndex(2)
        dlg.reject()
        _, tabs = self.open(open_sound=True)
        self.assertEqual(self.caption(tabs), "🔊 Sound && player")

    def test_the_wall_right_click_opens_on_the_cartwall_tab(self):
        """Marcel: the pad's right-click "should get into the relevant
        setting part" — the wall's own, not wherever Settings last closed."""
        dlg, tabs = self.open()
        tabs.setCurrentIndex(2)
        dlg.reject()
        _, tabs = self.open(open_cartwall=True)
        self.assertEqual(self.caption(tabs), "🎛 Cartwall")

    def test_a_tab_the_app_mode_hides_falls_back_to_general(self):
        dlg, tabs = self.open()
        sets = next(i for i in range(tabs.count())
                    if tabs.tabText(i) == "🎛 Playsets")
        tabs.setCurrentIndex(sets)
        dlg.reject()
        _, tabs = self.open({"app_mode": "planner"})
        self.assertEqual(self.caption(tabs), "⚙ General")


class WheelTest(unittest.TestCase):
    """Marcel: scrolling the page over an input changed the setting. An input
    takes the wheel only once it has been clicked into; until then the page
    scrolls."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dlg = SettingsDialog({}, None)
        self.addCleanup(self.dlg.deleteLater)
        tabs = self.dlg.findChild(QTabWidget)
        tabs.setCurrentIndex([tabs.tabText(i) for i in range(tabs.count())]
                             .index("🔊 Sound && player"))
        self.dlg.resize(700, 400)
        self.dlg.show()
        self.scroll = tabs.currentWidget()

    def wheel(self, widget, notches=-1):
        centre = QPointF(widget.rect().center())
        event = QWheelEvent(centre, QPointF(widget.mapToGlobal(centre.toPoint())),
                            QPoint(), QPoint(0, 120 * notches), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                            False)
        QApplication.sendEvent(widget, event)

    # ===== Acceptance criteria =====

    def test_the_wheel_over_an_unclicked_input_scrolls_the_page_instead(self):
        slider = self.dlg._eq_panels["music"]._sliders[1]
        combo = self.dlg._tempo_engine_combo
        bar = self.scroll.verticalScrollBar()
        before = bar.value()
        self.wheel(slider)
        self.wheel(combo)
        self.assertEqual(slider.value(), 0)
        self.assertEqual(combo.currentData(), "qt")
        self.assertGreater(bar.value(), before)

    def test_a_clicked_input_takes_the_wheel(self):
        slider = self.dlg._eq_panels["music"]._sliders[1]
        self.dlg.activateWindow()
        QTest.qWaitForWindowActive(self.dlg)
        slider.setFocus()
        self.assertTrue(slider.hasFocus())
        self.wheel(slider, notches=1)
        self.assertNotEqual(slider.value(), 0)

    # ===== Core behavior =====

    def test_spin_boxes_on_every_tab_are_guarded(self):
        self.wheel(self.dlg._duck_spin, notches=1)
        self.assertEqual(self.dlg._duck_spin.value(), 10)


class EqSectionTest(unittest.TestCase):
    """🎚 The equalizer in ⚙ Settings → 🔊 Sound & player."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, settings=None, **kw):
        dlg = SettingsDialog(settings or {}, None, **kw)
        self.addCleanup(dlg.deleteLater)
        return dlg

    # ===== Acceptance criteria =====

    def test_an_edit_is_heard_on_the_playing_music_at_once(self):
        heard = []
        dlg = self.dialog(eq_live_cb=heard.append)
        dlg._eq_panels["music"]._sliders[2].setValue(-6)
        self.assertEqual(eqs.eq_of(heard[-1], "music")["bands"][2]["gain"], -3.0)

    def test_cancel_gives_back_the_equalizer_it_opened_with(self):
        stored = eqs.with_eq({}, "music", {**eqs.default_eq("music"), "on": True})
        heard = []
        dlg = self.dialog(stored, eq_live_cb=heard.append)
        dlg._eq_panels["music"]._sliders[2].setValue(-6)
        dlg.reject()
        self.assertEqual(heard[-1]["equalizer"], stored["equalizer"])

    def test_cancel_takes_away_an_equalizer_there_was_none_of(self):
        """Opened without one stored: the live settings lose it again."""
        heard = []
        dlg = self.dialog(eq_live_cb=heard.append)
        dlg._eq_panels["cue"]._sliders[1].setValue(4)
        dlg.reject()
        self.assertIsNone(heard[-1]["equalizer"])

    def test_ok_keeps_what_was_heard(self):
        heard = []
        dlg = self.dialog(eq_live_cb=heard.append)
        dlg._eq_panels["music"]._sliders[2].setValue(-6)
        n = len(heard)
        dlg.accept()
        self.assertEqual(len(heard), n, "OK sent the old equalizer back")

    def test_an_edit_comes_back_from_values(self):
        dlg = self.dialog()
        dlg._eq_panels["announcer"]._sliders[3].setValue(-4)
        self.assertEqual(eqs.eq_of(dlg.values(), "announcer")["bands"][3]["gain"], -2.0)

    def test_each_source_has_its_tab_on_the_sound_page(self):
        dlg = self.dialog()
        self.assertEqual(set(dlg._eq_panels), {"music", "announcer", "cue"})
        tabs = dlg.findChild(QTabWidget)
        page = tabs.widget([tabs.tabText(i) for i in range(tabs.count())]
                           .index("🔊 Sound && player"))
        self.assertTrue(page.isAncestorOf(dlg._eq_tabs))

    def test_tempo_and_the_equalizer_close_the_sound_page(self):
        """Marcel: below the player position, at the end of the page; only
        the reset button comes after them."""
        dlg = self.dialog()
        lyt = dlg._tempo_engine_combo.parentWidget().layout()
        order = [lyt.indexOf(w) for w in (
            dlg._player_layout_combo, dlg._dblclick_head,
            dlg._tempo_engine_combo, dlg._eq_tabs)]
        self.assertEqual(order, sorted(order))
        self.assertNotIn(-1, order)

    def test_switching_the_music_on_asks_and_the_answer_is_kept(self):
        dlg = self.dialog()
        with mock.patch.object(MusicEqQuestion, "ask", return_value=(True, True)):
            dlg._eq_panels["music"]._on.setChecked(True)
        vals = dlg.values()
        self.assertIs(vals[eqs.PITCH_OK_KEY], True)
        self.assertTrue(eqs.eq_of(vals, "music")["on"])

    def test_return_in_a_typed_readout_does_not_close_the_dialog(self):
        dlg = self.dialog()
        tabs = dlg.findChild(QTabWidget)
        tabs.setCurrentIndex([tabs.tabText(i) for i in range(tabs.count())]
                             .index("🔊 Sound && player"))
        dlg.show()
        readout = dlg._eq_panels["music"]._readouts[1]
        readout._open()
        edit = readout.findChild(QLineEdit)
        edit.setText("3")
        QTest.keyClick(edit, Qt.Key.Key_Return)
        self.assertTrue(dlg.isVisible())
        self.assertEqual(dlg._eq_panels["music"]._sliders[1].value(), 6)
        dlg.reject()

    # ===== Core behavior =====

    def test_the_stored_equalizer_is_shown_and_the_presets_kept(self):
        stored = eqs.with_user_preset(
            eqs.with_eq({}, "music", {**eqs.default_eq("music"), "on": True}),
            "My hall", [-2.0, -3.0, 1.0, 0.0])
        dlg = self.dialog(stored)
        self.assertTrue(dlg._eq_panels["music"]._on.isChecked())
        dlg._eq_panels["cue"]._sliders[1].setValue(2)
        self.assertIn("My hall", eqs.user_presets(dlg.values()))

    def test_an_own_preset_comes_back_from_values_and_shows_on_every_tab(self):
        dlg = self.dialog()
        dlg._eq_panels["announcer"]._sliders[3].setValue(2)
        with mock.patch("PySide6.QtWidgets.QInputDialog.getText",
                        return_value=("Hall B", True)):
            dlg._eq_panels["announcer"]._save_btn.click()
        self.assertEqual(eqs.user_presets(dlg.values())["Hall B"], (0.0, 0.0, 1.0, 0.0))
        self.assertGreaterEqual(dlg._eq_panels["music"]._preset.findData("Hall B"), 0)

    def test_greyed_where_the_backend_has_no_eq(self):
        with mock.patch("gui.dialogs.settings_sound.eq_available", return_value=False):
            dlg = self.dialog()
        self.assertFalse(dlg._eq_tabs.isEnabled())

    def test_a_no_to_the_question_leaves_the_music_off(self):
        dlg = self.dialog()
        with mock.patch.object(MusicEqQuestion, "ask", return_value=(False, False)):
            dlg._eq_panels["music"]._on.setChecked(True)
        vals = dlg.values()
        self.assertNotIn(eqs.PITCH_OK_KEY, vals)
        self.assertFalse(eqs.eq_of(vals, "music")["on"])

    # ===== Coverage and null checks =====

    def test_untouched_it_adds_nothing(self):
        self.assertNotIn("equalizer", self.dialog().values())


if __name__ == "__main__":
    unittest.main(verbosity=2)
