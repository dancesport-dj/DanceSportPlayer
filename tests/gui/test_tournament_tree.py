"""🏆 The tournament tree: the JSON it keeps, and the pane built on it.

The tree is the operator's filing of a competition weekend, so what is tested
here is that nothing they filed can be lost — a hand-edited file survives, a
removed entry never touches the disk, and a playlist shows the tracks it lists
even when the library has never heard of them.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_"))

from PySide6.QtCore import QMimeData, QPoint, QPointF, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui import tournament_tree as gt  # noqa: E402
from planner.store import JsonStore  # noqa: E402
from planner.m3u import read_m3u_tracks  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def _tmp(prefix="dp_tree_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _m3u(folder: Path, name: str, tracks=()) -> Path:
    p = folder / f"{name}.m3u"
    lines = ["#EXTM3U"]
    for path, title in tracks:
        lines += [f"#EXTINF:120,{title}", str(path)]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


class ReadM3uTracksTest(unittest.TestCase):
    """The plain reading of a playlist file — order kept, markers ignored."""

    def test_paths_and_titles_in_file_order(self):
        folder = _tmp()
        p = _m3u(folder, "round", [(r"C:\music\a.mp3", "Waltz A"),
                                   (r"C:\music\b.mp3", "Tango B")])
        self.assertEqual(read_m3u_tracks(p),
                         [(Path(r"C:\music\a.mp3"), "Waltz A"),
                          (Path(r"C:\music\b.mp3"), "Tango B")])

    def test_the_apps_own_markers_are_not_tracks(self):
        folder = _tmp()
        p = folder / "marked.m3u"
        p.write_text("#EXTM3U\n# ══ Vorrunde (1 Heat) ══\n"
                     "# ── Langsamer Walzer ──\n"
                     "#EXTINF:120,Waltz A\nC:\\music\\a.mp3\n", encoding="utf-8")
        self.assertEqual(read_m3u_tracks(p), [(Path(r"C:\music\a.mp3"), "Waltz A")])

    def test_a_track_without_an_extinf_line_still_counts(self):
        folder = _tmp()
        p = folder / "bare.m3u"
        p.write_text("C:\\music\\a.mp3\n", encoding="utf-8")
        self.assertEqual(read_m3u_tracks(p), [(Path(r"C:\music\a.mp3"), "")])

    def test_a_file_that_is_not_there_reads_as_empty(self):
        self.assertEqual(read_m3u_tracks(Path("nope") / "gone.m3u"), [])


class TreeFileTest(unittest.TestCase):
    """load_tree / save_tree — the file is meant to be hand-editable."""

    def test_a_saved_tree_comes_back_the_same(self):
        f = _tmp() / "tournaments.json"
        nodes = [{"name": "DanceComp 2026", "children": [
            {"name": "Freitag", "children": [
                {"name": "Turnier 1", "m3u": r"D:\lists\t1.m3u"}]}]}]
        gt.save_tree(JsonStore.at(f), nodes)
        self.assertEqual(gt.load_tree(JsonStore.at(f)), nodes)

    def test_nothing_saved_yet_is_an_empty_tree(self):
        self.assertEqual(gt.load_tree(JsonStore.at(_tmp() / "tournaments.json")), [])

    def test_a_broken_file_costs_the_tree_but_never_raises(self):
        f = _tmp() / "tournaments.json"
        f.write_text("{not json", encoding="utf-8")
        self.assertEqual(gt.load_tree(JsonStore.at(f)), [])

    def test_a_hand_edited_branch_survives_its_own_typos(self):
        # A nameless node and a stray string go; everything around them stays.
        nodes = gt.normalize_nodes([
            {"name": "Samstag", "children": [
                {"name": ""}, "oops",
                {"name": "Turnier 2", "m3u": "x.m3u"}]},
            {"nope": 1},
        ])
        self.assertEqual(nodes, [{"name": "Samstag", "children": [
            {"name": "Turnier 2", "m3u": "x.m3u"}]}])

    def test_a_folder_without_children_is_still_a_folder(self):
        self.assertEqual(gt.normalize_nodes([{"name": "Leer"}]),
                         [{"name": "Leer", "children": []}])


class _PaneCase(unittest.TestCase):
    """A pane over its own empty state file, per test.

    `view` picks which of the two the case runs in. The pane opens on the ▦
    slot board, where the tree holds folders only — anything that reaches for a
    playlist as a tree row belongs in the ▤ reading view."""

    view = gt.VIEW_SLOTS

    def setUp(self):
        self.dir = _tmp()
        self.state = JsonStore.at(self.dir / "tournaments.json")
        self.pane = gt.TournamentTree(self.state)
        self.addCleanup(reap_widget, self.pane)
        if self.view == gt.VIEW_LIST:
            self.use_list_view()

    def use_list_view(self):
        if self.pane._view != gt.VIEW_LIST:
            self.pane._toggle_view()

    def leaves(self):
        return [n["m3u"] for n in self.pane._nodes if n.get("m3u")]


class PaneFilingTest(_PaneCase):
    """What the operator files: drops, folders, removals, restarts."""

    def test_a_dropped_playlist_becomes_a_leaf_named_after_the_file(self):
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(None, [m3u])
        self.assertEqual(self.pane._nodes,
                         [{"name": "Turnier 1", "m3u": str(m3u)}])
        self.assertEqual(self.pane._tree.topLevelItemCount(), 1)

    def test_what_is_added_is_on_disk_at_once(self):
        # The desk can be closed the hard way; nothing may wait for a clean quit.
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(None, [m3u])
        saved = json.loads(self.state.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["tournaments"],
                         [{"name": "Turnier 1", "m3u": str(m3u)}])

    def test_a_playlist_dropped_on_a_folder_lands_inside_it(self):
        self.pane._nodes.append({"name": "Freitag", "children": []})
        self.pane._rebuild()
        folder_item = self.pane._tree.topLevelItem(0)
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(folder_item, [m3u])
        self.assertEqual(self.pane._nodes[0]["children"],
                         [{"name": "Turnier 1", "m3u": str(m3u)}])

    def test_a_playlist_dropped_on_a_playlist_lands_beside_it(self):
        self.use_list_view()   # a playlist is only a tree row there
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": "Turnier 1", "m3u": "t1.m3u"}]})
        self.pane._rebuild()
        leaf_item = self.pane._tree.topLevelItem(0).child(0)
        m3u = _m3u(self.dir, "Turnier 2")
        self.pane._on_files_dropped(leaf_item, [m3u])
        self.assertEqual([n["name"] for n in self.pane._nodes[0]["children"]],
                         ["Turnier 1", "Turnier 2"])

    def test_removing_an_entry_leaves_the_playlist_file_alone(self):
        self.use_list_view()   # a playlist is only a tree row there
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.pane._remove_from(self.pane._nodes, self.pane._current_node())
        self.assertEqual(self.pane._nodes, [])
        self.assertTrue(m3u.is_file())

    def test_a_saved_playlist_is_filed_where_a_dropped_one_would_land(self):
        """Marcel: save playlists or whole competition days from the
        right-click menu and add them to the Tournament tab too."""
        self.pane._nodes.append({"name": "Freitag", "children": []})
        self.pane._rebuild()
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        m3u = _m3u(self.dir, "Turnier 1")
        self.assertEqual(self.pane.file_saved([m3u]), 1)
        self.assertEqual(self.pane._nodes[0]["children"],
                         [{"name": "Turnier 1", "m3u": str(m3u)}])
        saved = json.loads(self.state.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["tournaments"], self.pane._nodes)

    def test_a_saved_day_is_filed_as_a_folder_named_after_it(self):
        t1, t2 = _m3u(self.dir, "HGR S STD"), _m3u(self.dir, "SEN I S STD")
        self.assertEqual(self.pane.file_saved([t1, t2], "Samstag"), 2)
        self.assertEqual(self.pane._nodes, [{"name": "Samstag", "children": [
            {"name": "HGR S STD", "m3u": str(t1)},
            {"name": "SEN I S STD", "m3u": str(t2)}]}])

    def test_saving_the_same_day_again_files_nothing_twice(self):
        t1, t2 = _m3u(self.dir, "HGR S STD"), _m3u(self.dir, "SEN I S STD")
        self.pane.file_saved([t1], "Samstag")
        self.assertEqual(self.pane.file_saved([t1, t2], "Samstag"), 1)
        self.assertEqual(len(self.pane._nodes), 1)
        self.assertEqual([n["m3u"] for n in self.pane._nodes[0]["children"]],
                         [str(t1), str(t2)])
        self.assertEqual(self.pane.file_saved([t1]), 0)       # Samstag is picked
        self.pane._tree.setCurrentItem(None)
        self.assertEqual(self.pane.file_saved([t1]), 1)       # the root is elsewhere
        self.assertEqual(self.pane.file_saved([t1]), 0)

    def test_a_filed_day_is_picked_with_its_playlists_on_the_board(self):
        """Marcel said yes to picking what was just filed."""
        t1, t2 = _m3u(self.dir, "HGR S STD"), _m3u(self.dir, "SEN I S STD")
        self.pane._nodes.append({"name": "Freitag", "children": []})
        self.pane._rebuild()
        self.pane.file_saved([t1, t2], "Samstag")
        self.assertEqual(self.pane._current_node()["name"], "Samstag")
        self.assertEqual(sorted(self.pane._board._tiles), ["1/0", "1/1"])

    def test_a_filed_playlist_is_picked_on_its_folders_board(self):
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": "T0", "m3u": "t0.m3u"}]})
        self.pane._rebuild()
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane.file_saved([m3u])
        self.assertEqual(self.pane._current_node()["name"], "Freitag")
        self.assertEqual([k for k, t in self.pane._board._tiles.items() if t._selected],
                         ["0/1"])

    def test_in_the_list_view_the_filed_playlist_itself_is_picked(self):
        self.use_list_view()
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane.file_saved([m3u])
        self.assertEqual(self.pane._current_node(), {"name": "Turnier 1", "m3u": str(m3u)})

    def test_a_branch_is_removed_with_everything_under_it(self):
        self.pane._nodes.extend([
            {"name": "Freitag", "children": [{"name": "T1", "m3u": "a.m3u"}]},
            {"name": "Samstag", "children": []}])
        self.pane._rebuild()
        self.pane._remove_from(self.pane._nodes, self.pane._nodes[0])
        self.assertEqual([n["name"] for n in self.pane._nodes], ["Samstag"])

    def test_a_folder_of_playlists_counts_them_all(self):
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": "T1", "m3u": "a.m3u"}, {"name": "T2", "m3u": "b.m3u"}]})
        self.pane._rebuild()
        self.assertIn("2 playlists", self.pane._count_lbl.text())

    def test_collapse_all_folds_the_folders_and_survives_a_rebuild(self):
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": "T1", "m3u": "a.m3u"}]})
        self.pane._rebuild()
        self.assertTrue(self.pane._tree.topLevelItem(0).isExpanded())
        self.pane._toggle_collapse_all()
        self.assertFalse(self.pane._tree.topLevelItem(0).isExpanded())
        self.pane._rebuild()   # a rename must not spring the tree open again
        self.assertFalse(self.pane._tree.topLevelItem(0).isExpanded())
        self.pane._toggle_collapse_all()
        self.assertTrue(self.pane._tree.topLevelItem(0).isExpanded())
        self.assertEqual(self.pane._collapse_btn.text(), "⊟")

    def test_only_playlist_files_are_taken_from_a_drop(self):
        # An .mp3 dragged onto the tree belongs on a deck, not in the filing.
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(r"C:\lists\t1.m3u"),
                      QUrl.fromLocalFile(r"C:\music\a.mp3")])
        self.assertEqual(gt._TourneyTree._m3u_urls(mime),
                         [Path(r"C:\lists\t1.m3u")])

    def test_a_folder_is_taken_from_a_drop_too(self):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.dir))])
        self.assertEqual(gt._TourneyTree._m3u_urls(mime), [self.dir])

    def test_a_dropped_folder_arrives_as_the_branch_it_is_on_disk(self):
        comp = self.dir / "DanceComp 2026"
        (comp / "Freitag").mkdir(parents=True)
        _m3u(comp / "Freitag", "Turnier 1")
        _m3u(comp / "Freitag", "Turnier 2")
        _m3u(comp, "Eintanzen")
        self.pane._on_files_dropped(None, [comp])
        self.assertEqual(self.pane._nodes[0]["name"], "DanceComp 2026")
        kids = self.pane._nodes[0]["children"]
        self.assertEqual([n["name"] for n in kids], ["Freitag", "Eintanzen"])
        self.assertEqual([n["name"] for n in kids[0]["children"]],
                         ["Turnier 1", "Turnier 2"])
        self.assertIn("3 playlists", self.pane._count_lbl.text())

    def test_a_folder_without_a_single_playlist_is_not_filed(self):
        music = self.dir / "just music"
        music.mkdir()
        (music / "a.mp3").write_bytes(b"")
        with mock.patch.object(gt.QMessageBox, "information"):
            self.pane._on_files_dropped(None, [music])
        self.assertEqual(self.pane._nodes, [])

    def test_the_tree_is_read_back_on_the_next_start(self):
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(None, [m3u])
        again = gt.TournamentTree(self.state)
        self.addCleanup(reap_widget, again)
        self.assertEqual(again._tree.topLevelItemCount(), 1)


class PaneViewTest(_PaneCase):
    """▦ / ▤ — the slot board the pane opens on, and the reading view behind
    the button. The pane is a wide, short strip, so the two halves always sit
    side by side; what the button changes is what the right half is."""

    def test_it_opens_on_the_slot_board(self):
        self.assertEqual(self.pane._view, gt.VIEW_SLOTS)
        self.assertIs(self.pane._right.currentWidget(), self.pane._board)
        self.assertEqual(self.pane._view_btn.text(), "▤")

    def test_the_two_halves_are_beside_each_other_not_stacked(self):
        self.assertEqual(self.pane._split.orientation(),
                         gt.Qt.Orientation.Horizontal)

    def test_the_button_swaps_the_two_views_and_back(self):
        self.pane._toggle_view()
        self.assertEqual(self.pane._view, gt.VIEW_LIST)
        self.assertIs(self.pane._right.currentWidget(), self.pane._table)
        self.assertEqual(self.pane._view_btn.text(), "▦")
        self.pane._toggle_view()
        self.assertIs(self.pane._right.currentWidget(), self.pane._board)
        self.assertEqual(self.pane._view_btn.text(), "▤")

    def test_the_choice_is_on_disk_at_once_and_comes_back(self):
        self.pane._toggle_view()
        saved = json.loads(self.state.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["view"], gt.VIEW_LIST)
        again = gt.TournamentTree(self.state)
        self.addCleanup(reap_widget, again)
        self.assertIs(again._right.currentWidget(), again._table)

    def test_switching_the_view_keeps_the_filed_tree(self):
        # Both go through the same _save — the view must not cost the tree.
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(None, [m3u])
        self.pane._toggle_view()
        self.assertEqual(gt.load_tree(self.state),
                         [{"name": "Turnier 1", "m3u": str(m3u)}])

    def test_a_tree_filed_before_the_button_existed_opens_on_the_board(self):
        f = self.dir / "old.json"
        f.write_text(json.dumps({"version": 1, "tournaments": []}),
                     encoding="utf-8")
        self.assertEqual(gt.load_view(JsonStore.at(f)), gt.VIEW_SLOTS)

    def test_a_broken_file_costs_the_view_but_never_raises(self):
        f = self.dir / "broken.json"
        f.write_text("{not json", encoding="utf-8")
        self.assertEqual(gt.load_view(JsonStore.at(f)), gt.VIEW_SLOTS)


class PaneTrackListTest(_PaneCase):
    """Picking a playlist: the tracks it lists, named and marked."""

    view = gt.VIEW_LIST

    def test_picking_a_playlist_shows_its_tracks_in_playing_order(self):
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A"),
                                           (r"C:\music\b.mp3", "Tango B")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual([self.pane._table.item(r, 4).text() for r in range(2)],
                         ["⚠  Waltz A", "⚠  Tango B"])   # not on this disk

    def test_a_missing_file_paints_its_whole_row(self):
        """The ⚠ is easy to scroll past; the orange row is what gets noticed."""
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        t = self.pane._table
        self.assertEqual(
            [t.item(0, c).background().color() for c in range(t.columnCount())],
            [gt._C_MISS_BG] * t.columnCount())

    def test_a_track_that_is_there_keeps_a_plain_row(self):
        track = self.dir / "lw30 - Waltz A.mp3"
        track.write_bytes(b"")
        m3u = _m3u(self.dir, "Turnier 1", [(track, "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertNotEqual(self.pane._table.item(0, 4).background().color(),
                            gt._C_MISS_BG)

    def test_the_rounds_are_named_beside_the_tracks(self):
        """The same cut the deck heads its ─── strips with, so the list can be
        read against the running order before it is loaded."""
        names = ["lw30 - Waltz A", "tg33 - Tango A",
                 "lw30 - Waltz B", "tg33 - Tango B"]
        m3u = _m3u(self.dir, "Turnier 1",
                   [(self.dir / f"{n}.mp3", n) for n in names])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        # Short, as the slots write them — "1. Zwischenrunde" does not fit the
        # column (Marcel: "Vorrunde, 1. Zwischenrunde etc is too long").
        self.assertEqual([self.pane._table.item(r, 1).text() for r in range(4)],
                         ["VR", "VR", "ER", "ER"])
        self.assertEqual([self.pane._table.item(r, 1).toolTip() for r in range(4)],
                         ["Vorrunde", "Vorrunde", "Finale", "Finale"])

    def test_a_list_whose_rounds_cannot_be_named_shows_none(self):
        """A single pass through the dances is one round — nothing to head."""
        names = ["lw30 - Waltz A", "tg33 - Tango A", "ww59 - Wiener A"]
        m3u = _m3u(self.dir, "Turnier 1",
                   [(self.dir / f"{n}.mp3", n) for n in names])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual([self.pane._table.item(r, 1).text() for r in range(3)],
                         ["", "", ""])

    def test_a_one_round_file_heads_every_row_with_that_round(self):
        """Nothing to cut in a single pass — but '07 ZR_WDSF' has already said
        what it is, and the column says the same as the slot."""
        names = ["lw30 - Waltz A", "tg33 - Tango A", "ww59 - Wiener A"]
        m3u = _m3u(self.dir, "07 ZR_WDSF",
                   [(self.dir / f"{n}.mp3", n) for n in names])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual([self.pane._table.item(r, 1).text() for r in range(3)],
                         ["ZR"] * 3)

    def test_a_track_the_library_knows_is_named_by_the_library(self):
        track = self.dir / "lw30 - Waltz A.mp3"
        track.write_bytes(b"")
        m3u = _m3u(self.dir, "Turnier 1", [(track, "whatever the file says")])
        self.pane.set_entries([MusicEntry(path=track, title="Waltz A",
                                          dance="LW", bpm=30)])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._table.item(0, 2).text(), "Langsamer Walzer")
        self.assertEqual(self.pane._table.item(0, 4).text(), "Waltz A")
        self.assertEqual(self.pane._table.item(0, 5).text(), "30")

    def test_a_track_outside_the_library_is_read_off_the_file(self):
        track = self.dir / "Tango B.mp3"
        track.write_bytes(b"")
        m3u = _m3u(self.dir, "Turnier 1", [(track, "Tango B")])
        self.pane.resolve_entry = lambda p: MusicEntry(
            path=p, title="Tango B", dance="TG", bpm=32)
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._table.item(0, 2).text(), "Tango")
        self.assertEqual(self.pane._table.item(0, 5).text(), "32")

    def test_a_playlist_file_that_is_gone_says_so_instead(self):
        self.pane._nodes.append({"name": "Turnier 1", "m3u": str(self.dir / "x.m3u")})
        self.pane._rebuild()
        self.assertTrue(self.pane._tree.topLevelItem(0).text(0).startswith("⚠"))

    def test_a_track_the_library_never_heard_of_is_not_called_fresh(self):
        """✦ says 'never played'. A track we couldn't resolve at all has no
        popularity to show — an empty cell, not a claim about it."""
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._table.item(0, 7).text(), "")

    def test_a_known_but_unplayed_track_still_shows_the_fresh_mark(self):
        track = self.dir / "lw30 - Waltz A.mp3"
        track.write_bytes(b"")
        m3u = _m3u(self.dir, "Turnier 1", [(track, "Waltz A")])
        self.pane.set_entries([MusicEntry(path=track, title="Waltz A",
                                          dance="LW", popularity=0)])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._table.item(0, 7).text(), "✦")

    def test_a_playlist_is_read_off_disk_once(self):
        """Clicking back and forth through a weekend must not re-read every
        file — that is what made the tree stutter."""
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        reads = []
        real = gt.read_m3u_tracks
        gt.read_m3u_tracks = lambda p: (reads.append(p), real(p))[1]
        self.addCleanup(lambda: setattr(gt, "read_m3u_tracks", real))
        for _ in range(3):
            self.pane._show_tracks()
        self.assertEqual(reads, [])
        self.assertEqual(self.pane._table.rowCount(), 1)

    def test_a_re_exported_playlist_is_read_again(self):
        """The cache is the file's own — a list exported under the same name
        must not show yesterday's tracks."""
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._table.rowCount(), 1)
        m3u.write_text("#EXTM3U\n"
                       "#EXTINF:120,Waltz A\nC:\\music\\a.mp3\n"
                       "#EXTINF:120,Tango B\nC:\\music\\b.mp3\n", encoding="utf-8")
        self.pane._show_tracks()
        self.assertEqual(self.pane._table.rowCount(), 2)

    def test_the_list_draws_no_cell_borders_like_a_deck(self):
        """Marcel: "style the playlist view there more like the normal playlist
        view. currently we have each cell with a border"."""
        self.assertFalse(self.pane._table.showGrid())

    def test_a_folder_shows_no_tracks(self):
        self.pane._nodes.append({"name": "Freitag", "children": []})
        self.pane._rebuild()
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._table.rowCount(), 0)


