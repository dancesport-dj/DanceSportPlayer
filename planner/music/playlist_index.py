"""What the past playlists say about a track: the playlist index of MusicLibrary.

The M3U tree is read into a co-occurrence index (which lists a track sits in,
which of them were finals or semifinals, the start class of each list), and
each entry's popularity is worked out from it. MusicLibrary inherits this as
PlaylistIndexMixin; the scan, the entries and the similarity queries stay in
planner.music.library.
"""

import copy
import hashlib
import logging
import os
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from planner.config import (  # auto-resolved
    folders_below,
    playlist_dir,
)
from planner.event.competition import (  # auto-resolved
    is_side_list,
    is_superseded_playlist,
    round_stages_in_name,
)
from planner.models import (  # auto-resolved
    MusicEntry,
)
from planner.music.parsing import (  # auto-resolved
    LIBRARY_EXTS,
    _title_key,
    detect_dance,
    norm_title,
    playlist_class_of,
    song_title_key,
    song_title_key_of_stem,
    stem_key,
    title_key_of_stem,
)
from planner.music.scan_caches import (
    PlaylistIndexCache,
)
from planner.playlist.playlist_text import PlaylistEncodingError, read_playlist_text

if TYPE_CHECKING:
    from planner.music.library import MusicLibrary

log = logging.getLogger("dancesport.library")


def warn_unreadable(m3u: Path, exc: PlaylistEncodingError) -> None:
    """A playlist left out of a folder walk because its text can't be decoded
    without losing characters — said out loud, not skipped in silence."""
    log.warning("⚠️ Playlist skipped, not read\n"
                "file: %s\n"
                "reason: %s", m3u, exc)


def _is_warmup_list_name(name: str) -> bool:
    """Playlist / folder names that mark warm-up, party or seasonal lists — those
    never count for popularity or co-occurrence."""
    return is_side_list(name)


# (path, "mtime:size") for one file under the playlist dir.
_TreeFile = tuple[Path, str]


def _playlist_tree() -> tuple[list[_TreeFile], list[_TreeFile]]:
    """One walk over PLAYLIST_DIR returning its .m3u files and its music files
    (LIBRARY_EXTS: MP3, FLAC, M4A, Ogg, Opus) with a change signature each.

    Both learners used to `rglob` the tree themselves (three walks in total). One
    `os.scandir` pass costs ~0.03 s for 2100 files INCLUDING the stat, because a
    Windows directory entry already carries mtime and size — so the signature that
    tells `PlaylistIndexCache` what actually changed is essentially free.
    """
    m3us: list[_TreeFile] = []
    mp3s: list[_TreeFile] = []
    stack = [str(playlist_dir())]
    while stack:
        try:
            with os.scandir(stack.pop()) as it:
                entries = list(it)
        except OSError:
            continue
        for de in entries:
            try:
                if de.is_dir(follow_symlinks=False):
                    stack.append(de.path)
                    continue
                low = de.name.lower()
                bucket = (m3us if low.endswith((".m3u", ".m3u8"))
                          else mp3s if low.endswith(LIBRARY_EXTS) else None)
                if bucket is not None:
                    st = de.stat()
                    bucket.append((Path(de.path), f"{st.st_mtime_ns}:{st.st_size}"))
            except OSError:
                continue
    m3us.sort()
    mp3s.sort()
    return m3us, mp3s


# A 4-digit year in a playlist path ('Turnier 2019 …') — the only date a plain
# M3U carries, and what 'last played' is read from.
_PLAYLIST_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


def playlist_year(path_str: str) -> int | None:
    """Newest year in a playlist's path, None when it carries no date."""
    years = [int(m.group(0)) for m in _PLAYLIST_YEAR_RE.finditer(path_str)]
    return max(years) if years else None


# Round stages as `_round_stages_in_name` numbers them: 50 is the Halbfinale,
# 60 the Endrunde. Those two are the rounds worth remembering — they are the
# ones a DJ picks by hand, one track per dance.
_SEMI_STAGE = 50
_FINAL_STAGE = 60

# A trailing block only counts as a round when the list uses at least this many
# dances. A one- or two-line list has a "last round without a repeated dance"
# too, and it says nothing at all about who danced a final.
_FINAL_MIN_DANCES = 3


