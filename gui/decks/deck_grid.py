"""🗂 The boxes, splitters and tabs the decks, competition days and wishlists sit in.

Split off MainWindow (H1, DeckManager steps), where they were 31 loose
attributes shared by the window, the deck, fold-to-tab and wishlist mixins.
Held here, the window has one name for "the deck grid's layout".

A first step only: the object holds the widgets, and the window still builds
them (`_setup_deck_grids`, `_setup_lower_panes`) and folds and resizes them.
The deck tables themselves (`tableA`…, `decks`, `wishlists`, `deck_of`)
are held next to it, in `gui.decks.deck_set`.
"""
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from PySide6.QtWidgets import QSplitter, QTabWidget, QWidget


# The window builds every one of these while it starts up, and none of them is
# None after that; only a test host that leaves one out sees the None. Typed
# as built, so that no caller has to check for a widget the window always has.
_UNBUILT = cast("Any", None)


class DeckGrid:
    """The layout widgets of the deck area, all built once at startup.

    - `deckB_box` … `deckH_box`: the header boxes of decks 2–8 (deck 1's box
      is placed straight into its column and kept by its Deck only).
    - `decks_col1`/`decks_col2` in `decks_split` (A/C left, B/D right) and
      `decks_col3`/`decks_col4` in `decks_split2` (E/G, F/H): the two 2×2
      deck grids, one per tab, built column-wise so a deck folded to a tab
      frees space in its own column.
    - `day_boxes`, `day_col1`…`day_col4`, `day_split`, `day_split2`: the same
      for the eight competition-day decks.
    - `wish_box` … `wish_box4` in `wish_split`, and `wish_col1`/`wish_col2`,
      the two columns `wish_split` holds instead in 2×2 wishlist mode.
    - `deck_tabs`: the tabs the deck grids sit on (A–D, E–H, the 📅 day),
      `day_tabs` the two sub-tabs of the day tab, `warmup_box` the warm-up
      list's box, and `right_split`, the decks above the library panes.
    """

    def __init__(self) -> None:
        self.deckB_box: QWidget = _UNBUILT
        self.deckC_box: QWidget = _UNBUILT
        self.deckD_box: QWidget = _UNBUILT
        self.deckE_box: QWidget = _UNBUILT
        self.deckF_box: QWidget = _UNBUILT
        self.deckG_box: QWidget = _UNBUILT
        self.deckH_box: QWidget = _UNBUILT
        self.decks_col1: QSplitter = _UNBUILT
        self.decks_col2: QSplitter = _UNBUILT
        self.decks_col3: QSplitter = _UNBUILT
        self.decks_col4: QSplitter = _UNBUILT
        self.decks_split: QSplitter = _UNBUILT
        self.decks_split2: QSplitter = _UNBUILT
        self.day_boxes: list[QWidget] = []
        self.day_col1: QSplitter = _UNBUILT
        self.day_col2: QSplitter = _UNBUILT
        self.day_col3: QSplitter = _UNBUILT
        self.day_col4: QSplitter = _UNBUILT
        self.day_split: QSplitter = _UNBUILT
        self.day_split2: QSplitter = _UNBUILT
        self.wish_box: QWidget = _UNBUILT
        self.wish_box2: QWidget = _UNBUILT
        self.wish_box3: QWidget = _UNBUILT
        self.wish_box4: QWidget = _UNBUILT
        self.wish_col1: QSplitter = _UNBUILT
        self.wish_col2: QSplitter = _UNBUILT
        self.wish_split: QSplitter = _UNBUILT
        self.warmup_box: QWidget = _UNBUILT
        self.deck_tabs: QTabWidget = _UNBUILT
        self.day_tabs: QTabWidget = _UNBUILT
        self.right_split: QSplitter = _UNBUILT
