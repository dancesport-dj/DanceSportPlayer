"""🔬 One undecodable file that sorts first must not condemn the whole library (#61)."""
import unittest
from pathlib import Path

from planner.music import analysis


class ProbeSeveralTest(unittest.TestCase):

    def run_probe(self, verdicts, **kw):
        seen = []

        def probe(path):
            seen.append(path.name)
            return verdicts[path.name]

        paths = [Path(n) for n in verdicts]
        return analysis.probe_decode_backend_any(paths, probe=probe, **kw), seen

    def test_a_broken_first_file_is_skipped_when_the_next_decodes(self):
        why, seen = self.run_probe({"a.mp3": analysis.PROBE_FAILED, "b.mp3": None})
        self.assertIsNone(why)
        self.assertEqual(seen, ["a.mp3", "b.mp3"])

    def test_all_files_failing_is_a_failure(self):
        why, seen = self.run_probe(dict.fromkeys(
            ("a.mp3", "b.mp3", "c.mp3", "d.mp3"), analysis.PROBE_FAILED))
        self.assertEqual(why, analysis.PROBE_FAILED)
        self.assertEqual(len(seen), 3)    # a few tries, not the whole library

    def test_a_missing_backend_ends_it_at_once(self):
        why, seen = self.run_probe({"a.mp3": analysis.PROBE_NO_BACKEND, "b.mp3": None})
        self.assertEqual(why, analysis.PROBE_NO_BACKEND)
        self.assertEqual(seen, ["a.mp3"])

    def test_no_files_probes_nothing(self):
        self.assertIsNone(analysis.probe_decode_backend_any([], probe=lambda p: "x"))


if __name__ == "__main__":
    unittest.main()
