"""🎧 Loud music on a headset: when to step in, and what the operator decided.

A volume that suits the hall's PA is a hearing injury in a headset. The desk
checks when it starts, when it plays, whenever the outputs change and whenever
the fader comes to rest; this module only decides, Qt-free.

Is it worn on the head? Windows says so itself: every output reports a form
factor, and an audio interface like a Maya is "line level", never a headset.
Where the system does not say (macOS, Linux, or a driver that reports plain
"speakers" for a USB headset) the output's name decides. A Mac's built-in jack
("External Headphones") is the exception: it may as well feed a speaker, so it
is asked about only with everything at 100 %.

How loud is too loud? What reaches the ears is the app's fader times the
system's volume slider, so 100 % in the app on a Windows slider at 7 % is fine
and 100 % on both is not. The operator is asked once per level: what they
confirmed (raised it again, or kept it lowered) is remembered for this run of
the app, and only a LOUDER setting than that is asked about again.
"""
HEADSET_WORDS = ("headset", "headphone", "kopfhörer", "kopfhoerer", "earphone",
                 "earbud", "earpods", "airpods", "buds", "beats", "hands-free",
                 "handsfree", "freisprech")
LOUD = 0.7    # fader x system slider above this is too loud for a headset
JACK_LEVEL = 0.99   # the Mac jack is asked about only from here on
SAFE = 0.7    # what it is pulled down to (of that same product)
SAFE_FULL = 0.5   # ... when the app fader is at 100 %: a bigger step down
LOWER = 0.5       # the second, lower button: one step below SAFE
LOWER_FULL = 0.3  # ... and below SAFE_FULL

# The Mac's built-in 3.5 mm jack is called "External Headphones" (localised)
# whatever is plugged in, and a powered speaker on a cinch cable is as likely as
# a headset. Nothing tells them apart, so the jack is only asked about when
# everything is at 100 % (JACK_LEVEL): that is wrong for ears and speakers alike.
JACK_NAMES = ("external headphones", "externe kopfhörer", "externe kopfhoerer",
              "casque externe", "auriculares externos", "cuffie esterne")

# Windows PKEY_AudioEndpoint_FormFactor: what the driver says the output is.
FORM_HEADPHONES = 3
FORM_HEADSET = 5
# Remote network device, line level (audio interface, mixer), S/PDIF, HDMI /
# DisplayPort: never on a head, whatever their name says.
FORM_NOT_WORN = (0, 2, 8, 9)

ASK = "ask"     # hold the play, ask: keep this volume or reduce it
WARN = "warn"   # asked about this level already: a red toast is enough


def is_headset(output_name: str, form_factor: int | None = None,
               level: float = 0.0) -> bool:
    """Whether an output is worn on the head: its reported form factor where
    there is one, else its name. The Mac jack counts only at `level` 100 %."""
    if form_factor in (FORM_HEADPHONES, FORM_HEADSET):
        return True
    if form_factor in FORM_NOT_WORN:
        return False
    name = (output_name or "").lower()
    if any(j in name for j in JACK_NAMES):
        return level >= JACK_LEVEL
    return any(w in name for w in HEADSET_WORDS)


def safe_volume(master: float = 1.0, volume: float = 0.0) -> float:
    """The app fader that, with the system slider at `master`, gives SAFE, or
    SAFE_FULL when the fader now stands at 100 %."""
    target = SAFE_FULL if volume >= JACK_LEVEL else SAFE
    return min(1.0, target / max(master, target))


def lower_volume(master: float = 1.0, volume: float = 0.0) -> float:
    """Like safe_volume, one step lower still: LOWER_FULL when the fader stands
    at 100 % (where safe_volume gives SAFE_FULL), else LOWER."""
    target = LOWER_FULL if volume >= JACK_LEVEL else LOWER
    return min(1.0, target / max(master, target))


class HeadsetGuard:
    """The session's memory of how loud the operator has been asked about."""

    def __init__(self):
        self.asked = 0.0    # the loudest level (fader x slider) a question was answered for
        self.warned = 0.0   # the level the last toast was shown for

    def assess(self, output_name: str, volume: float, master: float = 1.0,
               form_factor: int | None = None) -> str | None:
        """ASK for a level louder than anything asked about this session (the
        dialog, before the music starts); WARN for a loud level that was asked
        about already (the red toast, once per level); else None."""
        level = volume * master
        if level <= LOUD + 0.005 or not is_headset(output_name, form_factor, level):
            self.warned = 0.0
            return None
        if level > self.asked + 0.005:
            self.warned = level
            return ASK
        if abs(level - self.warned) <= 0.005:
            return None
        self.warned = level
        return WARN

    def remember(self, level: float) -> None:
        """A question was asked at `level` (fader x slider as it was found, not
        as the operator then set it): that level cannot get louder, so a raise
        back to it gets the toast only. Anything louder asks again."""
        self.asked = max(self.asked, level)
