"""📚 The music libraries the window works on, and the threads that load them.

Split off MainWindow (H1), where they were six loose attributes read and
written by fourteen mixins. Held here, the window has one name for "the
library side" instead of six, and the generation, analysis and duplicate code
can later ask this object instead of reaching into the window.

A first step only: the object holds the state, and the window still starts the
loaders and handles their signals. Moving those handlers in here is the next
one. The generation's own PlaylistSuggester is not library state: it belongs
to the deck that was generated (see gui.decks.deck_snapshot) and stays on the window.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.common import BusyDialog
    from gui.library_load_bar import LibraryLoadBar
    from gui.workers import GlobalCacheLoader, GlobalLibraryLoader, LibraryLoader
    from planner.models import MusicEntry
    from planner.music.db import AudioCache
    from planner.music.library import MusicLibrary


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
    - `restore_memo`: path → entry while one saved env is being put back
      (see RestoreMixin._restore_env), None the rest of the time.
    - `load_bar`: the scan's progress in the status bar (gui.library_load_bar);
      `load_bar.running` is True while `lib` is still being scanned.
    - `repo_bar`: the same for 🔄 the walk of the whole repository.
    - `preloader`: the `cache_loader` started after startup to have
      `global_lib` ready before anyone asks; `preload_busy` the dialog of
      whoever asked while it still ran, None while nobody waits for it;
      `whole_waiting` True while 🌐 waits for it, with no dialog.
    """

    def __init__(self) -> None:
        self.lib: MusicLibrary | None = None
        self.cache: AudioCache | None = None
        self.global_lib: MusicLibrary | None = None
        self.loader: LibraryLoader | None = None
        self.global_loader: GlobalLibraryLoader | None = None
        self.cache_loader: GlobalCacheLoader | None = None
        self.restore_memo: dict[str, MusicEntry | None] | None = None
        self.load_bar: LibraryLoadBar | None = None
        self.repo_bar: LibraryLoadBar | None = None
        self.preloader: GlobalCacheLoader | None = None
        self.preload_busy: BusyDialog | None = None
        self.whole_waiting = False
        self._stand_in: MusicLibrary | None = None

    def resolver(self) -> MusicLibrary | None:
        """The library that turns a saved path into an entry.

        `lib` once it is scanned. Before that — the window opens and the last
        session comes back while the scan still runs — an empty stand-in, so
        every path is rebuilt from its file like a track dropped in from
        outside (MusicLibrary.adopt later adds what the scan knows). None
        while there is not even an audio cache to read features from."""
        if self.lib is not None:
            return self.lib
        if self.cache is None:
            return None
        if self._stand_in is None:
            from planner.music.library import MusicLibrary
            self._stand_in = MusicLibrary()
        return self._stand_in
