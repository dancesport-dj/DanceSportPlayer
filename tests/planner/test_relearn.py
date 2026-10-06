#!/usr/bin/env python3
"""Tests for MusicLibrary.relearn_playlists() — popularity refresh WITHOUT a
library rescan.

Run:  py -m unittest tests.planner.test_relearn -v

The playlist folder is redirected to a temp dir, so no real M3Us (and no music
files) are touched. Entries are built by hand: relearn must only re-read the
M3U text files and re-apply popularity in place.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from planner import config as planner_config
from dancesport_planner import MusicEntry, MusicLibrary


class PlaylistDirTestBase(unittest.TestCase):
    """Shared temp PLAYLIST_DIR redirect + a one-track library."""

    def setUp(self):
        self._orig_dir = planner_config.PLAYLIST_DIR
        self._dir = Path(tempfile.mkdtemp(prefix="dp_relearn_"))
        self._point_at(self._dir)

    def tearDown(self):
        self._point_at(self._orig_dir)
        shutil.rmtree(self._dir, ignore_errors=True)

    @staticmethod
    def _point_at(folder: Path) -> None:
        # Every module that holds the name, as the ⚙ setting does: a temp
        # dir seen only by planner.library is judged by its full path elsewhere.
        planner_config.set_playlist_dir(folder)

    @staticmethod
    def _lib_with_entry() -> MusicLibrary:
        lib = MusicLibrary()
        lib.entries.append(MusicEntry(
            path=Path(r"C:\music\standardcd\Tanguera (TG 32).mp3"),
            title="Tanguera", dance="TG", bpm=32))
        return lib


class OldLookingTempDirTest(PlaylistDirTestBase):
    def test_a_temp_dir_named_like_an_old_folder_still_counts(self):
        """mkdtemp's random suffix can read as an "old" marker ('dp_relearn_x_alt',
        'dp_relearn_12alte9q'). The GitHub suite once lost every playlist that
        way: only planner.library was pointed at the temp dir, so
        `_is_superseded_playlist` (planner.competition) judged its full path."""
        old = Path(tempfile.mkdtemp(prefix="dp_relearn_", suffix="_alt"))
        self.addCleanup(shutil.rmtree, old, True)
        self._point_at(old)
        (old / "Turnier 2026 Hgr B TG.m3u").write_text(
            r"D:\export\Tanguera (TG 32).mp3", encoding="utf-8")
        lib = self._lib_with_entry()
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 1)


class RelearnPlaylistsTest(PlaylistDirTestBase):
    def test_new_playlist_counts_without_rescan(self):
        lib = self._lib_with_entry()
        self.assertEqual(lib.relearn_playlists(), 0)
        self.assertEqual(lib.entries[0].popularity, 0)

        # A tournament export appears (different drive — filename matching).
        (self._dir / "Turnier 2026 Hgr B TG.m3u").write_text(
            r"D:\export\Tanguera (TG 32).mp3", encoding="utf-8")
        self.assertEqual(lib.relearn_playlists(), 1)
        self.assertEqual(lib.entries[0].popularity, 1)

    def test_index_is_rebuilt_not_accumulated(self):
        lib = self._lib_with_entry()
        m3u = self._dir / "Turnier 2026 Hgr B TG.m3u"
        m3u.write_text(r"D:\export\Tanguera (TG 32).mp3", encoding="utf-8")
        lib.relearn_playlists()
        lib.relearn_playlists()   # a second run must not double-count
        self.assertEqual(lib.entries[0].popularity, 1)

        m3u.unlink()              # playlist gone → popularity resets
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 0)
        self.assertEqual(lib.entries[0].source_info, "")

    def test_eintanzen_playlists_stay_excluded(self):
        lib = self._lib_with_entry()
        (self._dir / "Eintanzen Samstag.m3u").write_text(
            r"D:\export\Tanguera (TG 32).mp3", encoding="utf-8")
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 0)


class LearnPlaylistFoldersTest(PlaylistDirTestBase):
    """Tournament FOLDER trees (copied music, no .m3u) count like playlists."""

    def _copy_track(self, *parts) -> Path:
        """Drop a dummy copy of the library track under the playlist dir."""
        folder = self._dir.joinpath(*parts)
        folder.mkdir(parents=True, exist_ok=True)
        f = folder / "Tanguera (TG 32).mp3"
        f.write_bytes(b"\x00" * 64)
        return folder

    def test_folder_tree_counts_as_playlist(self):
        lib = self._lib_with_entry()
        self._copy_track("DM Latein 2026", "HGR S Lat", "Finale")
        self.assertEqual(lib.relearn_playlists(), 1)
        self.assertEqual(lib.entries[0].popularity, 1)
        self.assertIn("Finale", lib.entries[0].source_info)

    def test_two_tournament_folders_count_twice(self):
        lib = self._lib_with_entry()
        self._copy_track("Sven Musik DanceComp 2026", "Standard")
        self._copy_track("Tobi Musik DanceComp 2026", "Standard")
        self.assertEqual(lib.relearn_playlists(), 2)
        self.assertEqual(lib.entries[0].popularity, 2)

    def test_tree_with_m3u_is_not_double_counted(self):
        lib = self._lib_with_entry()
        folder = self._copy_track("Turnier 2026", "music")
        (self._dir / "Turnier 2026" / "Hgr B TG.m3u").write_text(
            str(folder / "Tanguera (TG 32).mp3"), encoding="utf-8")
        self.assertEqual(lib.relearn_playlists(), 1)   # the m3u only
        self.assertEqual(lib.entries[0].popularity, 1)

    def test_eintanzen_folder_stays_excluded(self):
        lib = self._lib_with_entry()
        self._copy_track("DM Latein 2026", "Eintanzen")
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 0)


class LineKeyMemoTest(PlaylistDirTestBase):
    """`_line_keys` is memoized — 2000 playlists repeat the same ~8k lines, and
    deriving their keys over and over was the bulk of every startup. The memo
    must not outlive the dance map it was derived from."""

    LINE = r"D:\export\Tanguera (TG 32).mp3"

    def test_the_second_call_is_the_same_answer(self):
        lib = self._lib_with_entry()
        lib._refresh_stem_dance()
        first = set(lib._line_keys(self.LINE))
        self.assertEqual(set(lib._line_keys(self.LINE)), first)

    def test_a_changed_dance_map_invalidates_it(self):
        lib = self._lib_with_entry()
        lib._refresh_stem_dance()
        before = set(lib._line_keys(self.LINE))
        lib.entries[0].dance = "WW"          # e.g. a corrected genre tag
        lib._refresh_stem_dance()
        self.assertNotEqual(set(lib._line_keys(self.LINE)), before)

    def test_a_track_in_two_playlists_still_counts_twice(self):
        """The memo hands the SAME set object to every caller — one that mutated
        it would corrupt every later line."""
        lib = self._lib_with_entry()
        for name in ("Turnier A Hgr B TG.m3u", "Turnier B Hgr B TG.m3u"):
            (self._dir / name).write_text(self.LINE, encoding="utf-8")
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 2)


class SourceInfoTest(PlaylistDirTestBase):
    """`source_info` names at most the first three playlists, in sorted order, and
    a repeated playlist NAME counts once. Only those three are ever built — the
    rest of a 149-playlist hit is never turned into a Path."""

    LINE = r"D:\export\Tanguera (TG 32).mp3"

    def _write(self, rel: str):
        p = self._dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.LINE, encoding="utf-8")

    def test_the_first_three_playlists_are_named(self):
        for name in "EDCBA":                      # written out of order on purpose
            self._write(f"Turnier {name} Hgr B TG.m3u")
        lib = self._lib_with_entry()
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 5)
        self.assertEqual(lib.entries[0].source_info,
                         "Turnier A Hgr B TG, Turnier B Hgr B TG, Turnier C Hgr B TG")

    def test_the_same_playlist_name_twice_is_named_once(self):
        for year in ("2024", "2025", "2026"):
            self._write(f"{year}/Turnier Hgr B TG.m3u")
        self._write("2026/Anderes Turnier Hgr B TG.m3u")
        lib = self._lib_with_entry()
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 4)
        self.assertEqual(lib.entries[0].source_info,
                         "Turnier Hgr B TG, Anderes Turnier Hgr B TG")


class PlaylistIndexCacheTest(PlaylistDirTestBase):
    """An untouched playlist must never be read twice. 2100 tournament exports sit
    unchanged for years, and re-reading all of them was ~1.3 s of every start —
    so each is cached by its mtime+size (`PlaylistIndexCache`).

    The cache rows are namespaced by the playlist dir they came from, so these
    temp roots can never answer for the real library's index.
    """

    LINE = r"D:\export\Tanguera (TG 32).mp3"
    OTHER = r"D:\export\Sway (TG 33).mp3"

    def setUp(self):
        super().setUp()
        self.reads = []

    def _lib(self) -> MusicLibrary:
        """A library whose `_m3u_keys` logs which playlists it actually opened."""
        lib = self._lib_with_entry()
        real = lib._m3u_keys

        def logging_keys(m3u):
            self.reads.append(m3u.name)
            return real(m3u)

        lib._m3u_keys = logging_keys            # instance attr shadows the method
        return lib

    def _write(self, name: str, *lines: str):
        (self._dir / name).write_text("\n".join(lines), encoding="utf-8")

    def test_an_unchanged_playlist_is_not_read_again(self):
        self._write("Turnier 2026 Hgr B TG.m3u", self.LINE)
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(len(self.reads), 1)
        self.reads.clear()

        lib.relearn_playlists()                 # nothing changed on disk
        self.assertEqual(self.reads, [])
        self.assertEqual(lib.entries[0].popularity, 1)

    def test_an_edited_playlist_is_read_again(self):
        self._write("Turnier 2026 Hgr B TG.m3u", self.OTHER)
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 0)   # our track is not in it yet
        self.reads.clear()

        self._write("Turnier 2026 Hgr B TG.m3u", self.OTHER, self.LINE)
        lib.relearn_playlists()
        self.assertEqual(self.reads, ["Turnier 2026 Hgr B TG.m3u"])
        self.assertEqual(lib.entries[0].popularity, 1)

    def test_only_the_new_playlist_is_read(self):
        self._write("Turnier A Hgr B TG.m3u", self.LINE)
        lib = self._lib()
        lib.relearn_playlists()
        self.reads.clear()

        self._write("Turnier B Hgr B TG.m3u", self.LINE)
        lib.relearn_playlists()
        self.assertEqual(self.reads, ["Turnier B Hgr B TG.m3u"])
        self.assertEqual(lib.entries[0].popularity, 2)

    def test_a_deleted_playlist_stops_counting(self):
        self._write("Turnier A Hgr B TG.m3u", self.LINE)
        self._write("Turnier B Hgr B TG.m3u", self.LINE)
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 2)

        (self._dir / "Turnier B Hgr B TG.m3u").unlink()
        lib.relearn_playlists()
        self.assertEqual(lib.entries[0].popularity, 1)

    def test_a_changed_dance_map_invalidates_every_cached_key(self):
        """Cached keys are dance-qualified (`_line_keys` → `_stem_dance`), and the
        dance map is not part of any playlist's mtime — so it has its own digest."""
        self._write("Turnier 2026 Hgr B TG.m3u", self.LINE)
        lib = self._lib()
        lib.relearn_playlists()
        before = {k: set(v) for k, v in lib._track_playlists.items()}
        self.reads.clear()

        lib.entries[0].dance = "WW"             # e.g. a corrected genre tag
        lib.relearn_playlists()
        self.assertEqual(self.reads, ["Turnier 2026 Hgr B TG.m3u"])
        self.assertNotEqual({k: set(v) for k, v in lib._track_playlists.items()}, before)

    def test_a_folder_playlist_is_cached_by_its_file_list(self):
        folder = self._dir / "DM Latein 2026" / "HGR S Lat" / "Finale"
        folder.mkdir(parents=True)
        (folder / "Tanguera (TG 32).mp3").write_bytes(b"\x00" * 64)
        lib = self._lib()
        self.assertEqual(lib.relearn_playlists(), 1)
        self.assertEqual(lib.entries[0].popularity, 1)

        lib.relearn_playlists()                 # served from the cache
        self.assertEqual(lib.entries[0].popularity, 1)
        cached = set(lib._track_playlists)

        (folder / "Sway (TG 33).mp3").write_bytes(b"\x00" * 64)
        lib.relearn_playlists()                 # a new track → the folder re-derives
        self.assertEqual(lib.entries[0].popularity, 1)
        self.assertTrue(set(lib._track_playlists) > cached,
                        "the second track's keys never made it into the index")


