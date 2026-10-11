"""🔔 The opt-in update check against GitHub's releases.

Run:  py -m unittest tests.app.test_update_check -v
"""
import io
import json
import sys
import unittest
from unittest import mock

from shared import update_check as uc


def _response(payload):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return mock.MagicMock(__enter__=lambda s: io.BytesIO(body),
                          __exit__=lambda s, *a: False)


class IsNewerTest(unittest.TestCase):
    def test_a_later_release_is_newer(self):
        self.assertTrue(uc.is_newer("1.3.0", "1.2.0"))
        self.assertTrue(uc.is_newer("1.10.0", "1.9.2"))
        self.assertTrue(uc.is_newer("2.0", "1.9.9"))

    def test_the_same_or_an_older_one_is_not(self):
        self.assertFalse(uc.is_newer("1.2.0", "1.2.0"))
        self.assertFalse(uc.is_newer("1.1.1", "1.2.0"))

    def test_a_source_run_is_never_behind(self):
        self.assertFalse(uc.is_newer("9.9.9", uc.DEV))


class AvailableTest(unittest.TestCase):
    def test_a_release_build_can_check(self):
        with mock.patch.object(uc, "app_version", return_value="1.2.0"):
            self.assertTrue(uc.available())

    def test_a_source_run_cannot(self):
        with mock.patch.object(uc, "app_version", return_value=uc.DEV):
            self.assertFalse(uc.available())

    def test_a_build_without_tls_cannot(self):
        # A player build without error reports drops ssl (dancesport.spec).
        with mock.patch.object(uc, "app_version", return_value="1.2.0"), \
                mock.patch.dict(sys.modules, {"ssl": None}):
            self.assertFalse(uc.available())


class LatestReleaseTest(unittest.TestCase):
    def test_the_tag_loses_its_v(self):
        page = "https://github.com/dancesport-dj/DanceSportPlayer/releases/tag/v1.3.0"
        with mock.patch.object(uc.urllib.request, "urlopen",
                               return_value=_response({"tag_name": "v1.3.0",
                                                       "html_url": page})) as urlopen:
            self.assertEqual(uc.latest_release(), ("1.3.0", page))
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, uc.LATEST_API)
        self.assertTrue(request.full_url.startswith("https://api.github.com/"))

    def test_the_request_carries_no_version(self):
        with mock.patch.object(uc.urllib.request, "urlopen",
                               return_value=_response({"tag_name": "v1.3.0"})) as urlopen, \
                mock.patch.object(uc, "app_version", return_value="1.2.0"):
            uc.latest_release()
        request = urlopen.call_args[0][0]
        self.assertNotIn("1.2.0", request.full_url)
        for value in request.headers.values():
            self.assertNotIn("1.2.0", value)

    def test_no_page_falls_back_to_the_releases_list(self):
        with mock.patch.object(uc.urllib.request, "urlopen",
                               return_value=_response({"tag_name": "1.3.0"})):
            self.assertEqual(uc.latest_release(), ("1.3.0", uc.RELEASES_PAGE))

    def test_no_network_or_a_strange_answer_is_none(self):
        for effect in (OSError("offline"), None):
            with self.subTest(effect=effect):
                kw = ({"side_effect": effect} if effect
                      else {"return_value": _response(b"<html>")})
                with mock.patch.object(uc.urllib.request, "urlopen", **kw):
                    self.assertIsNone(uc.latest_release())
        for payload in ([], {"message": "Not Found"}):
            with mock.patch.object(uc.urllib.request, "urlopen",
                                   return_value=_response(payload)):
                self.assertIsNone(uc.latest_release())


class CheckInBackgroundTest(unittest.TestCase):
    def setUp(self):
        self.heard = []
        version = mock.patch.object(uc, "app_version", return_value="1.2.0")
        version.start()
        self.addCleanup(version.stop)
        latest = mock.patch.object(uc, "latest_release",
                                   return_value=("1.3.0", "https://x/1.3.0"))
        self.latest = latest.start()
        self.addCleanup(latest.stop)

    def _check(self, settings):
        thread = uc.check_in_background(settings, lambda *a: self.heard.append(a))
        if thread is not None:
            thread.join(5)
        return thread

    def test_off_asks_nothing(self):
        self.assertIsNone(self._check({}))
        self.assertIsNone(self._check({uc.SETTING: False}))
        self.latest.assert_not_called()

    def test_a_source_run_asks_nothing(self):
        with mock.patch.object(uc, "app_version", return_value=uc.DEV):
            self.assertIsNone(self._check({uc.SETTING: True}))
        self.latest.assert_not_called()

    def test_a_newer_release_is_announced(self):
        self._check({uc.SETTING: True})
        self.assertEqual(self.heard, [("1.3.0", "https://x/1.3.0")])

    def test_only_once_per_release(self):
        self._check({uc.SETTING: True, uc.SEEN_SETTING: "1.3.0"})
        self.assertEqual(self.heard, [])

    def test_nothing_newer_or_no_answer_is_silent(self):
        self.latest.return_value = ("1.2.0", "https://x/1.2.0")
        self._check({uc.SETTING: True})
        self.latest.return_value = None
        self._check({uc.SETTING: True})
        self.assertEqual(self.heard, [])


if __name__ == "__main__":
    unittest.main()
