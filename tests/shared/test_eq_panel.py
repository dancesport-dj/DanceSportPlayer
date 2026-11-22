"""🎚 One source's EQ as controls (shared.audio.eq_panel).

Run:  .venv/Scripts/python.exe -m unittest tests.shared.test_eq_panel -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_eq_panel_"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from planner.playing import equalizer as eqs
from shared.audio.eq_panel import EqPanel, freq_text
from tests.qt_test_support import reap_widget


class _Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, source="music", cfg=None, **kw):
        panel = EqPanel(source, cfg or eqs.default_eq(source), **kw)
        self.addCleanup(reap_widget, panel)
        self.edits = []
        panel.changed.connect(lambda: self.edits.append(panel.cfg()))
        return panel


class EqPanelTest(_Test):

    # ===== Acceptance criteria =====

    def test_a_slider_sets_its_band_gain(self):
        panel = self.make()
        panel._sliders[2].setValue(-6)      # 0.5 dB steps
        self.assertEqual(panel.cfg()["bands"][2]["gain"], -3.0)
        self.assertEqual(len(self.edits), 1)
        self.assertEqual(panel._readouts[2].text(), "-3.0 dB")

    def test_a_typed_gain_moves_the_slider(self):
        panel = self.make()
        readout = panel._readouts[4]
        readout.double_clicked.emit()
        readout._edit.setText("+2,5 dB")
        readout._edit.editingFinished.emit()
        self.assertEqual(panel.cfg()["bands"][4]["gain"], 2.5)

    def test_a_double_click_on_a_slider_sets_it_back_to_0_db(self):
        panel = self.make()
        slider = panel._sliders[3]
        slider.setValue(9)
        panel.show()
        QTest.mouseDClick(slider, Qt.MouseButton.LeftButton, pos=slider.rect().center())
        self.assertEqual(slider.value(), 0)
        self.assertEqual(panel.cfg()["bands"][3]["gain"], 0.0)
        self.assertEqual(panel._readouts[3].text(), "+0.0 dB")
        self.assertEqual(self.edits[-1]["bands"][3]["gain"], 0.0)

    def test_a_preset_sets_the_four_gains(self):
        panel = self.make()
        panel._preset.activated.emit(panel._preset.findData("boomy_hall"))
        gains = [b["gain"] for b in panel.cfg()["bands"][1:]]
        self.assertEqual(gains, list(eqs.PRESETS["boomy_hall"]))
        self.assertEqual(panel.cfg()["preset"], "boomy_hall")
        self.assertEqual(panel._sliders[1].value(), -6)

    def test_switching_the_music_on_asks_first(self):
        asked = []
        panel = self.make(confirm_on=lambda: asked.append(1) or True)
        panel._on.setChecked(True)
        self.assertEqual(asked, [1])
        self.assertTrue(panel.cfg()["on"])

    def test_a_no_leaves_it_off_without_asking_twice(self):
        asked = []
        panel = self.make(confirm_on=lambda: asked.append(1) or False)
        panel._on.setChecked(True)
        self.assertEqual(asked, [1])
        self.assertFalse(panel._on.isChecked())
        self.assertFalse(panel.cfg()["on"])
        self.assertEqual(self.edits, [])

    # ===== Core behavior =====

    def test_moving_a_slider_after_a_preset_makes_it_custom(self):
        panel = self.make()
        panel._preset.activated.emit(panel._preset.findData("small_room"))
        panel._sliders[3].setValue(4)
        self.assertEqual(panel.cfg()["preset"], "")
        self.assertEqual(panel._preset.currentData(), "")

    def test_bypass_needs_the_eq_on(self):
        panel = self.make()
        self.assertFalse(panel._bypass.isEnabled())
        panel._on.setChecked(True)
        self.assertTrue(panel._bypass.isEnabled())

    def test_switching_off_never_asks(self):
        cfg = {**eqs.default_eq("music"), "on": True}
        panel = self.make(cfg=cfg, confirm_on=lambda: self.fail("asked"))
        panel._on.setChecked(False)
        self.assertFalse(panel.cfg()["on"])

    def test_advanced_shows_frequency_and_width(self):
        panel = self.make()
        panel.show()
        self.assertTrue(panel._freq_spins[2].isHidden())
        panel._advanced.setChecked(True)
        self.assertFalse(panel._freq_spins[2].isHidden())
        # A shelf's slope is fixed: no width for it.
        self.assertTrue(panel._q_spins[1].isHidden())
        panel._freq_spins[2].setValue(400)
        self.assertEqual(panel.cfg()["bands"][2]["freq"], 400)

    def test_leaving_advanced_goes_back_to_the_defaults(self):
        panel = self.make()
        panel._advanced.setChecked(True)
        panel._freq_spins[2].setValue(400)
        panel._advanced.setChecked(False)
        self.assertEqual(panel.cfg()["bands"][2]["freq"], 250)

    def test_a_band_switched_off_greys_its_slider(self):
        """The voice has no bass shelf by default."""
        panel = self.make("announcer")
        self.assertFalse(panel._sliders[1].isEnabled())
        self.assertTrue(panel._sliders[2].isEnabled())

    def test_the_low_cut_is_picked_from_a_list(self):
        """Marcel: Off / 30 / 60 / 80 / 100 / 150 Hz, without ⚙ Advanced."""
        panel = self.make()
        panel.show()
        combo = panel._low_cut
        self.assertFalse(combo.isHidden())
        self.assertTrue(panel._band_on[0].isHidden())
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         [0, 30, 60, 80, 100, 150])
        self.assertEqual(combo.currentData(), 30)
        combo.setCurrentIndex(combo.findData(80))
        cut = panel.cfg()["bands"][0]
        self.assertEqual((cut["freq"], cut["on"]), (80, True))
        combo.setCurrentIndex(combo.findData(0))
        self.assertFalse(panel.cfg()["bands"][0]["on"])
        self.assertTrue(self.edits)

    def test_the_voice_list_starts_on_100_hz(self):
        self.assertEqual(self.make("announcer")._low_cut.currentData(), 100)

    def test_a_low_cut_switched_off_shows_off(self):
        cfg = eqs.default_eq("music")
        cfg["bands"][0]["on"] = False
        self.assertEqual(self.make(cfg=cfg)._low_cut.currentData(), 0)

    def test_advanced_trades_the_list_for_switch_and_field(self):
        panel = self.make()
        panel.show()
        panel._advanced.setChecked(True)
        self.assertTrue(panel._low_cut.isHidden())
        self.assertFalse(panel._band_on[0].isHidden())
        self.assertFalse(panel._freq_spins[0].isHidden())

    def test_a_typed_cut_off_joins_the_list_and_stays_after_advanced(self):
        panel = self.make()
        panel._advanced.setChecked(True)
        panel._freq_spins[0].setValue(45)
        panel._advanced.setChecked(False)
        self.assertEqual(panel.cfg()["bands"][0]["freq"], 45)
        self.assertEqual(panel._low_cut.currentData(), 45)
        self.assertEqual(panel._low_cut.currentText(), "45 Hz")

    def test_a_band_switched_off_greys_its_whole_column(self):
        """Marcel: on the Voice tab it was not clear that Bass is off; only
        the slider was grey, the heading, frequency and dB still looked live."""
        panel = self.make("announcer")
        for widget in (panel._heads[1], panel._freq_lbls[1], panel._readouts[1]):
            self.assertFalse(widget.isEnabled())
        for widget in (panel._heads[2], panel._freq_lbls[2], panel._readouts[2]):
            self.assertTrue(widget.isEnabled())
        panel._advanced.setChecked(True)
        panel._band_on[1].setChecked(True)
        self.assertTrue(panel._heads[1].isEnabled())
        self.assertTrue(panel._readouts[1].isEnabled())

    def test_the_operators_presets_are_offered(self):
        settings = eqs.with_user_preset({}, "Hall B", [1.0, 2.0, 3.0, 4.0])
        panel = self.make(settings=lambda: settings)
        panel._preset.activated.emit(panel._preset.findData("Hall B"))
        self.assertEqual([b["gain"] for b in panel.cfg()["bands"][1:]], [1, 2, 3, 4])

    def test_the_headroom_is_shown_when_raised(self):
        panel = self.make(headroom=lambda cfg: 3.25)
        self.assertIn("3.2", panel._headroom_lbl.text())

    # ===== Coverage and null checks =====

    def test_set_cfg_says_nothing(self):
        panel = self.make()
        panel.set_cfg({**eqs.default_eq("music"), "on": True})
        self.assertEqual(self.edits, [])
        self.assertTrue(panel._on.isChecked())

    def test_no_headroom_without_a_boost(self):
        panel = self.make(headroom=lambda cfg: 0.0)
        self.assertEqual(panel._headroom_lbl.text(), "")

    def test_frequencies_read_in_hz_and_khz(self):
        self.assertEqual(freq_text(250), "250 Hz")
        self.assertEqual(freq_text(2500), "2.5 kHz")


class OwnPresetTest(_Test):
    """💾 / 🗑: the operator's own presets, saved and deleted from the panel.
    The panel says what to store; the owner stores it (as the card and
    ⚙ Settings do) and has the panels refill their lists."""

    def setUp(self):
        self.settings = {}
        self.panel = self.make(settings=lambda: self.settings)
        self.saved = []

        def store(name, gains):
            self.saved.append((name, gains))
            self.settings = eqs.with_user_preset(self.settings, name, gains)
            self.panel.refill_presets()
        self.panel.presetSaved.connect(store)

    def name(self, text, ok=True):
        return mock.patch.object(QInputDialog, "getText", return_value=(text, ok))

    def answer(self, yes):
        button = QMessageBox.StandardButton.Yes if yes else QMessageBox.StandardButton.No
        return mock.patch.object(QMessageBox, "question", return_value=button)

    # ===== Acceptance criteria =====

    def test_save_keeps_the_four_gains_under_a_name(self):
        self.panel._sliders[1].setValue(-4)
        self.panel._sliders[4].setValue(3)
        with self.name("My hall"):
            self.panel._save_btn.click()
        self.assertEqual(self.saved, [("My hall", (-2.0, 0.0, 0.0, 1.5))])
        self.assertEqual(eqs.user_presets(self.settings)["My hall"], (-2.0, 0.0, 0.0, 1.5))
        self.assertEqual(self.panel._preset.currentData(), "My hall")
        self.assertEqual(self.edits[-1]["preset"], "My hall")

    def test_delete_removes_the_own_preset_shown(self):
        with self.name("My hall"):
            self.panel._save_btn.click()
        self.assertTrue(self.panel._delete_btn.isEnabled())
        with self.answer(True):
            self.panel._delete_btn.click()
        self.assertEqual(self.saved[-1], ("My hall", None))
        self.assertNotIn("My hall", eqs.user_presets(self.settings))
        self.assertEqual(self.panel._preset.findData("My hall"), -1)
        self.assertEqual(self.edits[-1]["preset"], "")

    # ===== Core behavior =====

    def test_a_built_in_preset_cannot_be_deleted(self):
        self.panel._preset.activated.emit(self.panel._preset.findData("boomy_hall"))
        self.assertFalse(self.panel._delete_btn.isEnabled())

    def test_a_built_in_name_is_refused(self):
        for taken in ("Flat", "boomy_hall", " Small room "):
            with self.name(taken), mock.patch.object(QMessageBox, "warning") as warn:
                self.panel._save_btn.click()
            warn.assert_called_once()
        self.assertEqual(self.saved, [])

    def test_an_own_name_again_asks_before_replacing(self):
        with self.name("My hall"):
            self.panel._save_btn.click()
        self.panel._sliders[2].setValue(6)
        with self.name("My hall"), self.answer(False):
            self.panel._save_btn.click()
        self.assertEqual(len(self.saved), 1)
        with self.name("My hall"), self.answer(True):
            self.panel._save_btn.click()
        self.assertEqual(self.saved[-1], ("My hall", (0.0, 3.0, 0.0, 0.0)))

    def test_delete_asks_first(self):
        with self.name("My hall"):
            self.panel._save_btn.click()
        with self.answer(False):
            self.panel._delete_btn.click()
        self.assertIn("My hall", eqs.user_presets(self.settings))

    # ===== Coverage and null checks =====

    def test_cancel_or_a_blank_name_saves_nothing(self):
        with self.name("My hall", ok=False):
            self.panel._save_btn.click()
        with self.name("   "):
            self.panel._save_btn.click()
        self.assertEqual(self.saved, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
