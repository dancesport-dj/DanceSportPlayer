"""PlaylistTable dynamic mode: drops build / extend the rounds & heats grid.

Mixin of PlaylistTable — extracted 1:1 from gui/playlist_table.py in the
big-module split; behaviour unchanged."""
import logging

import planner.models
from planner import i18n

from planner.parsing import _detect_dance, _song_title_key

from PySide6.QtCore import (
    QTimer,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMessageBox,
)
from pathlib import Path
from planner.models import (
    ALLOW_REPEAT,
    MusicEntry,
    ROUND_NAMES,
    RoundConfig,
)
from planner.terms import dance_name
from shared.widgets import (
    _show_toast,
)

log = logging.getLogger("dancesport.gui.playlist_table")

# `PlaylistTable` is late-bound into this module by gui.playlist_table after
# the class is defined (a top-level import would be circular): the methods
# here isinstance-check drag sources against it at call time.
PlaylistTable = None


class DynamicModeMixin:
    """Dynamic-deck concern: unlocked decks grow rounds/heats from dropped
    songs (6-3-2-1 field), incl. final-round backups stacked under a slot."""

    # ── Dynamic mode: drops build / extend the rounds & heats grid ──────────────

    def _can_dynamic_drop(self, e) -> bool:
        """Cheap check (for dragMove) that a drop carries something placeable."""
        src = e.source()
        if isinstance(src, PlaylistTable) and src is not self and src._drag_src_rows:
            return True
        # expand_dirs=False: a dropped folder counts as "something placeable"
        # without its tree being walked once per mouse move of the drag.
        return bool(self._wishlist_droppables(e, expand_dirs=False))

    def _collect_drop_entries(self, e) -> list[MusicEntry]:
        """Resolve every track carried by a drop to a MusicEntry — from another deck
        / wishlist (via its dragged rows) or from external files / .m3u playlists."""
        src = e.source()
        out: list[MusicEntry] = []
        if isinstance(src, PlaylistTable) and src is not self:
            for r in src._drag_src_rows:
                if 0 <= r < len(src._row_meta):
                    m = src._row_meta[r]
                    if m and m.entry is not None:
                        out.append(m.entry)
            if out:
                return out
        # Flattened to one path list first, so a whole dropped folder resolves in
        # a single pass under a single progress dialog (see _entries_for_paths).
        paths: list[Path] = []
        for p in self._wishlist_droppables(e):
            if p.suffix.lower() in (".m3u", ".m3u8"):
                paths += self._m3u_track_paths(p)
            else:
                paths.append(p)
        return [ent for ent in self._entries_for_paths(paths) if ent is not None]

    def _enter_dynamic(self, default_capacity: list[int]):
        """Flip this deck to dynamic mode. A deck with an existing (static) grid keeps
        its structure — capacity becomes its per-round heat counts; an empty deck takes
        the supplied default pattern (from the '6-3-2-1' Rounds field)."""
        self._dynamic = True
        if self._dynamic_backups is None:
            self._dynamic_backups = {}
        if self._playlist:
            self._dynamic_capacity = [len(heats) for heats in self._playlist.values()]
            if not self._dynamic_dances:
                self._dynamic_dances = self._recover_dynamic_dances()
        else:
            self._playlist = self._playlist or {}
            self._dynamic_capacity = list(default_capacity) or [6, 3, 2, 1]
            self._dynamic_dances = []

    def _field_capacity(self) -> list[int]:
        """The configured '6-3-2-1' Rounds-field pattern (via the deck's capacity
        provider), or the 6-3-2-1 default when no provider is wired."""
        if self._capacity_provider is not None:
            try:
                cap = self._capacity_provider()
                if cap:
                    return list(cap)
            except Exception as exc:
                log.debug("🔢 Capacity provider failed — falling back to 6-3-2-1: %s", exc)
        return [6, 3, 2, 1]

    def _enter_dynamic_from_drop(self):
        """Empty deck → its first drop turns it dynamic, capacity from the Rounds field."""
        self._enter_dynamic(self._field_capacity())
        self.dynamicChanged.emit(self)

    def current_dances(self) -> list[str]:
        """The dance columns actually present in this deck's grid — the source of
        truth for the config checkboxes. A dynamic deck's live column list wins (so
        empty columns still count); otherwise the dances the grid was loaded with.
        Used on deck-focus switch so the checkboxes follow what the user sees, not a
        possibly-stale `self._dances` that drifted out of sync."""
        if self._dynamic and self._dynamic_dances:
            return list(self._dynamic_dances)
        return list(self._loaded_dances)

    def _recover_dynamic_dances(self) -> list[str]:
        """Recover the dance column order (first-seen) from the current grid rows."""
        by_idx: dict[int, str] = {}
        for m in self._row_meta:
            if (m and not m.theme and m.round_name
                    and not m.backup):
                by_idx[m.d_idx] = m.dance
        return [by_idx[i] for i in sorted(by_idx)]

    def _new_heat(self) -> list[MusicEntry | None]:
        return [None] * len(self._dynamic_dances)

    def _canonical_order(self, dances: list[str]) -> list[str]:
        """Order dance codes by the standard competition sequence (LW,TG,WW,SF,QS /
        SA,CC,RB,PD,JI / social dances). Codes outside that reference keep their
        first-seen order, after the known ones. Style-independent: the per-style
        code sets don't overlap, so one master order sorts any deck correctly."""
        ref: list[str] = []
        for st in ("Standard", "Latin", "Others"):
            ref.extend(planner.models.DEFAULT_DANCES.get(st, {}).get("S", []))
        rank = {d: i for i, d in enumerate(ref)}
        seen = {d: i for i, d in enumerate(dances)}
        return sorted(dances, key=lambda d: rank.get(d, len(ref) + seen.get(d, 0)))

    def _ensure_dynamic_dance(self, dance: str):
        """Make sure `dance` is a grid column, kept in the canonical dance order
        (so e.g. Langsamer Walzer stays at the top even if dropped last). When a new
        column shifts the layout, existing heats and backups are reordered to match."""
        if dance in self._dynamic_dances:
            return
        old = list(self._dynamic_dances)
        new = self._canonical_order(old + [dance])
        self._dynamic_dances = new
        old_idx = {d: i for i, d in enumerate(old)}
        width = len(new)
        for heats in (self._playlist or {}).values():
            for h_i, heat in enumerate(heats):
                row: list[MusicEntry | None] = [None] * width
                for ni, d in enumerate(new):
                    oi = old_idx.get(d)
                    if oi is not None and oi < len(heat):
                        row[ni] = heat[oi]
                heats[h_i] = row
        if self._dynamic_backups:
            new_idx = {d: i for i, d in enumerate(new)}
            rekey: dict[tuple[str, int, int], list[MusicEntry]] = {}
            for (rname, h_i, d_i), entries in self._dynamic_backups.items():
                d = old[d_i] if d_i < len(old) else dance
                rekey[(rname, h_i, new_idx.get(d, d_i))] = entries
            self._dynamic_backups = rekey

    def _dynamic_specs(self) -> list[tuple[str, int]]:
        """(round_name, capacity) per round, in order. Existing rounds keep their names;
        not-yet-created rounds borrow the standard names for the pattern length."""
        caps = self._dynamic_capacity or [6, 3, 2, 1]
        existing = list(self._playlist.keys()) if self._playlist else []
        names = ROUND_NAMES.get(len(caps), [f"Runde {i + 1}" for i in range(len(caps))])
        specs: list[tuple[str, int]] = []
        for i, cap in enumerate(caps):
            if i < len(existing):
                name = existing[i]
            elif i < len(names):
                name = names[i]
            else:
                name = f"Runde {i + 1}"
            specs.append((name, cap))
        return specs

    def _dynamic_round_configs(self) -> list[RoundConfig]:
        """RoundConfigs for the rounds that currently hold heats (in pattern order)."""
        specs = self._dynamic_specs()
        n = len(specs)
        cfgs: list[RoundConfig] = []
        for i, (name, _cap) in enumerate(specs):
            if not self._playlist or name not in self._playlist:
                continue
            tier = ("final" if i == n - 1 else "semi" if i == n - 2
                    else "pre_semi" if i == n - 3 else "early")
            cfgs.append(RoundConfig(
                name=name, heats=len(self._playlist[name]), tier=tier,
                prefer_fresh=(tier == "pre_semi")))
        return cfgs

    def _round_of_row(self, row: int) -> str | None:
        """Round name a drop at `row` targets. Heat / backup rows carry it in their
        meta; a drop onto a round- or dance-HEADER row resolves to that header's round
        (so dropping a dance that doesn't exist in the round yet — e.g. a Latin track
        onto a Standard round's header — still lands in the focused round, not round 1).
        None only for truly empty space below the grid."""
        if 0 <= row < len(self._row_meta):
            m = self._row_meta[row]
            if m and m.round_name:
                return m.round_name
        return self._row_round_name.get(row)

    def _iter_planned_entries(self):
        """Yield every entry already in this deck — grid heats AND stacked backups."""
        for heats in (self._playlist or {}).values():
            for heat in heats:
                for e in heat:
                    if e is not None:
                        yield e
        for entries in self._dynamic_backups.values():
            for e in entries:
                yield e

    def _entry_fingerprint(self, entry: MusicEntry | None) -> str | None:
        """Content fingerprint of a track — identical audio shares one fingerprint even
        after a rename / re-encode. In-memory cache only, never reads the file (see
        `_audio_keys` for the on-demand identity). None when unknown."""
        if entry is None or not getattr(entry, "path", None) or self._cache is None:
            return None
        try:
            return self._cache.known_fingerprint(Path(entry.path))
        except Exception:
            return None

    @staticmethod
    def _same_path(a: str | None, b: str | None) -> bool:
        """True if two file paths point at the same file, ignoring case and separator
        style (Windows paths from an imported .m3u often differ from the library's)."""
        if not a or not b:
            return False
        return str(Path(a)).lower() == str(Path(b)).lower()

    def _dup_keys(self, entry: MusicEntry | None):
        """(filename_lower, content_fingerprint) identifying a song for dedup — the
        same notion of 'same song' as _find_duplicate. Either part may be None."""
        p = getattr(entry, "path", None) if entry else None
        if not p:
            return (None, None)
        return (Path(str(p)).name.lower(), self._entry_fingerprint(entry))

    def _exclude_with_dupes(self, entries) -> set:
        """Re-roll exclusion set: every given track's path PLUS any LIBRARY track that
        is the same song (same filename or content fingerprint). Without this a re-roll
        could return a COPY of a song already planned here — a duplicate that lives under
        a different path, which the picker's path-only filter would not catch."""
        entries = [e for e in entries if e is not None and getattr(e, "path", None)]
        excl = {str(e.path) for e in entries}
        lib = self._suggester.lib if self._suggester else None
        if lib is None or not entries:
            return excl
        names, fps = set(), set()
        for e in entries:
            n, fp = self._dup_keys(e)
            if n:
                names.add(n)
            if fp:
                fps.add(fp)
        for e in lib.entries:
            ep = getattr(e, "path", None)
            if not ep:
                continue
            n, fp = self._dup_keys(e)
            if (n and n in names) or (fp and fp in fps):
                excl.add(str(ep))
        return excl

    def _audio_keys(self, entry: MusicEntry | None) -> set:
        """Everything that names this track's AUDIO: the path (case and separators
        folded), the content fingerprint and the tag-free audio fingerprint. Two
        tracks sharing any of them are the same recording — the copy on another
        drive shares the content fingerprint, a copy whose tags were edited still
        shares the audio one. Hashed on demand when the DB doesn't know the file
        yet. Path only while there is no cache."""
        p = getattr(entry, "path", None) if entry is not None else None
        if not p:
            return set()
        keys = {("p", str(Path(p)).lower())}
        if self._cache is None:
            return keys
        try:
            fp = self._cache.fingerprint(Path(p))
            if fp:
                keys.add(("f", fp))
                afp = self._cache.audio_fingerprint(Path(p))
                if afp:
                    keys.add(("a", afp))
        except Exception as exc:
            log.debug("🔑 No fingerprint for %s: %s", p, exc)
        return keys

    @staticmethod
    def _title_key(entry: MusicEntry | None) -> tuple | None:
        """(dance, cleaned title) — the song a file holds, going by its name (track
        number, tempo tag, a '_cut' marker stripped: `_song_title_key`). A tournament
        cut or a re-encode shares no byte with the original, only this. Compare two
        with `_same_title`. None when the name leaves no title."""
        p = getattr(entry, "path", None) if entry is not None else None
        if not p:
            return None
        key = _song_title_key(str(p))
        if not key:
            return None
        return ((getattr(entry, "dance", None) or "").upper(), key)

    @staticmethod
    def _same_title(a: tuple | None, b: tuple | None) -> bool:
        """Two `_title_key`s name one song: the same title in the same dance — the
        dance keeps 'Candela' the Cha Cha apart from 'Candela' the Rumba. A file with
        no known dance (no code in its name, not in the library) matches any."""
        if a is None or b is None or a[1] != b[1]:
            return False
        return not a[0] or not b[0] or a[0] == b[0]

    def _holds_same_audio(self, entry: MusicEntry | None, entries) -> MusicEntry | None:
        """The first of `entries` that is the same recording as `entry`, or None."""
        keys = self._audio_keys(entry)
        if not keys:
            return None
        for e in entries:
            if e is not None and keys & self._audio_keys(e):
                return e
        return None

    def _duplicate_rows(self) -> list[tuple[int, int, bool]]:
        """(row, row of the first occurrence, same_audio) for every track that
        repeats one above it. `same_audio` True: the first row carrying that very
        audio. `same_audio` False: the first file of the same title (`_title_key`),
        a cut or a re-encode. ALLOW_REPEAT dances (PD) may come round again,
        except in a wishlist."""
        first_row: dict = {}
        titles: dict = {}               # cleaned title -> [(title key, first row)]
        out = []
        for r, m in self._row_meta.numbered():
            e = m.entry
            if not self._flat_mode and (getattr(e, "dance", None) or "") in ALLOW_REPEAT:
                continue
            audio = self._audio_keys(e)
            title = self._title_key(e)
            first = next((first_row[k] for k in audio if k in first_row), None)
            same_audio = first is not None
            if first is None and title is not None:
                first = next((row for held, row in titles.get(title[1], ())
                              if self._same_title(title, held)), None)
            if first is not None:
                out.append((r, first, same_audio))
            origin = r if first is None else first
            for k in audio:              # a copy of this very file points here, not at the title
                first_row.setdefault(k, first if same_audio else r)
            if title is not None:
                titles.setdefault(title[1], []).append((title, origin))
        return out

    def _find_duplicate(self, entry: MusicEntry):
        """Detect whether `entry` duplicates something already in the deck:
          • 'hard' — the SAME audio (path, content or audio fingerprint, see
            `_audio_keys`) → a sure duplicate, incl. a copy on another drive and a
            renamed / re-tagged one; skip automatically.
          • 'soft' — only the FILENAME or the title (`_title_key`, e.g. a '_cut'
            edit) matches, the audio differs → maybe a duplicate, so the caller
            asks the user.
        Returns ('hard'|'soft', existing_entry) or None. PD/ALLOW_REPEAT may repeat → None."""
        if getattr(entry, "dance", None) in ALLOW_REPEAT:
            return None
        p = str(entry.path) if getattr(entry, "path", None) else None
        if not p:
            return None
        planned = [e for e in self._iter_planned_entries() if getattr(e, "path", None)]
        same = self._holds_same_audio(entry, planned)
        if same is not None:
            return ("hard", same)
        fname = Path(p).name.lower()
        title = self._title_key(entry)
        name_hit = next((e for e in planned
                         if Path(str(e.path)).name.lower() == fname
                         or self._same_title(title, self._title_key(e))), None)
        return ("soft", name_hit) if name_hit is not None else None

    def _ask_soft_duplicate(self, entry: MusicEntry, existing: MusicEntry) -> str:
        """A track whose FILENAME or title matches one already in the deck but is a
        DIFFERENT file (path + fingerprint differ) — ask the user to replace the existing
        track or keep it. Returns 'replace' or 'skip'."""
        fname = Path(str(entry.path)).name if getattr(entry, "path", None) else (entry.title or "this track")
        held = Path(str(existing.path)).name if getattr(existing, "path", None) else ""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Possible duplicate")
        if not held or held.lower() == fname.lower():
            box.setText(i18n.t("A track named “%s” is already in this playlist,\n"
                               "but it’s a different file.") % fname)
        else:
            box.setText(i18n.t("“%s” is already in this playlist —\n"
                               "“%s” looks like the same title in another file.") % (held, fname))
        box.setInformativeText("Replace the existing track with this one?")
        repl_btn = box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
        skip_btn = box.addButton("Keep existing", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(skip_btn)
        box.exec()
        return "replace" if box.clickedButton() is repl_btn else "skip"

    def _replace_planned_entry(self, old: MusicEntry, new: MusicEntry) -> bool:
        """Swap `old` (matched by identity) for `new` wherever it sits — heat or backup."""
        for heats in (self._playlist or {}).values():
            for heat in heats:
                for i, e in enumerate(heat):
                    if e is old:
                        heat[i] = new
                        return True
        for entries in self._dynamic_backups.values():
            for i, e in enumerate(entries):
                if e is old:
                    entries[i] = new
                    return True
        return False

    def _iter_deck_entries(self):
        """Every track this deck is holding, however it holds them.

        `_iter_planned_entries` reads the GRID, and a deck in free order (or a
        theme list, or the warm-up panel) has none — its tracks live in the rows
        themselves. Anything asking "is this title in that deck?" has to look
        where the deck actually keeps it, or a drag out of a free deck finds
        nothing and never becomes a move."""
        if self._playlist is None:
            for m in self._row_meta:
                if m and m.entry is not None:
                    yield m.entry
            return
        yield from self._iter_planned_entries()

    def _contains_path_or_fp(self, entry: MusicEntry | None) -> bool:
        """True if this deck already holds `entry` — the same audio by path or
        fingerprint (so a renamed copy still counts). Unlike `_find_duplicate` this
        ignores ALLOW_REPEAT, so it can drive a wishlist→deck MOVE even for PD."""
        return self._holds_same_audio(entry, self._iter_deck_entries()) is not None

    def _entry_keys(self, entry: MusicEntry | None) -> set:
        """Identity keys (path and/or content fingerprint) for one track, for set
        membership tests against `_planned_keys`."""
        keys = set()
        if entry is not None and getattr(entry, "path", None):
            keys.add(("p", str(entry.path)))
            fp = self._entry_fingerprint(entry)
            if fp is not None:
                keys.add(("f", fp))
        return keys

    def _planned_keys(self) -> set:
        """Identity keys of every track currently planned in this deck — snapshotted
        before a drop so the move-out can tell a track this drop newly added from one
        that was already there."""
        keys = set()
        for e in self._iter_deck_entries():
            keys |= self._entry_keys(e)
        return keys

    def _move_from_drag_source(self, e, pre_planned: set | None = None) -> int:
        """A drop into THIS deck that came from another deck or a wishlist MOVES the
        tracks (unless Ctrl forces a copy): every dragged source row whose track now
        lives in this deck is vacated in the source — a wishlist row is removed, a deck
        slot is emptied. Warm-up rows are left alone (dragging out of Eintanzen is a
        copy). A track that was ALREADY planned before this drop (in `pre_planned`) was
        not added by it, so vacating the source would silently lose it — confirm first.
        Returns how many source rows were vacated."""
        if self._drop_ctrl(e):
            return 0
        src = e.source()
        if not (isinstance(src, PlaylistTable) and src is not self and src._drag_src_rows):
            return 0
        src_flat = getattr(src, "_flat_mode", False)
        # Dragging out of the Eintanzen panel is a copy: it is a source of music,
        # not a list anything is taken from. A DECK in free order is a list, and
        # it carries the very same warm-up rows — so tell the two apart before the
        # panel's rule sends the drag off as a copy and leaves the title sitting
        # in both decks.
        src_free_deck = (getattr(src, "_player_list", False)
                         and src is not self.host.warmup_table())
        if not src_flat and getattr(src, "_warmup", False) and not src_free_deck:
            return 0
        auto, ask = [], []
        for r in src._drag_src_rows:
            if not (0 <= r < len(src._row_meta)):
                continue
            m = src._row_meta[r]
            ent = m.entry if m else None
            if ent is None or not self._contains_path_or_fp(ent):
                continue
            if pre_planned and (self._entry_keys(ent) & pre_planned):
                ask.append(r)       # already planned before this drop
            else:
                auto.append(r)      # newly placed by this drop
        rows = list(auto)
        if ask and self._confirm_remove_already_planned(src, ask, src_flat):
            rows += ask
        if not rows:
            return 0
        ok = (src._remove_rows(rows, select_after=True) if src_flat
              else src._clear_slots_at(set(rows), select_after=True))
        return len(rows) if ok else 0

    def _confirm_remove_already_planned(self, src, rows, src_flat: bool) -> bool:
        """Ask whether to pull tracks that were already planned out of the source
        (wishlist / deck). Returns True to remove them, False to keep them."""
        titles = [src._row_meta[r].entry.title for r in rows
                  if 0 <= r < len(src._row_meta) and src._row_meta[r]
                  and src._row_meta[r].entry]
        if len(titles) == 1:
            text = (i18n.t("“%s” is already in this playlist.\n\nRemove it from the wishlist anyway?")
                    if src_flat else
                    i18n.t("“%s” is already in this playlist.\n\nRemove it from the playlist anyway?")
                    ) % titles[0]
        else:
            text = (i18n.t("%d dragged track(s) are already in this playlist.\n\n"
                           "Remove them from the wishlist anyway?")
                    if src_flat else
                    i18n.t("%d dragged track(s) are already in this playlist.\n\n"
                           "Remove them from the playlist anyway?")) % len(titles)
        ans = QMessageBox.question(
            self, "Already planned", text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return ans == QMessageBox.StandardButton.Yes

    @staticmethod
    def _drop_dance(entry: MusicEntry) -> str | None:
        """Which dance a dropped track is, for a deck that sorts by dance.

        The entry's own answer first. Failing that the FILE NAME, which is
        where this library writes the code ("(WW 29)", "T50") — and not the
        title, which is that very name with exactly those markers taken back
        out of it, so asking the title could only ever come up empty."""
        dance = getattr(entry, "dance", None)
        if dance:
            return dance
        path = getattr(entry, "path", None) if entry is not None else None
        name = Path(str(path)).name.replace("_", " ") if path else ""
        return _detect_dance(name) or _detect_dance(getattr(entry, "title", "") or "")

    def _dynamic_place_one(self, entry: MusicEntry, target_row: int,
                           prefer_existing: bool = False) -> str:
        """Place one track into the dynamic grid. Returns "" if it was placed,
        otherwise WHY it was not: "dance" (no dance to file it under) or "dup"
        (this list already holds it). The caller says so once for the whole
        drop — one toast lives per window, so a message per track is a message
        the next one wipes out.

        `prefer_existing` (the extra tracks of a multi-drop) fills any EXISTING
        empty slot of this dance, deck-wide, before falling back to extending a
        round — so dropping N tracks tops up N empty slots instead of stacking
        new heats."""
        dance = self._drop_dance(entry)
        if not dance:
            return "dance"
        entry.dance = dance
        dup = self._find_duplicate(entry)
        if dup is not None:
            kind, existing = dup
            if kind == "hard":
                return "dup"
            # soft duplicate (same filename, different file) → let the user decide
            if self._ask_soft_duplicate(entry, existing) == "replace":
                if self._replace_planned_entry(existing, entry):
                    _show_toast(self, i18n.t("🔁  Replaced “%s” with “%s”")
                                % (existing.title, entry.title))
                    return ""
                # couldn't locate it (shouldn't happen) → fall through to a normal add
            else:
                return "dup"
        self._ensure_dynamic_dance(dance)
        # Extra tracks of a multi-drop: fill an existing empty slot of this dance
        # anywhere in the deck first (never create a heat while a slot is free).
        if prefer_existing and self._fill_existing_empty_slot(dance, entry):
            return ""
        # Exact-slot drop: an EMPTY same-dance slot right under the cursor takes
        # the track 1:1 (h_idx stays valid even if a new dance column was added
        # earlier in this batch; d_idx is recomputed, the meta one may be stale).
        if not prefer_existing:
            m = self._row_meta[target_row] if 0 <= target_row < len(self._row_meta) else None
            if (m and not m.theme and not m.backup
                    and m.dance == dance
                    and m.round_name in (self._playlist or {})):
                heats = self._playlist[m.round_name]
                d_idx = self._dynamic_dances.index(dance)
                if m.h_idx < len(heats):
                    heat = heats[m.h_idx]
                    if d_idx < len(heat) and heat[d_idx] is None:
                        heat[d_idx] = entry
                        return ""
        tgt = self._round_of_row(target_row)
        if tgt is not None and tgt in (self._playlist or {}):
            self._dynamic_extend_round(tgt, dance, entry)
        else:
            self._dynamic_autofill(dance, entry)
        return ""

    def _dynamic_replace_slot(self, target_row: int, entry: MusicEntry) -> bool:
        """Ctrl + drop onto a FILLED dynamic slot: overwrite the song there with
        `entry`, keeping the slot's dance column. Returns True if the slot was
        replaced, False if the user cancelled a dance mismatch, the track would
        duplicate another slot, or `target_row` isn't a filled main slot."""
        if not (0 <= target_row < len(self._row_meta)):
            return False
        m = self._row_meta[target_row]
        if (not m or m.theme or m.backup
                or m.entry is None
                or m.round_name not in (self._playlist or {})):
            return False
        slot_dance = m.dance
        if not slot_dance or slot_dance not in self._dynamic_dances:
            return False
        old = m.entry
        if (getattr(entry, "path", None) and getattr(old, "path", None)
                and self._same_path(str(entry.path), str(old.path))):
            return False   # the same track already sits here — nothing to replace
        # Dance-mismatch guard, mirroring the static-deck replace.
        drop_dance = self._drop_dance(entry)
        if drop_dance and drop_dance != slot_dance:
            a = dance_name(drop_dance, drop_dance)
            b = dance_name(slot_dance, slot_dance)
            ans = QMessageBox.question(
                self, "Different dance",
                i18n.t("“%s” looks like a %s track, but this slot is %s.\n\nReplace anyway?")
                % (entry.title, a, b),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return False
        # Block a duplicate that lives in ANOTHER slot; the one being overwritten is fine.
        dup = self._find_duplicate(entry)
        if dup is not None and dup[1] is not old:
            _show_toast(self, i18n.t("⚠  “%s” is already in this playlist — not replaced")
                        % entry.title)
            return False
        heats = self._playlist[m.round_name]
        d_idx = self._dynamic_dances.index(slot_dance)
        if not (m.h_idx < len(heats)):
            return False
        heat = heats[m.h_idx]
        if d_idx >= len(heat):
            return False
        heat[d_idx] = entry
        return True

    def _fill_existing_empty_slot(self, dance: str, entry: MusicEntry) -> bool:
        """Drop `entry` into the first EXISTING empty slot of `dance`, scanning the
        rounds in progression order then heats top-to-bottom. Never adds a heat;
        returns True only when a free slot took the track."""
        if not self._playlist or dance not in self._dynamic_dances:
            return False
        d_idx = self._dynamic_dances.index(dance)
        for rname, _cap in self._dynamic_specs():
            skip = self._round_skip_dances.get(rname)
            if skip and dance in skip:
                continue
            heats = self._playlist.get(rname)
            if not heats:
                continue
            for h in heats:
                if d_idx < len(h) and h[d_idx] is None:
                    h[d_idx] = entry
                    return True
        return False

    def _dynamic_extend_round(self, rname: str, dance: str, entry: MusicEntry):
        """Targeted drop into round `rname`: fill the round's first EMPTY slot for
        this dance; only when none is left does a fresh heat get added (empty slots
        for every other dance). The full final round stacks extras as backups."""
        # Dropping this dance back in un-hides it if it had been removed from the round.
        skip = self._round_skip_dances.get(rname)
        if skip:
            skip.discard(dance)
        d_idx = self._dynamic_dances.index(dance)
        heats = (self._playlist or {}).get(rname)
        if heats is None:
            self._playlist[rname] = [self._new_heat()]
            self._playlist[rname][0][d_idx] = entry
            return
        for h in heats:
            if d_idx < len(h) and h[d_idx] is None:
                h[d_idx] = entry
                return
        order = [n for n, _ in self._dynamic_specs()]
        if order and rname == order[-1]:
            self._add_backup(rname, len(heats) - 1, d_idx, entry)
            return
        heats.append(self._new_heat())
        heats[-1][d_idx] = entry

    def _dynamic_autofill(self, dance: str, entry: MusicEntry):
        """Place a track into the first round with free capacity for its dance; spill
        into the next round when full. The final round stacks extras as backups."""
        d_idx = self._dynamic_dances.index(dance)
        specs = self._dynamic_specs()
        final_i = len(specs) - 1
        for i, (rname, cap) in enumerate(specs):
            is_final = (i == final_i)
            heats = (self._playlist or {}).get(rname)
            if heats is None:
                self._playlist[rname] = [self._new_heat()]
                self._playlist[rname][0][d_idx] = entry
                return
            filled = sum(1 for h in heats if d_idx < len(h) and h[d_idx] is not None)
            if not is_final and filled >= cap:
                continue
            for h in heats:
                if h[d_idx] is None:
                    h[d_idx] = entry
                    return
            if is_final:
                self._add_backup(rname, len(heats) - 1, d_idx, entry)
                return
            heats.append(self._new_heat())
            heats[-1][d_idx] = entry
            return
        # Every round full → stack onto the final round as a backup.
        rname = specs[final_i][0]
        heats = self._playlist.setdefault(rname, [self._new_heat()])
        self._add_backup(rname, len(heats) - 1, d_idx, entry)

    def _add_backup(self, rname: str, h_idx: int, d_idx: int, entry: MusicEntry):
        self._dynamic_backups.setdefault((rname, h_idx, d_idx), []).append(entry)

    def _remove_dynamic_heat(self, row: int):
        """Remove a whole heat (one grid row across every dance) in dynamic mode.
        Empties the round if it was the last heat; backups re-key to follow."""
        if not self._dynamic or not (0 <= row < len(self._row_meta)):
            return
        meta = self._row_meta[row]
        if not meta or meta.backup:
            return
        rname = meta.round_name
        h_idx = meta.h_idx
        heats = (self._playlist or {}).get(rname)
        if heats is None or not (0 <= h_idx < len(heats)):
            return
        if not self._confirm_delete(
                "Remove heat",
                i18n.t("Remove this whole heat (all dances) from %s?") % rname):
            return
        if self._current_play_row == row and self._play_cb:
            self._play_cb(None)
            self._current_play_row = -1
        moved = self._move_up_from_heat(heats, h_idx)
        del heats[h_idx]
        if moved:
            _show_toast(self, i18n.t("⬆  %d song(s) moved up into empty slots") % moved)
        if heats:
            # Round keeps other heats → just re-key its backups around the gap.
            self._reindex_backups_for_heat(rname, h_idx)
        elif not self._promote_backups_to_heats(rname):
            # Last heat gone and no backups to take its place → drop the round, then
            # re-progress the remaining round names (Vorrunde, Zwischenrunde…, Finale).
            self._playlist.pop(rname, None)
            self._resync_dynamic_rounds()
        self._rebuild_dynamic()

    @staticmethod
    def _move_up_from_heat(heats: list, h_idx: int) -> int:
        """Before heat `h_idx` goes: move each of its titles into the first empty
        slot of the same dance in another heat of the round, so shrinking a round
        only drops titles that have no room left. Returns how many moved."""
        moved = 0
        for d_idx, entry in enumerate(heats[h_idx]):
            if entry is None:
                continue
            for i, h in enumerate(heats):
                if i != h_idx and d_idx < len(h) and h[d_idx] is None:
                    h[d_idx] = entry
                    moved += 1
                    break
        return moved

    def _add_dynamic_heat(self, row: int):
        """Append one empty heat (a blank slot for every dance) to the round the
        clicked row belongs to — the counterpart of _remove_dynamic_heat, so a
        loaded playlist can grow heat by heat. Works from a heat, a backup, OR a
        round/dance header row (round resolved via _round_of_row)."""
        if not self._dynamic:
            return
        rname = self._round_of_row(row)
        heats = (self._playlist or {}).get(rname)
        if heats is None:
            return
        heats.append(self._new_heat())
        self._rebuild_dynamic()

    def _remove_dynamic_round(self, row: int):
        """Remove an ENTIRE round (all its heats and stacked backups) in dynamic
        mode — the largest-scope shrink. The remaining rounds are renamed back to
        the standard progression (Vorrunde, Zwischenrunde…, Finale)."""
        if not self._dynamic:
            return
        rname = self._round_of_row(row)
        if rname is None or rname not in (self._playlist or {}):
            return
        n_heats = len(self._playlist[rname])
        if not self._confirm_delete(
                "Remove round",
                i18n.t("Remove the entire round “%s” and all %d of its heats?") % (rname, n_heats)):
            return
        if self._current_play_row == row and self._play_cb:
            self._play_cb(None)
            self._current_play_row = -1
        self._playlist.pop(rname, None)
        # Drop this round's stacked backups; _resync re-keys the survivors' backups.
        self._dynamic_backups = {k: v for k, v in self._dynamic_backups.items()
                                 if k[0] != rname}
        self._resync_dynamic_rounds()
        self._rebuild_dynamic()

    def _remove_dance_from_round(self, round_name: str, dance: str):
        """Remove ONE dance from a SINGLE round (e.g. Quickstep out of the Vorrunde):
        empty all of that dance's slots in this round, drop its stacked backups here,
        and hide its row for this round only — the heats and every other dance stay.
        Other rounds keep the dance. Dragging the dance back into the round restores it."""
        if not self._dynamic or self._playlist is None:
            return
        heats = self._playlist.get(round_name)
        if heats is None or dance not in self._dynamic_dances:
            return
        d_idx = self._dynamic_dances.index(dance)
        dn = dance_name(dance, dance)
        n = sum(1 for h in heats if d_idx < len(h) and h[d_idx] is not None)
        msg = (i18n.t("Remove %s from %s?\n%d song(s) in this round will be cleared.")
               % (dn, round_name, n)
               if n else i18n.t("Hide the empty %s from %s?") % (dn, round_name))
        if not self._confirm_delete("Remove dance", msg):
            return
        # Stop playback if the playing row is one of the slots about to be cleared.
        cpr = self._current_play_row
        if 0 <= cpr < len(self._row_meta) and self._play_cb:
            cm = self._row_meta[cpr]
            if cm and cm.round_name == round_name and cm.dance == dance:
                self._play_cb(None)
                self._current_play_row = -1
        for h in heats:
            if d_idx < len(h):
                h[d_idx] = None
        self._dynamic_backups = {k: v for k, v in self._dynamic_backups.items()
                                 if not (k[0] == round_name and k[2] == d_idx)}
        self._round_skip_dances.setdefault(round_name, set()).add(dance)
        self._rebuild_dynamic()

    def _remove_dance_everywhere(self, dance: str):
        """Remove ONE dance from EVERY round and heat: empty all its slots, drop its
        backups, and hide its row in all rounds. The heats and other dances stay.
        Dragging the dance back into a round restores it for that round."""
        if not self._dynamic or self._playlist is None:
            return
        if dance not in self._dynamic_dances:
            return
        d_idx = self._dynamic_dances.index(dance)
        dn = dance_name(dance, dance)
        n = sum(1 for heats in self._playlist.values()
                for h in heats if d_idx < len(h) and h[d_idx] is not None)
        msg = (i18n.t("Remove %s from all rounds and heats?\n"
                      "%d song(s) across the playlist will be cleared.") % (dn, n)
               if n else i18n.t("Hide the empty %s from all rounds?") % dn)
        if not self._confirm_delete("Remove dance", msg):
            return
        # Stop playback if the playing row is a slot of this dance.
        cpr = self._current_play_row
        if 0 <= cpr < len(self._row_meta) and self._play_cb:
            cm = self._row_meta[cpr]
            if cm and cm.dance == dance:
                self._play_cb(None)
                self._current_play_row = -1
        for round_name, heats in self._playlist.items():
            for h in heats:
                if d_idx < len(h):
                    h[d_idx] = None
            self._round_skip_dances.setdefault(round_name, set()).add(dance)
        self._dynamic_backups = {k: v for k, v in self._dynamic_backups.items()
                                 if k[2] != d_idx}
        self._rebuild_dynamic()

    def _reindex_backups_for_heat(self, rname: str, removed: int):
        """After deleting heat `removed` from round `rname`, drop that heat's backups
        and shift the backups of later heats down by one."""
        rekeyed: dict[tuple[str, int, int], list[MusicEntry]] = {}
        for (r, hi, di), entries in self._dynamic_backups.items():
            if r != rname:
                rekeyed[(r, hi, di)] = entries
            elif hi == removed:
                continue
            else:
                rekeyed[(r, hi - 1 if hi > removed else hi, di)] = entries
        self._dynamic_backups = rekeyed

    def _promote_backups_to_heats(self, rname: str) -> bool:
        """Rebuild an emptied final round's heats from its stacked backups (each
        dance's backups become successive heats). Returns False if there were none."""
        per_dance: dict[int, list[MusicEntry]] = {}
        for (r, _hi, di), entries in list(self._dynamic_backups.items()):
            if r == rname:
                per_dance.setdefault(di, []).extend(entries)
                self._dynamic_backups.pop((r, _hi, di), None)
        if not per_dance:
            return False
        n_heats = max(len(v) for v in per_dance.values())
        heats = [self._new_heat() for _ in range(n_heats)]
        for di, entries in per_dance.items():
            for j, ent in enumerate(entries):
                heats[j][di] = ent
        self._playlist[rname] = heats
        return True

    def _discard_backup_entry(self, meta) -> bool:
        """Drop the single backup entry described by a '↳ backup N' row's `meta` from
        the `_dynamic_backups` overlay (matched by identity, else by path). Returns True
        if it was found and removed. Does NOT re-render — callers do that once."""
        key = (meta.round_name, meta.h_idx, meta.d_idx)
        entry = meta.entry
        lst = self._dynamic_backups.get(key)
        if not lst:
            return False
        for i, e in enumerate(lst):
            if e is entry or (e is not None and entry is not None
                              and str(e.path) == str(entry.path)):
                del lst[i]
                break
        else:
            return False
        if not lst:
            self._dynamic_backups.pop(key, None)
        return True

    def _remove_dynamic_backup(self, row: int):
        """Remove a single stacked backup (final-round '↳ backup N' row)."""
        if not self._dynamic or not (0 <= row < len(self._row_meta)):
            return
        meta = self._row_meta[row]
        if not meta or not meta.backup:
            return
        if not self._confirm_delete("Remove backup", "Remove this backup song?"):
            return
        if self._current_play_row == row and self._play_cb:
            self._play_cb(None)
            self._current_play_row = -1
        if self._discard_backup_entry(meta):
            self._rebuild_dynamic()

    def _remove_empty_dynamic_slot(self, row: int):
        """Clear a single empty (no-song) heat slot from the context menu. If a backup is
        stacked under it, that backup steps up to fill the slot — the whole point of a
        stand-in; otherwise the dance's empty slot is dropped from this round."""
        if not self._dynamic or not (0 <= row < len(self._row_meta)):
            return
        meta = self._row_meta[row]
        if not meta or meta.backup or meta.entry is not None:
            return
        rname = meta.round_name
        dance = meta.dance
        if rname is None or self._playlist is None:
            return
        key = (rname, meta.h_idx, meta.d_idx)
        backups = self._dynamic_backups.get(key)
        if backups:
            self._playlist[rname][meta.h_idx][meta.d_idx] = backups.pop(0)
            if not backups:
                self._dynamic_backups.pop(key, None)
            self._rebuild_dynamic()
            _show_toast(self, "⬆  Backup moved up into the empty slot")
            return
        if dance:
            self._remove_dance_from_round(rname, dance)

    def _append_dynamic_round(self) -> str:
        """Manually add one empty round to the dynamic deck (it becomes the new last
        round). All rounds are then re-named to the standard dancesport progression
        for the new count (Vorrunde, Zwischenrunde…, Halbfinale, Finale) — so adding
        rounds never produces 'Finale (2)'. Returns the new round's name."""
        return self._insert_dynamic_round(None)

    def _insert_dynamic_round(self, after_row: int | None) -> str:
        """Add one empty round to the dynamic deck. If `after_row` points at a round,
        the new round is inserted directly AFTER that round; otherwise it is appended
        last. Either way every round is then re-named positionally to the standard
        progression (Vorrunde, Zwischenrunde…, Halbfinale, Finale) — so inserting from
        the Vorrunde grows the front, and inserting from the Finale pushes the old
        final down to Halbfinale and makes the new round the Finale. Returns the new
        round's name."""
        if not self._dynamic:
            return ""
        if self._playlist is None:
            self._playlist = {}
        new_key = f"__new_{len(self._playlist)}"
        after_name = (self._round_of_row(after_row)
                      if after_row is not None else None)
        if after_name is not None and after_name in self._playlist:
            pos = list(self._playlist.keys()).index(after_name) + 1
        else:
            pos = len(self._playlist)
        # A manually-added round always starts with a single empty heat — the user
        # grows it with "Add a heat to this round" as needed. (The Rounds field only
        # sizes auto-generated rounds; hand-building is fully explicit so e.g. a
        # 1-heat Vorrunde + 1-heat Finale takes just two clicks.)
        default_cap = 1
        rounds = list(self._playlist.keys())
        rounds.insert(pos, new_key)
        self._playlist[new_key] = [self._new_heat() for _ in range(default_cap)]
        self._playlist = {k: self._playlist[k] for k in rounds}
        caps = list(self._dynamic_capacity)
        caps.insert(pos, default_cap)
        self._dynamic_capacity = caps
        self._resync_dynamic_rounds()       # renames new_key → its positional name
        self._rebuild_dynamic()
        keys = list(self._playlist.keys())
        new_name = keys[pos] if 0 <= pos < len(keys) else (keys[-1] if keys else "")
        self._focus_round(new_name)         # move the view/selection to the new round
        return new_name

    def _focus_round(self, name: str):
        """Scroll the new/target round into view and select its header row, so the
        focus follows the round just created instead of staying where it was."""
        rows = [r for r in self._round_hdr_rows
                if self._row_round_name.get(r) == name]
        if not rows:
            # 🚫 No-grouping view: there is no header row — take the round's
            # first song row instead, so the focus still follows the round.
            rows = [r for r, m in enumerate(self._row_meta)
                    if m and m.round_name == name]
        if not rows:
            return
        row = min(rows)
        item = self.item(row, 0)
        if item is not None:
            self.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        self.clearSelection()
        self.setCurrentCell(row, 0)

    def _resync_dynamic_rounds(self):
        """Keep the dynamic structure self-consistent: the capacity pattern tracks the
        round count, and rounds are renamed positionally to the standard progression
        (`ROUND_NAMES[count]`: Vorrunde, Zwischenrunde…, Halbfinale, Finale). Heat
        contents and stacked backups follow their round to the new name."""
        rounds = list((self._playlist or {}).keys())
        n = len(rounds)
        # Capacity length tracks the round count (pad with the last value, else trim).
        caps = list(self._dynamic_capacity)
        last = caps[-1] if caps else 1
        if n > len(caps):
            caps += [max(1, last)] * (n - len(caps))
        self._dynamic_capacity = caps[:n]
        if n == 0:
            return
        names = ROUND_NAMES.get(n, [f"Runde {i + 1}" for i in range(n)])
        if rounds == names[:n]:
            return   # already correctly named
        mapping = {old: names[i] for i, old in enumerate(rounds)}
        self._playlist = {names[i]: self._playlist[old]
                          for i, old in enumerate(rounds)}
        if self._dynamic_backups:
            self._dynamic_backups = {
                (mapping.get(r, r), h, d): v
                for (r, h, d), v in self._dynamic_backups.items()}
        if self._round_skip_dances:
            self._round_skip_dances = {
                mapping.get(r, r): v for r, v in self._round_skip_dances.items()}

    def _dance_style(self, dance: str | None) -> str | None:
        """Competition style ('Standard'/'Latin'/'Others') a dance code belongs to,
        or None if unknown. Built from planner.DEFAULT_DANCES (S-class = full set)."""
        if not dance:
            return None
        for st in ("Standard", "Latin", "Others"):
            if dance in planner.models.DEFAULT_DANCES.get(st, {}).get("S", ()):
                return st
        return None

    def _confirm_cross_style(self, entries: list[MusicEntry]) -> bool:
        """Dropping track(s) whose dance belongs to a different competition style than
        this deck (e.g. a Standard dance onto a Latin list) confirms once before
        placing. Returns True to proceed, False to cancel the whole drop. Only guards
        Standard ⇄ Latin decks; an 'Others' deck mixes social dances freely."""
        deck_style = self._style
        if deck_style not in ("Standard", "Latin"):
            return True
        foreign: dict[str, int] = {}
        for ent in entries:
            dance = self._drop_dance(ent)
            st = self._dance_style(dance)
            if st and st != deck_style:
                foreign[st] = foreign.get(st, 0) + 1
        if not foreign:
            return True
        other = " / ".join(sorted(foreign))
        n = sum(foreign.values())
        ans = QMessageBox.question(
            self, "Different style",
            i18n.t("%d dropped track(s) look like %s dances, but this is a "
                   "%s list.\n\nAdd them anyway?") % (n, other, deck_style),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return ans == QMessageBox.StandardButton.Yes

    def _dynamic_drop(self, e, target_row: int, replace: bool = False):
        """Resolve and place every dropped track, then re-render the grid once.

        `replace` (Ctrl held): the FIRST track overwrites the song in the OCCUPIED
        slot under the cursor instead of filling the next free slot / adding a heat;
        any extra tracks of a multi-drop fall back to the normal top-up behaviour."""
        if self._suggester is None:
            self.host.ensure_deck_ready()
        entries = self._collect_drop_entries(e)
        if not entries:
            _show_toast(self, "Couldn't read the dropped track(s).")
            return
        if not self._confirm_cross_style(entries):
            return
        if not self._dynamic:
            self._enter_dynamic_from_drop()
            # An empty/cleared deck adopts the style of its first drop, so the
            # cross-style guard re-arms for any later foreign-style tracks.
            if not self._style:
                styles = [self._dance_style(self._drop_dance(en))
                          for en in entries]
                styles = [s for s in styles if s]
                if styles:
                    self._style = max(set(styles), key=styles.count)
        if self._playlist is None:
            self._playlist = {}
        # Ctrl + drop on a filled slot: the first track REPLACES the song there.
        m0 = self._row_meta[target_row] if 0 <= target_row < len(self._row_meta) else None
        replace_first = (replace and m0 and not m0.theme
                         and not m0.backup and m0.entry is not None)
        placed = replaced = 0
        skipped: dict[str, list] = {}   # why it stayed out → the tracks
        landed = []   # the entry objects that actually went into the grid
        for i, ent in enumerate(entries):
            if i == 0 and replace_first:
                # A cancelled dance-mismatch / blocked duplicate just drops the track;
                # it must NOT silently add a heat instead of the asked-for replace.
                if self._dynamic_replace_slot(target_row, ent):
                    placed += 1
                    replaced += 1
                    landed.append(ent)
                continue
            # Only the first track is aimed at the cursor slot; the rest top up the
            # deck's existing empty slots of their dance before any heat is added.
            why = self._dynamic_place_one(ent, target_row, prefer_existing=(i > 0))
            if why:
                skipped.setdefault(why, []).append(ent)
            else:
                placed += 1
                landed.append(ent)
        if placed:
            self._rebuild_dynamic()
            self._notify_changed()
            # Instant Check-Music on the landed rows (resolved AFTER the rebuild
            # re-created the grid) — play length / takt issues mark the rows red.
            rows = [r for r, m in enumerate(self._row_meta)
                    if m and any(m.entry is en for en in landed)]
            if rows:
                QTimer.singleShot(0, lambda: self._mark_drop_issues(rows))
            if replaced and placed == replaced:
                msg = i18n.t("🔁  Replaced %d track(s)") % replaced
            elif replaced:
                msg = (i18n.t("🔁  Replaced %d, ➕ added %d track(s)")
                       % (replaced, placed - replaced))
            else:
                msg = i18n.t("➕  Added %d track(s)") % placed
            if skipped:
                msg += i18n.t("  (%s — skipped)") % self._skipped_tail(skipped)
            _show_toast(self, msg)
        elif skipped:
            _show_toast(self, self._nothing_added(skipped))

    @staticmethod
    def _skipped_tail(skipped: dict) -> str:
        """"2 already planned, 1 with no dance" — what a drop left behind."""
        parts = []
        if skipped.get("dup"):
            parts.append(i18n.t("%d already planned") % len(skipped["dup"]))
        if skipped.get("dance"):
            parts.append(i18n.t("%d with no dance") % len(skipped["dance"]))
        return ", ".join(parts)

    def _nothing_added(self, skipped: dict) -> str:
        """Why a drop placed nothing. A single track is worth naming — "already
        planned" over a track that is nowhere in the list is the kind of answer
        that sends somebody looking for it."""
        dups, no_dance = skipped.get("dup", []), skipped.get("dance", [])
        if len(dups) + len(no_dance) == 1:
            if no_dance:
                return (i18n.t("⚠  Couldn't tell what dance “%s” is — nothing added")
                        % no_dance[0].title)
            return (i18n.t("⚠  “%s” is already in this playlist — nothing added")
                    % dups[0].title)
        return i18n.t("Nothing added — %s") % self._skipped_tail(skipped)

    def _rebuild_dynamic(self):
        """Re-render the dynamic grid from the working `_playlist` + backups.
        Keeps the current scroll offset so edits don't jump the view to the top."""
        scroll = self.verticalScrollBar().value()
        self.load(
            self._playlist or {}, list(self._dynamic_dances),
            self._dynamic_round_configs(), self._dance_class,
            play_cb=self._play_cb, suggester=self._suggester,
            use_timbre=self._use_timbre, style=self._style,
            dynamic=True, capacity=list(self._dynamic_capacity),
            backups=dict(self._dynamic_backups),
            round_skip_dances={k: set(v) for k, v in self._round_skip_dances.items()},
            marked=set(self._marked_paths),
        )
        self._restore_scroll(scroll)

    def _reselect_song(self, path: str) -> bool:
        """Put the selection back on `path` after a re-render renumbered the rows.

        False when there was no selected song, or it is not in the list any more —
        then the caller falls back to restoring the old scroll position."""
        if not path:
            return False
        for row, r in self._row_meta.numbered():
            if r.path_str == path:
                self._focus_row(row, focus=False)
                return True
        return False

    def set_grouping(self, state: int):
        """Header view of this table, re-rendered in place: 0 = all headers,
        1 = 🗜 compact (no per-dance headers), 2 = 🚫 no grouping (no round /
        ─── section headers either), 3 = 🔢 numbers (no grouping plus the Nb.
        column). Flat lists have no headers to drop."""
        compact = state >= 1
        nogroup = state >= 2
        self.set_numbered(state >= 3)
        if compact == self._compact and nogroup == self._nogroup:
            return
        self._compact = compact
        self._nogroup = nogroup
        # Dropping or restoring header rows renumbers everything under them, so the
        # selected row number would end up on whatever slid into its place. Follow
        # the song instead of the row number.
        cur = self._row_meta.at(self.currentRow())
        keep = cur.path_str if cur is not None else ""
        if self._warmup:
            self._reload_warmup()   # its ─── headers are cut during load_warmup
            self._reselect_song(keep)
            return
        if self._flat_mode or self._playlist is None:
            return   # nothing with headers to re-render
        scroll = self.verticalScrollBar().value()
        if self._dynamic:
            self._rebuild_dynamic()
        else:
            rounds = list(self._loaded_rounds)
            pools = ([self._round_pools_by_name.get(rc.name, []) for rc in rounds]
                     if self._round_pools_by_name else None)
            self.load(self._playlist, list(self._loaded_dances), rounds,
                      self._dance_class, play_cb=self._play_cb,
                      suggester=self._suggester, use_timbre=self._use_timbre,
                      style=self._style, round_pools=pools)
        if self._reselect_song(keep):
            return   # _focus_row scrolled the song into view already
        self._restore_scroll(scroll)

