"""🎛 The window's playlist tables: the decks, the 📅 day decks, the wishlists
and the warm-up list, and the Deck kept for each of them.

Split off MainWindow (H1, DeckManager steps), where they were 19 loose
attributes that every deck, fold, wishlist, persistence and player mixin
read. Held here, the window has one name for "its tables".

A state move only: the window still creates the tables (`_setup_decks`)
and wires them up, decides which one has the focus and how many show, and
`self.deck(table)` still hands out each table's Deck.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.deck import Deck
    from gui.playlist_table import PlaylistTable


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
        self.tableA: PlaylistTable | None = None
        self.tableB: PlaylistTable | None = None
        self.tableC: PlaylistTable | None = None
        self.tableD: PlaylistTable | None = None
        self.tableE: PlaylistTable | None = None
        self.tableF: PlaylistTable | None = None
        self.tableG: PlaylistTable | None = None
        self.tableH: PlaylistTable | None = None
        self.wishlist: PlaylistTable | None = None
        self.wishlist2: PlaylistTable | None = None
        self.wishlist3: PlaylistTable | None = None
        self.wishlist4: PlaylistTable | None = None
        self.warmup_table: PlaylistTable | None = None
        self.decks: list[PlaylistTable] = []
        self.day_decks: list[PlaylistTable] = []
        self.wishlists: list[PlaylistTable] = []
        self.all_tables: list[PlaylistTable] = []
        self.deck_of: dict[PlaylistTable, Deck] = {}
        self.table: PlaylistTable | None = None
        self.deck_count = 1
