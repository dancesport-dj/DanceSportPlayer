"""Playlist import plus duplicate / music checks and path fixing.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
"""
import logging

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
)
from pathlib import Path
from planner import i18n
from planner.config import OUTPUT_DIR
from planner.m3u import import_playlist_m3u
from planner.parsing import detect_playlist_meta
from planner.suggester import PlaylistSuggester, generate_hints
from gui.common import (
    BusyDialog,
)
from shared.widgets import (
    _show_toast,
)
from shared.stores import save_settings  # auto-resolved
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from gui.main_dupes import DuplicateCheckMixin
from gui.main_music import MusicCheckMixin
from gui.main_paths import PathFixMixin
from gui.main_print import PrintMixin

log = logging.getLogger("dancesport.gui.import")


def build_import_remap_report(res: dict, name: str) -> dict | None:
    """What 📂 Import has to say about paths it could not take at face value.

    A playlist written on another machine names the library at ITS drive, so the
    import re-roots those lines under the search folders (Settings). That changes
    what the deck points at — never silently: `text` is the summary the dialog
    shows, `details` the full old → new list behind it. None when every path
    resolved as written, which is the normal case on the PC that wrote it."""
    moved = list(res.get("remapped") or [])
    missing = int(res.get("missing") or 0)
    if not moved and not missing:
        return None
    lines = []
    if moved:
        lines.append(f"🧭  {len(moved)} track{'' if len(moved) == 1 else 's'} "
                     f"in {name} named a folder this machine does not have. "
                     "They were found under the search folders and the deck "
                     "points at those files now.")
    if missing:
        lines.append(f"⚠  {missing} track{'' if missing == 1 else 's'} could "
                     "not be found at all — those slots stay in the deck but "
                     "have no file.\nAdd the folder your music is in under "
                     "Settings → search folders, then import again.")
    return {"text": "\n\n".join(lines),
            "details": "\n".join(f"{old}\n   →  {new}" for old, new in moved),
            "moved": len(moved), "missing": missing}