def _split_last_round(lines: list[str], dances: list[str | None],
                      known: set[str]) -> tuple[list[str], list[str]]:
    """(the last round in `lines`, everything before it) — ([], lines) if there
    is none.

    A round is one pass through the dances, so it is the trailing run in which
    no dance comes up twice, and it only counts when that run covers EVERY dance
    the list uses. A preliminary laid out in heats ends on two of the same dance,
    so its run stops early and is correctly not read as a round of its own.

    Lines whose dance could not be worked out neither break the run nor have to
    be covered by it — about one line in twenty is one of those, and letting a
    single unrecognised filename veto the round cost more than half the finals
    in the real tree."""
    seen: set[str] = set()
    tail: list[str] = []
    for line, dance in zip(reversed(lines), reversed(dances), strict=True):
        if dance in seen:
            break
        if dance:
            seen.add(dance)
        tail.append(line)
    if seen != known:
        return [], lines
    return list(reversed(tail)), lines[:len(lines) - len(tail)]


def _named_stage(name: str) -> int | None:
    """The one round a playlist's own name declares, or None.

    'HGR S Lat Finale' is a final and nothing else; a name that lists several
    rounds ('VR-ZR-ER') holds all of them, so it is treated like a silent one
    and sectioned by position instead."""
    stages = round_stages_in_name(name)
    return stages[0] if len(stages) == 1 else None


def dq(dance: str | None, key: str) -> str:
    """Namespace a title-derived match key by its dance so same-title, different-dance
    tracks don't collapse together. `_clean_title` strips the leading dance code, so
    'QS - No Roots' and 'TG - No Roots' both reduce to 'no roots' — without this they
    would share popularity. The full-filename stem key already carries the dance, so it
    stays plain. Dance unknown → the bare key (best effort, as before)."""
    return f"{dance}\x1f{key}" if dance else key


# What `_apply_popularity` sets on an entry — copied over by `adopt_playlist_index`.
_POPULARITY_FIELDS = ("popularity", "class_plays", "final_plays", "semi_plays",
                      "last_played", "source_info")


class LearnedPlaylistIndex(NamedTuple):
    """A playlist index built off the library (`learn_playlist_index`), waiting
    to be swapped in (`adopt_playlist_index`)."""
    playlists: int                   # playlists analyzed
    scratch: PlaylistIndexMixin    # holds the new index dicts
    values: list[tuple[MusicEntry, dict[str, Any]]]   # entry → popularity fields


