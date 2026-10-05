"""Tests for shared.error_reports: opt-in error reports to GlitchTip.

Run:  py -m unittest tests.app.test_error_reports -v

Nothing is sent unless the user switched it on AND the build knows where to
send it; the address comes from the build, never from the source; and the
user's home folder does not leave the machine."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner import config
from shared import error_reports

_DSN = "https://key@errors.example.invalid/1"


class DsnTest(unittest.TestCase):

    def setUp(self):
        self._base = config.INSTALL_DIR
        self._bundle = Path(tempfile.mkdtemp(prefix="dp_dsn_"))
        config.INSTALL_DIR = self._bundle
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(error_reports.DSN_ENV, None)
        # Not the repo's own .env, which may hold the real address.
        env_file = mock.patch.object(error_reports, "ENV_FILE",
                                     self._bundle / ".env")
        env_file.start()
        self.addCleanup(env_file.stop)

    def tearDown(self):
        config.INSTALL_DIR = self._base
        for attr in ("frozen", "_MEIPASS"):
            if hasattr(sys, attr):
                delattr(sys, attr)

    def test_a_source_run_has_none(self):
        self.assertEqual(error_reports.dsn(), "")
        self.assertFalse(error_reports.available())

    def test_the_variable_names_it(self):
        os.environ[error_reports.DSN_ENV] = f"  {_DSN}\n"
        self.assertEqual(error_reports.dsn(), _DSN)

    def test_a_build_reads_the_file_it_bundled(self):
        sys.frozen = True
        sys._MEIPASS = str(self._bundle)
        (self._bundle / error_reports.DSN_FILE).write_text(_DSN + "\n",
                                                           encoding="utf-8")
        self.assertEqual(error_reports.dsn(), _DSN)

    def test_a_source_run_ignores_a_stray_file(self):
        (self._bundle / error_reports.DSN_FILE).write_text(_DSN, encoding="utf-8")
        self.assertEqual(error_reports.dsn(), "")

    def test_a_source_run_reads_the_env_file(self):
        error_reports.ENV_FILE.write_text(
            "OTHER=1\n# comment\n" f'{error_reports.DSN_ENV} = "{_DSN}"\n',
            encoding="utf-8")
        self.assertEqual(error_reports.dsn(), _DSN)

    def test_the_variable_wins_over_the_env_file(self):
        error_reports.ENV_FILE.write_text(f"{error_reports.DSN_ENV}=https://other@x/2",
                                          encoding="utf-8")
        os.environ[error_reports.DSN_ENV] = _DSN
        self.assertEqual(error_reports.dsn(), _DSN)

    def test_a_build_ignores_the_env_file(self):
        sys.frozen = True
        sys._MEIPASS = str(self._bundle)
        error_reports.ENV_FILE.write_text(f"{error_reports.DSN_ENV}={_DSN}",
                                          encoding="utf-8")
        self.assertEqual(error_reports.dsn(), "")

    def test_an_address_without_the_client_offers_nothing(self):
        # A player venv built from requirements-player.txt before it named
        # sentry-sdk: the switch would be there and do nothing.
        os.environ[error_reports.DSN_ENV] = _DSN
        # Only this one entry: patch.dict(sys.modules) clears the whole table
        # on the way out, under whatever thread is importing at that moment.
        saved = sys.modules.get("sentry_sdk")
        sys.modules["sentry_sdk"] = None
        try:
            self.assertFalse(error_reports.available())
        finally:
            if saved is None:
                del sys.modules["sentry_sdk"]
            else:
                sys.modules["sentry_sdk"] = saved


class ApplyTest(unittest.TestCase):

    def setUp(self):
        dsn = mock.patch.object(error_reports, "dsn", return_value=_DSN)
        dsn.start()
        self.addCleanup(dsn.stop)
        self.init = mock.patch("sentry_sdk.init").start()
        self.addCleanup(mock.patch.stopall)
        error_reports._active = False

    def test_off_unless_the_user_switched_it_on(self):
        self.assertFalse(error_reports.apply({}))
        self.init.assert_not_called()

    def test_on_without_an_address_sends_nothing(self):
        with mock.patch.object(error_reports, "dsn", return_value=""):
            self.assertFalse(error_reports.apply({"error_reports": True}))
        self.init.assert_not_called()

    def test_on_with_an_address_starts_the_client(self):
        self.assertTrue(error_reports.apply({"error_reports": True}))
        kw = self.init.call_args.kwargs
        self.assertEqual(kw["dsn"], _DSN)
        self.assertFalse(kw["send_default_pii"])
        self.assertFalse(kw["include_local_variables"])
        self.assertEqual(kw["server_name"], "")

    def test_switching_it_off_closes_the_client(self):
        error_reports.apply({"error_reports": True})
        with mock.patch("sentry_sdk.get_client") as client:
            self.assertFalse(error_reports.apply({"error_reports": False}))
        client.return_value.close.assert_called_once()

    def test_a_second_apply_does_not_start_a_second_client(self):
        error_reports.apply({"error_reports": True})
        error_reports.apply({"error_reports": True})
        self.assertEqual(self.init.call_count, 1)


class ScrubTest(unittest.TestCase):

    def setUp(self):
        home = mock.patch.object(Path, "home",
                                 return_value=Path(r"C:\Users\Someone"))
        home.start()
        self.addCleanup(home.stop)

    def test_the_home_folder_leaves_no_trace(self):
        event = {
            "server_name": "SOMEONES-PC",
            "exception": {"values": [{"stacktrace": {"frames": [
                {"abs_path": r"C:\Users\Someone\DanceSport-Player\_internal\x.py"},
                {"abs_path": "c:/users/someone/Music/a.mp3"}]}}]},
            "breadcrumbs": {"values": [
                {"message": r"▶ C:\\Users\\Someone\\Music\\LW 1.mp3"}]},
            "extra": {"sys.argv": [r"C:\Users\Someone\list.m3u"]},
        }
        out = error_reports.scrub(event)
        text = repr(out)
        self.assertNotIn("Someone", text)
        self.assertNotIn("SOMEONE", text)
        self.assertNotIn("server_name", out)
        frames = out["exception"]["values"][0]["stacktrace"]["frames"]
        self.assertEqual(frames[0]["abs_path"], r"~\DanceSport-Player\_internal\x.py")
        self.assertEqual(frames[1]["abs_path"], "~/Music/a.mp3")

    def test_other_text_is_left_as_it_is(self):
        event = {"message": r"F:\my music\tanzcds\SA 50.mp3", "level": "error"}
        self.assertEqual(error_reports.scrub(dict(event)), event)


class RealClientTest(unittest.TestCase):
    """The real sentry_sdk, with a transport that keeps what would be sent."""

    def test_a_report_goes_out_without_the_home_folder(self):
        import sentry_sdk
        from sentry_sdk.transport import Transport

        sent = []

        class _Keep(Transport):
            def capture_envelope(self, envelope):
                sent.extend(i.payload.json for i in envelope.items
                            if i.headers.get("type") == "event")

        real_init = sentry_sdk.init
        error_reports._active = False
        with mock.patch.object(error_reports, "dsn", return_value=_DSN), \
                mock.patch("sentry_sdk.init",
                           lambda **kw: real_init(**{**kw, "transport": _Keep})):
            self.assertTrue(error_reports.apply({"error_reports": True}))
            try:
                raise RuntimeError(f"cannot open {Path.home() / 'list.m3u'}")
            except RuntimeError:
                sentry_sdk.capture_exception()
            sentry_sdk.flush()
            error_reports.apply({})
        self.assertEqual(len(sent), 1)
        text = repr(sent[0])
        self.assertIn("cannot open ~", text)
        self.assertNotIn(Path.home().name, text)
        self.assertNotIn("server_name", sent[0])


class TrustTest(unittest.TestCase):
    """A virus scanner that inspects HTTPS (Norton on Marcel's PC) presents
    its own certificate, which Windows trusts and certifi does not."""

    def test_the_connection_trusts_what_the_system_trusts(self):
        import ssl

        import sentry_sdk

        error_reports._active = False
        with mock.patch.object(error_reports, "dsn", return_value=_DSN):
            error_reports.apply({"error_reports": True})
            try:
                options = sentry_sdk.get_client().transport._get_pool_options()
            finally:
                error_reports.apply({})
        context = options.get("ssl_context")
        self.assertIsInstance(context, ssl.SSLContext)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        if sys.platform == "win32":
            # The Windows ROOT store, loaded before urllib3 adds certifi.
            self.assertGreater(context.cert_store_stats()["x509_ca"], 0)


# The real address, from the variable (the GitHub secret in CI) or the repo's
# git-ignored .env — read before any test above patches either.
_LIVE_DSN = error_reports.dsn()
# Every run of it is one event in GlitchTip, so it runs only when asked for.
LIVE_SWITCH = "DANCEPLAYLIST_LIVE_TESTS"


@unittest.skipUnless(os.environ.get(LIVE_SWITCH) == "1", f"{LIVE_SWITCH}=1 not set")
@unittest.skipUnless(_LIVE_DSN, f"no {error_reports.DSN_ENV} in the environment or .env")
class LiveServerTest(unittest.TestCase):
    """One real event to the real GlitchTip project, through the same apply()
    the app calls. Tagged test=unittest so it can be told apart there."""

    def test_the_server_takes_a_report(self):
        import sentry_sdk
        from sentry_sdk.transport import HttpTransport

        statuses = []
        real_request = HttpTransport._request

        def _request(transport, *args, **kwargs):
            response = real_request(transport, *args, **kwargs)
            statuses.append(response.status)
            return response

        error_reports._active = False
        with mock.patch.object(error_reports, "dsn", return_value=_LIVE_DSN), \
                mock.patch.object(HttpTransport, "_request", _request):
            self.assertTrue(error_reports.apply({"error_reports": True}))
            try:
                raise RuntimeError("test event from tests.app.test_error_reports")
            except RuntimeError as exc:
                sentry_sdk.capture_exception(exc, tags={"test": "unittest"})
            sentry_sdk.flush(timeout=15)
            error_reports.apply({})
        self.assertTrue(statuses, "nothing reached the server")
        self.assertEqual([s for s in statuses if not 200 <= s < 300], [])


if __name__ == "__main__":
    unittest.main()
