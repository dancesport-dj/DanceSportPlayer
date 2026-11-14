#!/usr/bin/env python3
"""One long marker line in a playlist does not freeze the import (review 6.C).

Run:  py -m unittest tests.planner.playlist.test_m3u_header_backtracking -v

The round and dance header patterns had `\\s*`, a lazy `(.*?)` and `\\s*` in a
row. On `# ═` followed by many spaces and one other character the matcher
tried every split of the spaces: 1,600 spaces took 3.6 s and 8.6 s, x8 per
doubling. The import runs the round pattern over every line on the GUI
thread, so a damaged or crafted file hung the app.
"""

import time
import unittest

from planner.playlist import m3u


class HeaderBacktrackingTest(unittest.TestCase):

    def _quick(self, pattern, line):
        start = time.perf_counter()
        m = pattern.match(line)
        self.assertLess(time.perf_counter() - start, 0.05, f"{len(line)} chars")
        return m

    def test_a_long_marker_line_is_matched_at_once(self):
        for bar in ("═", "─"):
            for n in (300, 480, 2000, 20000):
                line = f"# {bar}" + " " * n + "x"
                with self.subTest(bar=bar, n=n):
                    self.assertIsNone(self._quick(m3u._IMPORT_ROUND_RE, line))
                    self.assertIsNone(self._quick(m3u._IMPORT_DANCE_RE, line))

    def test_the_headers_still_read(self):
        m = m3u._IMPORT_ROUND_RE.match("# ═══ Vorrunde (3 Heats) ═══")
        self.assertEqual(m.group(1).strip(), "Vorrunde")
        m = m3u._IMPORT_ROUND_RE.match("#═ Finale (A) ( 1 heat )═")
        self.assertEqual(m.group(1).strip(), "Finale (A)")
        m = m3u._IMPORT_DANCE_RE.match("# ─── Wiener Walzer ───")
        self.assertEqual(m.group(1).strip(), "Wiener Walzer")
        self.assertIsNone(m3u._IMPORT_DANCE_RE.match("# ─── Walzer"))


if __name__ == "__main__":
    unittest.main()
