"""🔊 How loud each output is — the one place the factors get multiplied.

Three things make sound at the desk: the deck playing the round, the 🎛 cartwall
pads fired over it, and the ⏸ filler music between two titles. They hear
different subsets of the same five factors, and those subsets used to be spelled
out at each of the three call sites that pushed a number into Qt — so "does the
desk duck reach the pads?" could only be answered by reading three formulas and
hoping they agreed.

Qt-free on purpose: what a level IS, and how it ramps towards a new one, is
arithmetic. The mixin that owns the QAudioOutputs asks here for a number and
pushes it.
"""
_ANNOUNCE_DUCK = 0.3      # filler volume factor while the announcement runs
_CART_DUCK = 0.1          # …and while a 🎛 cartwall pad plays: ≈ −20 dB, not −10
_DUCK_DOWN_MS = 180       # how long the music takes to get out of the way…
_DUCK_UP_MS = 600         # …and how long it takes to come back, unhurried
_DESK_DUCK = 0.2          # 🔉 what the desk's duck button pulls everything to

_GAIN_RAMP_MS = 500       # a late loudness correction is a swell, not a step

# Level changes that ride a ramp step every this many ms. Setting a level in one
# go is an audible click, and the ear reads the click as damage to the music;
# 25 ms is under its resolution for a level change.
_RAMP_STEP_MS = 25

# Gain differences below these are not worth acting on: the first for a snap
# (the music is silent at that moment, so it may be finer), the second for a
# ramp under running music.
_GAIN_SNAP_EPS = 0.005
_GAIN_RAMP_EPS = 0.01


def _clamped(v: float) -> float:
    """A level Qt will accept. Five factors multiplied can leave the range only
    through a broken measurement, and a blast is worse than a wrong level."""
    return max(0.0, min(1.0, v))


class OutputMix:
    """The five factors behind every level, and the ramps that move them.

    Nothing here touches Qt or a widget, so the whole thing can be stepped in a
    test at whatever tick length the assertion needs.
    """

    step_ms = _RAMP_STEP_MS

    def __init__(self, base: float = 1.0):
        self.base = _clamped(base)   # the master fader, persisted
        self.gain = 1.0              # per-track loudness (R128) equalization
        self.fade = 1.0              # the timed fade-out of the running title
        self.duck = 1.0              # 🔈 pulled down while something speaks
        self.desk = 1.0              # 🔉 the desk's own duck button
        self.filler_fade = 1.0       # the ⏸ filler's fade in and out
        # Where the two ramped factors are headed, and how fast the gain gets
        # there (the duck's speed depends on its direction, so it is derived).
        self.gain_target = 1.0
        self.gain_step = 0.0
        self.duck_target = 1.0
        # Who is currently holding the music down — a set, not a counter, so an
        # unbalanced `off` cannot leave the music stuck (see duck_reason).
        self.duck_reasons: set[str] = set()

    # ── The three outputs ────────────────────────────────────────────────────

    def deck(self) -> float:
        """The round's own music: every factor applies to it."""
        return _clamped(self.base * self.gain * self.fade * self.duck * self.desk)

    def cartwall(self) -> float:
        """🎛 The pads follow the master fader and the 🔉 desk duck only.

        Not the deck track's fade or loudness gain — those belong to a title the
        pad is not part of — and not `duck`, which is the duck the pads
        themselves cause.
        """
        return _clamped(self.base * self.desk)

    def filler(self, share: float) -> float:
        """⏸ The filler between two titles, at `share` (0…1) of the master.

        It carries the announcement duck (the announcer speaks over the filler,
        which is the whole point of the break) but not the deck's loudness gain
        or fade — no deck title is running.
        """
        return _clamped(self.base * self.desk * self.duck * share
                        * self.filler_fade)

    # ── Moving them ──────────────────────────────────────────────────────────

    def set_base(self, v: float):
        self.base = _clamped(v)

    def set_desk_duck(self, on: bool) -> float:
        """🔉 Everything audible down to _DESK_DUCK, and back. Stepped, not
        ramped: it is a deliberate operator action, and it must be immediate."""
        self.desk = _DESK_DUCK if on else 1.0
        return self.desk

    def duck_reason(self, reason: str, on: bool):
        """Ref-counted duck: the announcer and the 🎛 cartwall both pull the
        music down, and whichever of them ends first must not lift it back up
        over the other.

        A set rather than a counter — reasons are idempotent, so an unbalanced
        `off` (the announcer's 8 s give-up watchdog exists precisely because one
        can happen) cannot leave the music stuck down."""
        if on:
            self.duck_reasons.add(reason)
        else:
            self.duck_reasons.discard(reason)
        # Each reason pulls to its own depth and the deepest wins: a pad has to
        # cut through running music, a voice only needs room next to it.
        self.duck_target = min(
            (_CART_DUCK if r == "cartwall" else _ANNOUNCE_DUCK
             for r in self.duck_reasons), default=1.0)

    def load_gain(self, gain: float):
        """A newly loaded title's loudness gain: in force before its first
        sample, so there is nothing audible to ramp and any ramp still aimed at
        the previous title is over."""
        self.gain = self.gain_target = gain
        self.gain_step = 0.0

    def snap_gain(self, target: float) -> bool:
        """Put the loudness gain at `target` with no ramp, for the moment the
        music is not audible anyway (a resume). False when it is already there."""
        if abs(target - self.gain) < _GAIN_SNAP_EPS:
            return False
        self.gain = self.gain_target = target
        return True

    def ramp_gain_to(self, target: float) -> bool:
        """Aim the loudness gain at `target`, reached over _GAIN_RAMP_MS — for a
        measurement that landed after the title already started. False when it is
        close enough that a correction under running music would only be heard
        as a wobble."""
        if abs(target - self.gain) < _GAIN_RAMP_EPS:
            return False
        self.gain_target = target
        self.gain_step = abs(target - self.gain) * self.step_ms / _GAIN_RAMP_MS
        return True

    @property
    def settled(self) -> bool:
        """Both ramps have arrived — nothing left for `step` to do."""
        return self.duck == self.duck_target and self.gain == self.gain_target

    def step(self) -> bool:
        """Advance both ramps by one tick.

        Returns True when the loudness gain LANDED on its target in this very
        step: the player card shows the gain as a dB readout, and it wants
        telling once, when the number stops moving.
        """
        if self.duck != self.duck_target:
            span = _DUCK_DOWN_MS if self.duck_target < self.duck else _DUCK_UP_MS
            step = (1.0 - _ANNOUNCE_DUCK) * self.step_ms / span
            if abs(self.duck_target - self.duck) <= step:
                self.duck = self.duck_target
            else:
                self.duck += step if self.duck_target > self.duck else -step
        landed = False
        if self.gain != self.gain_target:
            if self.gain_step <= 0 or abs(self.gain_target - self.gain) <= self.gain_step:
                self.gain = self.gain_target
                landed = True
            else:
                self.gain += (self.gain_step if self.gain_target > self.gain
                              else -self.gain_step)
        return landed
