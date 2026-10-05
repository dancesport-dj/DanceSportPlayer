"""Tests for the 🎛 cartwall document model — pure logic, no Qt.

The promises the wall makes to the operator:
  • a pad you placed stays where you placed it, including across a grid change
  • no edit and no reload ever loses a pad
  • a cartwall.json this build does not understand is left alone, not overwritten
"""
import unittest

from planner.cartwall import (
    CARTWALL_VERSION, DEFAULT_GRID, DEFAULT_PAD_COLOUR, DEFAULT_PAGES,
    GRID_SIZES, LABEL_MAX, SLOT_KEYS, CartPad, Page, blank_page, cell_key,
    clean_slot_keys, clear_pad, default_label, dump_doc, fill_pads, is_portrait,
    load_doc, missing_paths, move_pad, new_wall, pack_one_page, pad_count,
    remap_pads,
    pad_title, parse_cell, resize_grid, set_pad, slot_key, transpose,
    trim_pages)


def _pad(name="x.mp3", **kw):
    return CartPad(path=name, **kw)


def _wall(cells, name=""):
    """One page holding a pad at each given cell, labelled by its cell."""
    return [Page(name=name, pads={c: _pad(f"{c[0]}_{c[1]}.mp3") for c in cells})]


class LabelTest(unittest.TestCase):

    def test_leading_track_number_is_dropped(self):
        self.assertEqual(default_label(r"F:\fx\01 - Tusch.mp3"), "Tusch")
        self.assertEqual(default_label(r"F:\fx\003_Applaus.mp3"), "Applaus")

    def test_trailing_tempo_tag_is_dropped(self):
        self.assertEqual(default_label(r"F:\fx\Fanfare (LW 29).mp3"), "Fanfare")

    def test_underscores_become_spaces(self):
        self.assertEqual(default_label("intro_sting_long.mp3"), "intro sting long")

    def test_long_name_is_capped_with_an_ellipsis(self):
        got = default_label("a_very_long_sample_name_that_never_ends_at_all.mp3")
        self.assertEqual(len(got), LABEL_MAX)
        self.assertTrue(got.endswith("…"))

    def test_a_name_that_is_only_scaffolding_still_yields_something(self):
        self.assertTrue(default_label("07 (LW 29).mp3"))

    def test_explicit_label_wins_over_the_filename(self):
        self.assertEqual(pad_title(_pad("01 - Tusch.mp3", label="Einmarsch")),
                         "Einmarsch")
        self.assertEqual(pad_title(_pad("01 - Tusch.mp3")), "Tusch")


class CellTest(unittest.TestCase):

    def test_key_round_trip(self):
        self.assertEqual(parse_cell(cell_key((3, 5))), (3, 5))

    def test_junk_keys_are_rejected(self):
        for key in ("x", "1", "", "1,2,3", "a,b", "-1,0", "0,-1", "1,"):
            self.assertIsNone(parse_cell(key), key)


class PadEditTest(unittest.TestCase):

    def test_set_and_clear(self):
        pages = [blank_page()]
        set_pad(pages, 0, (1, 1), _pad("tusch.mp3"))
        self.assertEqual(pad_count(pages), 1)
        clear_pad(pages, 0, (1, 1))
        self.assertEqual(pad_count(pages), 0)

    def test_clearing_an_empty_cell_is_harmless(self):
        pages = [blank_page()]
        clear_pad(pages, 0, (0, 0))
        self.assertEqual(pad_count(pages), 0)

    def test_move_into_an_empty_cell(self):
        pages = _wall([(0, 0)])
        move_pad(pages, 0, (0, 0), 0, (2, 3))
        self.assertEqual(list(pages[0].pads), [(2, 3)])

    def test_move_onto_an_occupied_cell_swaps(self):
        pages = _wall([(0, 0), (1, 1)])
        move_pad(pages, 0, (0, 0), 0, (1, 1))
        self.assertEqual(pages[0].pads[(1, 1)].path, "0_0.mp3")
        self.assertEqual(pages[0].pads[(0, 0)].path, "1_1.mp3")
        self.assertEqual(pad_count(pages), 2)

    def test_move_across_pages(self):
        pages = _wall([(0, 0)]) + [blank_page()]
        move_pad(pages, 0, (0, 0), 1, (0, 0))
        self.assertEqual(pad_count(pages[:1]), 0)
        self.assertEqual(pad_count(pages[1:]), 1)

    def test_move_onto_itself_changes_nothing(self):
        pages = _wall([(0, 0)])
        move_pad(pages, 0, (0, 0), 0, (0, 0))
        self.assertEqual(list(pages[0].pads), [(0, 0)])