class PlaylistIndexMixin:
    """🎼 The playlist index of MusicLibrary: learning it, sharing it, reading it."""

    # Set up by MusicLibrary.__init__, see there.
    _track_playlists: dict[str, set[str]]
    _playlist_cls: dict[str, str | None]
    _playlist_year: dict[str, int | None]
    _track_finals: dict[str, set[str]]
    _track_semis: dict[str, set[str]]
    _stem_dance: dict[str, str | None]
    _line_key_memo: dict[str, set[str]]

    if TYPE_CHECKING:
        @property
        def entries(self) -> list[MusicEntry]: ...

    def _dance_map_digest(self) -> str:
        """Fingerprint of the stem → dance map `_line_keys` qualifies its keys by.

        The cached keys of an untouched playlist are only still correct while this
        is unchanged — see `PlaylistIndexCache`."""
        h = hashlib.blake2b(digest_size=16)
        for stem in sorted(self._stem_dance):
            h.update(f"{stem}\x1f{self._stem_dance[stem] or ''}\n".encode("utf-8", "ignore"))
        return h.hexdigest()

    def _index_playlist(self, cache: PlaylistIndexCache, pl_id: str, sig: str,
                        derive: Callable[[], tuple[str | None, list[str],
                                                   list[str], list[str]]]
                        ) -> None:
        """Fold one playlist into the co-occurrence index, from cache when it has
        not changed on disk. `derive` is only called on a miss."""
        hit = cache.get(pl_id, sig)
        if hit is None:
            hit = derive()
            cache.put(pl_id, sig, *hit)
        cls, keys, final_keys, semi_keys = hit
        self._playlist_cls[pl_id] = cls
        for k in keys:
            self._track_playlists[k].add(pl_id)
        for k in final_keys:
            self._track_finals[k].add(pl_id)
        for k in semi_keys:
            self._track_semis[k].add(pl_id)

    def _learn_playlists(self) -> int:
        count = 0
        root = playlist_dir()
        if not root.exists():
            return count
        self._refresh_stem_dance()   # so lines qualify by the file's calculated dance
        m3us, mp3s = _playlist_tree()
        cache = PlaylistIndexCache(root, self._dance_map_digest())
        seen: set[str] = set()
        failed = 0
        for m3u, sig in m3us:
            try:
                if is_superseded_playlist(m3u):
                    continue
                count += 1
                # Eintanzen playlists count for nothing — neither popularity nor
                # co-occurrence — so they are never even read.
                if _is_warmup_list_name(m3u.stem):
                    continue
                pl_id = str(m3u)
                seen.add(pl_id)
                self._index_playlist(
                    cache, pl_id, sig,
                    lambda: (playlist_class_of(m3u), *self._m3u_keys(m3u)))
            except Exception as exc:
                # One bad file must not cost the others, but it leaves a trace.
                failed += 1
                log.debug("⚠️ Playlist not learned\n"
                          "file: %s\n"
                          "reason: %r", m3u, exc)
        if failed:
            log.info("  ⚠️ %s playlist(s) skipped while learning, see the debug log",
                     failed)
        count += self._learn_playlist_folders(cache, seen, m3us, mp3s)
        cache.prune(seen)
        cache.save()
        return count

    def _m3u_keys(self, m3u: Path) -> tuple[list[str], list[str], list[str]]:
        """Every match key the lines of one playlist file derive, and the subsets
        of them that were danced in its FINAL and in its SEMIFINAL round.

        Dance-qualified (stem + title + aggressive song-title) so 'jive(43) - Bim
        Bam', '16 Bim Bam' and 'Bim Bam' map together within a dance, while 'No
        Roots' QS vs TG stay apart — see `_line_keys` / `_dq`. Renamed / moved
        files still match, because no key is a path.

        An OSError (a file locked by another program, a share briefly away) is
        raised, not read as an empty list: the index caches what this returns
        under the file's mtime, so an empty answer would stick until the file
        changed. `_learn_playlists` skips the file and tries it next time."""
        try:
            raw = read_playlist_text(m3u)[0].splitlines()
        except PlaylistEncodingError as exc:
            warn_unreadable(m3u, exc)
            return [], [], []
        lines = [ln.strip() for ln in raw
                 if ln.strip() and not ln.strip().startswith('#')]
        return self._keys_and_rounds(m3u.stem, lines)

    def _folder_keys(self, folder: Path, files: list[_TreeFile]
                     ) -> tuple[list[str], list[str], list[str]]:
        """`_m3u_keys` for a tournament folder — the copied files ARE its lines."""
        return self._keys_and_rounds(folder.name, [str(mp3) for mp3, _sig in files])

    def _keys_and_rounds(self, name: str, lines: list[str]
                         ) -> tuple[list[str], list[str], list[str]]:
        """(all match keys, the final's, the semifinal's) for one playlist's lines.

        Two things say which round a line belongs to, and both are needed here:
        the NAME, when the list is one round ('… Finale.m3u', a 'Finale' folder),
        and otherwise the POSITION, because most saved lists hold a whole
        competition back to back — see `_late_lines`."""
        keys: set[str] = set()
        for line in lines:
            keys |= self._line_keys(line)
        stage = _named_stage(name)
        if stage is not None:
            final_lines = lines if stage == _FINAL_STAGE else []
            semi_lines = lines if stage == _SEMI_STAGE else []
        else:
            final_lines, semi_lines = self._late_lines(lines)

        def _keys_of(block: list[str]) -> set[str]:
            out: set[str] = set()
            for line in block:
                out |= self._line_keys(line)
            return out

        return sorted(keys), sorted(_keys_of(final_lines)), sorted(_keys_of(semi_lines))

    def _late_lines(self, lines: list[str]) -> tuple[list[str], list[str]]:
        """(final, semifinal) of a list that holds a whole competition.

        A saved competition reads SA SA CC CC … | SA CC RB PD JI | SA CC RB PD JI
        — the heats first, then the two rounds that are danced once through. So
        the final is the last full pass (`_split_last_round`) and the semifinal
        is the one before it. A preliminary never reaches back that far: its heats
        repeat the dances, the run stops early, and nothing is claimed.

        What sits before the final is not always a Halbfinale by name — in a
        three-round event it is the Zwischenrunde. It is picked the same way a
        semifinal is, one track per dance, so it counts as one.

        The guess is deliberately generous: two independent lists are needed
        before anything acts on it (`planner.generate.scoring._FINAL_MIN_PLAYS`), so a
        stray misread washes out, while a miss is a fact nothing can recover."""
        dances = [self._line_dance(line) for line in lines]
        known = {d for d in dances if d}
        if len(known) < _FINAL_MIN_DANCES:
            return [], []
        final, rest = _split_last_round(lines, dances, known)
        if not final:
            return [], []
        semi, _ = _split_last_round(rest, dances[:len(rest)], known)
        return final, semi

    def _learn_playlist_folders(self, cache: PlaylistIndexCache, seen: set[str],
                                m3us: list[_TreeFile], mp3s: list[_TreeFile]) -> int:
        """Learn popularity + co-occurrence from tournament FOLDER trees: not
        everyone writes .m3u files — many DJs just copy the music into one folder
        per tournament (e.g. 'H:\\DM Latein 2026\\HGR S Lat\\Finale\\…').

        Every directory under PLAYLIST_DIR that directly contains music files
        (MP3, FLAC, M4A, Ogg, Opus) acts as one virtual playlist (its files are
        the lines), so class detection and
        co-occurrence work per round folder the same way they do per M3U file.
        Top-level trees that contain any .m3u are skipped — those are already
        learned from their playlists, and counting the copied files again would
        double every song. Warm-up / party / seasonal folders are skipped like
        their M3U counterparts. Returns the number of folder playlists learned."""
        # Top-level subfolders whose tree already carries .m3u playlists
        # ('' = playlist dir root itself).
        m3u_tops = set()
        root = str(playlist_dir())
        for m3u, _sig in m3us:
            folders = folders_below(str(m3u), root)
            m3u_tops.add(folders[0] if folders else "")
        groups: dict[Path, list[_TreeFile]] = defaultdict(list)
        for mp3, sig in mp3s:
            groups[mp3.parent].append((mp3, sig))
        count = 0
        for folder in sorted(groups):
            rel_parts = folders_below(str(groups[folder][0][0]), root) or []
            top = rel_parts[0] if rel_parts else ""
            if top in m3u_tops:
                continue
            if any(_is_warmup_list_name(p) for p in rel_parts):
                continue
            files = sorted(groups[folder])
            pl_id = str(folder)
            seen.add(pl_id)
            # A folder playlist IS its file list, so its own names+mtimes are the
            # signature — adding or replacing one track re-derives just that folder.
            self._index_playlist(
                cache, pl_id, "|".join(f"{p.name}:{s}" for p, s in files),
                lambda: (playlist_class_of(folder),
                         *self._folder_keys(folder, files)))
            count += 1
        return count

    def relearn_playlists(self) -> int:
        """Re-learn playlist popularity + co-occurrence from PLAYLIST_DIR alone.

        No filesystem walk and no audio analysis: the existing `entries` are kept;
        only the M3U-derived index (co-occurrence + playlist classes) is rebuilt
        from scratch and popularity re-applied per entry — so a freshly exported
        tournament counts without a full library reload.
        Returns the number of M3U files analyzed."""
        return self.adopt_playlist_index(self.learn_playlist_index())

    def learn_playlist_index(self) -> LearnedPlaylistIndex:
        """The slow half of `relearn_playlists`, safe on a worker thread.

        Builds the index into a scratch copy of this library and works out every
        entry's popularity from it on a copy of the entry — this library and its
        entries stay exactly as they were, so a Generate meanwhile still draws
        from the whole old index. `adopt_playlist_index` swaps the result in."""
        scratch = copy.copy(self)
        scratch._track_playlists = defaultdict(set)
        scratch._playlist_cls = {}
        scratch._track_finals = defaultdict(set)
        scratch._track_semis = defaultdict(set)
        scratch._line_key_memo = {}
        scratch._playlist_year = dict(self._playlist_year)
        n = scratch._learn_playlists()
        values = []
        for e in list(self.entries):
            probe = copy.copy(e)
            probe.source_info = ""   # _apply_popularity only overwrites on a hit
            scratch._apply_popularity(probe)
            values.append((e, {f: getattr(probe, f) for f in _POPULARITY_FIELDS}))
        return LearnedPlaylistIndex(n, scratch, values)

    def adopt_playlist_index(self, learned: LearnedPlaylistIndex) -> int:
        """Swap a `learn_playlist_index` result in — plain assignments, for the GUI
        thread. Returns the number of playlists analyzed."""
        scratch = learned.scratch
        self._track_playlists = scratch._track_playlists
        self._playlist_cls = scratch._playlist_cls
        self._track_finals = scratch._track_finals
        self._track_semis = scratch._track_semis
        self._stem_dance = scratch._stem_dance
        self._line_key_memo = scratch._line_key_memo
        self._playlist_year = scratch._playlist_year
        for e, values in learned.values:
            for field, value in values.items():
                setattr(e, field, value)
        return learned.playlists

    def _refresh_stem_dance(self) -> None:
        """(Re)build the stem-key → calculated-dance map from the current entries, so
        `_line_keys` can qualify a playlist line by the SAME dance the library assigned
        the file (genre tag wins over the filename — see `_make_entry`)."""
        self._stem_dance = {stem_key(str(e.path)): e.dance for e in self.entries}
        self._line_key_memo.clear()   # the map the memoized keys were derived from

    def _line_dance(self, line: str) -> str | None:
        """Dance for a playlist line: the calculated dance of the library file it points
        at (via stem key), else detected from the filename / path. This keeps the line's
        qualifier consistent with the entry's `dance` even when an ID3 genre tag overrode
        the filename guess."""
        d = self._stem_dance.get(stem_key(line))
        if d:
            return d
        return detect_dance(Path(line).name) or detect_dance(line)

    def _line_keys(self, line: str) -> set[str]:
        """Dance-qualified co-occurrence keys for one playlist entry (a file path / M3U
        line). Mirrors `_match_keys` so the learn side and the entry side meet on the
        same keys. Title / song-title keys are namespaced by the line's dance; the bare
        filename stem key stays plain (it already carries the dance).

        Memoized on the raw line, and never mutated by a caller. 2000 playlists
        hold ~141k lines but only ~8k distinct ones — a well-used track derives
        the same keys twenty times over, which was ~4 s of every single start."""
        hit = self._line_key_memo.get(line)
        if hit is not None:
            return hit
        d = self._line_dance(line)
        keys = {stem_key(line)}
        tkey = _title_key(line)
        if tkey:
            keys.add(dq(d, tkey))
        skey = song_title_key(line)
        if len(skey) >= 3:
            keys.add(dq(d, skey))
        self._line_key_memo[line] = keys
        return keys

    def _match_keys(self, entry: MusicEntry) -> set[str]:
        """All keys under which `entry` may appear in the playlist index:
        exact filename, filename-derived title, and ID3 tag title / 'artist title'.
        This is what lets a renamed file still match its old playlist entries.

        Title-derived keys are namespaced by the track's own dance (`_dq`) so a
        same-titled track of a DIFFERENT dance ('No Roots' QS vs TG, 'Flowers' SF vs
        RB) can't borrow its popularity — mirroring `_line_keys` on the
        learn side. The bare filename stem key stays plain (it already carries the dance)."""
        d = entry.dance
        stem = entry.path.stem   # once: three keys of 46k titles each split it again
        keys = {stem.lower().strip()}   # = _stem_key
        tkey = title_key_of_stem(stem)
        if tkey:
            keys.add(dq(d, tkey))
        # Same aggressive key the learn side indexes — matches renamed / moved /
        # re-encoded copies (different path, same song) to their playlist history.
        skey = song_title_key_of_stem(stem)
        if len(skey) >= 3:
            keys.add(dq(d, skey))
        if entry.tag_title:
            tt = norm_title(entry.tag_title)
            if len(tt) >= 3:
                keys.add(dq(d, tt))
            if entry.tag_artist:
                at = norm_title(f"{entry.tag_artist} {entry.tag_title}")
                if len(at) >= 3:
                    keys.add(dq(d, at))
        return keys

    def share_playlist_index_from(self, other: MusicLibrary) -> None:
        """Adopt another library's learned playlist co-occurrence + popularity data.

        The playlist index is keyed by filename / title (path-independent), so a
        library scanned WITHOUT playlist learning (e.g. the global repo, which uses
        learn=False for speed) can reuse the index the competition library already
        built — making 'based on my playlist history' work there too. Popularity is
        recomputed per entry from the shared index (filename-matched, so it works
        even when the repo lives on a different drive than the playlists).
        """
        if other is self or not getattr(other, "_track_playlists", None):
            return
        if self._track_playlists is other._track_playlists:
            return   # adopted already (by the loader thread); a relearn swaps the dict
        self._track_playlists = other._track_playlists
        self._playlist_cls = getattr(other, "_playlist_cls", {})
        self._track_finals = getattr(other, "_track_finals", {})
        self._track_semis = getattr(other, "_track_semis", {})
        for e in self.entries:
            self._apply_popularity(e)

    def playlists_for(self, entry: MusicEntry) -> set[str]:
        """Which past playlists this track turns up in — for anything outside
        this class that wants to reason about what was played together."""
        return self._playlists_for(entry)

    def _playlists_for(self, entry: MusicEntry, keys: set[str] | None = None) -> set[str]:
        """Union of every playlist this entry appears in, across all match keys.

        `keys` lets a caller that already has `_match_keys(entry)` (regex-heavy)
        pass it in rather than have this recompute it — see `_apply_popularity`."""
        out: set[str] = set()
        for k in keys if keys is not None else self._match_keys(entry):
            pls = self._track_playlists.get(k)
            if pls:
                out |= pls
        return out

    def _finals_for(self, entry: MusicEntry, keys: set[str] | None = None) -> set[str]:
        """…of those, the ones that danced it in their FINAL round."""
        return self._round_playlists_for(entry, self._track_finals, keys)

    def _semis_for(self, entry: MusicEntry, keys: set[str] | None = None) -> set[str]:
        """…and the ones that danced it in their SEMIFINAL."""
        return self._round_playlists_for(entry, self._track_semis, keys)

    def _round_playlists_for(self, entry: MusicEntry, index: dict[str, set[str]],
                             keys: set[str] | None = None) -> set[str]:
        out: set[str] = set()
        for k in keys if keys is not None else self._match_keys(entry):
            pls = index.get(k)
            if pls:
                out |= pls
        return out

    def _apply_popularity(self, entry: MusicEntry) -> None:
        """Set entry.popularity + source_info from the playlist index.

        popularity = number of DISTINCT (non-eintanzen) playlists this track appears
        in, matched by the path-independent keys in `_match_keys` (filename, derived
        title, aggressive song-title, ID3 tags). This is what makes a moved / renamed /
        re-encoded copy still count — exact-path matching missed e.g.
        'LatinEnergy\\08 1-16 El Sonador (CC 31).mp3', which lives under a
        different folder/name than its playlist entries.
        """
        keys = self._match_keys(entry)
        pls = self._playlists_for(entry, keys)
        entry.popularity = len(pls)
        # Per-class play counts: how many of those playlists were run as which start
        # class (parsed from the playlist file/folder name). Lists whose class can't
        # be detected still count toward `popularity`, just not toward any class.
        cls_counts: Counter = Counter()
        for p in pls:
            c = self._playlist_cls.get(p)
            if c:
                cls_counts[c] += 1
        entry.class_plays = dict(cls_counts) or None
        # How many of those plays were a FINAL, and how many a SEMIFINAL. A title
        # can be the most-played in the library and still be a heat title — which
        # is exactly what the two picked rounds must not reach for first (see
        # planner.generate.scoring / `_get_pool`).
        entry.final_plays = len(self._finals_for(entry, keys) & pls)
        entry.semi_plays = len(self._semis_for(entry, keys) & pls)
        # When it was last used: the newest year any of those playlists is dated
        # to. Lists without a date in their path say nothing, so a track that
        # only ever appears in those stays None rather than counting as old.
        years = []
        for p in pls:
            if p not in self._playlist_year:
                self._playlist_year[p] = playlist_year(p)
            y = self._playlist_year[p]
            if y:
                years.append(y)
        entry.last_played = max(years) if years else None
        if pls:
            # Only the first three names are ever shown. A well-used track sits in
            # 149 playlists, and building a Path for every one of them to throw 146
            # away was ~40 % of this call — stop as soon as three distinct stems are
            # in hand (still in sorted order, so the shown names don't wobble).
            stems: list[str] = []
            for p in sorted(pls):
                stem = Path(p).stem
                if stem not in stems:
                    stems.append(stem)
                    if len(stems) == 3:
                        break
            entry.source_info = ", ".join(stems)
