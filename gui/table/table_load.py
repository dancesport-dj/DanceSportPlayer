"""Filling a playlist table: a generated playlist, a theme, the warm-up, the
evening's player list and the wishlist, plus the round and dance header rows
they are drawn with.

Mixin of PlaylistTable, split off gui/table/playlist_table.py.
"""
import logging
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)

from gui.common import (
    C_DANCE_BG,
    C_DANCE_FG,
    C_ROUND_BG,
    C_ROUND_FG,
    C_ROW_EVEN,
    C_ROW_ODD,
    fmt_track_secs,
)
from gui.decks.running_order import Row, RunningOrder
from planner import i18n, terms
from planner.generate.suggester import PlaylistSuggester
from planner.generate.warmup import warmup_code, warmup_rounds
from planner.models import MusicEntry, RoundConfig, RoundTier, Strategy
from planner.playlist.m3u import running_order_rounds
from planner.terms import dance_name
from shared.columns import _COL_TITLE, _N_COLS, COL_HEAT, COL_REGEN

if TYPE_CHECKING:
    from gui.window.hosts import PlaylistTableHost
else:
    PlaylistTableHost = object

log = logging.getLogger("dancesport.gui.playlist_table")


# A file not on disk: a light-red row, paler than the issue red so the two
# stay apart — the orange mark's counterpart for the red ❗.
C_MISSING_BG = QColor(255, 222, 222)