class PaneBadgeTest(_PaneCase):
    """The badge: how many songs the selection is, and how long."""

    view = gt.VIEW_LIST

    def test_the_badge_counts_the_songs_and_their_play_time(self):
        tracks = []
        for name in ("lw30 - Waltz A", "tg33 - Tango B"):
            p = self.dir / f"{name}.mp3"
            p.write_bytes(b"")
            tracks.append((p, name))
        m3u = _m3u(self.dir, "Turnier 1", tracks)
        self.pane.set_entries([MusicEntry(path=p, title=n, duration=180)
                               for p, n in tracks])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._total_lbl.text(), "Σ  2 songs  ·  ~6:00")
        self.assertTrue(self.pane._total_lbl.isVisibleTo(self.pane))

    def test_the_badge_goes_away_with_nothing_selected(self):
        self.pane._nodes.append({"name": "Freitag", "children": []})
        self.pane._rebuild()
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertFalse(self.pane._total_lbl.isVisibleTo(self.pane))

    def test_a_playlist_of_tracks_nobody_knows_still_counts_them(self):
        """No entry means no duration — the song count is still the truth."""
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._total_lbl.text(), "Σ  1 song")


class PaneInteractionTest(_PaneCase):
    """Double-click, the ▶ column and dragging a row out."""

    view = gt.VIEW_LIST

    def test_double_clicking_a_playlist_asks_for_it_to_be_loaded(self):
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(None, [m3u])
        asked = []
        self.pane.loadRequested.connect(asked.append)
        self.pane._on_tree_double_click(self.pane._tree.topLevelItem(0), 0)
        self.assertEqual(asked, [str(m3u)])

    def test_double_clicking_a_folder_loads_nothing(self):
        self.pane._nodes.append({"name": "Freitag", "children": []})
        self.pane._rebuild()
        asked = []
        self.pane.loadRequested.connect(asked.append)
        self.pane._on_tree_double_click(self.pane._tree.topLevelItem(0), 0)
        self.assertEqual(asked, [])

    def test_the_play_column_toggles_between_start_and_stop(self):
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        played = []
        self.pane.playRequested.connect(lambda p, r: played.append(p))
        self.pane._on_cell_clicked(0, 0)
        self.assertEqual(self.pane._table.item(0, 0).text(), "■")
        self.pane._on_cell_clicked(0, 0)          # same row again → stop
        self.assertEqual(self.pane._table.item(0, 0).text(), "▶")
        self.assertEqual(played, [Path(r"C:\music\a.mp3"), None])

    def test_a_leaf_hands_out_its_playlist_file_when_dragged(self):
        m3u = _m3u(self.dir, "Turnier 1")
        self.pane._on_files_dropped(None, [m3u])
        item = self.pane._tree.topLevelItem(0)
        node = self.pane._tree.node_of(item.data(0, gt._ROLE_KEY))
        self.assertEqual(node["m3u"], str(m3u))

    def test_a_track_row_carries_the_file_the_drag_exports(self):
        m3u = _m3u(self.dir, "Turnier 1", [(r"C:\music\a.mp3", "Waltz A")])
        self.pane._on_files_dropped(None, [m3u])
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.assertEqual(self.pane._table.item(0, 0).data(gt._ROLE_PATH),
                         Path(r"C:\music\a.mp3"))


