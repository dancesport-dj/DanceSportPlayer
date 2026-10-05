"""♊ Duplicate checks: the same song twice in one evening, and what to do about it.

Split off gui/main_import.py as a MainWindow mixin. Covers the decks' own check,
the one run over dropped .m3u files and the resolve dialog's aftermath.
"""
import logging

import shiboken6

from planner.parsing import _song_title_keys

from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
)
from pathlib import Path
from planner.models import ALLOW_REPEAT, MusicEntry
from gui.common import (
    _C_ROW_EVEN,
    _C_ROW_ODD,
    _unreadable_playlist,
)
from shared.widgets import (
    _show_toast,
)
from gui.dialogs import (  # auto-resolved
    DuplicateResolveDialog,
    SimilarTracksDialog,
)
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from planner import i18n
from planner.checks import build_dropped_dup_report, dup_clashes
from planner.planned import is_planned, path_key
from planner.playlist_text import PlaylistEncodingError, read_playlist_text

log = logging.getLogger("dancesport.gui.dupes")


def m3u_track_paths(m3u: Path) -> list[Path]:
    """The audio file paths referenced by an .m3u (non-comment lines), resolved
    relative to the playlist's own folder when they aren't absolute. Empty when
    the file can't be read; PlaylistEncodingError when it can't be decoded."""
    try:
        lines = read_playlist_text(m3u)[0].splitlines()
    except OSError:
        return []
    base = Path(m3u).parent
    out: list[Path] = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        p = Path(ln)
        out.append(p if p.is_absolute() else base / p)
    return out