class FillPadsTest(unittest.TestCase):
    """Dropping a whole library selection on one pad."""

    def test_one_path_behaves_exactly_like_the_old_single_drop(self):
        pages = _wall([(1, 1)])
        filled = fill_pads(pages, 0, (1, 1), ["new.mp3"], (4, 4))
        self.assertEqual(filled, [(0, (1, 1))])
        self.assertEqual(pages[0].pads[(1, 1)].path, "new.mp3")

    def test_the_aimed_cell_always_takes_the_first_track(self):
        pages = [blank_page()]
        fill_pads(pages, 0, (2, 2), ["a.mp3", "b.mp3", "c.mp3"], (4, 4))
        self.assertEqual(pages[0].pads[(2, 2)].path, "a.mp3")

    def test_the_rest_go_into_the_free_cells_that_follow(self):
        pages = [blank_page()]
        fill_pads(pages, 0, (0, 1), ["a.mp3", "b.mp3", "c.mp3"], (4, 4))
        self.assertEqual([(c, p.path) for c, p in sorted(pages[0].pads.items())],
                         [((0, 1), "a.mp3"), ((0, 2), "b.mp3"), ((0, 3), "c.mp3")])

    def test_pads_that_are_already_set_up_are_skipped_not_overwritten(self):
        pages = _wall([(0, 1)])
        fill_pads(pages, 0, (0, 0), ["a.mp3", "b.mp3"], (4, 4))
        self.assertEqual(pages[0].pads[(0, 1)].path, "0_1.mp3")
        self.assertEqual(pages[0].pads[(0, 2)].path, "b.mp3")

    def test_a_selection_bigger_than_the_page_spills_onto_the_next_one(self):
        pages = [blank_page()]
        paths = [f"{n}.mp3" for n in range(6)]
        filled = fill_pads(pages, 0, (0, 0), paths, (2, 2))
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(filled), 6)
        self.assertEqual(sorted(p.path for p in pages[1].pads.values()),
                         ["4.mp3", "5.mp3"])

    def test_dropping_nothing_changes_nothing(self):
        pages = _wall([(0, 0)])
        self.assertEqual(fill_pads(pages, 0, (1, 1), [], (4, 4)), [])
        self.assertEqual(pad_count(pages), 1)

    def test_every_pad_it_reports_placed_survives_a_reload(self):
        """A huge selection used to spill onto as many pages as it needed, but
        a saved wall is read back only up to its page cap — the pads beyond it
        were reported placed and gone after the next start."""
        pages = [blank_page()]
        paths = [f"{n}.mp3" for n in range(200)]
        filled = fill_pads(pages, 0, (0, 0), paths, (2, 2))
        self.assertLess(len(filled), len(paths), "the wall is full before the list is")
        reloaded = load_doc(dump_doc((2, 2), pages, 0)).pages
        self.assertEqual(pad_count(reloaded), len(filled))


class SlotKeyTest(unittest.TestCase):

    def test_the_first_nine_slots_read_left_to_right_top_to_bottom(self):
        self.assertEqual(slot_key((4, 4), (0, 0)), "Ctrl+1")
        self.assertEqual(slot_key((4, 4), (0, 3)), "Ctrl+4")
        self.assertEqual(slot_key((4, 4), (1, 0)), "Ctrl+5")
        self.assertEqual(slot_key((4, 4), (2, 0)), "Ctrl+9")

    def test_past_the_ninth_slot_there_is_no_default_key(self):
        self.assertEqual(slot_key((4, 4), (2, 1)), "")
        self.assertEqual(len(SLOT_KEYS), 9)

    def test_a_cell_outside_the_grid_has_no_key(self):
        self.assertEqual(slot_key((4, 4), (9, 9)), "")

    def test_a_wall_can_bring_its_own_keys(self):
        keys = ("F1", "F2", "F3")
        self.assertEqual(slot_key((4, 4), (0, 0), keys), "F1")
        self.assertEqual(slot_key((4, 4), (0, 2), keys), "F3")

    def test_a_slot_past_the_wall_s_own_list_has_no_key(self):
        self.assertEqual(slot_key((4, 4), (0, 3), ("F1", "F2", "F3")), "")

    def test_own_keys_may_reach_past_the_ninth_slot(self):
        keys = tuple(f"F{n}" for n in range(1, 13))
        self.assertEqual(slot_key((4, 4), (2, 3), keys), "F12")