class RoundShortTest(unittest.TestCase):
    """The round codes a slot wears: short, and never a dance code."""

    def test_the_named_rounds_get_their_letters(self):
        self.assertEqual([gt._round_short(n) for n in
                          ("Vorrunde", "Zwischenrunde", "Finale")],
                         ["VR", "ZR", "ER"])

    def test_a_numbered_round_keeps_its_number(self):
        self.assertEqual(gt._round_short("2. Zwischenrunde"), "2ZR")

    def test_the_semifinal_is_sf(self):
        self.assertEqual(gt._round_short("Semifinale"), "SF")
        self.assertEqual(gt._round_short("Halbfinale"), "SF")

    def test_a_round_the_file_numbered_itself(self):
        self.assertEqual(gt._round_short("Runde 3"), "R3")

    def test_a_name_nothing_knows_is_cut_not_dropped(self):
        self.assertEqual(gt._round_short("Trostrunde"), "TR")

    def test_a_round_listed_twice_is_still_that_round(self):
        self.assertEqual(gt._round_short("Vorrunde (2)"), "VR")


class RoundsInNameTest(unittest.TestCase):
    """What a file NAME says about its rounds — the only thing that knows, when
    a file holds a single round and so reads as a single pass."""

    def test_the_usual_filing_of_one_file_per_round(self):
        self.assertEqual([gt._rounds_in_name(s) for s in
                          ("01_VR_JUGD_KINC_JUND", "07 ZR_WDSF", "09 ER_WDSF")],
                         [["Vorrunde"], ["Zwischenrunde"], ["Finale"]])

    def test_a_numbered_zwischenrunde_either_way_round(self):
        self.assertEqual(gt._rounds_in_name("08 2ZR_WDSF"), ["2. Zwischenrunde"])
        self.assertEqual(gt._rounds_in_name("WDSF_ZR3_JUG"), ["3. Zwischenrunde"])

    def test_the_words_spelled_out_count_too(self):
        self.assertEqual(gt._rounds_in_name("STD_HGR_b_vor-zwischen-endrunde"),
                         ["Vorrunde", "Zwischenrunde", "Finale"])

    def test_a_file_holding_two_classes_rounds_names_both(self):
        self.assertEqual(gt._rounds_in_name("08 ZR_WDSF_ER_JUGC"),
                         ["Zwischenrunde", "Finale"])

    def test_only_whole_words_are_rounds(self):
        # ERSATZ is a reserve list, not an Endrunde.
        self.assertEqual(gt._rounds_in_name("_ZR_WDSF_ERSATZ"), ["Zwischenrunde"])

    def test_sf_in_a_name_stays_slowfox(self):
        self.assertEqual(gt._rounds_in_name("SF Serie 2"), [])

    def test_an_ordinary_tournament_name_claims_nothing(self):
        self.assertEqual([gt._rounds_in_name(s) for s in
                          ("HGR 2 BLAT", "SEN 1 A LAT", "LM_JUN_I_B_STD",
                           "eintanzen", "wunschReserve")],
                         [[], [], [], [], []])