class DuplicateCheckMixin:
    """♊ Duplicate detection over the decks and over dropped lists."""

    def _exact_key(self, entry) -> str | None:
        """Identity for the SAME audio file: the content fingerprint (so re-encoded /
        renamed copies collapse), else the plain path. Two tracks with the same exact
        key are byte-identical music."""
        if entry is None:
            return None
        if entry.path and self._cache is not None:
            try:
                fp = self._cache.known_fingerprint(Path(entry.path))   # in-memory only
                if fp:
                    return f"fp:{fp}"
            except Exception as exc:
                log.debug("🔑 No cached fingerprint for %s: %s", entry.path, exc)
        return f"p:{path_key(entry.path)}" if entry.path else None

    def _title_keys(self, entry) -> list[str]:
        """The candidate cleaned-title keys (track number / dance code / BPM stripped)
        used for ≈ Similar matching: the full title plus, for an 'Artist - Title' name,
        each side — so a match on ANY of them flags the pair (see _song_title_keys).
        Two tracks whose cleaned titles are within the Levenshtein threshold but whose
        exact keys differ are different recordings of one song — which content
        fingerprints can never match."""
        if entry is None:
            return []
        # Prefer the ID3 title tag: filenames in this library are frequently truncated
        # ('… (From Twilight) (.mp3', '… (Tg 32.mp3'), so a path-derived key misses real
        # duplicates the tag would catch. Fall back to the path, then the cleaned title.
        tag = (getattr(entry, "tag_title", "") or "").strip()
        src = tag or (str(entry.path) if entry.path else (entry.title or ""))
        if not src:
            return []
        try:
            return _song_title_keys(src)
        except Exception:
            return []

    def _deck_dedup_index(self, exclude=None):
        """(paths, fingerprints) of every track in the visible playlist DECKS (wishlists
        excluded). Used to keep a wishlist free of tracks already planned somewhere.
        `exclude` leaves one deck out — what the OTHER decks hold, for cleaning that
        one against them."""
        paths: set = set()
        fps: set = set()
        for t in self._visible_deck_tables():
            if exclude is not None and t is exclude:
                continue
            entries = t._row_meta.entries()
            if getattr(t, "_playlist", None):   # dynamic decks: also the model + backups
                try:
                    entries.extend(t._iter_planned_entries())
                except Exception as exc:
                    log.debug("📋 Could not read planned entries off a dynamic deck: %s", exc)
            for e in entries:
                if not getattr(e, "path", None):
                    continue
                paths.add(path_key(e.path))
                if self._cache is not None:
                    try:
                        fp = self._cache.fingerprint(Path(e.path))   # hashed on demand
                        if fp:
                            fps.add(fp)
                    except Exception as exc:
                        log.debug("🔑 Fingerprinting failed for %s: %s", e.path, exc)
        return paths, fps

    def _clean_deck_against_others(self, table) -> int:
        """🧹 Empty every slot of `table` holding a track another OPEN playlist plans.

        The evening is one thing to the people in the hall: a title that ran in
        the last competition should not come round again in the next. Which
        playlists count is what is on screen — two decks in view means the other
        one, eight means the other seven, and a 📅 day plan's decks come along.

        Matched by path OR content fingerprint, so a renamed copy of the same
        recording counts. ALLOW_REPEAT dances (PD) are left alone — they are
        meant to come back. Only the deck the menu was opened on loses tracks;
        the others are read, never touched. Returns how many slots were emptied.
        """
        if table is None or getattr(table, "_flat_mode", False):
            return 0
        others = [t for t in self._visible_deck_tables()
                  if t is not table and t._row_meta.has_songs()]
        if not others:
            _show_toast(self, "✅  No other open playlist to compare against")
            return 0
        paths, fps = self._deck_dedup_index(exclude=table)
        # hashed on demand
        fingerprint = self._cache.fingerprint if self._cache is not None else None
        rows = []
        for r, m in table._row_meta.numbered():
            e = m.entry
            if (getattr(e, "dance", None) or "") in ALLOW_REPEAT:
                continue
            if is_planned(getattr(e, "path", None), paths, fps, fingerprint):
                rows.append(r)
        here = self._deck_report_name(table)
        against = ", ".join(self._deck_report_name(t) for t in others)
        if not rows:
            _show_toast(self, "✅  Nothing here is in another open playlist")
            return 0
        n = len(rows)
        if not table._confirm_delete(
                "Remove duplicates",
                (i18n.t("Remove %d title from %s?\nIt is already planned in: %s") if n == 1
                 else i18n.t("Remove %d titles from %s?\nThey are already planned in: %s"))
                % (n, here, against)):
            return 0
        table._clear_slots_at(set(rows))
        log.info("🧹 Deck cleaned against the other open playlists\n"
                 "deck: %s\n"
                 "removed: %d\n"
                 "compared against: %s", here, n, against)
        _show_toast(self, (
            i18n.t("🧹  Removed %d title already in another playlist") if n == 1
            else i18n.t("🧹  Removed %d titles already in another playlist")) % n)
        return n

    def _check_duplicates(self):
        """Scan the playlists (see _dup_check_tables) for duplicate songs → open the
        resolve dialog, which lists them in playlist order (🔁 doubled inside one
        list, 🔀 shared between two)
        with a Keep / Replace control per occurrence. Reports both 🟰 exact copies
        (identical audio) and ≈ similar songs (same title, a different recording)."""
        if not self._lib:
            QMessageBox.information(self, "Check duplicates",
                                    "Load the music library first.")
            return
        open_dlg = getattr(self, "_dup_dlg", None)
        if open_dlg is not None:
            # One at a time: its report owns `_dup_slots`, and a second one
            # would renumber them under the first one's ✅ Apply.
            open_dlg.raise_()
            open_dlg.activateWindow()
            return
        report = self._deck_dup_report()
        # Always open the dialog (even with no deck duplicates) so its second tab —
        # "drag loose files in to check them against each other" — stays reachable.
        dlg = DuplicateResolveDialog(report, self, self._pick_dup_replacement,
                                     drop_check_fn=self._check_dropped_duplicates,
                                     ref_clean_factory=self._make_reference_clean_worker,
                                     play_cb=self._play_or_stop, seek_cb=self._seek)
        # show(), not exec(): on the tabs for dragged-in files it stays open beside
        # the decks (see _sync_modality), which can be worked on meanwhile —
        # `_apply_dup_resolutions` finds each copy where it sits by then.
        dlg.finished.connect(lambda result, d=dlg: self._on_dup_dialog_finished(d, result))
        self._dup_dlg = dlg
        dlg.show()

    def _on_dup_dialog_finished(self, dlg, result: int):
        self._dup_dlg = None
        resolutions = dlg.resolutions
        # A child of this window: without this, every check leaves one behind.
        # A compare still running was adopted when the dialog finished.
        dlg.deleteLater()
        if result == QDialog.DialogCode.Accepted and resolutions:
            self._apply_dup_resolutions(resolutions)

    def _deck_report_name(self, table) -> str:
        """Display name of a deck for the duplicate report (with its 🅰/🅱 letter)."""
        d = self.deck(table)
        return f"{d.letter} {d.title}" if d.letter else d.title

    def _dup_check_tables(self) -> list[PlaylistTable]:
        """The lists 🔁 Check duplicates compares: every deck that holds titles,
        on whichever tab or view it sits (five playlists don't fit on one
        screen), plus the wishlists and the Eintanzen panel that are shown and
        hold titles. A folded list still counts as shown."""
        tables = self._checkable_deck_tables()
        for t in [*self._wishlists, self._warmup_table]:
            box = self.deck(t).box
            if box is not None and box.isVisibleTo(self) and t._row_meta.has_songs():
                tables.append(t)
        return tables

    def _deck_dup_report(self) -> dict:
        """Build the within/cross duplicate report (same shape as the dropped-files
        report) for the lists of _dup_check_tables, each one's songs in running
        order.

        Every record that came from a real deck carries a `slot` — its number in
        `self._dup_slots`, which is where the (table, row) it actually sits in is
        kept, with the entry it held then. The report used to carry the deck widget itself, through a planner
        function that only ever sorted and grouped the records: the dialog then
        had to key its dedup on `id(table)`, and a rule the planner owns could not
        be exercised without a live QTableWidget. Records from dropped files have
        no slot at all — nothing in them can be replaced."""
        self._dup_slots: list[tuple] = []
        files: list[tuple] = []
        for table in self._dup_check_tables():
            recs: list[dict] = []
            pos = 0
            for row, m in table._row_meta.numbered():
                e = m.entry
                pos += 1
                self._dup_slots.append((table, row, e))
                recs.append({"idx": pos, "title": e.title or "?",
                             "path": str(e.path) if getattr(e, "path", None) else "",
                             "exact": self._exact_key(e), "tkeys": self._title_keys(e),
                             "dance": getattr(e, "dance", None) or None,
                             "entry": e, "slot": len(self._dup_slots) - 1})
            files.append((self._deck_report_name(table), recs))
        return build_dropped_dup_report(files)

    def _m3u_track_paths(self, m3u: Path) -> list[Path]:
        """`m3u_track_paths` for a drop: a file that can't be decoded reads as
        empty, and a toast says why."""
        try:
            return m3u_track_paths(m3u)
        except PlaylistEncodingError as exc:
            _unreadable_playlist(self, m3u, exc)
            return []

    def _make_reference_clean_worker(self, ref_path, tournament_paths):
        """Build the threaded reference-base cleaner for the '🧹 Reference base' tab:
        compares the dropped reference .m3u against the tournament files and finds the
        hard (byte-identical) duplicates so they can be exported out. Paso Doble is
        excluded (handled inside the worker).

        The worker gets the reader that raises: a tournament list read as empty
        would make every reference track look unused."""
        from gui.workers import ReferenceCleanWorker
        return ReferenceCleanWorker(ref_path, tournament_paths,
                                    self._cache, m3u_track_paths)

    def _check_dropped_duplicates(self, paths: list, progress_cb=None) -> dict:
        """Tab 2 of Check duplicates: check the dragged-in .m3u playlists (raw audio is
        treated as a one-track list) for duplicate songs, the way the old TurnierCheck
        did — but tidier. Two views are returned:
          • within  — songs doubled INSIDE one playlist (a real listing error),
          • cross   — songs shared BETWEEN a pair of playlists.
        'Exact' = byte-identical file (content fingerprint, or same path); 'Similar' =
        same normalised title but a different file. Each track keeps its 1-based line
        number in its own playlist. Returns
        {'within': [...], 'cross': [...]}; calls progress_cb(done, total) while reading."""
        if not self._lib or self._cache is None:
            return {"within": [], "cross": []}
        # One (name, [rec]) per dropped file, in drop order.
        file_tracks: list[tuple] = []
        for p in paths:
            if p.suffix.lower() in (".m3u", ".m3u8"):
                file_tracks.append((Path(p).name, self._m3u_track_paths(p)))
            else:
                file_tracks.append((Path(p).name, [Path(p)]))
        total = sum(len(ts) for _, ts in file_tracks)
        done = 0
        files: list[tuple] = []
        for name, tracks in file_tracks:
            recs: list[dict] = []
            for i, t in enumerate(tracks, 1):
                entry = self._external_entry(t)
                title = (entry.title if entry and entry.title else t.stem)
                fp = None
                if entry is not None:
                    try:
                        fp = self._cache.known_fingerprint(Path(t))
                    except Exception:
                        fp = None
                exact = f"fp:{fp}" if fp else f"p:{str(t).lower()}"
                # Key off the ID3 title tag when we have it (filenames are often
                # truncated), else the path — same rule as the open-deck check.
                tkeys = self._title_keys(entry) if entry is not None else []
                if not tkeys:
                    try:
                        tkeys = _song_title_keys(str(t))
                    except Exception:
                        tkeys = []
                recs.append({"idx": i, "title": title, "path": str(t),
                             "exact": exact, "tkeys": tkeys,
                             "dance": getattr(entry, "dance", None) or None})
                done += 1
                if progress_cb and (done == 1 or done % 5 == 0 or done == total):
                    progress_cb(done, total)
            files.append((name, recs))
        return build_dropped_dup_report(files)

    def _dup_rec(self, entry) -> dict:
        """The match keys of one track, as the duplicate report records them."""
        return {"exact": self._exact_key(entry), "tkeys": self._title_keys(entry),
                "dance": getattr(entry, "dance", None) or None}

    def _pick_dup_replacement(self, entry) -> MusicEntry | None:
        """The picker 🔁 Check duplicates opens: it leaves out every track the next
        check would flag again — anything in the lists it covers, and the
        replacements already chosen in its dialog. Otherwise a replacement is the
        next duplicate, and the check plays ping-pong. The wishlists stay on
        offer: they are where a replacement comes from (its ⭐ option)."""
        taken = [m.entry for t in self._dup_check_tables() if t not in self._wishlists
                 for _r, m in t._row_meta.numbered()]
        dlg = getattr(self, "_dup_dlg", None)
        if dlg is not None:
            taken += dlg.pending_replacements()
        return self._pick_replacement(entry, avoid=[self._dup_rec(e) for e in taken])

    def _pick_replacement(self, entry, avoid=None) -> MusicEntry | None:
        """Open the Similar-Tracks picker for `entry`; return the chosen track or None.
        `avoid` (duplicate-report records) hides the tracks that clash with them."""
        lib = self._lib
        if lib is None:
            return None
        results = lib.similar_tracks(entry, n=100, same_dance=True, min_display=0.5)
        if not results:
            QMessageBox.information(
                self, "Replace duplicate",
                "No similar tracks found — the song may not be audio-analyzed yet.")
            return None
        hide = None
        if avoid:
            def hide(res):
                clash = dup_clashes([self._dup_rec(e) for _s, e in res], avoid)
                return [r for i, r in enumerate(res) if i not in clash]
            results = hide(results)
            if not results:
                QMessageBox.information(
                    self, "Replace duplicate",
                    "Every similar track is already in an open playlist.")
                return None
        holder = {"entry": None}
        dlg = SimilarTracksDialog(
            entry, results, self, play_cb=self._play_or_stop, lib=lib,
            cache=self._cache, seek_cb=self._seek,
            wishlist_paths=self.current_wishlist_paths(), hide_fn=hide,
            pick_cb=lambda e: holder.__setitem__("entry", e))
        dlg.setModal(True)
        dlg.exec()
        return holder["entry"]

    def _apply_dup_resolutions(self, resolutions: list):
        """Apply (slot, new_entry) swaps from the resolve dialog — the dialog names
        the copies it wants changed, this side knows where they sit (see
        _deck_dup_report). A new_entry of None takes the copy out."""
        changed = set()
        removals: dict = {}          # table → rows to take out
        taken = []                   # replacements placed outside the wishlists
        n = 0
        gone = 0
        for slot, new_entry in resolutions:
            table, row = self._dup_slot_now(slot)
            if table is None:
                gone += 1
                continue
            if new_entry is None:
                removals.setdefault(table, set()).add(row)
            elif self._replace_occurrence(table, row, new_entry):
                changed.add(table)
                n += 1
                if table not in self._wishlists:
                    taken.append(new_entry)
        for table in changed:
            table._notify_changed()   # persists + feeds the undo timeline
        # After the swaps: taking a wishlist row out renumbers the rows below it.
        removed = sum(len(rows) for table, rows in removals.items()
                      if self._remove_occurrences(table, rows))
        self._take_out_of_wishlists(taken)
        if n:
            msg = (i18n.t("🔁  Replaced %d duplicate") if n == 1
                   else i18n.t("🔁  Replaced %d duplicates")) % n
            self.statusBar().showMessage(msg)
            _show_toast(self, msg)
        if removed:
            msg = (i18n.t("🗑  Removed %d duplicate") if removed == 1
                   else i18n.t("🗑  Removed %d duplicates")) % removed
            self.statusBar().showMessage(msg)
            _show_toast(self, msg)
        if gone:
            msg = (i18n.t("⚠  %d duplicate was no longer in its playlist — left as it is")
                   if gone == 1 else
                   i18n.t("⚠  %d duplicates were no longer in their playlist — left as they are")
                   ) % gone
            self.statusBar().showMessage(msg, 8000)
            _show_toast(self, msg)

    def _take_out_of_wishlists(self, entries: list):
        """A replacement taken from a wishlist MOVES out of it, as a title dragged
        from there into a deck does — left in, the next check flags it
        wishlist↔deck. Matched by path or audio (a copy dropped from elsewhere)."""
        paths, fps = set(), set()
        for e in entries:
            if not getattr(e, "path", None):
                continue
            paths.add(path_key(e.path))
            if self._cache is not None:
                try:
                    fp = self._cache.fingerprint(Path(e.path))
                    if fp:
                        fps.add(fp)
                except Exception as exc:
                    log.debug("🔁 Could not fingerprint a replacement: %s", exc)
        if not paths:
            return
        fingerprint = self._cache.fingerprint if self._cache is not None else None
        for wishlist in self._wishlists:
            rows = [r for r, m in wishlist._row_meta.numbered()
                    if is_planned(getattr(m.entry, "path", None), paths, fps, fingerprint)]
            if rows:
                wishlist._remove_rows(rows)

    def _dup_slot_now(self, slot: int) -> tuple:
        """(table, row) where the copy the report named as `slot` sits NOW, or
        (None, -1) when it is gone. The dialog does not block the decks, so a
        title may have moved since the check, or been swapped for another."""
        table, row, entry = self._dup_slots[slot]
        if not shiboken6.isValid(table):
            return None, -1
        meta = table._row_meta
        if 0 <= row < len(meta) and meta[row] is not None and meta[row].entry is entry:
            return table, row
        rows = [r for r, m in meta.numbered() if m.entry is entry]
        return (table, rows[0]) if len(rows) == 1 else (None, -1)

    @staticmethod
    def _remove_occurrences(table: PlaylistTable, rows: set) -> bool:
        """Take the copies at `rows` out the way Del does in that list: a wishlist
        drops the rows, the Eintanzen panel re-cuts its order, a deck empties the
        heat slots."""
        if table._flat_mode:
            return table._remove_rows(rows)
        if table._warmup:
            return table._drop_running_order_rows(rows)
        return table._clear_slots_at(rows)

    def _replace_occurrence(self, table: PlaylistTable, row: int, new_entry) -> bool:
        """Swap the song at one grid slot for `new_entry`, in both the model and the
        rendered row. Replace keeps the grid shape, so row indices stay valid."""
        if not (0 <= row < len(table._row_meta)):
            return False
        meta = table._row_meta[row]
        if not meta or meta.entry is None:
            return False
        rn = meta.round_name
        h, d = meta.h_idx, meta.d_idx
        # Keep the underlying model in sync so the change survives serialization.
        if meta.backup:
            lst = table._dynamic_backups.get((rn, h, d))
            bn = meta.backup_n - 1
            if lst is not None and 0 <= bn < len(lst):
                lst[bn] = new_entry
        elif isinstance(getattr(table, "_playlist", None), dict) and rn in table._playlist:
            try:
                table._playlist[rn][h][d] = new_entry
            except (IndexError, KeyError, TypeError):
                pass
        meta.entry = new_entry
        if meta.theme or meta.warmup:
            # A flat list has no heats; its stripes count songs (_restripe_song_rows).
            h = next(i for i, (r, _m) in enumerate(table._row_meta.numbered()) if r == row)
        bg = _C_ROW_EVEN if h % 2 == 0 else _C_ROW_ODD
        table._fill_song_row(row, meta, bg)
        return True
