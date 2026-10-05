"""Tests for the internal slot-to-slot drop target
(gui.table_dnd.TableDragDropMixin._resolve_internal_drop) — above all that the
round/dance HEADER rows between two rounds are no longer dead zones."""
import os
import tempfile
import unittest

from gui.running_order import Row, RunningOrder


# Both mixins pull in gui.dialogs, which resolves the state files at import
# time — keep the import at TEST time (not module load), so during discovery
# test_state_files still gets to set its own DANCEPLAYLIST_STATE_DIR first.
def _deck_mixins():
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_drop_"))
    from gui.table_dnd import TableDragDropMixin
    from gui.table_dynamic import DynamicModeMixin
    return TableDragDropMixin, DynamicModeMixin


class _Deck:
    """A two-round deck, LW + TG, one heat each:

        0  ═══ VORRUNDE ═══        (round header)
        1    Langsamer Walzer      (dance header)
        2      <LW song>
        3    Tango                 (dance header)
        4      <TG song>
        5  ═══ ENDRUNDE ═══
        6    Langsamer Walzer
        7      <LW song>
        8    Tango
        9      <TG song>
    """

    def __init__(self):
        def slot(rn, dance, **extra):
            return Row(round_name=rn, dance=dance, entry=object(), **extra)
        self._row_meta = RunningOrder([
            None, None, slot("Vorrunde", "LW"), None, slot("Vorrunde", "TG"),
            None, None, slot("Endrunde", "LW"), None, slot("Endrunde", "TG"),
        ])
        self._row_round_name = {0: "Vorrunde", 1: "Vorrunde", 3: "Vorrunde",
                                5: "Endrunde", 6: "Endrunde", 8: "Endrunde"}


class ResolveInternalDropTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Deck(_Deck, *_deck_mixins()):
            pass
        cls.Deck = Deck

    def setUp(self):
        self.d = self.Deck()

    def test_song_slot_of_the_same_dance_is_taken_as_is(self):
        self.assertEqual(self.d._resolve_internal_drop(7, src=2), 7)

    def test_round_header_lands_in_that_round(self):
        # Dragging the Vorrunde LW track onto the ENDRUNDE header used to hit a
        # row with no meta and be refused — the round boundary dead zone.
        self.assertEqual(self.d._resolve_internal_drop(5, src=2), 7)
        self.assertEqual(self.d._resolve_internal_drop(5, src=4), 9)

    def test_dance_header_lands_in_its_own_round_not_its_own_dance(self):
        # The dragged track's dance decides the slot; the header only names the
        # round — so a Tango dropped on Endrunde's "Langsamer Walzer" header
        # still lands in Endrunde's Tango slot.
        self.assertEqual(self.d._resolve_internal_drop(6, src=4), 9)

    def test_header_of_the_source_round_lands_back_in_it(self):
        self.assertEqual(self.d._resolve_internal_drop(0, src=7), 2)

    def test_song_row_of_another_dance_is_left_refused(self):
        # A wrong-dance aim is a real mistake, not a boundary — don't silently
        # redirect it (the caller's _internal_drop_ok then rejects the drop).
        self.assertEqual(self.d._resolve_internal_drop(9, src=2), 9)

    def test_row_below_the_grid_is_left_alone(self):
        self.assertEqual(self.d._resolve_internal_drop(99, src=2), 99)
        self.assertEqual(self.d._resolve_internal_drop(-1, src=2), -1)

    def test_no_drag_source_changes_nothing(self):
        self.assertEqual(self.d._resolve_internal_drop(5, src=None), 5)

    def test_round_without_the_dragged_dance_is_left_refused(self):
        # Endrunde skips the Tango → nothing to redirect its header to.
        self.d._row_meta[9] = None
        self.assertEqual(self.d._resolve_internal_drop(5, src=4), 5)


if __name__ == "__main__":
    unittest.main()