class _Move:
    """The one thing _SlotTile.mouseMoveEvent asks a mouse event for."""

    def __init__(self, x: int, y: int):
        self._pt = QPointF(x, y)

    def position(self):
        return self._pt


class PaneSlotBoardTest(_PaneCase):
    """▦ The board: a folder on the left, its playlists as tiles to grab."""

    def _file_a_weekend(self):
        """Freitag holds two playlists, Samstag one, and Samstag has a
        sub-folder of its own — enough to tell 'directly in it' from 'under
        it somewhere'."""
        t1 = _m3u(self.dir, "Turnier 1", [
            (self.dir / "Fascination LW 29.mp3", "Fascination"),
            (self.dir / "Jealousy TG 32.mp3", "Jealousy")])
        t2 = _m3u(self.dir, "Turnier 2", [
            (self.dir / "Bailamos CC 31.mp3", "Bailamos")])
        t3 = _m3u(self.dir, "Turnier 3")
        self.pane._nodes.extend([
            {"name": "Freitag", "children": [
                {"name": "Turnier 1", "m3u": str(t1)},
                {"name": "Turnier 2", "m3u": str(t2)}]},
            {"name": "Samstag", "children": [
                {"name": "Turnier 3", "m3u": str(t3)},
                {"name": "Abends", "children": [
                    {"name": "Turnier 4", "m3u": str(t3)}]}]}])
        self.pane._rebuild()
        return t1, t2, t3

    def _pick(self, *path: int):
        item = self.pane._tree.topLevelItem(path[0])
        for i in path[1:]:
            item = item.child(i)
        self.pane._tree.setCurrentItem(item)
        return item

    def test_the_tree_holds_the_folders_only(self):
        self._file_a_weekend()
        self.assertEqual([self.pane._tree.topLevelItem(i).text(0)
                          for i in range(self.pane._tree.topLevelItemCount())],
                         ["📁  Freitag  (2)", "📁  Samstag  (1)"])
        # Samstag's own sub-folder stays a row; its playlist does not.
        samstag = self.pane._tree.topLevelItem(1)
        self.assertEqual([samstag.child(i).text(0)
                          for i in range(samstag.childCount())],
                         ["📁  Abends  (1)"])

    def test_picking_a_folder_lays_its_playlists_out_as_tiles(self):
        self._file_a_weekend()
        self._pick(0)
        self.assertEqual([t._name_lbl.text()
                          for t in self.pane._board._tiles.values()],
                         ["Turnier 1", "Turnier 2"])

    def test_only_what_is_filed_directly_in_the_folder_is_on_the_board(self):
        self._file_a_weekend()
        self._pick(1)                       # Samstag: 1 of its own + a folder
        self.assertEqual(len(self.pane._board._tiles), 1)
        self._pick(1, 0)                    # …and the sub-folder has the other
        self.assertEqual([t._name_lbl.text()
                          for t in self.pane._board._tiles.values()],
                         ["Turnier 4"])

    def test_a_tile_says_how_many_songs_and_which_dances(self):
        self._file_a_weekend()
        self._pick(0)
        tiles = list(self.pane._board._tiles.values())
        self.assertEqual(tiles[0]._sub_lbl.text(), "2 ♪  ·  LW TG")
        self.assertEqual(tiles[0]._style, "Standard")
        self.assertEqual(tiles[1]._style, "Latin")

    def test_a_playlist_whose_file_is_gone_is_marked_on_its_tile(self):
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": "Turnier 1", "m3u": str(self.dir / "weg.m3u")}]})
        self.pane._rebuild()
        self._pick(0)
        tile = next(iter(self.pane._board._tiles.values()))
        self.assertTrue(tile._missing)
        self.assertIn("gone", tile._sub_lbl.text())

    def test_the_badge_counts_the_folders_playlists_and_their_songs(self):
        self._file_a_weekend()
        self._pick(0)
        self.assertEqual(self.pane._total_lbl.text(),
                         "Σ  2 playlists  ·  3 songs")

    def test_a_playlist_filed_at_the_root_is_still_reachable(self):
        # Leaves are not rows on the board, so the root gets a stand-in folder.
        m3u = _m3u(self.dir, "Eintanzen")
        self.pane._on_files_dropped(None, [m3u])
        first = self.pane._tree.topLevelItem(0)
        self.assertEqual(first.text(0), "📂  (not in a folder)")
        self.pane._tree.setCurrentItem(first)
        self.assertEqual([t._name_lbl.text()
                          for t in self.pane._board._tiles.values()],
                         ["Eintanzen"])

    def test_no_stand_in_folder_while_nothing_is_filed_at_the_root(self):
        self._file_a_weekend()
        self.assertNotIn("📂  (not in a folder)",
                         [self.pane._tree.topLevelItem(i).text(0)
                          for i in range(self.pane._tree.topLevelItemCount())])

    def test_double_clicking_a_tile_asks_for_it_to_be_loaded(self):
        t1, _, _ = self._file_a_weekend()
        self._pick(0)
        asked = []
        self.pane.loadRequested.connect(asked.append)
        next(iter(self.pane._board._tiles.values())).mouseDoubleClickEvent(None)
        self.assertEqual(asked, [str(t1)])

    def test_clicking_a_tile_selects_that_one_and_no_other(self):
        self._file_a_weekend()
        self._pick(0)
        keys = list(self.pane._board._tiles)
        self.pane._on_slot_picked(keys[1])
        self.assertEqual([t._selected for t in self.pane._board._tiles.values()],
                         [False, True])

    def test_a_tile_hands_out_its_playlist_file_when_dragged(self):
        t1, _, _ = self._file_a_weekend()
        self._pick(0)
        tile = next(iter(self.pane._board._tiles.values()))
        tile._press = QPoint(0, 0)
        with mock.patch.object(gt, "QDrag") as drag_cls:
            tile.mouseMoveEvent(_Move(200, 200))
        mime = drag_cls.return_value.setMimeData.call_args[0][0]
        self.assertEqual([Path(u.toLocalFile()) for u in mime.urls()], [t1])
        self.assertEqual(mime.text(), str(t1))

    def test_a_press_that_only_wandered_is_not_a_drag(self):
        self._file_a_weekend()
        self._pick(0)
        tile = next(iter(self.pane._board._tiles.values()))
        tile._press = QPoint(0, 0)
        with mock.patch.object(gt, "QDrag") as drag_cls:
            tile.mouseMoveEvent(_Move(1, 1))
        drag_cls.assert_not_called()

    def test_showing_a_slots_tracks_switches_view_with_it_selected(self):
        self._file_a_weekend()
        self._pick(0)
        key = list(self.pane._board._tiles)[1]
        self.pane._show_tracks_of(key)
        self.assertEqual(self.pane._view, gt.VIEW_LIST)
        self.assertEqual(self.pane._current_key(), key)
        self.assertIn("Bailamos", self.pane._table.item(0, 4).text())

    def _rounds_m3u(self, name: str, passes: int) -> Path:
        """A playlist that runs the five Standard dances `passes` times — which
        is all the round derivation reads to say how far the tournament goes."""
        return _m3u(self.dir, name, [
            (self.dir / f"{t} #{r}.mp3", f"{t} #{r}")
            for r in range(passes)
            for t in ("Fascination LW 29", "Jealousy TG 32", "Moon River WW 30",
                      "Sing Sing SF 50", "Intermezzo QS 51")])

    def _tile_of(self, m3u: Path):
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": m3u.stem, "m3u": str(m3u)}]})
        self.pane._rebuild()
        self._pick(0)
        return next(iter(self.pane._board._tiles.values()))

    def test_a_tile_says_how_far_the_tournament_runs(self):
        tile = self._tile_of(self._rounds_m3u("Turnier 1", 3))
        self.assertEqual(tile._round_lbl.text(), "VR - ZR - ER")

    def test_the_rounds_of_a_long_tournament_are_all_named(self):
        # Read off the slot itself, not the label: what a label of that width
        # elides is the offscreen platform's font metrics talking, not ours.
        m3u = self._rounds_m3u("Turnier 1", 5)
        meta = self.pane._slot_meta({"name": "Turnier 1", "m3u": str(m3u)}, "0")
        self.assertEqual(meta["rounds"], "VR - 1ZR - 2ZR - SF - ER")

    def test_a_list_that_plays_no_rounds_claims_none(self):
        # One pass through the dances is a warm-up, not a tournament.
        tile = self._tile_of(self._rounds_m3u("Eintanzen", 1))
        self.assertEqual(tile._round_lbl.text(), "")

    def test_a_file_that_is_one_round_takes_it_from_its_name(self):
        # One round is one pass through the dances — nothing to cut, so the
        # name is all there is, and it is what the operator wrote.
        tile = self._tile_of(self._rounds_m3u("07 ZR_WDSF", 1))
        self.assertEqual(tile._round_lbl.text(), "ZR")

    def test_a_file_naming_rounds_of_two_classes_shows_both(self):
        tile = self._tile_of(self._rounds_m3u("08 ZR_WDSF_ER_JUGC", 1))
        self.assertEqual(tile._round_lbl.text(), "ZR - ER")

    def test_a_warm_up_is_still_not_a_tournament(self):
        tile = self._tile_of(self._rounds_m3u("eintanzen", 1))
        self.assertEqual(tile._round_lbl.text(), "")

    def test_the_rounds_are_written_out_in_the_tooltip(self):
        tile = self._tile_of(self._rounds_m3u("Turnier 1", 3))
        self.assertIn("Vorrunde  →  Zwischenrunde  →  Finale", tile.toolTip())

    def test_the_tiles_of_the_old_folder_go_when_another_is_picked(self):
        self._file_a_weekend()
        self._pick(0)
        self._pick(1, 0)
        self.assertEqual([t._name_lbl.text()
                          for t in self.pane._board._tiles.values()],
                         ["Turnier 4"])