class CleanSlotKeysTest(unittest.TestCase):
    """What may come out of a hand-edited file or a half-filled dialog."""

    def test_a_gap_keeps_the_slots_after_it_in_place(self):
        self.assertEqual(clean_slot_keys(["F1", "", "F3"]), ("F1", "", "F3"))

    def test_trailing_blanks_are_dropped(self):
        self.assertEqual(clean_slot_keys(["F1", "", ""]), ("F1",))

    def test_nothing_but_blanks_is_no_keys_at_all(self):
        self.assertEqual(clean_slot_keys(["", "  "]), ())

    def test_whitespace_is_stripped_so_it_cannot_become_the_space_key(self):
        # QKeySequence("   ") parses as Space — a key nobody asked for.
        self.assertEqual(clean_slot_keys([" F1 ", "   "]), ("F1",))

    def test_a_non_string_entry_becomes_a_gap_not_a_crash(self):
        self.assertEqual(clean_slot_keys(["F1", 7, None, "F4"]),
                         ("F1", "", "", "F4"))

    def test_something_that_is_not_a_list_falls_back_to_the_defaults(self):
        self.assertEqual(clean_slot_keys("F1"), SLOT_KEYS)
        self.assertEqual(clean_slot_keys(None), SLOT_KEYS)

    def test_an_absurd_list_is_capped(self):
        self.assertLessEqual(len(clean_slot_keys(["F1"] * 5000)), 144)


class TransposeTest(unittest.TestCase):
    """Turning the wall follows the dock between a side edge and a top edge, so
    it has to be lossless — the pads travel with the shape."""

    def test_the_shape_and_every_pad_turn_together(self):
        grid, pages = transpose((8, 2), _wall([(0, 7), (1, 0)]))
        self.assertEqual(grid, (2, 8))
        self.assertEqual(sorted(pages[0].pads), [(0, 1), (7, 0)])

    def test_turning_twice_is_exactly_where_you_started(self):
        cells = [(0, 0), (1, 3), (3, 7)]
        grid, pages = transpose(*transpose((8, 4), _wall(cells)))
        self.assertEqual(grid, (8, 4))
        self.assertEqual(sorted(pages[0].pads), cells)
        self.assertEqual(pages[0].pads[(3, 7)].path, "3_7.mp3")

    def test_no_pad_is_lost_even_off_a_lopsided_grid(self):
        pages = _wall([(r, c) for r in range(4) for c in range(8)])
        self.assertEqual(pad_count(transpose((8, 4), pages)[1]), 32)

    def test_page_names_survive(self):
        self.assertEqual(transpose((4, 4), _wall([(0, 0)], "Fanfaren"))[1][0].name,
                         "Fanfaren")

    def test_portrait_is_taller_than_it_is_wide(self):
        self.assertTrue(is_portrait((2, 8)))
        self.assertFalse(is_portrait((8, 2)))
        self.assertFalse(is_portrait((4, 4)))   # square is not a side-dock shape


class TrimPagesTest(unittest.TestCase):

    def test_trailing_empty_pages_are_dropped(self):
        pages = _wall([(0, 0)]) + [blank_page(), blank_page()]
        self.assertEqual(len(trim_pages(pages)), 1)

    def test_one_page_always_survives(self):
        self.assertEqual(len(trim_pages([blank_page()])), 1)

    def test_a_named_empty_page_is_kept(self):
        pages = _wall([(0, 0)]) + [blank_page("Siegerehrung")]
        self.assertEqual(len(trim_pages(pages)), 2)

    def test_an_empty_page_between_two_full_ones_is_kept(self):
        pages = _wall([(0, 0)]) + [blank_page()] + _wall([(0, 0)])
        self.assertEqual(len(trim_pages(pages)), 3)


