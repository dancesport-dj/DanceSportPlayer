#!/usr/bin/env python3
"""Editing tags must not throw the cached analysis away.

Run:  py -m unittest tests.planner.test_retag_reattach -v

Everything expensive in the DB is keyed by the content fingerprint, and mp3tag
rewrites the file — so an evening of tidying tags used to orphan the features,
loudness, silences and embeddings of every touched track. The audio fingerprint
beside it skips the tag blocks, so the old rows can be found and copied onto the
new key.
"""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_retag_"))

from planner.db import (  # noqa: E402
    _AUDIO_FEAT_DIM, _FP_SAMPLE, AudioCache, AudioFeatures, _db,
    _fingerprints, _tag_offsets,
)

_AUDIO = bytes(range(256)) * 2048          # 512 KB of "music", stable across runs


def _synchsafe_bytes(n: int) -> bytes:
    return bytes(((n >> 21) & 0x7f, (n >> 14) & 0x7f, (n >> 7) & 0x7f, n & 0x7f))


def _mp3(audio: bytes = _AUDIO, front: int = 0, id3v1: bytes = b"") -> bytes:
    """A file shaped like an MP3: [ID3v2 tag] audio [ID3v1 block]."""
    head = b"ID3\x04\x00\x00" + _synchsafe_bytes(front) + b"T" * front if front else b""
    return head + audio + id3v1


def _v1(text: bytes) -> bytes:
    return b"TAG" + text.ljust(125, b"\x00")


class TagOffsetsTest(unittest.TestCase):
    """What counts as tag, from the two byte windows the fingerprint already reads."""

    def test_an_untagged_file_is_all_audio(self):
        self.assertEqual(_tag_offsets(_AUDIO[:64], _AUDIO[-64:]), (0, 0))

    def test_the_id3v2_size_is_read_synchsafe(self):
        blob = _mp3(front=300)
        self.assertEqual(_tag_offsets(blob[:512], blob[-512:])[0], 310)

    def test_a_trailing_id3v1_block_is_128_bytes(self):
        blob = _mp3(id3v1=_v1(b"Tusch"))
        self.assertEqual(_tag_offsets(blob[:512], blob[-512:])[1], 128)

    def test_an_ape_tag_is_measured_from_its_footer(self):
        ape = (b"APETAGEX" + (2000).to_bytes(4, "little") + (64).to_bytes(4, "little")
               + (1).to_bytes(4, "little") + (0).to_bytes(4, "little") + b"\x00" * 8)
        self.assertEqual(_tag_offsets(b"", b"x" * 100 + ape)[1], 64)


class AudioFingerprintTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_retag_f_"))

    def _write(self, name: str, blob: bytes) -> Path:
        p = self.dir / name
        p.write_bytes(blob)
        return p

    def test_the_content_fingerprint_is_the_one_the_database_already_holds(self):
        """Changing how it is computed would orphan every cached row at once."""
        blob = _AUDIO * 3
        p = self._write("plain.mp3", blob)
        h = hashlib.sha1()
        h.update(str(len(blob)).encode())
        h.update(blob[:_FP_SAMPLE])
        h.update(blob[-_FP_SAMPLE:])
        self.assertEqual(_fingerprints(p)[0],
                         f"{len(blob)}_{h.hexdigest()[:20]}")

    def test_a_retag_changes_the_content_key_but_not_the_audio_one(self):
        before = self._write("a.mp3", _mp3(front=120, id3v1=_v1(b"Old Title")))
        after = self._write("b.mp3", _mp3(front=4096, id3v1=_v1(b"New Title")))
        fp_before, afp_before = _fingerprints(before)
        fp_after, afp_after = _fingerprints(after)
        self.assertNotEqual(fp_before, fp_after)
        self.assertEqual(afp_before, afp_after)

    def test_a_cover_art_tag_larger_than_the_head_sample_still_matches(self):
        """The audio window then lies past the buffer — it gets re-read."""
        plain = self._write("plain2.mp3", _mp3())
        arty = self._write("arty.mp3", _mp3(front=_FP_SAMPLE + 4096))
        self.assertEqual(_fingerprints(plain)[1], _fingerprints(arty)[1])

    def test_a_short_jingle_sees_its_trailing_tag_too(self):
        """Under 512 KB nothing is read from the end for the content hash."""
        audio = bytes(range(256)) * 40      # 10 KB, a cartwall Tusch
        bare = self._write("t1.mp3", _mp3(audio))
        tagged = self._write("t2.mp3", _mp3(audio, front=64, id3v1=_v1(b"Tusch")))
        self.assertEqual(_fingerprints(bare)[1], _fingerprints(tagged)[1])

    def test_different_music_gets_a_different_audio_fingerprint(self):
        one = self._write("one.mp3", _mp3(_AUDIO, front=64))
        two = self._write("two.mp3", _mp3(_AUDIO[::-1], front=64))
        self.assertNotEqual(_fingerprints(one)[1], _fingerprints(two)[1])


def _features(bpm: float) -> AudioFeatures:
    return AudioFeatures(bpm=bpm, mfcc=[0.5] * _AUDIO_FEAT_DIM, centroid=1.0, rms=0.25,
                         mfcc_mean=[0.1] * 20, mfcc_cov=[0.2] * 400)


