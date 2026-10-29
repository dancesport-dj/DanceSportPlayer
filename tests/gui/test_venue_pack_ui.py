"""📦 ⚙ Settings → export / import a venue pack."""
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication, QMessageBox, QTabWidget

from gui.dialogs.settings_dialog import SettingsDialog
from gui.window import main_export
from planner.event import venue_pack as vp

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No
_CANCEL = QMessageBox.StandardButton.Cancel


def _host():
    """A MainWindow stand-in: the venue job runs inline, without a dialog."""
    host = mock.Mock()
    host._settings = {"library_dir": r"C:\lib", "zoom": 2}
    host._run_venue_job.side_effect = lambda message, fn: fn(
        lambda done, total: None, lambda: False)
    return host


class VenuePackUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_venue_ui_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.state = self.root / "state"
        env = mock.patch.dict(os.environ, {"DANCEPLAYLIST_STATE_DIR": str(self.state)})
        env.start()
        self.addCleanup(env.stop)
        self.state.mkdir()
        self.track = self.root / "lib" / "LW" / "Moon (LW 29).mp3"
        self.track.parent.mkdir(parents=True)
        self.track.write_bytes(b"M" * 64)
        (self.state / "autosave_playlist.json").write_text(
            json.dumps({"rows": [str(self.track)]}), encoding="utf-8")
        (self.state / "cartwall.json").write_text(
            json.dumps({"slot_keys": ["Ctrl+1"]}), encoding="utf-8")

    def test_settings_has_both_buttons(self):
        exp, imp = mock.Mock(), mock.Mock()
        dlg = SettingsDialog({}, None, venue_export_cb=exp, venue_import_cb=imp)
        self.addCleanup(dlg.deleteLater)
        self.assertTrue(dlg._venue_export_btn.isEnabled())
        dlg._venue_export_btn.click()
        exp.assert_called_once()
        dlg2 = SettingsDialog({}, None, venue_export_cb=exp, venue_import_cb=imp)
        self.addCleanup(dlg2.deleteLater)
        dlg2._venue_import_btn.click()
        imp.assert_called_once()

    def test_the_buttons_have_a_tab_of_their_own(self):
        dlg = SettingsDialog({}, None)
        self.addCleanup(dlg.deleteLater)
        tabs = dlg.findChild(QTabWidget)
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        page = tabs.widget(captions.index("📦 Venue pack"))
        self.assertTrue(page.isAncestorOf(dlg._venue_export_btn))
        self.assertTrue(page.isAncestorOf(dlg._venue_import_btn))

    def test_buttons_are_off_without_callbacks(self):
        dlg = SettingsDialog({}, None)
        self.addCleanup(dlg.deleteLater)
        self.assertFalse(dlg._venue_export_btn.isEnabled())
        self.assertFalse(dlg._venue_import_btn.isEnabled())

    def _export(self, with_music: bool) -> Path:
        dest = self.root / "venue.dpvenue"
        host = _host()
        with mock.patch.object(main_export.QMessageBox, "question",
                               return_value=_YES if with_music else _NO), \
                mock.patch.object(main_export.QFileDialog, "getSaveFileName",
                                  return_value=(str(dest), "")), \
                mock.patch.object(main_export.QMessageBox, "information") as info:
            main_export.ExportMixin._export_venue_pack(host)
        # The desk is written out first, so the pack holds what is on screen.
        host._autosave_playlist.assert_called_once()
        host._save_cartwall.assert_called_once_with(edit=False)
        info.assert_called_once()
        return dest

    def test_export_without_music(self):
        dest = self._export(with_music=False)
        pack = vp.read_pack(dest)
        self.assertEqual(pack.docs["gui_settings.json"]["zoom"], 2)
        self.assertEqual(pack.docs["autosave_playlist.json"],
                         {"rows": [str(self.track)]})
        self.assertEqual(pack.docs["cartwall.json"], {"slot_keys": ["Ctrl+1"]})
        self.assertEqual(pack.music, {})

    def test_export_with_music(self):
        dest = self._export(with_music=True)
        with zipfile.ZipFile(dest) as z:
            self.assertIn("music/LW/Moon (LW 29).mp3", z.namelist())

    def _suggested_name(self, answer) -> str:
        with mock.patch.object(main_export.QMessageBox, "question",
                               return_value=answer), \
                mock.patch.object(main_export.QFileDialog, "getSaveFileName",
                                  return_value=("", "")) as ask:
            main_export.ExportMixin._export_venue_pack(_host())
        return Path(ask.call_args.args[2]).name

    def test_the_suggested_name_marks_a_pack_with_music(self):
        self.assertRegex(self._suggested_name(_YES),
                         r"^venue-\d{4}-\d\d-\d\d-with-music\.dpvenue$")
        self.assertRegex(self._suggested_name(_NO),
                         r"^venue-\d{4}-\d\d-\d\d\.dpvenue$")

    def test_cancel_at_the_question_writes_nothing(self):
        with mock.patch.object(main_export.QMessageBox, "question",
                               return_value=_CANCEL), \
                mock.patch.object(main_export.QFileDialog, "getSaveFileName") as ask:
            main_export.ExportMixin._export_venue_pack(_host())
        ask.assert_not_called()

    def test_import_with_music_stages_and_offers_a_restart(self):
        dest = self._export(with_music=True)
        music = self.root / "venue_music"
        host = _host()
        with mock.patch.object(main_export.QFileDialog, "getOpenFileName",
                               return_value=(str(dest), "")), \
                mock.patch.object(main_export.QMessageBox, "question",
                                  return_value=_YES), \
                mock.patch.object(main_export.QFileDialog, "getExistingDirectory",
                                  return_value=str(music)), \
                mock.patch.object(main_export.QTimer, "singleShot",
                                  side_effect=lambda ms, fn: fn()):
            main_export.ExportMixin._import_venue_pack(host)
        self.assertTrue(vp.has_pending(self.state))
        host._offer_restart.assert_called_once()
        staged = json.loads((self.state / vp.STAGE_DIR / "autosave_playlist.json")
                            .read_text(encoding="utf-8"))
        self.assertTrue(Path(staged["rows"][0]).is_relative_to(music))
        # The live files stay as they are until the next start applies it.
        live = json.loads((self.state / "autosave_playlist.json").read_text("utf-8"))
        self.assertEqual(live, {"rows": [str(self.track)]})

    def test_a_wrong_file_is_refused(self):
        bad = self.root / "bad.dpvenue"
        bad.write_text("nope")
        host = _host()
        with mock.patch.object(main_export.QFileDialog, "getOpenFileName",
                               return_value=(str(bad), "")), \
                mock.patch.object(main_export.QMessageBox, "warning") as warn:
            main_export.ExportMixin._import_venue_pack(host)
        warn.assert_called_once()
        self.assertFalse(vp.has_pending(self.state))
        host._offer_restart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