class PackOnePageTest(unittest.TestCase):
    """🗂 → 'All pads on one page': no paging mid-heat."""

    def test_the_second_page_fills_the_free_cells_of_the_first(self):
        pages = _wall([(0, 0), (2, 1)]) + _wall([(0, 0), (1, 1)])
        out, ok = pack_one_page(pages, (2, 4))
        self.assertTrue(ok)
        self.assertEqual(len(out), 1)
        self.assertEqual(pad_count(out), 4)

    def test_the_pads_already_on_page_one_do_not_move(self):
        pages = _wall([(3, 1)]) + _wall([(0, 0)])
        out, _ok = pack_one_page(pages, (2, 4))
        self.assertEqual(out[0].pads[(3, 1)].path, "3_1.mp3")
        self.assertEqual(out[0].pads[(0, 0)].path, "0_0.mp3")

    def test_a_wall_that_does_not_fit_is_left_alone(self):
        pages = _wall([(0, 0), (0, 1), (1, 0), (1, 1)]) + _wall([(0, 0)])
        out, ok = pack_one_page(pages, (2, 2))
        self.assertFalse(ok)
        self.assertEqual(len(out), 2)
        self.assertEqual(pad_count(out), 5)

    def test_the_first_page_keeps_its_name(self):
        pages = _wall([(0, 0)], name="Fanfaren") + _wall([(0, 0)])
        out, _ok = pack_one_page(pages, (2, 4))
        self.assertEqual(out[0].name, "Fanfaren")


class ResizeGridTest(unittest.TestCase):
    """The whole reason pads are keyed by (row, col)."""

    def test_growing_moves_nothing(self):
        pages = _wall([(0, 0), (3, 3), (1, 2)])
        out, moved = resize_grid(pages, (8, 6))
        self.assertEqual(moved, 0)
        self.assertEqual(sorted(out[0].pads), [(0, 0), (1, 2), (3, 3)])

    def test_shrinking_relocates_only_what_no_longer_fits(self):
        pages = _wall([(0, 0), (5, 7)])
        out, moved = resize_grid(pages, (4, 4))
        self.assertEqual(moved, 1)
        self.assertEqual(pad_count(out), 2)
        self.assertEqual(out[0].pads[(0, 0)].path, "0_0.mp3")
        self.assertIn("5_7.mp3", [p.path for p in out[0].pads.values()])
        for row, col in out[0].pads:
            self.assertLess(row, 4)
            self.assertLess(col, 4)

    def test_shrinking_never_loses_a_pad(self):
        full = [Page(pads={c: _pad(f"{c[0]}_{c[1]}.mp3")
                           for c in [(r, c) for r in range(6) for c in range(8)]})]
        out, moved = resize_grid(full, (4, 4))
        self.assertEqual(pad_count(out), 48)
        self.assertEqual(moved, 48 - 16)
        self.assertEqual(len(out), 3)     # 48 pads at 16 per page

    def test_spill_lands_on_a_new_page_in_reading_order(self):
        pages = _wall([(r, 0) for r in range(6)])
        out, _ = resize_grid(pages, (2, 2))
        self.assertEqual([p.path for p in out[0].pads.values()][:2],
                         ["0_0.mp3", "1_0.mp3"])
        self.assertEqual(pad_count(out), 6)

    def test_an_empty_wall_survives_a_resize(self):
        out, moved = resize_grid([], (4, 4))
        self.assertEqual((len(out), moved, pad_count(out)), (1, 0, 0))


class MissingPathsTest(unittest.TestCase):

    def test_only_the_gone_ones_are_reported(self):
        pages = [Page(pads={(0, 0): _pad("here.mp3"), (0, 1): _pad("gone.mp3")})]
        got = missing_paths(pages, exists=lambda p: p == "here.mp3")
        self.assertEqual(got, {(0, (0, 1))})

    def test_nothing_missing_is_an_empty_set(self):
        pages = _wall([(0, 0)])
        self.assertEqual(missing_paths(pages, exists=lambda p: True), set())


class RemapPadsTest(unittest.TestCase):
    """A wall that moved to another PC: 🧭 Fix paths re-points the pads."""

    @staticmethod
    def _found(mapping):
        return lambda path: mapping.get(path)

    def _wall_of(self, *paths):
        return [Page(pads={(0, i): _pad(p) for i, p in enumerate(paths)})]

    def test_a_missing_pad_is_repointed_and_reported(self):
        pages = self._wall_of("C:/old/tusch.mp3")
        got = remap_pads(pages, self._found({"C:/old/tusch.mp3": "F:/new/tusch.mp3"}),
                         exists=lambda p: False)
        self.assertEqual(got, [(0, (0, 0), "C:/old/tusch.mp3", "F:/new/tusch.mp3")])
        self.assertEqual(pages[0].pads[(0, 0)].path, "F:/new/tusch.mp3")

    def test_a_pad_that_plays_fine_is_never_touched(self):
        """Only a broken pad is a question — a working one is an answer."""
        pages = self._wall_of("F:/new/tusch.mp3")
        self.assertEqual(remap_pads(pages, lambda p: "somewhere/else.mp3",
                                    exists=lambda p: True), [])
        self.assertEqual(pages[0].pads[(0, 0)].path, "F:/new/tusch.mp3")

    def test_a_pad_the_remapper_cannot_place_keeps_its_path(self):
        """Marked missing is recoverable; overwritten with a guess is not."""
        pages = self._wall_of("C:/old/tusch.mp3")
        self.assertEqual(remap_pads(pages, lambda p: None, exists=lambda p: False), [])
        self.assertEqual(pages[0].pads[(0, 0)].path, "C:/old/tusch.mp3")

    def test_every_page_of_the_wall_is_covered(self):
        pages = [Page(pads={(0, 0): _pad("C:/old/a.mp3")}),
                 Page(pads={(1, 1): _pad("C:/old/b.mp3")})]
        got = remap_pads(pages, lambda p: p.replace("C:/old", "F:/new"),
                         exists=lambda p: False)
        self.assertEqual([g[0] for g in got], [0, 1])
        self.assertEqual(pages[1].pads[(1, 1)].path, "F:/new/b.mp3")

    def test_an_empty_wall_is_no_work(self):
        self.assertEqual(remap_pads([], lambda p: "x", exists=lambda p: False), [])


