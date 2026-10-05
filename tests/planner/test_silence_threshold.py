#!/usr/bin/env python3
"""Only REAL silence counts as silence.

Run:  py -m unittest tests.planner.test_silence_threshold -v

The probe ran at −30 dB, which is not silence — it is a fade-out still playing
(“Fare Thee Well” fades under it for twenty seconds, and the wall of red ⏱
cells in a party list was the result). Music stops being music somewhere around
the noise floor of a tape rip, so the threshold sits there instead, and every
span probed at the old one is dropped from the database the next time it opens:
the spans are content-addressed with no per-row version, exactly like the
cached dance detection.
"""

import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sil_thr_"))

import planner.db as pdb  # noqa: E402


class ThresholdTest(unittest.TestCase):

    def test_the_threshold_is_real_silence_not_a_fade(self):
        self.assertLessEqual(pdb.SILENCE_NOISE_DB, -45)

    def test_the_probe_asks_ffmpeg_for_that_threshold(self):
        from unittest import mock

        from shared import audio_probes
        seen = []

        def fake(cmd, *_a, **_kw):
            seen.append(cmd)
            return (0, "")

        with mock.patch.object(audio_probes, "_ffmpeg_probe", fake):
            audio_probes.detect_silences("ffmpeg", Path("x.mp3"))
        flt = seen[0][seen[0].index("-af") + 1]
        self.assertIn(f"noise={pdb.SILENCE_NOISE_DB}dB", flt)


class StaleSpansTest(unittest.TestCase):
    """A span probed at another threshold is wrong, not merely old."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_sil_thr_db_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)
        self.conn = pdb._db()

    def _restore(self):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def _reopen(self):
        pdb._DB_LOCAL.conn.close()
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.conn = pdb._db()

    def _spans(self):
        return self.conn.execute("SELECT fp FROM silences").fetchall()

    def _store(self, threshold: str | None):
        self.conn.execute("INSERT OR REPLACE INTO silences (fp, spans) "
                          "VALUES ('fp1', '[[100, 130]]')")
        if threshold is None:
            self.conn.execute("DELETE FROM app_meta WHERE key = 'silence_noise_db'")
        else:
            self.conn.execute("INSERT OR REPLACE INTO app_meta (key, value) "
                              "VALUES ('silence_noise_db', ?)", (threshold,))
        self.conn.commit()

    def test_spans_from_the_old_threshold_are_dropped(self):
        self._store("-30")
        self._reopen()
        self.assertEqual(self._spans(), [])

    def test_spans_from_a_database_that_never_noted_one_are_dropped(self):
        self._store(None)
        self._reopen()
        self.assertEqual(self._spans(), [])

    def test_spans_probed_at_the_current_threshold_are_kept(self):
        self._store(str(pdb.SILENCE_NOISE_DB))
        self._reopen()
        self.assertEqual(len(self._spans()), 1)

    def test_the_threshold_in_force_is_noted_for_the_next_start(self):
        self._store("-30")
        self._reopen()
        self.assertEqual(
            self.conn.execute("SELECT value FROM app_meta WHERE key = ?",
                              ("silence_noise_db",)).fetchone()[0],
            str(pdb.SILENCE_NOISE_DB))


if __name__ == "__main__":
    unittest.main(verbosity=2)