class ImportMixin(DuplicateCheckMixin, MusicCheckMixin, PathFixMixin, PrintMixin):
    """Reading a playlist back in — a dropped .m3u, or one picked from disk.

    The checks that go with it are their own modules now: ♊ duplicates
    (gui.main_dupes), 🎵 the music check (gui.main_music), 🔗 broken paths
    (gui.main_paths) and 🖨 printing (gui.main_print). MainWindow keeps
    importing this one name.
    """

    # ── where the pickers open ───────────────────────────────────────────────
    def _remember_open_dir(self, folder: str) -> None:
        """Keep the folder an open/add picker last took a file from, so the next
        one starts there (shared.audio_files.remember_browse_dir hands it over)."""
        self._settings["open_dir"] = folder
        save_settings(self._settings)

    def _remember_import_dir(self, path) -> None:
        """Same for 📂 Import M3U, which lives in the playlist folders rather
        than in the music tree — its own memory, not the music one."""
        folder = str(Path(path).parent)
        if folder == self._settings.get("import_dir"):
            return
        self._settings["import_dir"] = folder
        save_settings(self._settings)

    def _import_dropped_playlist(self, table: PlaylistTable, path):
        """A .m3u dropped onto a deck → focus that deck, then import the file into it
        (same detection as the 📂 Import M3U button, which targets the focused deck)."""
        if not self._lib:
            QMessageBox.information(self, "Import M3U",
                                   "Load the music library first.")
            return
        self._set_active_table(table)        # make the dropped-on deck the import target
        self._import_playlist_path(str(path))

    def _load_tournament_m3u(self, m3u_path: str):
        """🏆 double-click in the tournament tree: load that playlist onto the
        focused deck, exactly as dropping the file on it would — the deck asks
        first when it already holds tracks, because an import REPLACES it."""
        table = getattr(self, "_focused_table", None) or self._table
        if table in self._wishlists or getattr(table, "_warmup", False):
            table = self._table   # a playlist file belongs on a deck
        if not table._confirm_m3u_replaces(Path(m3u_path)):
            return
        if table.plays_flat():
            self._load_player_list_from_m3u(table, m3u_path)
            return
        self._import_dropped_playlist(table, m3u_path)

    def _import_playlist(self):
        """📂 Import M3U button: load an .m3u into the focused table — a deck gets
        the full rounds/heats detection, a focused wishlist appends the tracks flat."""
        table = getattr(self, "_focused_table", None) or self._table
        self._import_m3u_into(table)

    def _import_m3u_into(self, table: PlaylistTable):
        """Pick an .m3u and import it into `table` (context menu + 📂 button).

        Decks: round / dance / heat structure is detected by the planner (markers
        when the file came from this app, otherwise heuristically); a final round
        with extra backup variants rides along as stacked backups.
        Wishlists: every track is appended flat (duplicates skipped)."""
        if not self._lib:
            QMessageBox.information(self, "Import M3U",
                                    "Load the music library first.")
            return
        start = self._settings.get("import_dir") or str(
            OUTPUT_DIR if OUTPUT_DIR.exists() else Path.home())
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import M3U", start, "Playlists (*.m3u *.m3u8);;All files (*.*)")
        if not paths:
            return
        self._remember_import_dir(paths[0])

        # A deck of a player-only install takes the file as its flat running
        # order — there is no draw in it to reconstruct.
        if table.plays_flat():
            self._load_player_list_from_m3u(table, paths[0])
            return

        # The Eintanzen panel takes a single .m3u as a flat warm-up list (not a
        # round/heat import, and never into a deck).
        if getattr(table, "_warmup", False):
            self._load_warmup_from_m3u(table, paths[0])
            return

        # Multiple files → fan them out into the FREE (empty) playlist slots, one each.
        if len(paths) > 1 and table not in self._wishlists:
            self._import_m3u_multi(paths)
            return

        path = paths[0]
        if table in self._wishlists:
            # A focused wishlist appends every picked file flat (duplicates skipped).
            added = table._insert_drop_files([Path(p) for p in paths], table.rowCount())
            self._update_wish_counts()
            if added:
                _show_toast(self, i18n.t("📂  Added %d track(s) from %d file(s)")
                            % (added, len(paths)))
            else:
                _show_toast(self, "📂  Nothing new — all tracks already in the wishlist")
            return
        self._set_active_table(table)   # deck import always targets the clicked deck
        self._import_playlist_path(path)

    def _import_m3u_multi(self, paths: list[str]):
        """Import several .m3u files at once, each into its own FREE (empty) playlist
        deck. Warns when no slot is free, and offers a partial import when there are
        fewer free slots than files."""
        # Only decks the view can actually reach — a player build stops at four,
        # and a deck nobody can bring on screen is not a free slot.
        decks = self._decks[:self._max_decks()]
        free = [t for t in decks if self._serialize_playlist_state(t) is None]
        if not free:
            QMessageBox.warning(
                self, "Import M3U",
                i18n.t("All %d playlists already hold tracks — there's no free slot to import "
                       "into.\n\nClear a playlist first, or pick a single file to overwrite the "
                       "focused deck.") % len(decks))
            return

        if len(paths) > len(free):
            ret = QMessageBox.question(
                self, "Not enough free playlists",
                i18n.t("You picked %d files but only %d playlist slot(s) are free.\n\n"
                       "Import the first %d into the free slots and skip the rest?")
                % (len(paths), len(free), len(free)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return
            paths = paths[:len(free)]

        targets = free[:len(paths)]
        # Grow the visible deck view so every target slot is actually on screen.
        highest = max(self._decks.index(t) for t in targets)
        want = 8 if highest >= 4 else 4 if highest >= 2 else 2 if highest >= 1 else 1
        want = min(want, self._max_decks())
        if want > self._deck_count:
            self._deck_count = want
            self._apply_deck_view()

        self._pending_import_reports = []
        for path, deck in zip(paths, targets):
            if deck.plays_flat():
                # A player-only install's deck: the file is its running order.
                self._load_player_list_from_m3u(deck, path)
                continue
            self._set_active_table(deck)
            self._import_playlist_path(path, report=False)

        _show_toast(self, i18n.t("📂  Imported %d playlists into %d free slot(s)")
                    % (len(paths), len(paths)))
        self._autosave_playlist()
        self._show_import_remap_report(self._pending_import_reports)
        self._pending_import_reports = []

    def _show_import_remap_report(self, reports: list):
        """🧭 The one dialog for what an import had to re-root, or could not find.

        A list of reports because 📂 Import M3U can fill several decks at once —
        one dialog at the end, not one per file."""
        if not reports:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("📂  Import — track paths")
        box.setText("\n\n".join(r["text"] for r in reports))
        details = "\n\n".join(r["details"] for r in reports if r["details"])
        if details:
            box.setDetailedText(details)
        box.exec()

    def _import_playlist_path(self, path: str, report: bool = True):
        """Import the .m3u at `path` into the currently focused deck (self._table).

        `report=False` holds the 🧭 path report back for the caller to show once
        (see `_import_m3u_multi`), instead of a dialog per file."""
        if not self._lib:
            return
        self._stash_active_replay()   # preserve any worked competition grid first
        self.statusBar().showMessage(i18n.t("Importing %s …") % Path(path).name)
        QApplication.processEvents()

        # Progress dialog (appears only if the import takes longer than a moment, so quick
        # lists don't flash a dialog). The import runs on the main thread, so tick → repaint.
        dlg = BusyDialog(self, message=i18n.t("📂 Importing %s…") % Path(path).name)
        dlg.show_after(250)

        def _prog(done: int, total: int, name: str = ""):
            dlg.set_progress(done, total, name)
            QApplication.processEvents()

        # A list carried over from another machine names the library at ITS drive
        # (and on a Mac `F:\…` cannot exist at all) — the same re-rooting 🧭 Fix
        # paths uses resolves those lines, and the report below says what moved.
        try:
            _, _, remapper = self._remap_index()
        except Exception:
            remapper = None

        try:
            res = import_playlist_m3u(path, self._lib, self._cache,
                                      progress_cb=_prog,
                                      remapper=remapper or None)
        except Exception as exc:
            dlg.finish()
            self.statusBar().showMessage(i18n.t("Import failed: %s") % exc)
            QMessageBox.critical(self, "Import Error", str(exc))
            return
        dlg.finish()

        dances   = res["dances"]
        playlist = res["playlist"]
        rounds   = res["rounds"]
        if not dances or not playlist:
            QMessageBox.warning(
                self, "Nothing imported",
                "Couldn't detect any danceable tracks in that playlist.")
            self.statusBar().showMessage("Import: no tracks detected")
            return

        cls         = res["dance_class"]
        latin       = {'CC', 'SA', 'RB', 'PD', 'JI'}
        style       = "Latin" if sum(d in latin for d in dances) >= len(dances) / 2 else "Standard"
        use_timbre  = self._cfg.timbre_check.isChecked()

        # Recover age / start class / style from the file name where possible, so the
        # combos match the imported playlist. Filename wins for age + class (not in the
        # tracks); for style the dance-derived value wins, name only fills a blank.
        meta = detect_playlist_meta(Path(path).stem)
        age  = meta.get("age") or self._age or "Hauptgruppe"
        if meta.get("cls"):
            cls = meta["cls"]
        if meta.get("style"):
            style = meta["style"]
        # Heat counts (e.g. "6-3-2-1") taken straight from the imported round structure.
        heat_str = "-".join(str(getattr(r, "heats", 0) or 0) for r in rounds)

        self._replay_label  = None
        self._replay_active = False
        self._clear_replay_sources()
        self._mode          = "Favorites"
        self._ui_mode       = "Favorites"
        self._theme_entries = []
        self._style         = style
        self._age           = age
        self._dance_class   = cls
        self._dances        = dances
        self._playlist      = playlist
        self._suggester     = PlaylistSuggester(self._lib)

        # Push the recovered settings into the visible combos + heat-count field so the
        # controls reflect what was imported (mode back to Favorites for editing).
        self._cfg.apply_config(mode="Favorites", style=style, age=age, cls=cls,
                               dances=dances)
        if heat_str:
            self._cfg.rounds_edit.setText(heat_str)
            self._cfg._parse_rounds()

        # Import into a DYNAMIC deck: the round heat-counts become the capacity pattern,
        # and the final round's extra same-dance variants (e.g. trailing Jives) ride along
        # as stacked backups instead of widening every dance with empty cells. Dynamic also
        # lets the user keep dragging songs in to extend the imported rounds (🔒 to revert).
        import_backups = res.get("backups") or {}
        capacity = [int(getattr(r, "heats", 0) or 0) for r in rounds]
        self._table.load(
            playlist, dances, rounds, cls,
            play_cb=self._play_or_stop,
            suggester=self._suggester,
            use_timbre=use_timbre,
            style=style,
            dynamic=True,
            capacity=capacity,
            backups=import_backups,
        )
        self._refresh_mode_btn(self._table)                 # sync the 🔒/🔓 glyph to dynamic
        self._set_deck_name(self._table, Path(path).stem)   # name the deck after the file
        # Remember the file: a playlist with its own picture beside it shows
        # that on the player card instead of the tracks' own covers.
        self._table._m3u_path = Path(path)
        self._cfg.save_btn.setEnabled(True)

        try:
            self._show_hints(generate_hints(self._lib, playlist, dances, cls, rounds))
        except Exception:
            self._show_hints([])

        notes = []
        n_backups = sum(len(v) for v in import_backups.values())
        if n_backups:
            notes.append(i18n.t("%d extra final-round track(s) kept as backups "
                                "(stacked under their dance)") % n_backups)
        if res.get("dupes"):
            notes.append(i18n.t("%s line(s) name a file the list already "
                                "had (imported again, not skipped)") % res["dupes"])
        if res["missing"]:
            notes.append(i18n.t("%s file(s) not found on disk") % res["missing"])
        if res["unknown"]:
            notes.append(i18n.t("%s track(s) with no recognizable dance (skipped)")
                         % res["unknown"])
        if res.get("dropped"):
            notes.append(i18n.t("%s track(s) left out — no round/dance "
                                "column to put them in") % res["dropped"])
        note_s = ("  —  " + "; ".join(notes)) if notes else ""
        # The progress bar counted every track the FILE lists; say so whenever the
        # grid holds fewer, so the number that ran up is not left unexplained.
        raw = res.get("raw") or res["total"]
        count_s = (i18n.t("%s of %s songs") % (res["total"], raw) if raw != res["total"]
                   else i18n.t("%s songs") % res["total"])
        self.statusBar().showMessage(
            (i18n.t("📂 Imported %s · %d round(s) · %d dance(s) (markers)")
             if res["structured"] else
             i18n.t("📂 Imported %s · %d round(s) · %d dance(s) (auto-detected)"))
            % (count_s, len(rounds), len(dances)) + note_s
        )
        # Brief toast instead of a blocking dialog; details (backups / missing / skipped)
        # stay in the status bar. Show the toast longer when there are notes to read.
        toast = i18n.t("📂 Imported %s · %d round(s)") % (count_s, len(rounds))
        if notes:
            toast += "\n" + "\n".join("• " + n for n in notes)
        # The load() above already ran the live Check-Music marks (via
        # _notify_changed) — tell the user how many rows came up red.
        n_issues = len(self._table._issue_paths)
        if n_issues:
            toast += "\n" + i18n.t("⚠ %d row(s) marked red — play-length / takt "
                                   "issues (hover a red title for details)") % n_issues
        _show_toast(self._table, toast, msec=4000 if (notes or n_issues) else 1800)
        self._table._remove_duplicate_titles(on_load=True)

        # Last, with the deck already on screen behind it: what the paths did.
        rep = build_import_remap_report(res, Path(path).name)
        if rep is not None:
            if report:
                self._show_import_remap_report([rep])
            else:
                self._pending_import_reports.append(rep)