class DocumentTest(unittest.TestCase):

    def test_no_file_yet_is_a_fresh_wall_that_may_be_saved(self):
        grid, pages, page, colour, ok, _fade, _keys = load_doc(None)
        self.assertEqual((grid, len(pages), page, colour, ok),
                         (DEFAULT_GRID, DEFAULT_PAGES, 0, DEFAULT_PAD_COLOUR,
                          True))

    def test_a_future_version_is_never_overwritten(self):
        ok = load_doc({"version": CARTWALL_VERSION + 1})[4]
        self.assertFalse(ok)

    def test_garbage_is_never_overwritten(self):
        for junk in ([], "wall", 7, {"pages": []}):
            self.assertFalse(load_doc(junk)[4], junk)

    def test_round_trip_keeps_every_pad_setting(self):
        pad = CartPad(path=r"F:\fx\bed.mp3", label="Bett", colour="#f2b134",
                      volume=0.25, loop=True, duck=False, shortcut="Ctrl+Shift+B")
        pages = [Page(name="Fanfaren", pads={(4, 0): pad})]
        grid, back, page, colour, ok, _fade, _keys = load_doc(
            dump_doc((8, 6), pages, 0, "#ffffff"))
        self.assertTrue(ok)
        self.assertEqual((grid, page, colour), ((8, 6), 0, "#ffffff"))
        self.assertEqual(back[0].name, "Fanfaren")
        self.assertEqual(back[0].pads[(4, 0)], pad)

    def test_the_wall_default_colour_survives_a_round_trip(self):
        pages = [Page(pads={(0, 0): _pad("a.mp3")})]
        doc = dump_doc((8, 4), pages, 0, "#2f8f4e")
        self.assertEqual(load_doc(doc)[3], "#2f8f4e")

    def test_a_wall_saved_before_the_colour_existed_opens_in_the_standard_one(self):
        """The absent key must not read as 'some grey nobody chose'."""
        doc = dump_doc((8, 4), [Page(pads={(0, 0): _pad("a.mp3")})], 0)
        doc.pop("default_colour", None)
        self.assertEqual(load_doc(doc)[3], DEFAULT_PAD_COLOUR)

    def test_defaults_fill_in_for_an_absent_setting(self):
        doc = {"version": CARTWALL_VERSION, "cols": 8, "rows": 6,
               "pages": [{"pads": {"0,0": {"path": "a.mp3"}}}]}
        pad = load_doc(doc)[1][0].pads[(0, 0)]
        self.assertEqual((pad.volume, pad.loop, pad.duck, pad.label),
                         (1.0, False, True, ""))

    def test_volume_is_clamped(self):
        doc = {"version": CARTWALL_VERSION, "cols": 8, "rows": 4,
               "pages": [{"pads": {
                   "0,0": {"path": "a.mp3", "volume": 4.5},
                   "0,1": {"path": "b.mp3", "volume": -2},
                   "0,2": {"path": "c.mp3", "volume": "loud"}}}]}
        pads = load_doc(doc)[1][0].pads
        self.assertEqual(pads[(0, 0)].volume, 1.0)
        self.assertEqual(pads[(0, 1)].volume, 0.0)
        self.assertEqual(pads[(0, 2)].volume, 1.0)

    def test_junk_keys_and_pathless_pads_are_dropped_neighbours_kept(self):
        doc = {"version": CARTWALL_VERSION, "pages": [{"pads": {
            "0,0": {"path": "keep.mp3"},
            "x": {"path": "junk.mp3"},
            "1": {"path": "junk.mp3"},
            "-1,0": {"path": "junk.mp3"},
            "0,1": {"label": "no path"},
            "0,2": "not even a dict"}}]}
        pads = load_doc(doc)[1][0].pads
        self.assertEqual([p.path for p in pads.values()], ["keep.mp3"])

    def test_an_out_of_grid_cell_is_relocated_not_dropped(self):
        doc = {"version": CARTWALL_VERSION, "cols": 4, "rows": 4,
               "pages": [{"pads": {"9,9": {"path": "far.mp3"}}}]}
        pages = load_doc(doc)[1]
        self.assertEqual(pad_count(pages), 1)
        self.assertEqual(list(pages[0].pads)[0], (0, 0))

    def test_an_unusable_grid_falls_back_to_the_default(self):
        for bad in ({"cols": 0, "rows": 6}, {"cols": 99, "rows": 6},
                    {"cols": "8", "rows": None}, {}):
            doc = dict(bad, version=CARTWALL_VERSION)
            self.assertEqual(load_doc(doc)[0], DEFAULT_GRID, bad)

    def test_every_offered_grid_size_round_trips(self):
        for grid in GRID_SIZES:
            cols, rows = grid
            pages = [Page(pads={(rows - 1, cols - 1): _pad("corner.mp3")})]
            back_grid, back, _page, _colour, ok, _fade, _keys = load_doc(
                dump_doc(grid, pages, 0))
            self.assertTrue(ok)
            self.assertEqual(back_grid, grid)
            self.assertEqual(list(back[0].pads), [(rows - 1, cols - 1)])

    def test_a_two_by_seven_wall_is_on_offer(self):
        """A side dock that fits seven rows of two, asked for by hand before."""
        self.assertIn((2, 7), GRID_SIZES)
        tall = [g for g in GRID_SIZES if g[0] == 2]
        self.assertEqual(tall, sorted(tall))

    def test_current_page_is_clamped_into_range(self):
        doc = dump_doc((8, 6), [blank_page(), blank_page("B")], 1)
        self.assertEqual(load_doc(doc)[2], 1)
        doc["page"] = 99
        self.assertEqual(load_doc(doc)[2], 1)
        doc["page"] = "second"
        self.assertEqual(load_doc(doc)[2], 0)

    def test_a_page_list_of_junk_yields_one_empty_page(self):
        doc = {"version": CARTWALL_VERSION, "pages": ["a", 3, None]}
        pages, ok = load_doc(doc)[1], load_doc(doc)[4]
        self.assertTrue(ok)
        self.assertEqual((len(pages), pad_count(pages)), (1, 0))

    def test_defaults_are_left_out_of_the_written_file(self):
        pages = [Page(pads={(0, 0): _pad("a.mp3")})]
        written = dump_doc((8, 6), pages, 0)["pages"][0]["pads"]["0,0"]
        self.assertEqual(written, {"path": "a.mp3"})

    def test_a_fresh_wall_opens_with_the_page_nav_worth_noticing(self):
        self.assertEqual(len(new_wall()), DEFAULT_PAGES)
        self.assertEqual(pad_count(new_wall()), 0)

    def test_remapped_slot_keys_survive_a_round_trip(self):
        keys = ("F5", "", "Ctrl+8") + SLOT_KEYS[3:]
        doc = dump_doc((8, 6), [blank_page()], 0, slot_keys=keys)
        self.assertEqual(load_doc(doc).slot_keys, keys)

    def test_a_wall_on_the_standard_keys_writes_no_key_list(self):
        """The file stays readable, and a later default change reaches walls
        nobody remapped."""
        doc = dump_doc((8, 6), [blank_page()], 0, slot_keys=SLOT_KEYS)
        self.assertNotIn("slot_keys", doc)

    def test_a_wall_saved_before_remapping_existed_keeps_the_standard_keys(self):
        doc = dump_doc((8, 6), [blank_page()], 0)
        doc.pop("slot_keys", None)
        self.assertEqual(load_doc(doc).slot_keys, SLOT_KEYS)

    def test_a_junk_key_list_in_the_file_cannot_reach_the_wall(self):
        doc = dump_doc((8, 6), [blank_page()], 0)
        doc["slot_keys"] = ["F5", 7, None, "  "]
        self.assertEqual(load_doc(doc).slot_keys, ("F5",))


if __name__ == "__main__":
    unittest.main()
