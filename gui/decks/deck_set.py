"""🎛 The window's playlist tables: the decks, the 📅 day decks, the wishlists
and the warm-up list, and the Deck kept for each of them.

Split off MainWindow (H1, DeckManager steps), where they were 19 loose
attributes that every deck, fold, wishlist, persistence and player mixin
read. Held here, the window has one name for "its tables".

A state move only: the window still creates the tables (`_setup_decks`)
and wires them up, decides which one has the focus and how many show, and
`self.deck(table)` still hands out each table's Deck.
"""
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from gui.decks.deck import Deck
    from gui.table.playlist_table import PlaylistTable


# MainWindow._setup_decks fills every table while the window is built, and
# none of them is None after that. Until then they are None, which only a test
# host that leaves a table out ever sees; typed as filled, so that no caller
# has to check for a table the window always has.
_UNSET = cast("PlaylistTable", None)


class DeckSet:
    """Every PlaylistTable the main window shows, built once at startup.

    - `tableA` … `tableH`: the eight playlist decks, also in `decks`.
    - `day_decks`: the eight 📅 competition-day decks.
    - `wishlist` … `wishlist4`: the flat wishlists, also in `wishlists`.
    - `warmup_table`: the warm-up (Eintanzen) list.
    - `all_tables`: all of the above, the decks first and the warm-up last.
    - `deck_of`: each table's Deck, reached through `MainWindow.deck(table)`.
    - `table`: the focused deck, the one the toolbar and the combos act on.
    - `deck_count`: how many decks are visible: 1, 2, 4 or 8, or 0 when
      only playing.
    """

    def __init__(self) -> None:
        self.tableA: PlaylistTable = _UNSET
        self.tableB: PlaylistTable = _UNSET
        self.tableC: PlaylistTable = _UNSET
        self.tableD: PlaylistTable = _UNSET
        self.tableE: PlaylistTable = _UNSET
        self.tableF: PlaylistTable = _UNSET
        self.tableG: PlaylistTable = _UNSET
        self.tableH: PlaylistTable = _UNSET
        self.wishlist: PlaylistTable = _UNSET
        self.wishlist2: PlaylistTable = _UNSET
        self.wishlist3: PlaylistTable = _UNSET
        self.wishlist4: PlaylistTable = _UNSET
        self.warmup_table: PlaylistTable = _UNSET
        self.decks: list[PlaylistTable] = []
        self.day_decks: list[PlaylistTable] = []
        self.wishlists: list[PlaylistTable] = []
        self.all_tables: list[PlaylistTable] = []
        self.deck_of: dict[PlaylistTable, Deck] = {}
        self.table: PlaylistTable = _UNSET
        self.deck_count = 1
