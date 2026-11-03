#!/usr/bin/env python3
"""9.1 ⚙ Settings → 🤖 AI: the OpenRouter key and a model out of the host's list.

Run:  py -m unittest tests.gui.dialogs.test_settings_ai_tab -v

The only window with these fields hangs off a button that is commented out, so
the key and the model could only be set by editing openrouter_config.json, and
the list it fetched held the free models alone: a paid one such as a DeepSeek
Flash could not be picked at all.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_ai_"))

from PySide6.QtWidgets import QApplication, QLineEdit

from gui.dialogs import ai_dialogs
from gui.dialogs import settings_ai as tab
from gui.dialogs.settings_dialog import SettingsDialog
from planner import i18n
from tests.qt_test_support import reap_widget

MAMMOUTH = "https://api.mammouth.ai/v1"
CFG = {"api_key": "sk-or-secret", "model": "deepseek/deepseek-v4-flash",
       "base_url": "https://openrouter.ai/api/v1"}


class AiTabCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def build(self, cfg=None, settings=None):
        with mock.patch.object(tab.ai, "load_openrouter_config",
                               return_value=dict(cfg or CFG)):
            dlg = SettingsDialog(dict(settings or {}))
        self.addCleanup(reap_widget, dlg)
        return dlg


class FieldsTest(AiTabCase):

    def test_the_tab_is_there(self):
        tabs = self.build()._tabs
        self.assertIn("🤖 AI", [tabs.tabText(i) for i in range(tabs.count())])

    def test_the_tab_goes_where_nothing_plans(self):
        dlg = self.build(settings={"app_mode": "player"})
        tabs = dlg._tabs
        i = next(i for i in range(tabs.count()) if tabs.tabText(i) == "🤖 AI")
        self.assertFalse(tabs.isTabVisible(i))

    def test_the_stored_config_shows_up(self):
        dlg = self.build({**CFG, "base_url": MAMMOUTH, "ask_first": True})
        self.assertEqual(dlg._ai_key.text(), CFG["api_key"])
        self.assertEqual(dlg._ai_key.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dlg._ai_model.currentText(), CFG["model"])
        self.assertEqual(dlg._ai_base.currentText(), MAMMOUTH)
        self.assertTrue(dlg._ai_first.isChecked())

    def test_the_key_stays_out_of_the_settings_file(self):
        self.assertFalse([k for k, v in self.build().values().items()
                          if v == CFG["api_key"]])


class ModelListTest(AiTabCase):

    def test_the_button_asks_for_every_model_with_the_typed_key(self):
        dlg = self.build()
        dlg._ai_key.setText("  typed  ")
        dlg._ai_base.setCurrentText(MAMMOUTH)
        with mock.patch.object(tab, "OpenRouterModelsWorker") as worker:
            dlg._ai_load.click()
        args, kwargs = worker.call_args
        self.assertEqual(args[0], "typed")
        self.assertEqual(kwargs["base_url"], MAMMOUTH)
        self.assertFalse(kwargs["free_only"])
        worker.return_value.start.assert_called_once_with()
        self.assertFalse(dlg._ai_load.isEnabled())

    def test_the_list_fills_the_combo_and_keeps_the_pick(self):
        dlg = self.build()
        dlg._on_ai_models(["a/one", CFG["model"], "b/two:free"])
        self.assertEqual(dlg._ai_model.count(), 3)
        self.assertEqual(dlg._ai_model.currentText(), CFG["model"])
        self.assertTrue(dlg._ai_load.isEnabled())
        self.assertIn("3", dlg._ai_status.text())

    def test_any_part_of_a_name_finds_it(self):
        dlg = self.build()
        dlg._on_ai_models(["a/one", "deepseek/deepseek-v4-flash", "b/two"])
        comp = dlg._ai_model.completer()
        comp.setCompletionPrefix("flash")
        self.assertEqual(comp.completionCount(), 1)

    def test_a_failed_fetch_keeps_what_is_there(self):
        dlg = self.build()
        dlg._on_ai_models_error("boom")
        self.assertEqual(dlg._ai_model.currentText(), CFG["model"])
        self.assertIn("boom", dlg._ai_status.text())
        self.assertTrue(dlg._ai_load.isEnabled())


class SavingTest(AiTabCase):

    def _save(self, dlg):
        with mock.patch.object(tab.ai, "save_openrouter_config") as save:
            dlg.save_ai_config()
        return save

    def test_an_untouched_tab_writes_nothing(self):
        """A key from the environment must not land in the file on OK."""
        self._save(self.build()).assert_not_called()

    def test_an_edit_is_saved_whole(self):
        dlg = self.build()
        dlg._ai_model.setCurrentText("  x/y  ")
        dlg._ai_first.setChecked(True)
        self._save(dlg).assert_called_once_with(
            CFG["api_key"], "x/y", CFG["base_url"], ask_first=True)

    def test_ok_writes_it(self):
        dlg = self.build()
        dlg._ai_model.setCurrentText("x/y")
        with mock.patch.object(tab.ai, "save_openrouter_config") as save:
            dlg.accept()
        save.assert_called_once()

    def test_cancel_writes_nothing(self):
        dlg = self.build()
        dlg._ai_model.setCurrentText("x/y")
        with mock.patch.object(tab.ai, "save_openrouter_config") as save:
            dlg.reject()
        save.assert_not_called()


class HintTest(unittest.TestCase):
    """The 🤖 AI Playlist dialog says who is going to answer."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _labels(self, cfg):
        with mock.patch.object(ai_dialogs, "load_openrouter_config",
                               return_value=cfg):
            dlg = ai_dialogs.AiPlaylistDialog({})
        self.addCleanup(reap_widget, dlg)
        return " ".join(w.text() for w in dlg.findChildren(ai_dialogs.QLabel))

    def test_a_model_asked_first_is_named(self):
        text = self._labels({**CFG, "ask_first": True})
        self.assertIn(CFG["model"], text)
        self.assertIn("openrouter.ai", text)

    def test_without_a_key_it_is_not_promised(self):
        text = self._labels({**CFG, "api_key": "", "ask_first": True})
        self.assertNotIn(CFG["model"], text)

    def test_not_first_it_is_not_named(self):
        self.assertNotIn(CFG["model"], self._labels(CFG))


class CatalogTest(unittest.TestCase):

    def test_the_new_words_are_translated(self):
        for lang in ("de", "es", "nl", "ru"):
            with self.subTest(lang=lang):
                i18n.set_active(lang)
                self.addCleanup(i18n.set_active, "en")
                self.assertNotEqual(
                    i18n.t("Ask this model first — the claude CLI becomes "
                           "the fallback"),
                    "Ask this model first — the claude CLI becomes the fallback")


if __name__ == "__main__":
    unittest.main()
