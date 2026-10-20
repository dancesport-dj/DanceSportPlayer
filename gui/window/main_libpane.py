"""🎼 The library pane below the decks, and the list settings the panes report.

Split off gui/window/main_decks.py: showing, filtering and previewing from the
📚 library pane, and keeping what a header menu changed (columns, widths, dance
names) for every list of that kind, plus the tempo-reset and TSO toggles.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from planner import i18n
from planner.playlist.planned import is_planned
from planner.terms import dance_name
from shared.stores import save_settings

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object


class LibraryPaneMixin(MainWindowHost):
    """The 📚 library pane and the per-kind list settings (MainWindow mixin)."""

    # ── 🎼 The library pane below the decks ─────────────────────────────────────
    def _on_library_pane_toggled(self, on: bool):
        """📚 toolbar toggle: show / hide the library browser entirely."""
        self._lib_tabs.setVisible(on)
        self._settings["library_pane"] = on
        save_settings(self._settings)
        self.statusBar().showMessage(
            "📚 Library browser shown" if on else "📚 Library browser hidden")

    def show_library_filtered(self, dance: str = "", cls: str = "",
                              plays: str = "", added: str = ""):
        """Reveal the 📚 library pane on ONE filtered view — 📊 the gap
        dashboard sends the user here to browse a thin dance × class."""
        if not self._lib_btn.isChecked():
            self._lib_btn.setChecked(True)   # fires _on_library_pane_toggled
        self._lib_tabs.setCurrentWidget(self._lib_browser)
        self._lib_browser.focus_filter(dance=dance, cls=cls, plays=plays,
                                       added=added)
        self.statusBar().showMessage(
            i18n.t("📚 Library filtered: %s")
            % (dance_name(dance, dance) or i18n.t("all dances"))
            + (i18n.t(" · class %s") % cls if cls else "")
            + (i18n.t(" · never played") if plays == "never" else ""))

    def _focus_library(self):
        """📚 A controller's focus button: the library pane comes on screen,
        unfolded, and takes the keyboard, so browsing and Space work in it."""
        if not self._lib_btn.isChecked():
            self._lib_btn.setChecked(True)   # fires _on_library_pane_toggled
        self._lib_tabs.setCurrentWidget(self._lib_browser)
        if self._lib_browser.is_folded():
            self._lib_browser.set_folded(False)
        self._lib_browser._table.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _on_lib_columns_reordered(self, order: list):
        self._settings["library_columns"] = list(order)
        save_settings(self._settings)

    def _on_lib_column_widths(self, widths: dict):
        # JSON keys are strings; store them that way for a clean round-trip.
        self._settings["library_col_widths"] = {str(k): int(v)
                                                 for k, v in widths.items()}
        save_settings(self._settings)

    def _on_lib_columns_hidden(self, hidden: list):
        # One pane, so one setting — unlike the decks, which keep theirs per
        # kind of list.
        self._settings["library_hidden_columns"] = [int(c) for c in hidden]
        save_settings(self._settings)

    def _on_lib_dance_names(self, short: bool):
        self._settings["library_short_dances"] = bool(short)
        save_settings(self._settings)

    def _on_columns_changed(self, kind: str, hidden: list):
        """A column was ticked off (or back on) in a header's right-click menu.

        It is a setting for the KIND of list, so every other deck / wishlist /
        party list gets the same treatment — the user sees one wishlist at a
        time and would otherwise have to repeat the tick four times."""
        cols = [int(c) for c in hidden]
        self._settings.setdefault("hidden_columns", {})[kind] = cols
        save_settings(self._settings)
        for t in self._deckset.all_tables:
            if t.list_kind == kind and t.hidden_columns() != cols:
                t.set_hidden_columns(cols)

    def _on_column_widths_changed(self, kind: str, widths: dict):
        """A handle was dragged to rest in one list of this kind — keep it, and
        give the others the same width. JSON keys are strings; store them that
        way for a clean round-trip, like library_col_widths."""
        cols = {str(k): int(v) for k, v in widths.items() if int(v) > 0}
        self._settings.setdefault("column_widths", {})[kind] = cols
        save_settings(self._settings)
        for t in self._deckset.all_tables:
            if t.list_kind == kind and t.column_widths() != widths:
                t.set_column_widths(cols)

    def _on_column_order_changed(self, kind: str, order: list):
        """A column was dragged elsewhere in one list of this kind — keep the
        order, and give the other lists of the kind the same one."""
        order = [int(c) for c in order]
        self._settings.setdefault("column_order", {})[kind] = order
        save_settings(self._settings)
        for t in self._deckset.all_tables:
            if t.list_kind == kind and t.column_order() != order:
                t.set_column_order(order)

    def _on_dance_names_changed(self, kind: str, short: bool):
        """The Dance column of this kind of list was switched between
        "Langsamer Walzer" and "LW" — the other lists of the kind follow."""
        short = bool(short)
        self._settings.setdefault("short_dances", {})[kind] = short
        save_settings(self._settings)
        for t in self._deckset.all_tables:
            if t.list_kind == kind:
                t.set_short_dances(short)

    def _on_tempo_reset_mode(self, on: bool):
        self._settings["tempo_reset_per_track"] = bool(on)
        save_settings(self._settings)

    def _on_tso_mode(self, on: bool):
        """TSO toggle flipped: persist it, and when switched ON pitch the title
        playing right now to the heat mean straight away (don't wait for the
        next track)."""
        self._settings["tso_equalize"] = bool(on)
        save_settings(self._settings)
        # …and it is the value of the list the card is serving.
        t = getattr(self, "_tso_list", None) or self._engine_list()
        if t is not None:
            self._list_vals(t)["tso"] = bool(on)
            self._autosave_playlist()
        if on:
            self._equalize_heat_tempo(auto=True)

    def _on_lib_tab_changed(self, index: int):
        """The fold clamps the whole pane, so a folded library would leave the
        🏆 tab a sliver — switching tabs unfolds it."""
        if index and self._lib_browser.is_folded():
            self._lib_browser.set_folded(False)

    def _on_lib_play(self, path: Path | None, row: int, pane=None):
        """▶ / double-click in the library — or the tournament — pane: preview
        via the shared player, with the mini overlay anchored to the clicked
        row. `pane` is which of the two asked for it."""
        pane = pane if pane is not None else self._lib_browser
        if self._cue_wanted():
            # 🎧 To the pre-listen output: the deck plays on, untouched.
            self._reset_aux_play_markers(keep=pane)
            self._prehear(path)
            if path is not None:
                self._show_cue_view(pane._table, row, Path(path).stem)
            return
        for t in self._deckset.all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers(keep=pane)
        self._play_or_stop(path)
        if (path is not None and row >= 0 and self._preview
                and self._settings.get("preview_player", True)
                and not self._is_playing_mode()):
            self._preview.show_for(pane._table, row, Path(path).stem)

    def _on_lib_unplanned_toggled(self, on: bool):
        """🆕 filter switched in the library pane — feed it the planned set."""
        if on:
            self._refresh_library_planned_filter()

    def _refresh_library_planned_filter(self):
        """Build the set of library paths already used in the open decks and hand it
        to the library browser. Matches by full path AND by content fingerprint, so a
        renamed/relocated copy of a planned track is hidden too."""
        if getattr(self, "_lib_browser", None) is None:
            return
        if not self._lib_browser.unplanned_active():
            return
        paths, fps = self._deck_dedup_index()
        planned = set(paths)
        fingerprint = (self._library.cache.recorded_fingerprint
                       if self._library.cache is not None else None)
        if self._library.lib is not None:
            for e in self._library.lib.entries:
                p = getattr(e, "path", None)
                # `paths` is lowercased; the browser looks up `str(path)` as is.
                if is_planned(p, paths, fps, fingerprint):
                    planned.add(str(p))
        self._lib_browser.set_planned_paths(planned)
