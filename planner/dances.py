"""The ten tournament dances' tempo tables, in one place.

A leaf: it imports nothing from the planner, so planner.db (which models
imports) and planner.models can both read it without a circular import.
"""

# Tempo ranges (bars per minute) – same for all age classes and all start classes.
# Songs outside this range but within BELOW_TEMPO_EXT are still allowed, marked *.
TEMPO_RANGES: dict[str, dict[str, tuple[int, int]]] = {
    'LW': {'D': (28,30),'C': (28,30),'B': (28,30),'A': (28,30),'S': (28,30)},
    'TG': {'D': (31,33),'C': (31,33),'B': (31,33),'A': (31,33),'S': (31,33)},
    'WW': {'D': (58,60),'C': (58,60),'B': (58,60),'A': (58,60),'S': (58,60)},
    'SF': {'D': (28,30),'C': (28,30),'B': (28,30),'A': (28,30),'S': (28,30)},
    'QS': {'D': (50,52),'C': (50,52),'B': (50,52),'A': (50,52),'S': (50,52)},
    'CC': {'D': (30,32),'C': (30,32),'B': (30,32),'A': (30,32),'S': (30,32)},
    'SA': {'D': (50,52),'C': (50,52),'B': (50,52),'A': (50,52),'S': (50,52)},
    'RB': {'D': (24,26),'C': (24,26),'B': (24,26),'A': (24,26),'S': (24,26)},
    'PD': {'D': (58,60),'C': (58,60),'B': (58,60),'A': (58,60),'S': (58,60)},
    'JI': {'D': (41,43),'C': (41,43),'B': (41,43),'A': (41,43),'S': (41,43)},
}

# Beats per BAR (takt) per dance code. The filename label is a TAKT (bars/min); the
# librosa tempo estimator works in musical BPM (beats/min) = takt × beats-per-bar.
BEATS_PER_BAR = {"LW": 3, "TG": 2, "WW": 3, "SF": 4, "QS": 4,
                 "CC": 4, "SA": 2, "RB": 4, "PD": 2, "JI": 4}


def default_takt(dance: str | None) -> int | None:
    """The middle of a dance's standard takt range, None for an unknown dance."""
    ranges = TEMPO_RANGES.get(dance or "")
    if not ranges:
        return None
    lo, hi = ranges["D"]
    return (lo + hi) // 2
