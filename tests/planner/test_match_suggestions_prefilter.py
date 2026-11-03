"""match_suggestions_to_library skips titles that cannot beat the best match; the
result must stay what matching every title in full gives."""
import random
import string
import unittest
from difflib import SequenceMatcher
from types import SimpleNamespace

from planner.generate.ai import match_suggestions_to_library
from planner.music.parsing import norm_title


def _brute(lib, suggestions, threshold=0.6):
    out = []
    for s in suggestions:
        target = norm_title(s.get("title", ""))
        best, best_r = None, 0.0
        if target:
            for e in lib.entries:
                nt = norm_title(e.title)
                if not nt:
                    continue
                r = SequenceMatcher(None, target, nt).ratio()
                if target in nt or nt in target:
                    r = max(r, 0.9)
                if r > best_r:
                    best_r, best = r, e
        owned = best is not None and best_r >= threshold
        out.append({"suggestion": s, "entry": best if owned else None, "ratio": best_r})
    return out


class MatchPrefilterTest(unittest.TestCase):
    def test_same_result_as_matching_every_title(self):
        rnd = random.Random(7)

        def word():
            return "".join(rnd.choice(string.ascii_lowercase[:8])
                           for _ in range(rnd.randint(2, 7)))

        def title():
            return " ".join(word() for _ in range(rnd.randint(1, 3)))

        lib = SimpleNamespace(entries=[SimpleNamespace(title=title()) for _ in range(400)])
        sugg = [{"artist": "", "title": title()} for _ in range(25)]
        sugg.append({"artist": "", "title": lib.entries[5].title + " live"})
        sugg.append({"artist": "", "title": ""})
        got = match_suggestions_to_library(lib, sugg)
        want = _brute(lib, sugg)
        self.assertEqual([(g["entry"], g["ratio"]) for g in got],
                         [(w["entry"], w["ratio"]) for w in want])


if __name__ == "__main__":
    unittest.main()
