"""The macOS output volume of the system's default output — read-only.

The Mac counterpart of player.audio.master_volume_win32: the music's loudness
in the ears is the app's fader times this slider. `osascript` ships with every
Mac, so there is nothing to install. It reports the default output only; the
caller treats an unreadable value (None) as "full".
"""

import subprocess

_SCRIPT = "output volume of (get volume settings)"


def parse_volume(text: str) -> float | None:
    """0..1 out of osascript's "47" — None for "missing value" (an output with
    no software volume, like HDMI) or anything else unreadable."""
    try:
        return max(0.0, min(1.0, int(text.strip()) / 100))
    except ValueError:
        return None


def master_volume() -> float | None:
    try:
        done = subprocess.run(["osascript", "-e", _SCRIPT], capture_output=True,
                              text=True, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_volume(done.stdout) if done.returncode == 0 else None
