"""Property tests: what an export writes, the readers read back — for any titles and paths.

The example tests pin a handful of names; these let Hypothesis make up the
titles (umlauts, other scripts, stray whitespace and line breaks) and the
folder names, in every file format the ⚙ setting offers.

Run:  .venv/Scripts/python.exe -m pytest tests/planner/playlist/test_m3u_properties.py -n0
"""
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from planner.models import MusicEntry
from planner.playlist import m3u
from planner.playlist.m3u import export_flat_m3u, m3u_marker_heats, read_m3u_tracks

# What a Windows file or folder name can hold: no control codes, none of
# <>:"/\|?*, and no space or dot at its end. A '#' in front would make the
# line a comment, but every path here starts with the drive.
_NAME_CHARS = st.characters(codec="utf-8", exclude_categories=("Cc", "Cs", "Zl", "Zp"),
                            exclude_characters='<>:"/\\|?*')
names = st.text(_NAME_CHARS, min_size=1, max_size=20).map(str.strip).filter(
    lambda s: s and not s.endswith(".") and s not in (".", ".."))
# A tag title may hold anything, line breaks included.
titles = st.text(st.characters(codec="utf-8", exclude_categories=("Cs",)), max_size=40)


@st.composite
def entries(draw, min_size=1, max_size=12):
    out = []
    for i in range(draw(st.integers(min_size, max_size))):
        folders = draw(st.lists(names, min_size=1, max_size=3))
        path = Path("C:/", *folders, f"{i:02d} {draw(names)}.mp3")
        out.append(MusicEntry(path=path, title=draw(titles), dance=draw(st.sampled_from(["SA", "CC", "LW", None])),
                              duration=draw(st.integers(0, 900)), year=draw(st.none() | st.integers(1950, 2030))))
    return out


class FlatExportRoundTripTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.addCleanup(m3u.set_m3u_format, "utf-8")

    @settings(deadline=None, max_examples=60)
    @given(entries(), st.sampled_from(sorted(m3u.M3U_FORMATS)))
    def test_every_track_comes_back_in_order_under_its_title(self, songs, fmt):
        m3u.set_m3u_format(fmt)
        out = export_flat_m3u(songs, "x", out_path=self.dir / f"list{m3u.m3u_suffix()}")
        back = read_m3u_tracks(out)
        self.assertEqual([p for p, _t in back], [e.path for e in songs])
        for (_p, title), e in zip(back, songs, strict=True):
            # The title is written on one line, its whitespace collapsed; the
            # dance and year follow it.
            self.assertTrue(title.startswith(" ".join(e.title.split())), (title, e.title))

    @settings(deadline=None, max_examples=60)
    @given(st.data())
    def test_the_rounds_and_heats_of_a_training_list_come_back(self, data):
        plan = []
        for _ in range(data.draw(st.integers(1, 4))):
            name = data.draw(st.text(st.sampled_from("ABCabcäöüß 0123456789-"), min_size=1, max_size=15)
                             .map(str.strip).filter(bool))
            heats = data.draw(st.integers(1, 4))
            dances = data.draw(st.integers(1, 3))
            plan.append((name, heats, heats * dances))
        songs = data.draw(entries(min_size=sum(n for *_x, n in plan), max_size=sum(n for *_x, n in plan)))
        out = export_flat_m3u(songs, "x", out_path=self.dir / "list.m3u8", heat_rounds=plan)
        self.assertEqual(m3u_marker_heats(out), plan)
        self.assertEqual([p for p, _t in read_m3u_tracks(out)], [e.path for e in songs])


if __name__ == "__main__":
    unittest.main()
