"""Playback arithmetic and machine state the desk and the evening share: the
loudness target, the idle hand-back of the sound device, the heat-equalize
floors, how many seconds the floor has really heard, and the OS wake lock that
keeps the screen on through a long set.
"""
import logging
import os
import subprocess
import sys

log = logging.getLogger("dancesport.gui")


# Loudness-equalization target (EBU R128 integrated). Tracks are pulled towards
# it, so where it sits decides how far below full scale the whole evening plays
# — and a sound card's noise floor does NOT come down with the music. Every dB
# of attenuation here is a dB of hiss the amplifier has to make up for, so the
# target is as high as the boost side safely allows.
#
# Measured over this library (4748 analyzed tracks, median −9.9 LUFS): at −14
# the typical track is attenuated 4.1 dB and 7 tracks want more boost than the
# +9 dB clamp allows — quiet anthems and soundtrack cues, not floor titles. The
# old −18 threw away 8.1 dB for headroom nothing was using; going further, to
# −12, would boost a quarter of the library with no true-peak figure to clamp
# against (only integrated LUFS is stored).
_TARGET_LUFS = -14.0


# 🔇 How long everything has to stay silent before the sound device is handed
# back (setting "release_audio_idle"). Long enough that the two-second gap
# between an announcement and the music does not close and re-open the card,
# short enough that the hiss is gone before anyone in the hall notices it.
_AUDIO_IDLE_S = 5.0


# TSO floor overrides for the heat-equalize clamp. Empty since the Rumba
# minimum moved down to T24 (the old 24.5 practice-floor covered the T25 era).
_TSO_FLOOR_OVERRIDE: dict[str, float] = {}


def audible_played_secs(position_ms: int, offset_ms: int, rate: float) -> float:
    """Wall-clock seconds of music the floor has actually heard.

    Two corrections on the raw player position, both of which the timed cut
    needs:

    * `offset_ms` — silence the 🔇 stillness skip jumped over. It IS file
      position but nobody danced to it, so a 1:45 play length on a track with
      an 8 s silent intro must still give 1:45 of music.
    * `rate` — the tempo fader. At +16 % the position advances 16 % faster than
      the clock, so 105 raw seconds are only 90 s on the floor. "Play length
      1:45" is a promise about how long the couples dance."""
    heard = max(0.0, (position_ms - offset_ms) / 1000.0)
    return heard / max(0.01, float(rate or 1.0))


def _awake_windows(on: bool) -> bool:
    """Windows: SetThreadExecutionState declares the process busy.

    ES_CONTINUOUS makes the declaration hold until it is taken back, so
    `on=False` restores the normal timers (and the process ending does the same
    by itself)."""
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    flags = ES_CONTINUOUS | ((ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED) if on else 0)
    import ctypes
    fn = ctypes.windll.kernel32.SetThreadExecutionState
    fn.argtypes = [ctypes.c_uint]
    fn.restype = ctypes.c_uint
    # Every success answers with the PREVIOUS state; 0 is the only failure.
    if not fn(flags):
        log.warning("☀️ Windows refused the wake lock (on=%s)", on)
        return False
    return True


# The macOS helper process while the screen is held, None while it is not.
_CAFFEINATE: subprocess.Popen | None = None


def _awake_macos(on: bool) -> bool:
    """macOS: `caffeinate`, the tool the system ships for exactly this.

    `-d` is the display assertion and `-i` keeps the machine itself from going
    idle — the pair of the two Windows flags. `-w <our pid>` ties the helper's
    life to ours: if the app is killed or crashes, the assertion goes with it
    instead of pinning the screen on until somebody reboots.

    An IOPMAssertion through ctypes would save the process, at the price of
    hand-rolled IOKit plumbing that has to be right on a machine this code is
    not developed on. caffeinate is the same assertion with Apple holding the
    end of it.
    """
    global _CAFFEINATE
    if not on:
        if _CAFFEINATE is not None:
            try:
                _CAFFEINATE.terminate()
            except Exception as ex:
                log.debug("😴 caffeinate was already gone: %s", ex)
            _CAFFEINATE = None
        return True
    if _CAFFEINATE is not None and _CAFFEINATE.poll() is None:
        return True                       # still holding from an earlier arm
    _CAFFEINATE = subprocess.Popen(
        ["caffeinate", "-d", "-i", "-w", str(os.getpid())])
    return True


# The private session-bus connection that holds the Linux inhibit, by name.
_INHIBIT_BUS = "dancesport-wake-lock"
_INHIBITED = False


def _awake_linux(on: bool) -> bool:
    """Linux: org.freedesktop.ScreenSaver.Inhibit, the call GNOME, KDE, Xfce,
    Cinnamon and MATE answer, on X11 and Wayland alike. (systemd-inhibit's
    idle lock is no substitute: GNOME blanks the screen regardless.)

    The inhibit belongs to the bus connection that asked for it, and the
    desktop drops it when that connection goes away. So it is asked on a
    private connection, and closing that connection is the release: no cookie
    to hand back (UnInhibit wants a uint32 PySide has no way to name), and if
    the app dies the hold dies with it, like caffeinate's -w on macOS."""
    global _INHIBITED
    from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
    if not on:
        if _INHIBITED:
            QDBusConnection.disconnectFromBus(_INHIBIT_BUS)
            _INHIBITED = False
        return True
    if _INHIBITED:
        return True
    bus = QDBusConnection.connectToBus(QDBusConnection.BusType.SessionBus,
                                       _INHIBIT_BUS)
    if not bus.isConnected():
        log.warning("☀️ No session bus, the screen cannot be kept awake")
        QDBusConnection.disconnectFromBus(_INHIBIT_BUS)
        return False
    screensaver = QDBusInterface("org.freedesktop.ScreenSaver",
                                 "/org/freedesktop/ScreenSaver",
                                 "org.freedesktop.ScreenSaver", bus)
    reply = screensaver.call("Inhibit", "DanceSport Player",
                             "Music is playing or the presenter screen is up")
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        log.warning("☀️ The desktop refused the wake lock\n"
                    "error: %s", reply.errorMessage())
        QDBusConnection.disconnectFromBus(_INHIBIT_BUS)
        return False
    _INHIBITED = True
    return True


def keep_display_awake(on: bool) -> bool:
    """Hold the screensaver and the display timeout off while the desk works —
    or hand the machine back to its normal idle timers.

    Both systems count idle time from the mouse and the keyboard, never from
    what comes out of the speakers. An hour of music with nobody touching the
    desk therefore blanks the screen and starts the screensaver, over the
    presenter beamer as well — which is the one screen the hall is looking at.

    Returns True when the state was really applied."""
    fn = {"win32": _awake_windows, "darwin": _awake_macos,
          "linux": _awake_linux}.get(sys.platform)
    if fn is None:
        return False
    try:
        if not fn(on):
            return False
    except Exception as ex:
        log.warning("☀️ Wake lock unavailable\n"
                    "on: %s\n"
                    "error: %s", on, ex)
        return False
    log.info("☀️ Screen kept awake" if on else
             "😴 Screen released to the normal timeout")
    return True