class TableLoadMixin(PlaylistTableHost):
    """Loading a playlist, theme, warm-up, player list or wishlist into the table."""

    # A dropped folder is read whole, subfolders included — a tournament's music
    # sits in one folder per dance. Past this many tracks it is more likely a slip
    # of the hand than an intention (a library root holds thousands, and every one
    # of them has its tags read on the way in), so ask before doing it.
    _DIR_DROP_ASK = 100

    def load(
        self,
        playlist: dict,
        dances: list[str],
        rounds: list[RoundConfig],
        dance_class: str,
        play_cb,
        suggester: PlaylistSuggester | None,
        use_timbre: bool = True,
        style: str | None = "Latin",
        round_pools: list[list[MusicEntry]] | None = None,
        dynamic: bool = False,
        capacity: list[int] | None = None,
        backups: dict | None = None,
        round_skip_dances: dict | None = None,
        round_ctx: dict | None = None,
        marked: set | None = None,
        pinned: set | None = None,
    ):
        self._playlist = playlist
        self._warmup = False
        self._player_list = False
        # 🖼 A fresh load is not the imported .m3u any more — the importer sets
        # this again right after, so the deck's cover follows what it holds.
        self._m3u_path = None
        self._dance_class = dance_class
        self._play_cb = play_cb
        self._suggester = suggester
        self._use_timbre = use_timbre
        self._style = style
        self._loaded_dances = list(dances)
        self._loaded_rounds = list(rounds)
        # The rows are rebuilt below — keep the placements, to hand the ids back.
        placed = self._row_meta.placements()
        playing = self._current_play_row >= 0
        self._row_meta = RunningOrder()
        self._played_saved.clear()   # rows are rebuilt with fresh colors
        # Dynamic-mode state: a static (combo-generated) load resets it; a dynamic
        # load / rebuild carries the pattern, column order and stacked backups.
        self._dynamic = dynamic
        self._dynamic_capacity = list(capacity) if capacity else ([] if not dynamic else self._dynamic_capacity)
        self._dynamic_dances = list(dances) if dynamic else []
        self._dynamic_backups = backups or {}
        self._round_skip_dances = ({k: set(v) for k, v in round_skip_dances.items()}
                                   if round_skip_dances else {})
        self._round_ctx = ({k: dict(v) for k, v in round_ctx.items()}
                           if round_ctx else {})
        # 🔁 "potential replace" marks: a fresh (generated / imported) load starts
        # clean — otherwise a re-picked song would come back already orange. Only a
        # restore hands its saved set in, so the rows below are painted marked.
        self._marked_paths = set(marked) if marked else set()
        # 📌 Pins likewise: only a restore or a re-render hands them in.
        self._pinned_paths = set(pinned) if pinned else set()
        # 'Past competitions': per-round history pool keyed by round name, so a row
        # ↺ re-rolls from the same round's history first (library as fallback).
        self._round_pools_by_name = {}
        if round_pools:
            for rc, pool in zip(rounds, round_pools, strict=True):
                self._round_pools_by_name[rc.name] = pool
        self._reset_collapse_state()
        self.setRowCount(0)

        rc_map = {rc.name: rc for rc in rounds}

        for round_name, heats in playlist.items():
            rc = rc_map.get(round_name)
            tier = rc.tier if rc else RoundTier.EARLY
            total = sum(1 for h in heats for e in h if e is not None)
            multi = len(heats) > 1

            # ── Round header (spans all columns) ──
            # Total play time of the round; "~" because tracks without a probed
            # duration count as 0 (and timed fade-out may cut songs early anyway).
            round_secs = sum(getattr(e, "duration", 0) or 0
                             for h in heats for e in h if e is not None)
            time_s = f",  ~{fmt_track_secs(round_secs)}" if round_secs else ""
            heat_s = "heat" if len(heats) == 1 else "heats"
            if self._nogroup:
                round_hdr = -1   # no grouping: the songs stand on their own
            else:
                round_hdr = self._add_span_row(
                    f"  ═══  {terms.round_name(round_name).upper()}   "
                    f"({len(heats)} {heat_s},  {total} songs{time_s})  ═══",
                    C_ROUND_BG, C_ROUND_FG, bold=True, collapsible=True,
                    regen_cb=(lambda rn=round_name: self._regen_round(rn)),
                    regen_tip="Regenerate every dance in this round",
                )
                self._round_hdr_rows.add(round_hdr)
                self._row_round_name[round_hdr] = round_name

            for d_idx, dance in enumerate(dances):
                # A dance explicitly removed from THIS round is not rendered (its slots
                # stay None in the data, d_idx stays aligned for the other rounds).
                if dance in self._round_skip_dances.get(round_name, ()):
                    continue
                dn = dance_name(dance, dance)

                # ── Dance header (with a per-dance ↺ that re-rolls every heat
                #    of THIS dance in THIS round, respecting the round strategy) ──
                # Compact view drops the dance header entirely; song rows fall under the
                # round header (which still collapses them) and keep their Dance column.
                if self._compact or self._nogroup:
                    dance_hdr = round_hdr
                else:
                    dance_hdr = self._add_span_row(
                        f"    {dn}", C_DANCE_BG, C_DANCE_FG, bold=False,
                        regen_cb=(lambda rn=round_name, di=d_idx, dc=dance:
                                  self._regen_dance(rn, di, dc)),
                        collapsible=True,
                    )
                    self._dance_hdr_rows.add(dance_hdr)
                    self._dance_hdr_dance[dance_hdr] = dance
                    self._row_round_hdr[dance_hdr] = round_hdr   # collapsing round hides it
                    self._row_round_name[dance_hdr] = round_name

                for h_idx, heat in enumerate(heats):
                    entry = heat[d_idx]
                    meta = Row(
                        round_name=round_name,
                        dance=dance,
                        h_idx=h_idx,
                        d_idx=d_idx,
                        tier=tier,
                        prefer_fresh=rc.prefer_fresh if rc else False,
                        strategy=rc.strategy if rc else Strategy.DEFAULT,
                        entry=entry,
                        multi=multi,
                    )
                    row = self.rowCount()
                    self.insertRow(row)
                    self._row_meta.append(meta)
                    self._row_round_hdr[row] = round_hdr
                    self._row_dance_hdr[row] = dance_hdr
                    bg = C_ROW_EVEN if h_idx % 2 == 0 else C_ROW_ODD
                    self._fill_song_row(row, meta, bg)

                    # Final-round backups: stacked, indented under their slot.
                    for bn, bentry in enumerate(
                            self._dynamic_backups.get((round_name, h_idx, d_idx), []), 1):
                        bmeta = meta.spare(bentry, bn)
                        brow = self.rowCount()
                        self.insertRow(brow)
                        self._row_meta.append(bmeta)
                        self._row_round_hdr[brow] = round_hdr
                        self._row_dance_hdr[brow] = dance_hdr
                        self._fill_song_row(brow, bmeta, bg)

        # …and put the ■ marker back on the playing one, wherever it sits now.
        self._row_meta.adopt(placed)
        self._follow_play_row()
        self._update_play_row_hl()
        self._grey_played_rows()   # re-apply played greys after the rebuild
        self._notify_changed()
        self._emit_loaded(playing)

    def _emit_loaded(self, playing: bool):
        """`loaded`, with `_play_dropped` set while it runs: this table was
        `playing` before its rows were rebuilt and the title is gone from them
        — the desk's stop handler tells that apart from music running elsewhere."""
        self._play_dropped = playing and self._current_play_row < 0
        try:
            self.loaded.emit(self)
        finally:
            self._play_dropped = False

    def load_theme(
        self,
        entries: list[MusicEntry],
        theme_label: str,
        play_cb,
        suggester: PlaylistSuggester,
    ):
        """Load a flat themed playlist (no rounds / heats)."""
        self._playlist = None
        self._warmup = False
        self._player_list = False
        self._dance_class = "S"
        self._play_cb = play_cb
        self._suggester = suggester
        self._use_timbre = False
        placed = self._row_meta.placements()   # to hand the ids back below
        playing = self._current_play_row >= 0
        self._row_meta = RunningOrder()
        self._played_saved.clear()   # rows are rebuilt with fresh colors
        self._reset_collapse_state()
        self.setRowCount(0)

        theme_secs = sum(getattr(e, "duration", 0) or 0 for e in entries)
        time_s = f",  ~{fmt_track_secs(theme_secs)}" if theme_secs else ""
        self._add_span_row(
            f"  ═══  {theme_label}   ({len(entries)} tracks{time_s})  ═══",
            C_ROUND_BG, C_ROUND_FG, bold=True,
        )
        for i, e in enumerate(entries):
            meta = Row(dance=e.dance or "", entry=e, theme=True)
            row = self.rowCount()
            self.insertRow(row)
            self._row_meta.append(meta)
            bg = C_ROW_EVEN if i % 2 == 0 else C_ROW_ODD
            self._fill_song_row(row, meta, bg)

        self._row_meta.adopt(placed)   # the ■ marker follows a title still here
        self._follow_play_row()
        self._update_play_row_hl()
        self._grey_played_rows()   # re-apply played greys after the rebuild
        self._notify_changed()
        self._emit_loaded(playing)

    def _warmup_sections(self, entries: list[MusicEntry]) -> list:
        """The ─── strips a warm-up / running-order list is cut into, as
        [(section, [entries])] — a pure function of the ORDER, which is why a
        drop re-cuts them.

        A running order is grouped by what is actually being played: the round
        each track belongs to where that could be derived, otherwise one strip
        per run of the same dance. A warm-up list follows the ETDS rule instead
        and starts a fresh round wherever a dance REPEATS — which would cut a
        dance-major order (all Walzer, then all Tango, …) into one strip per
        song, so a running order never uses it."""
        if not self._player_list:
            return warmup_rounds(entries)
        rounds: list[tuple[str, list[MusicEntry]]] = []
        for section, e in zip(self._player_section_labels(entries), entries, strict=True):
            if not rounds or rounds[-1][0] != section:
                rounds.append((section, []))
            rounds[-1][1].append(e)
        return rounds

    def _section_title(self, section: str, songs: list[MusicEntry]) -> str:
        """The ─── strip over a section: what it is, and what is in it."""
        r_secs = sum(getattr(s, "duration", 0) or 0 for s in songs)
        r_time = f",  ~{fmt_track_secs(r_secs)}" if r_secs else ""
        song_s = "song" if len(songs) == 1 else "songs"
        if self._player_list:
            # The strip names the round — or the dance, when the rounds couldn't
            # be derived — never a heat count: a running order is played straight
            # through.
            title = (f"{terms.round_name(section)}   "
                     f"({len(songs)} {song_s}{r_time})")
        else:
            title = f"{terms.round_name(section)}   (1 heat,  {len(songs)} {song_s}{r_time})"
        return f"    ───  {title}  ───"

    def load_warmup(self, entries: list[MusicEntry], label: str,
                    style: str, dance_class: str, relax: bool,
                    play_cb, suggester: PlaylistSuggester | None,
                    running_order: bool = False):
        """Load a flat warm-up ("Eintanzen") list as its OWN category. Like a theme,
        but each row keeps a 'warmup' tag so the ↺ button re-rolls a timbre-matched,
        TSO-conform track of the same dance and a drag-drop can replace a slot.

        `running_order` says the list is a competition order rather than a warm-up
        (see `load_player_list`) — the panel then heads its strips with the rounds
        instead of cutting a fresh one wherever a dance repeats. A plain warm-up
        list clears that again, so a panel that held an order once doesn't keep
        grouping the next Eintanzen list by rounds it no longer has."""
        self._player_list = bool(running_order)
        if not running_order:
            self._player_sections = {}
        self._flat_mode = False
        self._playlist = None
        self._dynamic = False
        self._warmup = True
        self._warmup_style = style
        self._warmup_class = dance_class
        self._warmup_relax = bool(relax)
        self._warmup_label = label
        self._dance_class = dance_class
        self._style = style
        self._play_cb = play_cb
        self._suggester = suggester
        self._use_timbre = True
        placed = self._row_meta.placements()   # to hand the ids back below
        playing = self._current_play_row >= 0
        self._row_meta = RunningOrder()
        self._played_saved.clear()   # rows are rebuilt with fresh colors
        self._reset_collapse_state()
        self.setRowCount(0)
        # Separate the flat list into the rounds it was built from, numbered per
        # section — Standardrunde 1, Lateinrunde 1, Socialrunde 1, … `warmup_rounds`
        # is where that cut lives, so a deck reading the same list back off disk
        # heads its strips with the very same rounds. Each header carries the
        # competition-style "(1 heat, N songs, ~t)" summary (a warm-up round is
        # always a single heat).
        rounds = self._warmup_sections(entries)
        try:
            self._fill_warmup_rows(rounds)
        finally:
            self._loading_rounds = None
        self._paint_player_heats()
        self._row_meta.adopt(placed)   # the ■ marker follows a title still here
        self._follow_play_row()
        self._update_play_row_hl()
        self._grey_played_rows()   # re-apply played greys after the rebuild
        self._notify_changed()
        self._emit_loaded(playing)

    def _fill_warmup_rows(self, rounds: list) -> None:
        """load_warmup's rows, strip by strip. Each row's round is its strip's,
        handed to `round_at` as it goes: the order is still being built, so
        working it out from the rows so far would be wrong, and once per row."""
        self._loading_rounds = {}
        i = 0
        for section, songs in rounds:
            # A section header counts as this list's round header, so ⊟ / ⊞ and a
            # click on the ─── strip fold it exactly like a competition round.
            round_hdr = -1
            if section and not self._nogroup:
                round_hdr = self._add_span_row(
                    self._section_title(section, songs),
                    C_ROUND_BG, C_ROUND_FG, bold=True, collapsible=True,
                )
                self._round_hdr_rows.add(round_hdr)
            for e in songs:
                # Social tracks have no .dance; warmup_code resolves their
                # genre (Discofox, Salsa, …) so the Dance column isn't blank.
                meta = Row(dance=warmup_code(e) or e.dance or "", d_idx=i,
                           entry=e, warmup=True)
                row = self.rowCount()
                self.insertRow(row)
                self._row_meta.append(meta)
                self._row_round_hdr[row] = round_hdr
                self._loading_rounds[row] = section
                bg = C_ROW_EVEN if i % 2 == 0 else C_ROW_ODD
                self._fill_song_row(row, meta, bg)
                i += 1

    def _warmup_plan(self, entries: list[MusicEntry]) -> list:
        """The rows load_warmup would render for `entries`: ("H", section) for a
        ─── strip header, ("S", entry) for a song. What the in-place edit below
        compares, so it can only ever skip a rebuild that would have come out
        the same way."""
        plan = []
        for section, songs in self._warmup_sections(entries):
            if section and not self._nogroup:
                plan.append(("H", section))
            plan.extend(("S", e) for e in songs)
        return plan

    def _warmup_edit_in_place(self, entries: list[MusicEntry]) -> bool:
        """Show an edit to a warm-up / running-order list by touching only the
        rows that actually changed. True when that was possible.

        Dragging one title between two 250-row running orders used to re-render
        both lists from scratch — a second of frozen window per drag, nearly all
        of it spent rebuilding rows that did not change. Adding or dropping a
        track moves the rows under it and re-shades them, and that is all this
        does.

        Only a clean insertion or removal is taken: the row plans before and
        after must agree apart from ONE run of songs, with no ─── strip
        appearing or vanishing. A re-order, a sort, a dropped dance that splits
        a strip in three — those say False and are rendered by load_warmup, as
        is a list with a folded strip (whose collapse state is keyed by row
        number and would be left pointing at the wrong rows)."""
        if not self._warmup or self._collapsed:
            return False
        old = self._warmup_plan(self._row_meta.entries())
        if len(old) != self.rowCount():
            return False              # the table is not what this plan describes
        new = self._warmup_plan(entries)

        def same(a, b) -> bool:
            # Songs by identity: two different tracks can share a title, and the
            # edited list is built from the very objects the old one held.
            return a[0] == b[0] and (a[1] is b[1] if a[0] == "S" else a[1] == b[1])

        head = 0
        while head < len(old) and head < len(new) and same(old[head], new[head]):
            head += 1
        tail = 0
        while (tail < len(old) - head and tail < len(new) - head
               and same(old[-1 - tail], new[-1 - tail])):
            tail += 1
        gone = old[head:len(old) - tail]
        added = new[head:len(new) - tail]
        if gone and added:
            return False              # changed on both sides: not an insert or a drop

        placed = self._row_meta.placements()   # to hand the ids back below
        playing = self._current_play_row >= 0
        for _ in gone:
            self.removeRow(head)
        for i in range(len(added)):
            self.insertRow(head + i)
        # Every row number below the edit moved, so the row-keyed bookkeeping is
        # re-derived wholesale — it is a few dicts, not a few hundred widgets.
        self._row_meta = RunningOrder()
        self._row_round_hdr = {}
        self._round_hdr_rows = set()
        self._hdr_base_text = {}
        def fresh(row: int) -> bool:
            """Is this one of the blank rows just inserted? Every other row is
            already drawn, and re-drawing it is the cost this exists to avoid."""
            return head <= row < head + len(added)

        row = 0
        i = 0
        round_hdr = -1
        for section, songs in self._warmup_sections(entries):
            if section and not self._nogroup:
                round_hdr = row
                self._round_hdr_rows.add(row)
                title = self._section_title(section, songs)
                if fresh(row):
                    self._paint_span_row(row, title, C_ROUND_BG, C_ROUND_FG,
                                         bold=True, collapsible=True)
                else:
                    # The strip was already there; only what it counts changed.
                    self._hdr_base_text[row] = title
                    self._set_header_text(row)
                self._row_meta.append(None)
                row += 1
            for e in songs:
                meta = Row(dance=warmup_code(e) or e.dance or "", d_idx=i,
                           entry=e, warmup=True)
                self._row_meta.append(meta)
                self._row_round_hdr[row] = round_hdr
                if fresh(row):
                    bg = C_ROW_EVEN if i % 2 == 0 else C_ROW_ODD
                    self._fill_song_row(row, meta, bg)
                i += 1
                row += 1
        self._restripe_song_rows(head)
        self._paint_player_heats()
        self._row_meta.adopt(placed)   # the ■ marker follows a title still here
        self._follow_play_row()
        self._notify_changed()
        self._emit_loaded(playing)
        return True

    def _restripe_song_rows(self, from_row: int) -> None:
        """Re-shade the song rows from `from_row` down. The stripes count songs,
        so inserting or dropping one flips the colour of everything under it —
        but only the colour, which is 500 brushes rather than 500 rebuilt rows.
        A row painted red by a live 🎵 issue, light red for a missing file or
        orange by a replace mark keeps what _fill_song_row gave it."""
        for i, (row, meta) in enumerate(self._row_meta.numbered()):
            if row < from_row:
                continue
            path = meta.path_str
            if path and (path in self._issue_paths or path in self._marked_paths
                         or path in self._pinned_paths):
                continue
            title = self.item(row, _COL_TITLE)
            if title is not None and title.background().color() == C_MISSING_BG:
                continue
            bg = C_ROW_EVEN if i % 2 == 0 else C_ROW_ODD
            for col in range(self.columnCount()):
                it = self.item(row, col)
                if it is not None:
                    it.setBackground(bg)

    def _player_section_labels(self, entries: list[MusicEntry]) -> list[str]:
        """One ─── strip label per entry of a running order.

        The round it is played in when the caller could work that out, the dance
        otherwise. A track dropped in later belongs to no round of its own — it
        takes the one it landed in, so the strips stay whole instead of tearing
        open around every wish. So does a title the order holds more than once
        (one Paso Doble in every round): the sections are keyed by path and know
        only one of its rounds."""
        if not self._player_sections:
            return [warmup_code(e) or e.dance or "" for e in entries]
        times = Counter(str(e.path) for e in entries)
        out: list[str] = []
        last = ""
        for e in entries:
            p = str(e.path)
            last = (self._player_sections.get(p) if times[p] == 1 else None) or last
            out.append(last)
        # Anything dropped ahead of the first known track joins that first round.
        first = next((lbl for lbl in out if lbl), "")
        return [lbl or first for lbl in out]

    def round_at(self, row: int) -> str:
        """The round `row` is danced in, "" where the list knows none: a grid
        row carries it, a running order's ─── strips name it."""
        meta = self._row_meta.at(row)
        if meta is None:
            return ""
        if meta.round_name or not (self._player_list and self._player_sections):
            return meta.round_name
        loading = self._loading_rounds
        if loading is not None and row in loading:
            return loading[row]
        rows = self._row_meta.numbered()
        labels = self._player_section_labels([m.entry for _, m in rows])
        return next((lbl for (i, _m), lbl in zip(rows, labels, strict=True)
                     if i == row), "")

    def _paint_player_heats(self) -> None:
        """Write "Heat 2" into the Heat column of a running order: the place of
        a title among the same dance in its round. Like the strips, a pure
        function of the order, so a drop renumbers its round. A dance played
        once in its round (a final, a party round) names no heat, and without
        known rounds there are none to count in."""
        self._player_heat_text = {}
        if not (self._player_list and self._player_sections):
            return
        rows = self._row_meta.numbered()
        labels = self._player_section_labels([m.entry for _, m in rows])
        keys = [(lbl, m.dance) for lbl, (_, m) in zip(labels, rows, strict=True)]
        total = Counter(keys)
        seen: Counter = Counter()
        for key, (row, _) in zip(keys, rows, strict=True):
            seen[key] += 1
            text = i18n.t("Heat %d") % seen[key] if total[key] > 1 else ""
            if text:
                self._player_heat_text[row] = text
            it = self.item(row, COL_HEAT)
            if it is not None:
                it.setText(text)

    def load_player_list(self, entries: list[MusicEntry], label: str,
                         play_cb, suggester: PlaylistSuggester | None = None,
                         sections: dict[str, str] | None = None):
        """Load a deck as the flat running order of a player-only install.

        There is no draw to plan in such an install: the deck IS the list the
        evening is played from, so it behaves like the ETDS party list — one
        running order, a dropped title lands where it was dropped, any row can be
        dragged anywhere. It keeps the ─── strips, because seeing where one round
        ends and the next begins is worth having; `sections` (track path → round
        name) is what heads them with 'Vorrunde' / 'Finale', and without it they
        fall back to naming the dance being played. Either way they are derived
        from the order and simply re-cut themselves around whatever was just
        dragged in. What they never do is refuse a drop.

        Handed no `sections`, the list works the rounds out of its own order —
        a grid that carried no round names into the conversion, a running order
        restored from a file saved before the strips knew about rounds, a list
        assembled by hand: all of them would otherwise be stuck naming dances
        for good, because nothing ever derives the rounds a second time."""
        self._player_sections = dict(sections or {})
        if not self._player_sections:
            self._player_sections = {str(e.path): name
                                     for name, seg in running_order_rounds(entries)
                                     for e in seg}
            if self._player_sections:
                log.info("🏁 Rounds derived from the running order\n"
                         "tracks: %s\n"
                         "rounds: %s", len(entries),
                         ", ".join(dict.fromkeys(self._player_sections.values())))
        self.load_warmup(entries, label, style="", dance_class="S", relax=True,
                         play_cb=play_cb, suggester=suggester, running_order=True)

    def load_wishlist(self, entries: list[MusicEntry], play_cb,
                      suggester: PlaylistSuggester | None):
        """Load the flat scratch Wishlist. Like a theme list but drops append to it."""
        self._flat_mode = True
        self._warmup = False
        self._playlist = None
        self._dance_class = "S"
        self._play_cb = play_cb
        self._suggester = suggester
        self._use_timbre = False
        placed = self._row_meta.placements()   # to hand the ids back below
        playing = self._current_play_row >= 0
        self._row_meta = RunningOrder()
        self._played_saved.clear()   # rows are rebuilt with fresh colors
        self._reset_collapse_state()
        self.setRowCount(0)
        for e in entries:
            self._append_entry(e, notify=False)
        self._row_meta.adopt(placed)   # the ■ marker follows a title still here
        self._follow_play_row()
        self._update_play_row_hl()
        self._grey_played_rows()   # re-apply played greys after the rebuild
        self._notify_changed()
        self._emit_loaded(playing)

    def _append_entry(self, entry: MusicEntry, notify: bool = True):
        """Append one track as a flat row (Wishlist)."""
        if entry is None:
            return
        # Skip exact duplicates already parked in the wishlist.
        for m in self._row_meta:
            if m and m.entry is not None and str(m.entry.path) == str(entry.path):
                return
        meta = Row(dance=entry.dance or "", entry=entry, theme=True)
        row = self.rowCount()
        self.insertRow(row)
        self._row_meta.append(meta)
        bg = C_ROW_EVEN if row % 2 == 0 else C_ROW_ODD
        self._fill_song_row(row, meta, bg)
        if notify:
            self._notify_changed()

    def _append_path(self, path: Path) -> bool:
        """Resolve a dropped file path to an entry and append it to the wishlist.
        Returns True when a track was added."""
        entry = self._entry_for(path)
        if entry is None:
            QMessageBox.information(
                self, "Wishlist",
                i18n.t("Couldn't read “%s” as an audio track.") % Path(path).name
            )
            return False
        before = len(self._row_meta)
        self._append_entry(entry)
        return len(self._row_meta) > before

    def _append_m3u(self, path: Path) -> int:
        """Expand a dropped .m3u/.m3u8 into the wishlist. Returns how many tracks
        were added (deduped against what's already parked there)."""
        try:
            lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return 0
        added = 0
        for line in lines:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.lower().startswith("file:"):
                u = QUrl(s)
                if u.isLocalFile():
                    s = u.toLocalFile()
            tp = self.host.resolve_file(Path(s.strip('"')))
            entry = self._entry_for(tp)
            if entry is not None:
                before = len(self._row_meta)
                self._append_entry(entry, notify=False)
                added += 1 if len(self._row_meta) > before else 0
        if added:
            self._notify_changed()
        return added

    def _files_from_dir(self, folder: Path) -> list[Path]:
        """Every audio file in a dropped FOLDER, subfolders included, in path order.
        Playlists inside it are skipped: what was dropped is the folder's own music,
        and an .m3u lying next to it would add every track a second time."""
        try:
            found = [p for p in sorted(folder.rglob("*"), key=lambda q: str(q).lower())
                     if p.suffix.lower() in self._AUDIO_DROP_EXTS and p.is_file()]
        except OSError as exc:
            log.warning("📂 Dropped folder could not be read\n"
                        "folder: %s\n"
                        "error: %s", folder, exc)
            return []
        if len(found) > self._DIR_DROP_ASK and not self._confirm_big_dir_drop(folder, len(found)):
            return []
        return found

    def _confirm_big_dir_drop(self, folder: Path, n: int) -> bool:
        ans = QMessageBox.question(
            self, "Add folder",
            i18n.t("“%s” holds %d tracks (subfolders included).\n\nReading them all takes a "
                   "moment — every file's tags are read on the way in.\n\nAdd them?")
            % (folder.name, n),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return ans == QMessageBox.StandardButton.Yes

    def _wishlist_droppables(self, e, expand_dirs: bool = True) -> list[Path]:
        """All local audio files and .m3u playlists carried by a drop (for the
        Wishlist's append-anything behaviour). A dropped FOLDER stands for the audio
        files inside it. Falls back to the text payload and finally the raw-mime path
        dig used for DJ apps.

        `expand_dirs=False` leaves a folder in the list as itself. That's for the
        drag accept-checks, which only ask whether there is anything to drop at all
        and must not walk a music tree on every mouse move of the drag."""
        md = e.mimeData()
        out: list[Path] = []
        ok = self._AUDIO_DROP_EXTS + (".m3u", ".m3u8")
        seen: set = set()

        def _add(s: str):
            s = (s or "").strip().strip('"').strip("'")
            if not s:
                return
            if s.lower().startswith("file:"):
                u = QUrl(s)
                if u.isLocalFile():
                    s = u.toLocalFile()
            p = Path(s)
            key = str(p).lower()
            if key in seen:
                return
            if p.suffix.lower() in ok and p.is_file():
                seen.add(key)
                out.append(p)
            elif p.is_dir():
                seen.add(key)
                out.extend(self._files_from_dir(p) if expand_dirs else [p])

        if md and md.hasUrls():
            for url in md.urls():
                _add(url.toLocalFile() if url.isLocalFile() else url.toString())
        if not out and md and md.hasText():
            for line in md.text().splitlines():
                _add(line)
        if not out:
            p = self._path_from_raw_mime(md)
            if p is not None:
                out.append(p)
        return out

    def wishlist_entries(self) -> list[MusicEntry]:
        return self._row_meta.entries()

    def _add_span_row(self, text: str, bg: QColor, fg: QColor, bold: bool,
                      regen_cb=None, collapsible: bool = False,
                      regen_tip: str = "Regenerate every heat of this dance (this round only)") -> int:
        row = self.rowCount()
        self.insertRow(row)
        self._row_meta.append(None)
        self._paint_span_row(row, text, bg, fg, bold, regen_cb, collapsible, regen_tip)
        return row

    def _paint_span_row(self, row: int, text: str, bg: QColor, fg: QColor, bold: bool,
                        regen_cb=None, collapsible: bool = False,
                        regen_tip: str = "") -> None:
        """Dress an EXISTING row as a header. Split out of `_add_span_row` so a
        row inserted in the middle of a list can be given the same look without
        being appended to the order."""
        if collapsible:
            # Store the bare label; the ▼/▶ arrow is rendered by _set_header_text.
            self._hdr_base_text[row] = text
            text = f"▼ {text}"
        item = QTableWidgetItem(text)
        item.setBackground(bg)
        item.setForeground(fg)
        if bold:
            f = item.font()
            f.setBold(True)
            item.setFont(f)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)   # not selectable / draggable
        if collapsible:
            item.setToolTip("Click to collapse / expand")
        self.setItem(row, 0, item)
        if regen_cb is not None:
            # Leave the last (↺) column free for a per-dance regenerate button.
            self.setSpan(row, 0, 1, _N_COLS - 1)
            btn = QPushButton("↺")
            btn.setFixedSize(26, 20)
            btn.setStyleSheet("padding: 0;")
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # keep keyboard focus on the table
            btn.setToolTip(regen_tip)
            btn.clicked.connect(lambda _: regen_cb())
            # Centered like the song rows' painted ↺, not top-left as Qt puts a cell widget.
            holder = QWidget()
            lay = QHBoxLayout(holder)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
            self.setCellWidget(row, COL_REGEN, holder)
        else:
            self.setSpan(row, 0, 1, _N_COLS)
        self.setRowHeight(row, 22)
