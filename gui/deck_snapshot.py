"""💾 A deck's saved form — what autosave, undo and export store for it.

Split off the persistence mixin: turning a deck into its JSON-able snapshot, and
a snapshot's rounds back into a playlist grid, needs the table's rows and a way
to resolve a path — not the window. So both are plain functions here, tested
without one; the window binds its deck context and its library to them.
"""
from pathlib import Path


def playlist_from_grid(rounds_data: list, n_dances: int, resolve,
                       progress_cb=None) -> dict:
    """Rebuild a {round_name: [[entry|None per dance] per heat]} dict from a
    serialized grid, `resolve(path)` turning each saved path into an entry.

    `progress_cb(done, total, name)` is for the callers that make the user
    wait: a path the library doesn't know has its tags read off the disk
    (~50 ms each), so a long imported list spends its whole save in here."""
    total = sum(1 for r in rounds_data
                for hcol in (r.get("grid") or {}).values()
                for p in hcol.values() if p)
    done = 0
    playlist: dict = {}
    for r in rounds_data:
        heats = int(r.get("heats", 1))
        grid = r.get("grid", {})
        heat_list = []
        for h in range(heats):
            hcol = grid.get(str(h), {})
            row = [None] * n_dances
            for d in range(n_dances):
                p = hcol.get(str(d))
                if p:
                    row[d] = resolve(p)
                    done += 1
                    if progress_cb:
                        progress_cb(done, total, Path(p).name)
            heat_list.append(row)
        playlist[r["name"]] = heat_list
    return playlist


def serialize_deck(table, meta_ctx: dict) -> dict | None:
    """Snapshot a deck's working grid (exactly as shown, incl. ↺ / moves / drops)
    into a JSON-able dict, or None when there's nothing worth saving.

    `meta_ctx` is the deck's generation context (mode/style/class/age/theme)."""
    metas = [m for m in table._row_meta if m]
    if getattr(table, "_player_list", False):
        entries = [m.entry for m in metas if m.entry is not None]
        if not entries:
            return None
        # Serialized as a theme, because in the file a running order IS a flat
        # list of tracks — export, undo diffing and the row flash then work
        # unchanged. The flag is what tells the restore to bring it back as a
        # player list rather than as a themed deck; the sections carry the
        # rounds its ─── strips are headed with (derived once, at load).
        paths = {str(e.path) for e in entries}
        sections = getattr(table, "_player_sections", None) or {}
        state = {
            "mode": "Theme",
            "player_list": True,
            "style": meta_ctx["style"],
            "dance_class": meta_ctx["dance_class"],
            "age": meta_ctx["age"],
            "theme_label": getattr(table, "_warmup_label", "") or "",
            "theme_entries": [str(e.path) for e in entries],
            "player_sections": {p: n for p, n in sections.items() if p in paths},
        }
        # 🔁 marks, same rule as the grid below: a free running order may
        # carry them too, and losing them at the next start would make the
        # mark useless exactly where the evening is longest.
        marked = sorted(table._marked_paths & paths)
        if marked:
            state["marked"] = marked
        return state
    if meta_ctx["mode"] == "Theme" and not table._dynamic:
        entries = [m.entry for m in metas
                   if m.theme and m.entry is not None]
        if not entries:
            return None
        return {
            "mode": "Theme",
            "style": meta_ctx["style"],
            "dance_class": meta_ctx["dance_class"],
            "age": meta_ctx["age"],
            "theme_label": meta_ctx["theme_label"],
            "theme_entries": [str(e.path) for e in entries],
        }

    song_metas = [m for m in metas if not m.theme
                  and m.round_name is not None and not m.backup]
    backup_metas = [m for m in metas if m.backup
                    and m.entry is not None]
    if not song_metas:
        return None

    # Dance column order — for dynamic decks it's the live column list (so empty
    # columns survive); otherwise recovered from the d_idx of the saved rows.
    if table._dynamic and table._dynamic_dances:
        dances = list(table._dynamic_dances)
    else:
        dance_by_idx: dict[int, str] = {}
        for m in song_metas:
            dance_by_idx[m.d_idx] = m.dance
        dances = [dance_by_idx[i] for i in sorted(dance_by_idx)]

    # Rounds in first-seen order; each carries its config + per-heat grid of paths.
    rounds: list[dict] = []
    seen: dict[str, dict] = {}
    for m in song_metas:
        rn = m.round_name
        r = seen.get(rn)
        if r is None:
            r = {
                "name": rn,
                "tier": m.tier,
                "prefer_fresh": bool(m.prefer_fresh),
                "strategy": m.strategy or "",
                "heats": 0,
                "grid": {},   # "h_idx" → {"d_idx" → path | null}
            }
            # Stacked 📅 day-plan deck: which competition this round belongs to.
            ctx = getattr(table, "_round_ctx", {}).get(rn)
            if ctx:
                r["ctx"] = dict(ctx)
            seen[rn] = r
            rounds.append(r)
        h, d = m.h_idx, m.d_idx
        r["heats"] = max(r["heats"], h + 1)
        e = m.entry
        r["grid"].setdefault(str(h), {})[str(d)] = str(e.path) if e else None

    # Final-round backups (stacked under a slot) → per-round "backups" map.
    for m in backup_metas:
        r = seen.get(m.round_name)
        if r is None:
            continue
        key = f"{m.h_idx}/{m.d_idx}"
        r.setdefault("backups", {}).setdefault(key, []).append(str(m.entry.path))

    # Per-round hidden dances (🗑 "remove dance from this round") → "skip_dances".
    for rn, skipped in getattr(table, "_round_skip_dances", {}).items():
        r = seen.get(rn)
        if r is not None and skipped:
            r["skip_dances"] = sorted(skipped)

    state = {
        "mode": "Favorites",
        "ui_mode": meta_ctx.get("ui_mode", "Favorites"),
        "style": meta_ctx["style"],
        "dance_class": meta_ctx["dance_class"],
        "age": meta_ctx["age"],
        "use_timbre": bool(table._use_timbre),
        "dances": dances,
        "rounds": rounds,
        "dynamic": bool(table._dynamic),
        "dynamic_capacity": list(table._dynamic_capacity),
    }

    # 🔁 "potential replace" marks (Ctrl+M) — only the ones whose song is still
    # in this deck, so marks left behind by re-rolled/removed tracks don't pile
    # up in the state file.
    live_paths = {str(m.entry.path) for m in metas
                  if m.entry is not None and getattr(m.entry, "path", None)}
    marked = sorted(table._marked_paths & live_paths)
    if marked:
        state["marked"] = marked
    return state
