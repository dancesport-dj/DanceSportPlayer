"""📦 Fuzz: a venue pack is a file somebody else hands over.

Callers: gui/window/main_export.py (`read_pack`) and the import worker
(`stage_import` -> `extract_music`) catch VenuePackError and OSError, nothing
else. So that is all a damaged pack may raise, and the music must never land
outside the folder the operator picked, whatever names the pack carries.
"""
import contextlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from hypothesis import example, given
from hypothesis import strategies as st

from planner.event import venue_pack as vp
from tests.fuzz_support import MP3_FRAME, fuzz, json_docs, json_values, mutated

ARC = "music/LW/Song 01 (LW 29).mp3"


def _seed() -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(vp.MANIFEST, json.dumps(
            {"format": vp.FORMAT, "version": vp.VERSION,
             "files": [vp.SETTINGS_FILE],
             "music": {"F:\\musik\\Song 01 (LW 29).mp3": ARC},
             "created": "2026-11-17"}))
        z.writestr(vp.SETTINGS_FILE, json.dumps({"library_dir": "F:\\musik"}))
        z.writestr(ARC, MP3_FRAME * 4)
    return b.getvalue()


SEED = _seed()

# Member names a crafted pack could carry to climb out of the target folder.
hostile_names = st.lists(st.sampled_from(
    ["music", "..", ".", "", "C:", "C:\\", "\\\\srv\\share", "/", "x", "a.mp3",
     "b.flac", "run.bat", "con", "aux.mp3", "LW", "..\\..", "a/../../b.mp3"]),
    min_size=1, max_size=6).map("/".join)


class VenuePackFuzzTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _write(self, data: bytes) -> Path:
        src = self.root / "fuzz.dpvenue"
        src.write_bytes(data)
        return src

    @fuzz(80)
    @given(mutated(SEED))
    def test_a_damaged_pack_raises_only_a_pack_error(self, data):
        src = self._write(data)
        for step in (vp.read_pack, lambda s: vp.extract_music(s, self.root / "d")):
            with contextlib.suppress(vp.VenuePackError, OSError):
                step(src)

    @fuzz(80)
    @given(json_docs(["format", "version", "files", "music", "created"]))
    @example({"format": vp.FORMAT, "version": vp.VERSION, "files": None})
    @example({"format": vp.FORMAT, "version": 1.5})
    def test_any_manifest_is_read_or_refused(self, manifest):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr(vp.MANIFEST, json.dumps(manifest))
            z.writestr(vp.SETTINGS_FILE, json.dumps({}))
        src = self._write(b.getvalue())
        try:
            pack = vp.read_pack(src)
        except vp.VenuePackError:
            return
        self.assertIsInstance(pack.docs, dict)
        self.assertIsInstance(pack.music, dict)

    @fuzz(40)
    @given(st.sampled_from(sorted(vp.PACK_FILES)), json_values)
    def test_any_document_is_read_or_refused(self, name, doc):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr(vp.MANIFEST, json.dumps(
                {"format": vp.FORMAT, "version": vp.VERSION, "files": [name]}))
            z.writestr(name, json.dumps(doc))
        with contextlib.suppress(vp.VenuePackError):
            vp.read_pack(self._write(b.getvalue()))

    @fuzz(80)
    @given(st.lists(hostile_names, min_size=1, max_size=4, unique=True))
    @example(["music/../../escape.mp3"])
    @example(["music/C:/escape.mp3"])
    def test_music_never_lands_outside_the_chosen_folder(self, names):
        b = io.BytesIO()
        music = {}
        with zipfile.ZipFile(b, "w") as z:
            for i, arc in enumerate(names):
                music[f"F:\\m\\{i}.mp3"] = arc
                with contextlib.suppress(ValueError):   # zipfile refuses some names
                    z.writestr(arc, MP3_FRAME)
            z.writestr(vp.MANIFEST, json.dumps(
                {"format": vp.FORMAT, "version": vp.VERSION, "files": [],
                 "music": music}))
        dest = self.root / "pick" / "here"
        dest.mkdir(parents=True, exist_ok=True)
        src = self._write(b.getvalue())
        before = set(self.root.rglob("*"))
        try:
            mapping = vp.extract_music(src, dest)
        except (vp.VenuePackError, OSError):
            mapping = {}
        new = set(self.root.rglob("*")) - before
        for p in new:
            if p.is_file():
                self.assertTrue(p.resolve().is_relative_to(dest.resolve()), p)
        for target in mapping.values():
            self.assertTrue(Path(target).resolve().is_relative_to(dest.resolve()))
        for p in sorted(new, key=lambda p: len(p.parts), reverse=True):
            if p.is_file():
                p.unlink()


if __name__ == "__main__":
    unittest.main()
