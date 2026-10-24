"""🎙 The announcement voice, set in ⚙ Settings.

Run:  py -m unittest tests.gui.test_announce_voice_setting -v

Voice (Female / Male / Mixed), '…with heat' and 🔈 Test sat on the ▶ Playing
panel under 🔈 Announce next dance. They are set once per venue, not on the
night, so they moved to ⚙ Settings → 🔊 Sound & player. The panel keeps one
line under the switch that says what was chosen — "Mixed voices · with heat" —
the way the play length shows a dance's own length under it.
"""
import os
import tempfile
import unittest
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_annvoice_"))

from PySide6.QtWidgets import QApplication

from tests.qt_test_support import reap_widget, stub_window_startup


class SoundTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings, **kw):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings, **kw)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_mixed_voices_without_the_heat_by_default(self):
        vals = self._dlg({}).values()
        self.assertEqual(vals["announce_voice"], "random")
        self.assertIs(vals["announce_heat"], False)

    def test_a_stored_choice_is_shown_and_saved(self):
        dlg = self._dlg({"announce_voice": "male", "announce_heat": True})
        self.assertEqual(dlg._voice_combo.currentData(), "male")
        self.assertTrue(dlg._heat_chk.isChecked())
        dlg._voice_combo.setCurrentIndex(dlg._voice_combo.findData("female"))
        dlg._heat_chk.setChecked(False)
        vals = dlg.values()
        self.assertEqual(vals["announce_voice"], "female")
        self.assertIs(vals["announce_heat"], False)

    def test_it_sits_between_the_waveform_and_the_player_position(self):
        from PySide6.QtCore import QPoint
        dlg = self._dlg({}, open_sound=True)
        dlg.show()
        self.app.processEvents()

        def y(w):
            return w.mapTo(dlg, QPoint(0, 0)).y()

        self.assertLess(y(dlg._waveform_chk), y(dlg._voice_combo))
        self.assertLess(y(dlg._voice_combo), y(dlg._player_layout_combo))

    def test_the_old_show_hide_switch_is_gone(self):
        dlg = self._dlg({})
        self.assertFalse(hasattr(dlg, "_voice_adv_chk"))
        self.assertNotIn("announce_advanced", dlg.values())

    def test_test_speaks_what_the_dialog_shows_not_what_was_saved(self):
        """Trying a voice before pressing OK is the point of the button."""
        heard = []
        dlg = self._dlg({"announce_voice": "female"},
                        announce_test_cb=lambda v, h: heard.append((v, h)))
        dlg._voice_combo.setCurrentIndex(dlg._voice_combo.findData("male"))
        dlg._heat_chk.setChecked(True)
        dlg._voice_test_btn.click()
        self.assertEqual(heard, [("male", True)])

    def test_without_an_announcer_there_is_no_test(self):
        self.assertFalse(self._dlg({})._voice_test_btn.isEnabled())

    # Marcel: "add the over the frist bars and before the music starts also
    # to settings" - where the call sits against the first bar.

    def test_the_dance_is_named_over_the_first_bars_by_default(self):
        dlg = self._dlg({})
        self.assertTrue(dlg._lead_over_radio.isChecked())
        self.assertIs(dlg.values()["announce_wait"], False)

    def test_a_stored_wait_is_shown_and_saved(self):
        dlg = self._dlg({"announce_wait": True})
        self.assertTrue(dlg._lead_wait_radio.isChecked())
        dlg._lead_over_radio.setChecked(True)
        self.assertIs(dlg.values()["announce_wait"], False)

    def test_the_pair_sits_under_the_voice(self):
        from PySide6.QtCore import QPoint
        dlg = self._dlg({}, open_sound=True)
        dlg.show()
        self.app.processEvents()

        def y(w):
            return w.mapTo(dlg, QPoint(0, 0)).y()

        self.assertLess(y(dlg._voice_combo), y(dlg._lead_over_radio))
        self.assertEqual(y(dlg._lead_over_radio), y(dlg._lead_wait_radio))
        self.assertLess(y(dlg._lead_over_radio), y(dlg._player_layout_combo))


class PanelCaptionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self, **settings):
        from player.widgets.play_mode_panel import PlayModePanel
        p = PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        p.show()
        return p

    def test_the_panel_has_no_voice_controls_any_more(self):
        p = self.panel(announce_next=True)
        for name in ("announce_voice_combo", "announce_heat_check",
                     "announce_test_btn", "set_voice_advanced_shown",
                     "announce_over_radio", "announce_wait_radio",
                     "announce_when_box"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(p, name))

    def test_the_default_reads_mixed_voices(self):
        p = self.panel(announce_next=True)
        self.assertTrue(p.announce_style_lbl.isVisible())
        self.assertEqual(p.announce_style_lbl.text(), "Mixed voices · over the music")
        self.assertEqual(p.announce_voice(), "random")
        self.assertIs(p.announce_heat(), False)

    def test_one_voice_with_the_heat(self):
        p = self.panel(announce_next=True, announce_voice="female",
                       announce_heat=True)
        self.assertEqual(p.announce_style_lbl.text(),
                         "Female voice · with heat · over the music")
        self.assertTrue(p.announce_heat())

    def test_the_wait_is_named_in_short(self):
        """Marcel: "add it as a info to the orange mixed voices text but in
        shorted form"."""
        p = self.panel(announce_next=True, announce_wait=True)
        self.assertEqual(p.announce_style_lbl.text(), "Mixed voices · before the music")
        self.assertTrue(p.announce_wait())

    def test_a_crossfade_leaves_the_wait_out_of_the_line(self):
        """The crossfade names the dance once the crossover is through, so
        the pair changes nothing then and is not named; its choice stays."""
        p = self.panel(announce_next=True, announce_wait=True, auto_advance=True,
                       xfade_on=True)
        self.assertEqual(p.announce_style_lbl.text(), "Mixed voices")
        self.assertFalse(p.announce_wait())
        self.assertTrue(p.announce_wait_setting_on())
        p.xfade_check.setChecked(False)
        self.assertEqual(p.announce_style_lbl.text(), "Mixed voices · before the music")
        self.assertTrue(p.announce_wait())

    def test_nothing_announced_nothing_to_say(self):
        p = self.panel(announce_next=False)
        self.assertFalse(p.announce_style_lbl.isVisible())
        p.announce_check.setChecked(True)
        self.assertTrue(p.announce_style_lbl.isVisible())

    def test_the_line_starts_under_the_a_of_announce(self):
        """Marcel: "align it at the a from announc next dance so after icon"
        — left-aligned with the caption's first word, not centred and not
        under the 🔈."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QFontMetrics
        p = self.panel(announce_next=True)
        p.resize(300, p.height())
        self.app.processEvents()
        lbl, sw = p.announce_style_lbl, p.announce_check
        self.assertFalse(lbl.alignment() & Qt.AlignmentFlag.AlignHCenter)
        text_x = lbl.mapTo(p, QPoint(lbl.contentsRect().left(), 0)).x()
        icon = sw.text()[:sw.text().index("A")]
        self.assertEqual(icon, "🔈  ")
        a_x = sw.mapTo(p, QPoint(
            sw.text_left() + QFontMetrics(sw.font()).horizontalAdvance(icon), 0)).x()
        self.assertEqual(text_x, a_x)

    def test_a_new_choice_reaches_the_caption(self):
        p = self.panel(announce_next=True)
        p.set_announce_style("male", True, True)
        self.assertEqual(p.announce_style_lbl.text(),
                         "Male voice · with heat · before the music")
        self.assertEqual(p.announce_voice(), "male")
        self.assertTrue(p.announce_heat())
        self.assertTrue(p.announce_wait())


class WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_annvoice_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_a_fresh_install_announces_in_mixed_voices(self):
        self.assertEqual(self.win._announcer._voice_mode, "random")

    def test_a_saved_change_is_applied_at_once(self):
        self._save_settings({"announce_voice": "male", "announce_heat": True,
                             "announce_wait": True})
        self.assertEqual(self.win._announcer._voice_mode, "male")
        panel = self.win._play_panel
        self.assertEqual(panel.announce_voice(), "male")
        self.assertTrue(panel.announce_heat())
        self.assertTrue(panel.announce_wait_setting_on())

    def test_a_panel_save_does_not_overwrite_it(self):
        self.win._settings["announce_voice"] = "male"
        self.win._settings["announce_wait"] = True
        self.win._save_play_settings()
        self.assertEqual(self.win._settings["announce_voice"], "male")
        self.assertIs(self.win._settings["announce_wait"], True)

    def test_the_settings_test_leaves_the_saved_voice_in_place(self):
        """🔈 Test in an open dialog tries a voice; Cancel must not keep it."""
        self.win._settings["announce_voice"] = "female"
        self.win._announcer.set_voice("female")
        spoken = []

        def speak(code, heat=None, **_k):
            spoken.append((self.win._announcer._voice_mode, code, heat))
            return True

        with mock.patch.object(self.win._announcer, "speak", speak):
            self.win._announce_test("male", True)
        self.assertEqual(spoken, [("male", "LW", 3)])
        self.assertEqual(self.win._announcer._voice_mode, "female")

    def _save_settings(self, change):
        """⚙ Settings opened, `change` made, Save pressed."""
        from PySide6.QtWidgets import QDialog
        given = dict(self.win._settings)

        class Dlg:
            def __init__(self, *_a, **_k):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def values(self):
                return {**given, **change}

            def running_look_touched(self):
                return False

            def deleteLater(self):
                pass

        with mock.patch("gui.window.main_global.SettingsDialog", Dlg), \
                mock.patch("gui.window.main_global.save_settings"):
            self.win._open_settings()


if __name__ == "__main__":
    unittest.main()
