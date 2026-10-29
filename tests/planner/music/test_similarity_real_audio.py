"""Find similar on real audio: analysed, stored, read back, compared.

Run:  py -m unittest tests.planner.music.test_similarity_real_audio -v

Every other similarity test hands the metric made-up feature vectors, and the
analysis tests stub analyze_file out. So nothing checked that librosa's
analysis of an actual sound, packed into the audio DB and unpacked again,
still puts a sound next to its own kind. Here three short WAVs are built from
numpy: a pulsed tone, the same tone under different faint noise (as two rips of
one record), and noise bursts at another tempo.
"""
import importlib.util
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from planner.models import MusicEntry
from tests.db_support import use_scratch_db

_SR = 22050
_SECONDS = 30


def _write_wav(path: Path, y) -> None:
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_SR)
        w.writeframes(pcm.tobytes())


def _pulsed_tone(seed: int):
    """A 220 Hz tone with two harmonics, swelling twice a second (120 BPM)."""
    t = np.arange(_SR * _SECONDS) / _SR
    pulse = 0.5 + 0.5 * (np.sin(2 * np.pi * 2.0 * t) > 0.6)
    y = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((220, .5), (440, .25), (660, .12)))
    noise = np.random.default_rng(seed).standard_normal(t.size)
    return 0.6 * y * pulse + 1e-3 * noise


def _noise_bursts(seed: int):
    """White noise in short bursts, three a second (180 BPM)."""
    t = np.arange(_SR * _SECONDS) / _SR
    env = (np.mod(t * 3.0, 1.0) < 0.15).astype(float)
    return 0.5 * np.random.default_rng(seed).standard_normal(t.size) * env


@unittest.skipUnless(importlib.util.find_spec("librosa"), "librosa not installed")
class RealAudioSimilarityTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from planner.music.analysis import analyze_file
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_sim_audio_"))
        cls.addClassCleanup(shutil.rmtree, cls.dir, True)
        cls.paths = {}
        cls.fresh = {}
        for name, y in (("tone", _pulsed_tone(1)), ("tone_again", _pulsed_tone(2)),
                        ("bursts", _noise_bursts(3))):
            cls.paths[name] = cls.dir / f"{name}.wav"
            _write_wav(cls.paths[name], y)
            cls.fresh[name] = analyze_file(cls.paths[name])

    def stored(self) -> dict:
        """The analyses put into a scratch DB and read back by a new cache,
        as the next start of the app reads them."""
        import planner.music.db as pdb
        use_scratch_db(self, self.dir / f"{self._testMethodName}.db")
        cache = pdb.AudioCache()
        for name, path in self.paths.items():
            cache.put(path, self.fresh[name])
        cache.save()
        again = pdb.AudioCache()
        return {name: again.get(path) for name, path in self.paths.items()}

    def entries(self, feats: dict) -> list[MusicEntry]:
        out = []
        for name, path in self.paths.items():
            e = MusicEntry(path=path, title=name)
            e.features = feats[name]
            out.append(e)
        return out

    def scores(self, feats: dict, method: str) -> dict[str, float]:
        from planner.music.similarity import timbre_similarity
        sims = timbre_similarity(feats["tone"], self.entries(feats), method)
        return {Path(p).stem: s for p, s in sims.items()}

    def test_the_tempo_is_read_off_the_audio(self):
        self.assertAlmostEqual(self.fresh["tone"].bpm, 120, delta=6)
        self.assertAlmostEqual(self.fresh["bursts"].bpm, 180, delta=9)

    def test_the_analysis_reads_back_from_the_db_unchanged(self):
        stored = self.stored()
        for name, feat in self.fresh.items():
            back = stored[name]
            self.assertIsNotNone(back, f"{name}: nothing read back")
            for field in ("bpm", "centroid", "rms"):
                self.assertEqual(getattr(back, field), getattr(feat, field), f"{name}.{field}")
            for field in ("mfcc", "mfcc_mean", "mfcc_cov"):
                np.testing.assert_array_equal(
                    np.asarray(getattr(back, field), dtype=np.float32),
                    np.asarray(getattr(feat, field), dtype=np.float32),
                    err_msg=f"{name}.{field}")

    def test_the_same_record_scores_near_one_and_another_sound_far_below(self):
        stored = self.stored()
        # The Gaussian's score is absolute; librosa's is z-scored across the
        # pool, so with three titles only the gap between them says anything.
        self.assertGreater(self.scores(stored, "gaussian_kl")["tone_again"], 0.85)
        for method in ("gaussian_kl", "librosa"):
            with self.subTest(method=method):
                sims = self.scores(stored, method)
                self.assertGreater(sims["tone_again"] - sims["bursts"], 0.5, sims)

    def test_the_stored_analysis_scores_as_the_fresh_one(self):
        stored = self.stored()
        for method in ("gaussian_kl", "librosa"):
            with self.subTest(method=method):
                fresh, back = self.scores(self.fresh, method), self.scores(stored, method)
                for name in self.paths:
                    self.assertAlmostEqual(back[name], fresh[name], places=6, msg=name)


if __name__ == "__main__":
    unittest.main()
