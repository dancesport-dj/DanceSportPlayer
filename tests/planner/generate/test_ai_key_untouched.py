"""Editing only the model or host must not move an env key into the store (#38)."""
import unittest
from unittest import mock

from planner.generate import ai


class KeyUntouchedTest(unittest.TestCase):

    def setUp(self):
        self.store = mock.patch.object(ai, "OPENROUTER").start()
        self.secrets = mock.patch.object(ai, "secret_store").start()
        self.addCleanup(mock.patch.stopall)
        self.store.read.return_value = {"model": "old"}

    def test_no_key_given_leaves_the_stored_key_alone(self):
        ai.save_openrouter_config(None, "new", "https://x.example/v1")
        self.secrets.put.assert_not_called()
        self.secrets.delete.assert_not_called()
        written = self.store.write.call_args[0][0]
        self.assertNotIn("api_key", written)
        self.assertEqual(written["model"], "new")

    def test_an_empty_key_still_clears_it(self):
        ai.save_openrouter_config("", "m")
        self.secrets.delete.assert_called_once()

    def test_the_settings_tab_passes_no_key_when_only_the_model_changed(self):
        from gui.dialogs.settings_ai import AiTabMixin

        class Tab(AiTabMixin):
            def __init__(self):
                self._ai_given = dict(api_key="env", model="a", base_url="b", ask_first=False)
                self.now = dict(self._ai_given, model="z")

            def ai_values(self):
                return self.now

        with mock.patch.object(ai, "save_openrouter_config") as save:
            Tab().save_ai_config()
        self.assertIsNone(save.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