class LateRoundTest(PlaylistDirTestBase):
    """Which ROUND a past list played a track in — not just how often.

    Play count alone makes the heat warhorses look like the best music in the
    library: a preliminary uses ten tracks per dance, a final uses one. Two
    things say where a line sat — the playlist's NAME when it is one round, and
    otherwise its POSITION, because a saved competition holds every round back
    to back and the last pass through the dances is the final, the one before
    it the semifinal. Those two are counted apart: they are the rounds a DJ
    picks by hand, and they are not picked from the same shelf.
    """

    DANCES = ["SA", "CC", "RB", "PD", "JI"]
    BPM = {"SA": 51, "CC": 31, "RB": 25, "PD": 62, "JI": 43}

    def _lib(self) -> MusicLibrary:
        lib = MusicLibrary()
        for dance in self.DANCES:
            for i in (1, 2, 3):
                lib.entries.append(MusicEntry(
                    path=Path(rf"C:\music\lateincd\{self._name(dance, i)}"),
                    title=f"{dance} {i}", dance=dance, bpm=self.BPM[dance]))
        return lib

    def _name(self, dance: str, i: int) -> str:
        return f"Track{dance}{i} ({dance} {self.BPM[dance]}).mp3"

    def _line(self, dance: str, i: int) -> str:
        """The same track as a playlist line — another drive, same filename."""
        return rf"D:\export\{self._name(dance, i)}"

    def _write(self, name: str, *lines: str):
        (self._dir / name).write_text("\n".join(lines), encoding="utf-8")

    def _finals(self, lib: MusicLibrary) -> dict:
        return {e.title: e.final_plays for e in lib.entries}

    def _semis(self, lib: MusicLibrary) -> dict:
        return {e.title: e.semi_plays for e in lib.entries}

    def _heat(self, i: int) -> list:
        return [self._line(d, i) for d in self.DANCES]

    def test_the_last_pass_through_the_dances_is_the_final(self):
        """SA SA CC CC … | SA CC RB PD JI — two heats, then the final."""
        heats = [self._line(d, i) for i in (1, 2) for d in self.DANCES]
        self._write("HGR S Lat.m3u", *heats, *self._heat(3))
        lib = self._lib()
        lib.relearn_playlists()
        finals = self._finals(lib)
        for dance in self.DANCES:
            self.assertEqual(finals[f"{dance} 3"], 1, dance)
            self.assertEqual(finals[f"{dance} 1"], 0, dance)
            self.assertEqual(finals[f"{dance} 2"], 0, dance)

    def test_the_pass_before_the_final_is_the_semifinal(self):
        """SA SA CC CC … | SA CC RB PD JI | SA CC RB PD JI — heats, semi, final.
        The two picked rounds are told apart; the heats stay heats."""
        heats = [self._line(d, i) for i in (1, 2) for d in self.DANCES]
        self._write("HGR S Lat.m3u", *heats, *self._heat(3), *self._heat(1))
        lib = self._lib()
        lib.relearn_playlists()
        finals, semis = self._finals(lib), self._semis(lib)
        for dance in self.DANCES:
            self.assertEqual((finals[f"{dance} 1"], semis[f"{dance} 1"]), (1, 0), dance)
            self.assertEqual((finals[f"{dance} 3"], semis[f"{dance} 3"]), (0, 1), dance)
            self.assertEqual((finals[f"{dance} 2"], semis[f"{dance} 2"]), (0, 0), dance)

    def test_heats_and_a_final_alone_claim_no_semifinal(self):
        """The block before the final repeats its dances, so it is a preliminary
        and says nothing about a semifinal."""
        heats = [self._line(d, i) for d in self.DANCES for i in (1, 2)]
        self._write("HGR S Lat.m3u", *heats, *self._heat(3))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 3"], 1)
        self.assertEqual(sum(self._semis(lib).values()), 0)

    def test_a_list_that_names_the_semifinal_is_all_semifinal(self):
        self._write("HGR S Lat Halbfinale.m3u", *self._heat(1))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._semis(lib)["SA 1"], 1)
        self.assertEqual(self._finals(lib)["SA 1"], 0)

    def test_the_heat_tracks_are_still_as_popular_as_ever(self):
        """The final is an extra fact about a play, never a filter on it."""
        self._write("HGR S Lat.m3u", *self._heat(1), *self._heat(2))
        lib = self._lib()
        lib.relearn_playlists()
        by_title = {e.title: e for e in lib.entries}
        self.assertEqual(by_title["SA 1"].popularity, 1)
        self.assertEqual(by_title["SA 1"].final_plays, 0)

    def test_a_list_that_names_the_final_is_all_final(self):
        self._write("HGR S Lat Finale.m3u", *self._heat(1))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 1"], 1)

    def test_a_list_that_names_an_earlier_round_has_no_final(self):
        """Its last pass through the dances is a preliminary heat, not a final —
        the name says so and outranks the position."""
        self._write("HGR S Lat Vorrunde.m3u", *self._heat(1), *self._heat(2))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 2"], 0)

    def test_an_uneven_heat_count_does_not_hide_the_final(self):
        """Real lists are lopsided: LW LW TG TG TG QS QS | LW TG QS. The rounds
        do not divide evenly, and the last pass through the dances is a final
        all the same."""
        self._write("HGR S Lat.m3u",
                    self._line("SA", 1), self._line("SA", 2),
                    self._line("CC", 1), self._line("CC", 2),
                    self._line("CC", 3),
                    self._line("RB", 1), self._line("PD", 1),
                    self._line("JI", 1), self._line("JI", 2),
                    *self._heat(3))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 3"], 1)
        self.assertEqual(self._finals(lib)["SA 1"], 0)

    def test_a_line_of_unknown_music_does_not_veto_the_round(self):
        """One filename the dance detection cannot read sits in about every
        twentieth list. It belongs to no dance, so it neither ends the final's
        run nor has to be covered by it."""
        self._write("HGR S Lat.m3u", *self._heat(1),
                    r"D:\export\Siegerehrung.mp3", *self._heat(2))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 2"], 1)
        self.assertEqual(self._finals(lib)["SA 1"], 0)

    def test_a_list_cut_off_mid_round_hands_its_tail_the_final(self):
        """A list whose last round breaks off is indistinguishable from one with
        uneven heats — SA CC RB PD JI | SA CC could be either — so its trailing
        run is read as a final and three heat tracks come along.

        The guess is left generous on purpose: a title needs finals from two
        independent lists before anything acts on it, so one stray washes out,
        while refusing the whole shape cost over half the real finals."""
        self._write("HGR S Lat.m3u", *self._heat(1),
                    self._line("SA", 2), self._line("CC", 2))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 2"], 1)
        self.assertEqual(self._finals(lib)["SA 1"], 0)

    def test_a_list_that_ends_on_a_pair_is_a_heat_not_a_final(self):
        """SA SA CC CC RB RB PD PD JI JI — one round danced twice over, so its
        last five lines are not one of each dance and no final is claimed."""
        lines = [self._line(d, i) for d in self.DANCES for i in (1, 2)]
        self._write("HGR S Lat.m3u", *lines)
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(sum(self._finals(lib).values()), 0)

    def test_a_two_dance_list_says_nothing_about_finals(self):
        """A one- or two-dance list has a 'last round' too, and it means
        nothing — a tournament round is three dances at the very least."""
        self._write("Kür.m3u", self._line("SA", 1), self._line("CC", 1))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(sum(self._finals(lib).values()), 0)

    def test_a_finale_folder_counts_the_same_as_a_finale_list(self):
        """Not everyone writes .m3u — many just copy the round into a folder."""
        folder = self._dir / "DM Latein 2026" / "HGR S Lat" / "Finale"
        folder.mkdir(parents=True)
        (folder / self._name("SA", 1)).write_bytes(b"\x00" * 64)
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 1"], 1)

    def test_two_events_add_up_and_survive_the_cache(self):
        self._write("Turnier A.m3u", *self._heat(1), *self._heat(2))
        self._write("Turnier B.m3u", *self._heat(1), *self._heat(2))
        lib = self._lib()
        lib.relearn_playlists()
        self.assertEqual(self._finals(lib)["SA 2"], 2)
        lib.relearn_playlists()          # second run: served from the cache
        self.assertEqual(self._finals(lib)["SA 2"], 2)

    def test_a_removed_playlist_takes_its_final_with_it(self):
        self._write("Turnier A.m3u", *self._heat(1), *self._heat(2))
        lib = self._lib()
        lib.relearn_playlists()
        (self._dir / "Turnier A.m3u").unlink()
        lib.relearn_playlists()
        self.assertEqual(sum(self._finals(lib).values()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