class HeaderLanguageTest(unittest.TestCase):
    """The track list's second column, which says which round plays it.

    It was written as "Runde" in a row of otherwise English headers, so the
    app said one German word to an English operator and had nothing left to
    translate for a German one. The headers go through
    `setHorizontalHeaderLabels`, which i18n patches — so the English spelling
    is what the catalog is keyed on.
    """

    def setUp(self):
        from planner import i18n
        self.i18n = i18n
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.addCleanup(i18n._restore_text_hook)

    def headers(self, language):
        self.i18n.set_active(language)
        self.i18n.install_text_hook()   # a no-op until a language is picked
        pane = gt.TournamentTree(JsonStore.at(_tmp() / "tournaments.json"))
        self.addCleanup(reap_widget, pane)
        return [pane._table.horizontalHeaderItem(c).text()
                for c in range(pane._table.columnCount())]

    def test_english_says_round(self):
        # The ⏱ column draws its own header, so its text is blank by then.
        self.assertEqual(self.headers("en"),
                         ["▶", "Round", "Dance", "Artist", "Title",
                          "BPM", "", "Pop", "Class"])

    def test_german_says_runde(self):
        cols = self.headers("de")
        self.assertEqual(cols[1], "Runde")
        self.assertNotIn("Dance", cols, "the neighbours translate too")


if __name__ == "__main__":
    unittest.main()
