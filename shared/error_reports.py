"""🐞 Error reports: uncaught exceptions to GlitchTip, if the user said yes.

Opt-in. Nothing is sent unless ⚙ Settings → "Send error reports" is on, and
that checkbox only exists in a build that knows where to send them. The
address (the DSN) is not in the source — the repository is public and anyone
could post to it — but put in by the build: dancesport.spec writes the
DANCEPLAYLIST_ERROR_DSN variable (a GitHub secret in CI) into the bundle as
error_report_dsn.txt. A source run takes the same variable from the
environment or from the repo's git-ignored .env.

What goes out: the exception with its stack, the log lines before it as
breadcrumbs, the OS, the Python, the build flavor and the version (the
release tag the build came from, planner.version). Not the values of local
variables and not the computer's name, and the user's home folder is cut out
of every string, so a path reads ~\\Music\\…, not C:\\Users\\<name>\\Music\\….
Song titles in the breadcrumbs stay. A native crash (crash.log) is not sent:
it never reaches Python.
"""
import logging
import os
import re
import sys
from pathlib import Path

from planner import config
from planner.version import app_version

log = logging.getLogger("dancesport.errors")

DSN_ENV = "DANCEPLAYLIST_ERROR_DSN"
DSN_FILE = "error_report_dsn.txt"
# The repo's .env (git-ignored) for a source run: DANCEPLAYLIST_ERROR_DSN=...
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

_active = False


def envFileValue(path: Path, key: str) -> str:
    """KEY=value from a .env file, or "" when the file or the key is missing."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        name, sep, value = line.partition("=")
        if sep and name.strip() == key:
            return value.strip().strip("\"'")
    return ""


def dsn() -> str:
    """Where reports go, or "" when this run has no address: the variable
    first, then the repo's .env in a source run, or the file the spec bundled
    in a build."""
    value = os.environ.get(DSN_ENV, "").strip()
    if value:
        return value
    if not getattr(sys, "frozen", False):
        return envFileValue(ENV_FILE, DSN_ENV)
    for folder in (Path(getattr(sys, "_MEIPASS", config.INSTALL_DIR)),
                   config.INSTALL_DIR):
        try:
            return (folder / DSN_FILE).read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return ""


def available() -> bool:
    """Whether this run could send reports at all — the settings offer the
    switch only then."""
    if not dsn():
        return False
    try:
        import sentry_sdk  # noqa: F401
    except ImportError:
        return False
    return True


def _home_pattern() -> re.Pattern:
    home = str(Path.home()).rstrip("\\/")
    parts = [p for p in re.split(r"[\\/]+", home) if p]
    # Any separator between the parts: C:\Users\x, c:/users/x, and the
    # doubled backslashes of a repr'd path.
    return re.compile(r"[\\/]+".join(re.escape(p) for p in parts), re.IGNORECASE)


def scrub(event: dict) -> dict:
    """The event without the home folder (→ "~") and without the computer's
    name."""
    pattern = _home_pattern()

    def walk(value):
        if isinstance(value, str):
            return pattern.sub("~", value)
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value

    out = walk(event)
    out.pop("server_name", None)
    return out


def _before_send(event, _hint):
    return scrub(event)


def _before_breadcrumb(crumb, _hint):
    return scrub(crumb)


def _systemTrustTransport():
    """sentry's HTTP transport, trusting the system's certificates as well as
    certifi's. A virus scanner that inspects HTTPS (Norton, on Marcel's PC)
    presents its own certificate, which Windows trusts and certifi does not —
    with certifi alone every report failed the handshake, silently."""
    import ssl

    from sentry_sdk.transport import HttpTransport

    class SystemTrustTransport(HttpTransport):
        def _get_pool_options(self):
            options = super()._get_pool_options()
            # The system store; urllib3 loads options["ca_certs"] (certifi)
            # into the same context on top.
            options["ssl_context"] = ssl.create_default_context()
            return options

    return SystemTrustTransport


def apply(settings: dict) -> bool:
    """Start or stop sending, as the settings say. Returns whether reports
    are on now. Called at start-up and whenever ⚙ Settings is saved."""
    global _active
    wanted = bool((settings or {}).get("error_reports")) and available()
    if wanted == _active:
        return _active
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError as exc:
        log.warning("🐞 Error reports unavailable: %s", exc)
        return False
    if wanted:
        sentry_sdk.init(
            dsn=dsn(),
            environment=config.build_flavor(),
            release=app_version(),
            send_default_pii=False,
            include_local_variables=False,
            server_name="",
            auto_enabling_integrations=False,
            # Log lines become breadcrumbs only; the uncaught exception is
            # the report, not every handled error that was logged.
            integrations=[LoggingIntegration(level=logging.INFO, event_level=None)],
            before_send=_before_send,
            before_breadcrumb=_before_breadcrumb,
            transport=_systemTrustTransport(),
        )
        log.info("🐞 Error reports on")
    else:
        sentry_sdk.get_client().close()
        log.info("🐞 Error reports off")
    _active = wanted
    return _active
