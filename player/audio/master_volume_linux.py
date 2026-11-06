"""The Linux output volume of the system's default sink — read-only.

The counterpart of player.audio.master_volume_win32 / _mac. PipeWire answers
`wpctl get-volume`, PulseAudio (and pipewire-pulse) `pactl get-sink-volume`;
either tool may be missing, so both are tried. None when neither answers.
"""

import re
import subprocess

_COMMANDS = (["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
             ["pactl", "get-sink-volume", "@DEFAULT_SINK@"])


def parse_volume(text: str) -> float | None:
    """0..1 out of "Volume: 0.47" (wpctl) or "... / 47% / -19.5 dB" (pactl).
    A muted wpctl line ("Volume: 0.47 [MUTED]") still reports the slider."""
    m = re.search(r"Volume:\s*([\d.]+)", text)
    if m:
        return max(0.0, min(1.0, float(m.group(1))))
    m = re.search(r"(\d+)%", text)
    return max(0.0, min(1.0, int(m.group(1)) / 100)) if m else None


def master_volume() -> float | None:
    for cmd in _COMMANDS:
        try:
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=2,
                                  check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        level = parse_volume(done.stdout) if done.returncode == 0 else None
        if level is not None:
            return level
    return None