class ReattachTest(unittest.TestCase):
    """The whole point: re-tag the file on disk, keep what was measured."""

    @classmethod
    def setUpClass(cls):
        cls.cache = AudioCache()

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_retag_c_"))
        # Own music per test: tracks that really share their audio share their
        # analysis, which is the whole feature — but it would leak between tests.
        self.audio = self.id().encode().ljust(64, b"-") + _AUDIO
        self.track = self.dir / "song.mp3"
        self.track.write_bytes(_mp3(self.audio, front=120, id3v1=_v1(b"Old Title")))

    def _retag(self, path: Path, audio: bytes = None) -> None:
        """What mp3tag does: same music, a different tag block, new mtime."""
        path.write_bytes(_mp3(self.audio if audio is None else audio,
                              front=900, id3v1=_v1(b"New Title")))
        st = path.stat()
        os.utime(path, (st.st_atime, st.st_mtime + 60))

    def test_features_survive_a_tag_edit(self):
        self.cache.put(self.track, _features(120.0))
        self._retag(self.track)
        got = self.cache.get(self.track)
        self.assertIsNotNone(got)
        self.assertEqual(got.bpm, 120.0)

    def test_the_side_tables_come_along(self):
        self.cache.put(self.track, _features(96.0))
        self.cache.put_lufs(self.track, -14.5)
        self.cache.put_noise_floor(self.track, -61.0)
        self._retag(self.track)
        self.assertAlmostEqual(self.cache.get_lufs(self.track), -14.5)
        self.assertAlmostEqual(self.cache.get_noise_floor(self.track), -61.0)

    def test_a_replaced_file_does_not_inherit_the_old_analysis(self):
        """Different music at the same path — attaching would be a wrong BPM."""
        self.cache.put(self.track, _features(120.0))
        self._retag(self.track, audio=self.audio[::-1])
        self.assertIsNone(self.cache.get(self.track))

    def test_a_file_hashed_before_the_table_existed_can_still_be_protected(self):
        """`ensure_audio_fp` is the one pass an old library needs."""
        self.cache.put(self.track, _features(60.0))
        fp = self.cache.fingerprint(self.track)
        _db().execute("DELETE FROM audio_fps WHERE fp = ?", (fp,))
        self.cache._afp.pop(fp, None)

        self.assertTrue(self.cache.ensure_audio_fp(self.track))
        self.assertFalse(self.cache.ensure_audio_fp(self.track))   # already on record
        self._retag(self.track)
        self.assertEqual(self.cache.get(self.track).bpm, 60.0)

    def test_what_is_already_on_record_can_be_asked_for_in_one_query(self):
        """So the backfill pass skips those files without reading them."""
        fp = self.cache.fingerprint(self.track)
        self.assertIn(fp, self.cache.audio_fp_keys())

    def test_nothing_to_re_attach_is_not_an_error(self):
        fresh = self.dir / "never-seen.mp3"
        fresh.write_bytes(_mp3(self.audio[100:], front=64))
        self.assertIsNone(self.cache.get(fresh))


class AudioFingerprintLookupTest(unittest.TestCase):
    """`AudioCache.audio_fingerprint`: what a copy on another drive is matched by."""

    def setUp(self):
        import threading
        import planner.db as pdb
        self.pdb = pdb
        self.dir = Path(tempfile.mkdtemp(prefix="dp_afp_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)

    def _restore(self):
        try:
            self.pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        self.pdb.AUDIO_DB_FILE, self.pdb._DB_LOCAL, self.pdb._DB_INITIALIZED = self._saved

    def _file(self, name: str, data: bytes) -> Path:
        p = self.dir / name
        p.write_bytes(data)
        return p

    def test_two_drives_one_retagged_share_the_audio_fingerprint(self):
        cache = AudioCache()
        c = self._file("c.mp3", _mp3(front=120, id3v1=_v1(b"Old")))
        f = self._file("f.mp3", _mp3(front=900, id3v1=_v1(b"New")))
        self.assertNotEqual(cache.fingerprint(c), cache.fingerprint(f))
        self.assertEqual(cache.audio_fingerprint(c), cache.audio_fingerprint(f))

    def test_different_music_does_not_share_it(self):
        cache = AudioCache()
        a = self._file("a.mp3", _mp3())
        b = self._file("b.mp3", _mp3(_AUDIO[::-1]))
        self.assertNotEqual(cache.audio_fingerprint(a), cache.audio_fingerprint(b))

    def test_a_later_session_reads_it_off_the_database(self):
        c = self._file("c.mp3", _mp3(front=120))
        want = AudioCache().audio_fingerprint(c)
        real = self.pdb._fingerprints

        def no_read(_path):
            raise AssertionError("the file was read again")
        self.pdb._fingerprints = no_read
        self.addCleanup(setattr, self.pdb, "_fingerprints", real)
        self.assertEqual(AudioCache().audio_fingerprint(c), want)

    def test_a_file_hashed_before_the_table_existed_gets_one_now(self):
        cache = AudioCache()
        c = self._file("c.mp3", _mp3(front=120))
        fp = cache.fingerprint(c)
        want = cache._afp.pop(fp)
        _db().execute("DELETE FROM audio_fps WHERE fp = ?", (fp,))
        self.assertEqual(cache.audio_fingerprint(c), want)

    def test_a_missing_file_has_none(self):
        self.assertIsNone(AudioCache().audio_fingerprint(self.dir / "gone.mp3"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
