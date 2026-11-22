"""🎚 The EQ floating card (player.widgets.eq_card) and the window's side of it
(EqCardController: the one card behind both buttons, its debounced save).

Run:  .venv/Scripts/python.exe -m unittest tests.player.widgets.test_eq_card -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_eq_card_"))

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMessageBox,
    QStyle,
    QStyleOptionButton,
    QStyleOptionSlider,
    QWidget,
)

from planner.playing import equalizer as eqs
from player.widgets import eq_card
from player.widgets.eq_card import EqCard, EqCardController, headroom_of
from player.widgets.player import BigPlayerWidget, PreviewOverlay
from player.window.main_audio import AudioLevelMixin
from shared.audio.eq_question import MusicEqQuestion
from tests.qt_test_support import reap_widget


class _Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        win = QWidget()
        win.resize(900, 600)
        anchor = QWidget(win)
        anchor.setGeometry(20, 20, 30, 20)
        win.show()
        self.addCleanup(reap_widget, win)
        return anchor


class EqCardTest(_Test):

    def setUp(self):
        self.settings = {}
        self.cue = True
        self.card = EqCard(lambda: self.settings, lambda: self.cue)
        self.addCleanup(reap_widget, self.card)
        self.sent = []
        self.card.settingsChanged.connect(self.sent.append)

    def cue_tab(self) -> int:
        return 2

    # ===== Acceptance criteria =====

    def test_a_slider_sends_the_new_equalizer(self):
        self.card.panels["music"]._sliders[1].setValue(4)
        self.assertEqual(len(self.sent), 1)
        music = eqs.eq_of(self.sent[0], "music")
        self.assertEqual(music["bands"][1]["gain"], 2.0)

    def test_each_source_has_its_tab(self):
        self.card.panels["announcer"]._sliders[3].setValue(-2)
        self.assertEqual(eqs.eq_of(self.sent[0], "announcer")["bands"][3]["gain"], -1.0)
        self.assertEqual(eqs.eq_of(self.sent[0], "music")["bands"][3]["gain"], 0.0)

    def test_the_cue_tab_is_greyed_while_it_plays_with_the_music(self):
        self.cue = False
        self.card.refresh()
        self.assertFalse(self.card._tabs.isTabEnabled(self.cue_tab()))
        self.cue = True
        self.card.refresh()
        self.assertTrue(self.card._tabs.isTabEnabled(self.cue_tab()))

    def test_switching_the_music_on_asks_and_remembers(self):
        with mock.patch.object(MusicEqQuestion, "ask", return_value=(True, True)):
            self.card.panels["music"]._on.setChecked(True)
        self.assertIs(self.settings[eqs.PITCH_OK_KEY], True)
        self.assertTrue(eqs.eq_of(self.sent[-1], "music")["on"])

    def test_the_question_does_not_take_the_cards_dark_style(self):
        """Marcel: the question was light text on a light box. A child of the
        card inherits its stylesheet, so the window is its parent."""
        anchor = self.window()
        self.card.show_for(anchor)
        with mock.patch.object(eq_card, "confirm_music_eq", return_value=False) as ask:
            self.card.panels["music"]._on.setChecked(True)
        parent = ask.call_args.args[1]
        self.assertIs(parent, anchor.window())
        self.assertFalse(self.card.isAncestorOf(parent))

    def test_the_preset_dialogs_do_not_take_the_cards_dark_style(self):
        """Marcel: the 💾 name box was unreadable too; so would the refusal
        and the delete question be."""
        anchor = self.window()
        self.card.show_for(anchor)
        music = self.card.panels["music"]
        with mock.patch.object(QInputDialog, "getText", return_value=("Flat", True)) as ask, \
                mock.patch.object(QMessageBox, "warning") as warn:
            music._save_btn.click()
        self.settings = eqs.with_user_preset({}, "Mine", (1.0, 0.0, 0.0, 0.0))
        music.set_cfg({**music.cfg(), "preset": "Mine"})
        with mock.patch.object(QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No) as confirm:
            music._delete_btn.click()
        for call in (ask, warn, confirm):
            self.assertIs(call.call_args.args[0], anchor.window())

    def test_the_voice_is_switched_on_without_a_question(self):
        with mock.patch.object(MusicEqQuestion, "ask") as ask:
            self.card.panels["announcer"]._on.setChecked(True)
        ask.assert_not_called()

    def test_it_opens_on_the_tab_of_the_button_that_opened_it(self):
        self.card.show_for(self.window(), "cue")
        self.assertEqual(self.card._tabs.currentIndex(), self.cue_tab())
        self.assertTrue(self.card.isVisible())

    def test_advanced_makes_room_instead_of_overlapping_the_sliders(self):
        """The frequency and width fields came on top of the sliders: the
        card kept the size it opened with."""
        anchor = self.window()
        anchor.window().resize(1200, 800)
        self.card.show_for(anchor, "music")
        self.card.panels["music"]._advanced.setChecked(True)
        QApplication.processEvents()   # the rows count once the layout has run
        need = self.card.minimumSizeHint()
        self.assertGreater(need.height(), 330)
        self.assertGreaterEqual(self.card.width(), need.width())
        self.assertGreaterEqual(self.card.height(), need.height())

    def test_each_bands_switch_sits_over_its_slider(self):
        """The card's 12 px indicator is drawn at the left of its checkbox:
        centring the checkbox put the box ~4 px left of the groove."""
        anchor = self.window()
        anchor.window().resize(1200, 800)
        self.card.show_for(anchor, "music")
        panel = self.card.panels["music"]
        panel._advanced.setChecked(True)
        QApplication.processEvents()
        for on, slider in zip(panel._band_on[1:], panel._sliders[1:], strict=True):
            opt = QStyleOptionButton()
            on.initStyleOption(opt)
            box = on.style().subElementRect(
                QStyle.SubElement.SE_CheckBoxIndicator, opt, on)
            sopt = QStyleOptionSlider()
            slider.initStyleOption(sopt)
            groove = slider.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, sopt,
                QStyle.SubControl.SC_SliderGroove, slider)
            box_x = on.mapTo(panel, box.center()).x()
            groove_x = slider.mapTo(panel, groove.center()).x()
            self.assertLessEqual(abs(box_x - groove_x), 1, (box_x, groove_x))

    # ===== Core behavior =====

    def test_it_shows_the_settings_as_they_are_when_opened(self):
        """⚙ Settings may have changed them while the card was closed."""
        self.settings = eqs.with_eq({}, "music", {**eqs.default_eq("music"), "on": True})
        self.card.show_for(self.window())
        self.assertTrue(self.card.panels["music"]._on.isChecked())

    def test_greyed_where_the_backend_has_no_eq(self):
        with mock.patch.object(eq_card, "eq_available", return_value=False):
            self.card.refresh()
        self.assertFalse(self.card._tabs.isEnabled())
        self.assertIn("FFmpeg", self.card._note.text())

    def test_a_cue_tab_not_offered_does_not_open(self):
        self.cue = False
        self.card.show_for(self.window(), "cue")
        self.assertEqual(self.card._tabs.currentIndex(), 0)

    def test_the_headroom_counts_a_boost(self):
        cfg = eqs.apply_preset(eqs.default_eq("music"), "weak_speakers", {})
        self.assertGreater(headroom_of(cfg), 1.0)
        self.assertEqual(headroom_of(eqs.default_eq("music")), 0.0)

    # ===== Coverage and null checks =====

    def test_no_note_where_the_backend_has_the_eq(self):
        self.card.refresh()
        self.assertTrue(self.card._note.isHidden())


class _Device:

    def __init__(self):
        self.synced = 0

    def sync_eq(self):
        self.synced += 1

    def cue_device(self):
        return None


class ControllerTest(_Test):

    def setUp(self):
        self.settings = {"master_volume": 0.8}
        self.device = _Device()
        win = QWidget()
        win.resize(900, 600)
        win.show()
        self.addCleanup(reap_widget, win)
        self.ctl = EqCardController(win, self.device, lambda: self.settings)
        self.addCleanup(lambda: self.ctl.card and reap_widget(self.ctl.card))
        self.anchor = QWidget(win)
        self.anchor.setGeometry(20, 20, 30, 20)
        self.anchor.show()
        saver = mock.patch.object(eq_card, "save_settings")
        self.saved = saver.start()
        self.addCleanup(saver.stop)

    # ===== Acceptance criteria =====

    def test_an_edit_is_heard_at_once_and_saved_once_it_rests(self):
        self.ctl.toggle(self.anchor)
        self.ctl.card.panels["music"]._sliders[1].setValue(2)
        self.ctl.card.panels["music"]._sliders[1].setValue(4)
        self.assertEqual(self.device.synced, 2)
        self.assertIn("equalizer", self.settings)
        self.assertEqual(self.settings["master_volume"], 0.8)   # merged, not replaced
        self.saved.assert_not_called()
        self.ctl.save_timer.timeout.emit()
        self.saved.assert_called_once_with(self.settings)

    def test_the_same_button_again_closes_it(self):
        self.ctl.toggle(self.anchor)
        self.assertTrue(self.ctl.card.isVisible())
        self.ctl.toggle(self.anchor)
        self.assertFalse(self.ctl.card.isVisible())

    # ===== Core behavior =====

    def test_closing_writes_what_was_still_waiting(self):
        self.ctl.toggle(self.anchor)
        self.ctl.card.panels["cue"]._sliders[1].setValue(2)
        self.ctl.card.closeRequested.emit()
        self.saved.assert_called_once()
        self.assertFalse(self.ctl.card.isVisible())

    def test_closing_with_its_button_writes_what_was_still_waiting(self):
        """The same button again hides the card without closeRequested:
        a quit right after must not lose the edit to the save timer."""
        self.ctl.toggle(self.anchor)
        self.ctl.card.panels["cue"]._sliders[1].setValue(2)
        self.ctl.toggle(self.anchor)
        self.saved.assert_called_once()
        self.assertFalse(self.ctl.save_timer.isActive())

    def test_an_own_preset_is_saved_and_offered_on_every_tab(self):
        self.ctl.toggle(self.anchor)
        music = self.ctl.card.panels["music"]
        music._sliders[1].setValue(4)
        with mock.patch.object(QInputDialog, "getText", return_value=("My hall", True)):
            music._save_btn.click()
        self.assertEqual(eqs.user_presets(self.settings)["My hall"], (2.0, 0.0, 0.0, 0.0))
        self.assertEqual(eqs.eq_of(self.settings, "music")["preset"], "My hall")
        self.assertGreaterEqual(self.ctl.card.panels["cue"]._preset.findData("My hall"), 0)
        self.ctl.card.closeRequested.emit()
        self.saved.assert_called_once_with(self.settings)

    def test_the_window_holds_no_eq_state(self):
        """tests/app/test_mainwindow_budget.py: the controller owns it."""
        self.assertFalse(any(n.startswith("_eq") for n in vars(AudioLevelMixin)))


class ButtonsTest(_Test):

    # ===== Acceptance criteria =====

    def test_the_player_card_has_a_button_for_the_music(self):
        w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, w)
        got = []
        w.eqRequested.connect(lambda anchor, source: got.append((anchor, source)))
        w._eq_act.trigger()
        self.assertEqual(got, [(w._tools_btn, "music")])

    def test_tempo_check_and_equalizer_share_one_button(self):
        """One click on the button, then pick: the row under the fader had
        no room for two (the tempo readout was cut off)."""
        w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, w)
        self.assertEqual(w._tools_menu.actions(), [w._takt_act, w._eq_act])
        with mock.patch.object(w._tools_menu, "popup") as popup:
            w._tools_btn.click()
        popup.assert_called_once()

    def test_the_button_again_closes_the_open_tempo_check_and_offers_the_menu(self):
        w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, w)
        w.resize(900, 500)
        w.show()
        w._takt_act.setChecked(True)
        with mock.patch.object(w._tools_menu, "popup") as popup:
            w._tools_btn.click()
        popup.assert_called_once()
        self.assertFalse(w._takt_act.isChecked())
        self.assertFalse(w._takt_overlay.isVisible())

    def test_the_button_again_closes_the_open_equalizer_and_offers_the_menu(self):
        w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, w)
        w.resize(900, 500)
        w.show()
        settings = {}
        ctl = EqCardController(w, _Device(), lambda: settings)
        w.eqRequested.connect(ctl.toggle)
        w._eq_act.trigger()
        self.assertTrue(ctl.card.isVisible())
        with mock.patch.object(w._tools_menu, "popup") as popup:
            w._tools_btn.click()
        popup.assert_called_once()
        self.assertFalse(ctl.card.isVisible())

    def test_the_shared_button_shows_only_the_note(self):
        w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, w)
        self.assertEqual(w._tools_btn.text(), "♪")

    def test_the_menu_wears_the_cards_look_without_a_checkbox(self):
        """The open tempo check is marked by its colour, not a white box."""
        w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, w)
        qss = w._tools_menu.styleSheet()
        self.assertIn("#2c3752", qss)          # the cards' background
        self.assertIn("QMenu::indicator", qss)
        self.assertIn("QMenu::item:checked", qss)

    def test_the_prelisten_mini_player_has_one_for_the_cue(self):
        ov = PreviewOverlay(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, ov)
        got = []
        ov.eqRequested.connect(lambda anchor, source: got.append(source))
        btn = next(b for b in ov.findChildren(type(ov._duck_btn)) if b.text() == "🎚")
        btn.click()
        self.assertEqual(got, ["cue"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
