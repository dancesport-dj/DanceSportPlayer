"""📚 The music libraries the window works on, and the threads that load them.

Split off MainWindow (H1), where they were six loose attributes read and
written by fourteen mixins. Held here, the window has one name for "the
library side" instead of six, and the generation, analysis and duplicate code
can later ask this object instead of reaching into the window.

A first step only: the object holds the state, and the window still starts the
loaders and handles their signals. Moving those handlers in here is the next
one. The generation's own PlaylistSuggester is not library state: it belongs
to the deck that was generated (see gui.deck_snapshot) and stays on the window.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.workers import GlobalCacheLoader, GlobalLibraryLoader, LibraryLoader
    from planner.db import AudioCache
    from planner.library import MusicLibrary


class LibraryService:
    """What is loaded, and what is loading it.

    - `lib`: the library scanned from `library_dir`, the one playlists are
      generated from. None until the first scan is done.
    - `cache`: the audio cache (features, fingerprints, measurements) that came
      with it; also what the player side reads loudness and PD marks from.
    - `global_lib`: the whole-repository library behind the ≈ global search,
      built on first use and never a source for a generated list.
    - `loader`, `global_loader`, `cache_loader`: the threads filling them.
      Parented to the window, so its shutdown still finds and joins them.
    """

    def __init__(self) -> None:
        self.lib: MusicLibrary | None = None
        self.cache: AudioCache | None = None
        self.global_lib: MusicLibrary | None = None
        self.loader: LibraryLoader | None = None
        self.global_loader: GlobalLibraryLoader | None = None
        self.cache_loader: GlobalCacheLoader | None = None
