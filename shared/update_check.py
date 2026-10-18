"""🔔 Update check: whether GitHub has a newer release, if the user said yes.

Opt-in, like the error reports, and asked about in the same first-start
question. Off, nothing here runs. On, every start of a release build sends one
HTTPS request for the latest release of the public repository to GitHub's API
(api.github.com). It carries no version, no settings and nothing about the
library; GitHub sees the IP address and the time, as any server would. A newer
release is announced once; the app never downloads or installs anything, the
notice only links the release page.

A source run ("dev") has no release to compare and never asks.

No Qt in here: the request runs on a plain daemon thread and hands a find to
`on_newer` on that thread, the caller moves it to the GUI thread (a Qt signal
does).
"""
import http.client
import json
import logging
import threading
import urllib.request

from planner.version import DEV, app_version, numbers

log = logging.getLogger("dancesport.update")

REPO = "dancesport-dj/DanceSportPlayer"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
# The settings keys: whether to check, and the last version announced.
SETTING = "update_check"
SEEN_SETTING = "update_seen"
_TIMEOUT_SECS = 10


def available() -> bool:  # slop-mop noqa: ambiguity-mine - an optional feature's own can-this-run check
    """Whether this run can check: a release build (a version to compare)
    that kept TLS — a player build without error reports drops the ssl
    module, see dancesport.spec."""
    if app_version() == DEV:
        return False
    try:
        import ssl  # noqa: F401
    except ImportError:
        return False
    return True


def is_newer(latest: str, current: str) -> bool:
    """Whether release `latest` comes after `current`; never for a dev run."""
    if current == DEV:
        return False
    return numbers(latest) > numbers(current)


def latest_release(timeout: float = _TIMEOUT_SECS) -> tuple[str, str] | None:
    """(version, release page) of the latest GitHub release, or None when
    GitHub cannot be reached or answers something else."""
    request = urllib.request.Request(LATEST_API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "DanceSportPlayer",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:  # nosec B310: fixed https URL
            data = json.load(resp)
    except (OSError, ValueError, http.client.HTTPException) as exc:
        log.info("🔔 Update check failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    tag = str(data.get("tag_name") or "").strip()
    if not tag:
        return None
    return tag.removeprefix("v"), str(data.get("html_url") or RELEASES_PAGE)


def check_in_background(settings: dict, on_newer) -> threading.Thread | None:
    """Ask GitHub on a daemon thread, when the check is on and this run is a
    release build. `on_newer(version, url)` hears a release newer than this
    one that was not announced before. Returns the thread, or None when
    nothing is asked."""
    if not settings.get(SETTING) or not available():
        return None
    current = app_version()
    seen = str(settings.get(SEEN_SETTING) or "")

    def run():
        found = latest_release()
        if found is None:
            return
        version, url = found
        log.info("🔔 Update check\n"
                 "running: %s\n"
                 "latest: %s", current, version)
        if is_newer(version, current) and version != seen:
            on_newer(version, url)

    thread = threading.Thread(target=run, daemon=True, name="update-check")
    thread.start()
    return thread
