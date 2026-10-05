"""What the analysed sound of a track says, in three digits.

The database keeps 84 numbers per analysed track — 60 MFCC dims (timbre), 10
spectral-contrast dims (brightness) and 14 rhythm dims (groove) — plus the mean
loudness and the spectral centroid. None of that is worth handing to a language
model as numbers: it cannot hear a covariance matrix, and 600 rows of floats
would drown the catalog it is supposed to read.

What a model CAN use is where a track sits *among its own kind*. So every track
gets three digits, 1 to 5, each one a fifth of its own dance:

    energy      how loud it sits           (rms)
    bright      how much high end it has   (spectral centroid)
    drive       how hard the beat pushes   (mean onset strength)

A "155" samba is a quiet, bright, hard-driving one; a "511" is loud, dark and
soft-edged. Comparing two codes says something real about how a heat will feel;
comparing raw MFCCs would not.

There is no chroma / key data in the database at all, so nothing here — and
nothing the model is told — speaks about harmony.
"""
import logging

log = logging.getLogger("dancesport.sound")

# How many steps a code has. 5 keeps every step meaningful: with 3 nearly
# everything lands in the middle, with 10 the difference is noise.
_BUCKETS = 5

# Offset of the mean onset strength inside the 84-dim vector AudioFeatures.mfcc
# holds: 60 MFCC | 10 spectral contrast | 12 tempogram bins | onset mean | onset
# std (see planner.db._AUDIO_FEAT_DIM). Vectors analysed under an older cache
# version can be shorter, so every read is length-guarded.
_ONSET_MEAN = 82


def _drive_of(feat) -> float | None:
    """Mean onset strength — how hard the beat hits, tempo aside."""
    vec = getattr(feat, "mfcc", None)
    if vec is None or len(vec) <= _ONSET_MEAN:
        return None
    return float(vec[_ONSET_MEAN])


def _buckets(values: list[float]) -> list[int]:
    """Rank `values` into 1.._BUCKETS, evenly by position, not by distance.

    A dance whose tracks are all mastered loud still gets its quiet fifth —
    which is the point: the code says where a track sits among its own kind,
    not what its absolute loudness is."""
    n = len(values)
    if n < _BUCKETS:
        # Too few to split into fifths without lying about the spread.
        return [(_BUCKETS + 1) // 2] * n
    out = [1] * n
    for rank, i in enumerate(sorted(range(n), key=lambda i: values[i])):
        out[i] = min(_BUCKETS, 1 + rank * _BUCKETS // n)
    return out


def sound_codes(entries, *, dance_of=None) -> dict[str, tuple[int, int, int]]:
    """{path: (energy, bright, drive)} for every analysed track, per dance.

    Tracks with no audio analysis behind them are simply absent — the caller
    prints a dash for those rather than guessing.

    `dance_of(entry)` decides which group a track is ranked inside; the default
    is its `dance` code, and everything without one is ranked together.
    """
    groups: dict[str, list] = {}
    for e in entries:
        feat = getattr(e, "features", None)
        drive = _drive_of(feat) if feat is not None else None
        if feat is None or drive is None:
            continue
        code = (dance_of(e) if dance_of else getattr(e, "dance", None)) or "??"
        groups.setdefault(code, []).append(
            (str(e.path), float(feat.rms), float(feat.centroid), drive))

    out: dict[str, tuple[int, int, int]] = {}
    for rows in groups.values():
        energy = _buckets([r[1] for r in rows])
        bright = _buckets([r[2] for r in rows])
        drive = _buckets([r[3] for r in rows])
        for i, row in enumerate(rows):
            out[row[0]] = (energy[i], bright[i], drive[i])
    log.debug("🔊 sound codes\n"
              "tracks: %d\n"
              "dances: %d", len(out), len(groups))
    return out


def code_text(code) -> str:
    """'352' — or '---' for a track nothing has analysed yet."""
    return "".join(str(d) for d in code) if code else "---"
