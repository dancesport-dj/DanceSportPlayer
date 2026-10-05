"""What a PlaylistTable asks of the window around it — the whole list.

The table used to reach for MainWindow's private members through
`self.window()` in 33 places, each behind its own hasattr. They are all here
now: the table talks to `table.host` only, and this is the one file that
knows MainWindow's member names.

Every question has the answer a table outside the main window gets — in a
dialog, or in a test's bare window: a window without the member means
"nothing to do", never an AttributeError.
"""
import logging

from gui.dialogs import app_mode_of

log = logging.getLogger("dancesport.gui.playlist_table")


class TableHost:
    """The window of one table, seen from that table."""

    def __init__(self, table):
        self._table = table

    def _win(self):
        return self._table.window()

    def _call(self, name, *args, default=None, **kwargs):
        fn = getattr(self._win(), name, None)
        return fn(*args, **kwargs) if fn is not None else default

    def dialog_parent(self):
        """The window a dialog opened from the table centres on."""
        return self._win()

    # ── Settings ────────────────────────────────────────────────────────────
    def settings(self) -> dict:
        return getattr(self._win(), "_settings", None) or {}

    def has_tournaments(self) -> bool:
        """The window keeps a 🏆 Tournaments tree a saved list can be filed in."""
        return getattr(self._win(), "_tourney_tree", None) is not None

    def player_only(self) -> bool:
        """⚙ app mode 'player': this install runs the music, never plans it."""
        return app_mode_of(self.settings()) == "player"

    def list_vals(self) -> dict | None:
        """This list's own play values (wishlist, party, tournament), or None
        where the window keeps none."""
        return self._call("_list_vals", self._table)

    # ── The player ──────────────────────────────────────────────────────────
    def has_big_player(self) -> bool:
        return bool(getattr(self._win(), "_big_player", None))

    def toggle_play(self):
        """⏯ on the player card: pause or resume the running title."""
        self._win()._big_player.toggle_play()

    def is_player_running(self) -> bool:
        return bool(self._call("_is_player_running"))

    def is_player_stopped(self) -> bool:
        """Fully stopped — a cued title, not a paused one."""
        return bool(self._call("_is_player_stopped"))

    def can_stop_and_skip(self) -> bool:
        win = self._win()
        return hasattr(win, "_on_stop_btn") and hasattr(win, "_on_player_next")

    def music_running(self) -> bool:
        """A title is playing, or the next one is about to start."""
        win = self._win()
        playback = getattr(win, "_playback", None)
        between = getattr(win, "_between", None)
        return ((playback is not None and playback.path is not None)
                or (between is not None and between.pending is not None))

    def stop_music(self):
        self._call("_on_stop_btn")

    def skip_to_next(self):
        self._call("_on_player_next")

    def cue(self, path: str):
        """Load the title on the player card and leave it silent."""
        self._call("_on_player_drop", path)

    # ── Checks on single tracks ─────────────────────────────────────────────
    def can_check_tracks(self) -> bool:
        win = self._win()
        return hasattr(win, "_track_issues") and hasattr(win, "_entry_takt")

    def track_issues(self, entry, probe_silence: bool, in_final: bool) -> list[str]:
        return self._win()._track_issues(entry, probe_silence=probe_silence,
                                         in_final=in_final)

    def entry_takt(self, entry):
        return self._win()._entry_takt(entry)

    def check_track_speed(self, entry):
        self._call("_check_track_speed", entry)

    def rescan_entry_tags(self, entry):
        self._call("_rescan_entry_tags", entry)

    def edit_entry_tags(self, entries):
        self._call("_edit_entry_tags", entries)

    # ── This table as a deck ────────────────────────────────────────────────
    def deck_name(self) -> str:
        win = self._win()
        return win.deck(self._table).name if hasattr(win, "deck") else ""

    def name_after_playlist(self, stem: str):
        """A wishlist that an .m3u filled is named after it."""
        win = self._win()
        if hasattr(win, "_set_deck_name"):
            base = win.deck(self._table).default_name or "⭐  Wishlist"
            win._set_deck_name(self._table, f"{base}: {stem}")

    def reset_wishlist_name(self):
        self._call("_reset_wishlist_name", self._table)

    def set_deck_mode(self, mode: str):
        self._call("_set_deck_mode", self._table, mode)

    def ensure_deck_ready(self):
        """Wire a deck that was never generated: play callback, suggester."""
        self._call("_ensure_deck_ready", self._table)

    def warmup_table(self):
        """The Eintanzen panel's table, or None."""
        return getattr(self._win(), "_warmup_table", None)

    # ── The other lists ─────────────────────────────────────────────────────
    def planned_paths(self) -> set:
        """Every path the open playlist decks plan. Raises what the window's
        index raises; the caller decides what a failure costs."""
        if not hasattr(self._win(), "_deck_dedup_index"):
            return set()
        planned, _ = self._win()._deck_dedup_index()
        return planned

    def wishlist_paths(self):
        """The paths in the wishlists, or None where there are none to ask."""
        return self._call("current_wishlist_paths")

    def can_clean_decks(self) -> bool:
        return hasattr(self._win(), "_clean_deck_against_others")

    def visible_deck_tables(self):
        return self._win()._visible_deck_tables()

    def clean_deck_against_others(self):
        self._call("_clean_deck_against_others", self._table)

    def clean_wishlist_against_playlists(self, **kwargs) -> int:
        return self._call("_clean_wishlist_against_playlists", self._table,
                          default=0, **kwargs)

    # ── Playlists and the library ───────────────────────────────────────────
    def import_m3u_into(self):
        self._call("_import_m3u_into", self._table)

    def warmup_m3u_loader(self):
        return getattr(self._win(), "_load_warmup_from_m3u", None)

    def player_list_m3u_loader(self):
        return getattr(self._win(), "_load_player_list_from_m3u", None)

    def import_m3u_loader(self):
        return getattr(self._win(), "_import_dropped_playlist", None)

    def import_m3u_multi_loader(self):
        return getattr(self._win(), "_import_m3u_multi", None)

    def show_library_filtered(self, dance: str, cls):
        self._call("show_library_filtered", dance=dance, cls=cls)

    def show_status(self, msg: str):
        """A short note in the main window's status bar, if there is one."""
        win = self._win()
        try:
            if win is not None and hasattr(win, "statusBar"):
                win.statusBar().showMessage(msg, 4000)
        except Exception as exc:
            log.debug("💬 Could not show a status message: %s", exc)
