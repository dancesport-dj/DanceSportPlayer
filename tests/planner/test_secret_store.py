"""🔐 The OS credential store behind the OpenRouter key (#57)."""
import json
import os
import tempfile
import unittest
import uuid
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_secret_"))

from planner import secret_store
from planner.generate import ai


class FakeStore:
    """What secret_store offers, in a dict."""

    def __init__(self, working=True):
        self.items, self.working = {}, working

    def get(self, name):
        return self.items.get(name) if self.working else None

    def put(self, name, value):
        if not self.working:
            return False
        self.items[name] = value
        return True

    def delete(self, name):
        self.items.pop(name, None)
        return self.working


@unittest.skipUnless(os.name == "nt", "Windows Credential Manager")
class WindowsCredentialTest(unittest.TestCase):

    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("DANCEPLAYLIST_NO_SECRET_STORE", None)
        self.name = f"dp-test-{uuid.uuid4().hex}"
        self.addCleanup(secret_store.delete, self.name)

    def test_a_secret_comes_back_as_it_went_in(self):
        self.assertIsNone(secret_store.get(self.name))
        self.assertTrue(secret_store.put(self.name, "sk-or-v1-äöü-" + "ab" * 600))
        self.assertEqual(secret_store.get(self.name), "sk-or-v1-äöü-" + "ab" * 600)

    def test_a_second_put_replaces_the_first(self):
        secret_store.put(self.name, "one")
        secret_store.put(self.name, "two")
        self.assertEqual(secret_store.get(self.name), "two")

    def test_deleted_is_gone_and_deleting_nothing_is_fine(self):
        secret_store.put(self.name, "one")
        secret_store.delete(self.name)
        self.assertIsNone(secret_store.get(self.name))
        secret_store.delete(self.name)


@unittest.skipIf(os.name == "nt", "Windows has a store")
class NoStoreTest(unittest.TestCase):
    def test_elsewhere_the_caller_is_told_there_is_none(self):
        self.assertFalse(secret_store.put("x", "y"))
        self.assertIsNone(secret_store.get("x"))


class OpenRouterKeyTest(unittest.TestCase):
    """The key lives in the store; model and base URL stay in the JSON."""

    def setUp(self):
        self.store = FakeStore()
        self.file = {}
        patch = [mock.patch.object(ai, "secret_store", self.store),
                 mock.patch.object(ai.OPENROUTER, "read", side_effect=lambda: dict(self.file)),
                 mock.patch.object(ai.OPENROUTER, "write", side_effect=self._write),
                 mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""})]
        for p in patch:
            p.start()
            self.addCleanup(p.stop)

    def _write(self, data):
        self.file = json.loads(json.dumps(data))

    def test_a_saved_key_goes_to_the_store_and_not_to_the_file(self):
        ai.save_openrouter_config("sk-secret", "some/model", "")
        self.assertEqual(self.store.items[ai.KEY_NAME], "sk-secret")
        self.assertNotIn("sk-secret", json.dumps(self.file))
        self.assertEqual(self.file["model"], "some/model")
        self.assertEqual(ai.load_openrouter_config()["api_key"], "sk-secret")

    def test_a_key_left_in_the_file_moves_over_on_the_next_load(self):
        self.file = {"api_key": "sk-old", "model": "m"}
        self.assertEqual(ai.load_openrouter_config()["api_key"], "sk-old")
        self.assertEqual(self.store.items[ai.KEY_NAME], "sk-old")
        self.assertNotIn("api_key", self.file)
        self.assertEqual(self.file["model"], "m")

    def test_without_a_working_store_the_key_stays_in_the_file(self):
        self.store.working = False
        ai.save_openrouter_config("sk-secret", "m", "")
        self.assertEqual(self.file["api_key"], "sk-secret")
        self.assertEqual(ai.load_openrouter_config()["api_key"], "sk-secret")

    def test_a_cleared_key_is_removed_from_both(self):
        ai.save_openrouter_config("sk-secret", "m", "")
        ai.save_openrouter_config("", "m", "")
        self.assertNotIn(ai.KEY_NAME, self.store.items)
        self.assertEqual(ai.load_openrouter_config()["api_key"], "")

    def test_the_environment_still_fills_in_a_missing_key(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-env"}):
            self.assertEqual(ai.load_openrouter_config()["api_key"], "sk-env")
        self.assertNotIn(ai.KEY_NAME, self.store.items)


if __name__ == "__main__":
    unittest.main()
