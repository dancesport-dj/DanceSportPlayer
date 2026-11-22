"""Fuzz tests: malformed input into what the app reads from outside.

A fuzz test hands a reader bytes or text it was never written for - a damaged
tag, a hand-edited pack, a model's answer - and checks the one thing every
input must keep: the reader raises nothing its caller does not catch. Each
test names that caller next to the exceptions it allows; read the call site
before widening one.

The modules sit beside the code they test (`tests/<area>/.../test_*_fuzz.py`)
so the commit hook runs them with their area. Per commit they try a few dozen
inputs each; a long run takes more:

    DANCEPLAYLIST_FUZZ_SCALE=100 .venv\\Scripts\\python.exe -m pytest -n0 -k fuzz tests

or coverage-guided, for hours, with tools/dev/hypofuzz_run.py. A failure prints
the smallest input that breaks it; add it as an `@example` with the fix.
Every seed here is made up - nothing from a real library (see
tests/app/test_publish_sync.py, which scans fixtures for private names).
"""
import copy
import os

from hypothesis import HealthCheck, settings
from hypothesis import strategies as st

SCALE = max(1, int(os.environ.get("DANCEPLAYLIST_FUZZ_SCALE", "1") or 1))


def fuzz(examples: int = 60) -> settings:
    """Settings for one fuzz test: `examples` per commit, times the scale."""
    return settings(max_examples=examples * SCALE, deadline=None,
                    suppress_health_check=[HealthCheck.too_slow,
                                           HealthCheck.function_scoped_fixture,
                                           HealthCheck.differing_executors])


# Text a reader of this app meets: dance and class codes, the separators of a
# comment field, ffmpeg's and fpcalc's keys, a model's JSON fences, and the
# characters that broke text handling before (BOM, RTL mark, ligatures).
TOKENS = ("LW", "WW", "SF", "TG", "QS", "CC", "SA", "RB", "PD", "JV", "29", "30.5",
          ";", ",", ":", ".", "-", " ", "\n", "\r\n", "\t", "\x00", "instr",
          "vocal_f", "A", "B", "C", "D", "S", "Hgr", "Sen", "Jun", "Kin", "I", "II",
          "Standard", "Latein", "Uhr", "10:30", "23:15", "2315", "999999999999",
          "silence_start: ", "silence_end: ", "silence_duration: ", "max_volume: ",
          "mean_volume: ", "dB", "-inf", "nan", "inf", "Noise floor dB: ",
          "DURATION=", "FINGERPRINT=", "1,2,3", "{", "}", "[", "]", '"', "```json",
          "```", '"swaps"', '"notes"', '"queries"', '"playlist"', '"artist"',
          '"title"', "null", "true", "1e999", "-0", "ß", "Ä", "\u202e", "\ufeff", "ﬁ",
          "#EXTM3U", "#EXTINF:", "-1,", "C:\\", "\\\\server\\share\\", "../", "%20")

texts = st.one_of(
    st.text(max_size=80),
    st.lists(st.one_of(st.sampled_from(TOKENS), st.text(max_size=4)), max_size=40)
    .map("".join))

# The numbers a reader forgets: Python's json reads Infinity and NaN, and a
# plain float draw seldom lands on them.
EDGE_NUMBERS = st.sampled_from((float("inf"), float("-inf"), float("nan"), -1, 0,
                                2 ** 63, -(2 ** 63), 10 ** 400, 1e-320))
LEAVES = (st.none() | st.booleans() | st.integers() | st.floats() | EDGE_NUMBERS
          | st.text(max_size=8))

json_values = st.recursive(
    LEAVES,
    lambda kids: st.lists(kids, max_size=5) | st.dictionaries(st.text(max_size=8), kids,
                                                             max_size=6),
    max_leaves=25)


def json_docs(keys) -> st.SearchStrategy:
    """JSON that looks like one of the app's documents: its own keys, with any
    value under them, mixed with any other JSON at all."""
    vals = st.recursive(
        LEAVES,
        lambda kids: st.lists(kids, max_size=5)
        | st.dictionaries(st.sampled_from(list(keys)) | st.text(max_size=6), kids,
                          max_size=6),
        max_leaves=30)
    return st.one_of(st.dictionaries(st.sampled_from(list(keys)), vals, max_size=8),
                     json_values)


def _parts(doc, at=()):
    """The path of every value inside `doc`, the root left out."""
    items = (doc.items() if isinstance(doc, dict)
             else enumerate(doc) if isinstance(doc, list) else ())
    for k, v in items:
        yield (*at, k)
        yield from _parts(v, (*at, k))


@st.composite
def perturbed(draw, seed):
    """The JSON document `seed` with up to five of its parts swapped for any
    JSON or left out: a file as the app writes it, edited by hand or by a
    newer build, so the reader gets past its first checks."""
    doc = copy.deepcopy(seed)
    for _ in range(draw(st.integers(1, 5))):
        parts = list(_parts(doc))
        if not parts:
            break
        *up, last = draw(st.sampled_from(parts))
        parent = doc
        for k in up:
            parent = parent[k]
        if isinstance(parent, dict) and draw(st.booleans()):
            del parent[last]
        else:
            parent[last] = draw(json_values)
    return doc


@st.composite
def mutated(draw, seed: bytes) -> bytes:
    """`seed` with up to 12 bytes changed, runs inserted or cut out."""
    data = bytearray(seed)
    for _ in range(draw(st.integers(1, 12))):
        op = draw(st.integers(0, 2))
        i = draw(st.integers(0, max(0, len(data) - 1)))
        if op == 0 and data:
            data[i] = draw(st.integers(0, 255))
        elif op == 1:
            data[i:i] = draw(st.binary(max_size=8))
        else:
            del data[i:i + draw(st.integers(1, 64))]
    return bytes(data)


# One silent MPEG-1 layer III frame (128 kbit/s, 44.1 kHz), as in test_apev2_tags.
MP3_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 413
