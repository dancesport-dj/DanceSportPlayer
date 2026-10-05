#!/usr/bin/env python3
"""Tests for tools/announce_eq.py — the EQ baked into the announcement clips.

Run:  py -m unittest tests.app.test_announce_eq -v

The tool overwrites the operator's recordings, and the one thing that makes
that safe is that every run reads from the untouched master rather than from
the file the last run wrote. Get that wrong and the second --apply stacks a
second EQ on the first, with nothing left to go back to. So that is what is
tested here, not the sound.
"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import announce_eq as eq


class ChainTest(unittest.TestCase):

    def test_a_preset_is_one_ffmpeg_argument(self):
        self.assertEqual(eq.chain("clear"), ",".join(eq.PRESETS["clear"]))
        self.assertIn("highpass=f=110", eq.chain("clear"))

    def test_the_reference_preset_filters_nothing(self):
        # `off` exists to hear the clip untreated through the same re-encode.
        self.assertEqual(eq.chain("off"), "")

    def test_every_preset_ends_in_a_limiter(self):
        # The makeup gain of the compressor is what makes this necessary: a
        # loud word would otherwise clip in the hall rather than in a meter.
        for name, filters in eq.PRESETS.items():
            if not filters:
                continue
            self.assertTrue(filters[-1].startswith("alimiter"), name)

    def test_the_default_audition_plays_clips_that_exist(self):
        # A missing one is skipped without a word, so a clip renamed under it
        # (SA became SB) quietly dropped out of every audition.
        root = eq.announce._CLIP_DIR / eq.announce._CLIP_FALLBACK
        for voice in eq.announce._CLIP_GENDERS:
            for stem in eq.AUDITION_CLIPS:
                self.assertTrue((root / voice / f"{stem}.mp3").is_file(),
                                f"{voice}/{stem}")


class _ClipTree(unittest.TestCase):
    """Two recorded voices whose clips are files with known contents, so a
    "treated" file can be told apart from an untouched one by reading it."""

    def setUp(self):
        # The tool is a CLI and says what it is doing; under the full suite the
        # stream it would say it on is gone, so catch it rather than write to it.
        self.said = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.root = Path(tempfile.mkdtemp(prefix="dp_eq_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for gender in ("female", "male"):
            folder = self.root / gender
            folder.mkdir()
            for name in ("next_dance", "LW", "SA"):
                (folder / f"{name}.mp3").write_bytes(b"recorded " + name.encode())
        self.folder = self.root / "female"

    def fake_render(self, _ffmpeg, src, dst, _filters):
        """Stand in for ffmpeg: writes what it read, marked as treated."""
        dst.write_bytes(b"EQ(" + src.read_bytes() + b")")
        return True, ""


class MasterTest(_ClipTree):
    """Where the untouched recording lives, and that it stays untouched."""

    def test_the_masters_sit_beside_the_clips_not_among_them(self):
        clip = self.folder / "LW.mp3"
        eq.keep_master(clip)
        self.assertTrue((self.folder / eq.ORIGINAL_DIR / "LW.mp3").is_file())
        self.assertNotIn("LW.mp3",
                         [p.name for p in eq.clips_of(self.folder)
                          if p.parent.name == eq.ORIGINAL_DIR])

    def test_the_clip_list_never_picks_up_a_master(self):
        eq.keep_master(self.folder / "LW.mp3")
        self.assertEqual([p.name for p in eq.clips_of(self.folder)],
                         ["LW.mp3", "next_dance.mp3", "SA.mp3"])

    def test_a_master_that_exists_is_never_written_over(self):
        """The only untreated copy left — overwriting it with a treated clip
        would be the one unrecoverable mistake this tool can make."""
        clip = self.folder / "LW.mp3"
        eq.keep_master(clip)
        clip.write_bytes(b"EQ(recorded LW)")     # as an --apply leaves it
        eq.keep_master(clip)
        self.assertEqual(eq.master_of(clip).read_bytes(), b"recorded LW")


class _Stubbed(_ClipTree):
    """A clip tree whose ffmpeg is the fake above, so a treated file can be
    recognised by reading it."""

    def setUp(self):
        super().setUp()
        self._real_render = eq.render
        eq.render = self.fake_render
        self.addCleanup(setattr, eq, "render", self._real_render)


class ApplyTest(_Stubbed):

    def test_every_clip_of_the_voice_is_treated(self):
        done, failed = eq.apply_voice("ffmpeg", self.folder, "clear")
        self.assertEqual((done, failed), (3, 0))
        self.assertEqual((self.folder / "LW.mp3").read_bytes(),
                         b"EQ(recorded LW)")

    def test_a_second_run_does_not_stack_a_second_eq(self):
        """The whole reason the masters exist: --apply twice, or --apply with
        another preset, must treat the RECORDING again, not its own output."""
        eq.apply_voice("ffmpeg", self.folder, "clear")
        eq.apply_voice("ffmpeg", self.folder, "bright")
        self.assertEqual((self.folder / "LW.mp3").read_bytes(),
                         b"EQ(recorded LW)")

    def test_no_half_written_clip_is_left_behind(self):
        eq.render = lambda *a: (False, "Error while filtering")
        done, failed = eq.apply_voice("ffmpeg", self.folder, "clear")
        self.assertEqual((done, failed), (0, 3))
        # The clip is still the recording, and no scratch file survives.
        self.assertEqual((self.folder / "LW.mp3").read_bytes(), b"recorded LW")
        self.assertEqual([p.name for p in eq.clips_of(self.folder)],
                         ["LW.mp3", "next_dance.mp3", "SA.mp3"])
        # And it says which clip it could not treat, with ffmpeg's own words.
        self.assertIn("LW.mp3: Error while filtering", self.said.getvalue())

    def test_the_recordings_come_back(self):
        eq.apply_voice("ffmpeg", self.folder, "clear")
        self.assertEqual(eq.restore_voice(self.folder), 3)
        self.assertEqual((self.folder / "LW.mp3").read_bytes(), b"recorded LW")

    def test_restoring_a_voice_that_was_never_treated_changes_nothing(self):
        self.assertEqual(eq.restore_voice(self.folder), 0)
        self.assertEqual((self.folder / "LW.mp3").read_bytes(), b"recorded LW")

    def test_an_interrupted_run_leaves_no_scratch_file_among_the_clips(self):
        """A scratch file named *.mp3 left in the voice folder would be played
        as a clip, and treated as one by the next --apply."""
        def interrupted(_ffmpeg, _src, dst, _filters):
            dst.write_bytes(b"half an EQ")
            raise KeyboardInterrupt
        eq.render = interrupted
        with self.assertRaises(KeyboardInterrupt):
            eq.apply_voice("ffmpeg", self.folder, "clear")
        self.assertEqual(sorted(p.name for p in self.folder.iterdir() if p.is_file()),
                         ["LW.mp3", "SA.mp3", "next_dance.mp3"])
        self.assertEqual((self.folder / "LW.mp3").read_bytes(), b"recorded LW")


class RerecordedTest(_Stubbed):
    """A clip recorded again after an --apply is the new master, not the old one."""

    def rerecord(self, name: str, take: bytes) -> Path:
        # As the speech script writes it: straight over the clip, after the note.
        clip = self.folder / name
        clip.write_bytes(take)
        note = (self.folder / eq.NOTE_NAME).stat().st_mtime_ns
        os.utime(clip, ns=(note + 10**9, note + 10**9))
        return clip

    def test_applying_again_treats_the_new_take(self):
        eq.apply_voice("ffmpeg", self.folder, "clear")
        clip = self.rerecord("LW.mp3", b"new take LW")
        eq.apply_voice("ffmpeg", self.folder, "clear")
        self.assertEqual(clip.read_bytes(), b"EQ(new take LW)")
        self.assertEqual(eq.master_of(clip).read_bytes(), b"new take LW")
        # The clips that were not recorded again still come from their masters.
        self.assertEqual((self.folder / "SA.mp3").read_bytes(), b"EQ(recorded SA)")

    def test_restoring_keeps_the_new_take(self):
        eq.apply_voice("ffmpeg", self.folder, "clear")
        clip = self.rerecord("LW.mp3", b"new take LW")
        eq.restore_voice(self.folder)
        self.assertEqual(clip.read_bytes(), b"new take LW")
        self.assertEqual((self.folder / "SA.mp3").read_bytes(), b"recorded SA")


class NoteTest(_Stubbed):
    """What was baked in is written down beside the clips it describes."""

    def note(self) -> Path:
        return self.folder / eq.NOTE_NAME

    def test_treating_a_voice_writes_down_what_it_now_carries(self):
        eq.apply_voice("ffmpeg", self.folder, "clear")
        said = self.note().read_text(encoding="utf-8")
        self.assertIn("**clear**", said)
        self.assertIn("Clips treated: 3", said)
        # The parameters themselves, so the note answers "what exactly" and not
        # only "which preset" - a preset can be retuned, a baked clip cannot.
        for f in eq.PRESETS["clear"]:
            self.assertIn(f, said)

    def test_treating_it_again_replaces_the_note(self):
        eq.apply_voice("ffmpeg", self.folder, "clear")
        eq.apply_voice("ffmpeg", self.folder, "bright")
        said = self.note().read_text(encoding="utf-8")
        self.assertIn("**bright**", said)
        self.assertNotIn("**clear**", said)
        self.assertIn("deesser=i=0.4", said)

    def test_a_note_never_outlives_the_clips_it_describes(self):
        eq.apply_voice("ffmpeg", self.folder, "clear")
        eq.restore_voice(self.folder)
        self.assertFalse(self.note().exists())

    def test_nothing_is_written_down_when_nothing_was_treated(self):
        eq.render = lambda *a: (False, "Error while filtering")
        eq.apply_voice("ffmpeg", self.folder, "clear")
        self.assertFalse(self.note().exists())

    def test_the_note_is_not_mistaken_for_a_clip(self):
        eq.apply_voice("ffmpeg", self.folder, "clear")
        self.assertEqual([p.name for p in eq.clips_of(self.folder)],
                         ["LW.mp3", "next_dance.mp3", "SA.mp3"])


class VoiceDirsTest(_ClipTree):

    def test_both_means_every_voice_installed(self):
        self.assertEqual([p.name for p in eq.voice_dirs(self.root, "both")],
                         ["female", "male"])

    def test_one_voice_is_worked_on_alone(self):
        self.assertEqual([p.name for p in eq.voice_dirs(self.root, "male")],
                         ["male"])

    def test_a_voice_that_was_never_recorded_is_not_invented(self):
        (self.root / "male").rename(self.root / "kid")
        self.assertEqual([p.name for p in eq.voice_dirs(self.root, "both")],
                         ["female"])


if __name__ == "__main__":
    unittest.main()
