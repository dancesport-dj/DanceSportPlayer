#!/usr/bin/env python3
"""
Dancesport Playlist Planner
Suggests competition playlists based on dance class, age group, and rounds with heats.
Uses your music library, learns from past playlists, and optionally uses librosa for
audio-feature-based similarity (rhythm + timbre).
"""

import io, re, random, sys, json, os, unicodedata
import logging
import urllib.request, urllib.error
from pathlib import Path
from dataclasses import dataclass
from collections import Counter, defaultdict, deque
from difflib import SequenceMatcher
from collections.abc import Callable
from datetime import datetime

# ── UTF-8 fix for Windows console ─────────────────────────────────────────────
# A windowed (no-console) build — pythonw or a PyInstaller GUI .exe — has no
# stdout at all (sys.stdout is None), so guard before touching its encoding.
if (sys.stdout is not None and sys.stdout.encoding
        and sys.stdout.encoding.lower() not in ('utf-8', 'utf-8-sig')):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Diagnostics go through logging; interactive CLI output (menus, prompts, result
# tables) stays on print. The CLI entry point installs a bare-message handler so
# console output looks unchanged; the GUI configures its own handler.
log = logging.getLogger("dancesport.planner")

# ── Optional dependencies ──────────────────────────────────────────────────────
# numpy/librosa availability is owned by planner.db (re-imported below with the
# rest of the shared names); only mutagen is used directly in this module.
try:
    from mutagen.id3 import ID3
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# ── Shared modules (light split) ────────────────────────────────────────────────
# The planner is a set of modules; this file re-exports their PUBLIC names so
# the tests and old scripts can keep saying `dancesport_planner.X`. Production
# code imports the owning planner.<module> instead (tests/app/test_facade_imports.py).
#
# Public only, deliberately. A facade that also forwarded the underscored names
# had no interface at all — every regex, every weight and every helper any of
# the modules happened to define was part of it, and a caller reaching for one
# could not tell it was reaching into an implementation. Whoever needs a private
# name imports it from the module that owns it, where it is visibly private.
from planner.config import (
    APP_DIR, INSTALL_DIR,
    MUSIC_DIR, PLAYLIST_DIR, OUTPUT_DIR,
    CACHE_FILE, AUDIO_DB_FILE, SCAN_CACHE_FILE, GLOBAL_SCAN_CACHE_FILE,
    PATH_CONFIG_FILE,
    write_json_atomic, set_playlist_dir, build_flavor, player_build,
)
from planner.db import (
    HAS_NUMPY, HAS_LIBROSA,
    AudioFeatures, AudioCache, ScanCache, GlobalScanCache,
    cleanup_orphans, db_maintenance, global_index_count, global_coverage,
    probe_decode_backend, PROBE_NO_LIBROSA, PROBE_NO_BACKEND, PROBE_FAILED,
)

# === split re-exports ===

from planner.m3u import (  # noqa: F401  (facade re-export)
    export_m3u,
    export_flat_m3u,
    numbered_folder_m3u,
    grid_from_running_order,
    running_order_rounds,
    m3u_marker_rounds,
    read_m3u_tracks,
    import_playlist_m3u,
)

from planner.cli import (  # noqa: F401  (facade re-export)
    DLINE,
    LINE,
    hdr,
    sep,
    ask_choice,
    ask_dances,
    ask_rounds_with_heats,
    display_playlist,
    interactive_refine,
    main,
)

from planner.library import (  # noqa: F401  (facade re-export)
    MusicLibrary,
)

from planner.suggester import (  # noqa: F401  (facade re-export)
    PlaylistSuggester,
    generate_hints,
    source_gap_hint,
)

from planner.gaps import (  # noqa: F401  (facade re-export)
    gap_stats,
    gap_reasons,
    ai_prompt,
    shopping_list,
    last_played_year,
    GAP_MIN_POOL,
    GAP_MIN_PROVEN,
)

from planner.ai import (  # noqa: F401  (facade re-export)
    DEFAULT_API_BASE,
    OPENROUTER_URL,
    OPENROUTER_MODELS_URL,
    FREE_MODELS_FALLBACK,
    api_host,
    load_openrouter_config,
    save_openrouter_config,
    openrouter_chat,
    openrouter_free_models,
    build_track_prompt,
    parse_ai_suggestions,
    match_suggestions_to_library,
)

from planner.themes import (  # noqa: F401  (facade re-export)
    THEMES,
    load_user_themes,
    all_themes,
)

from planner.competition import (  # noqa: F401  (facade re-export)
    CompetitionSpec,
    parse_competition_schedule,
    competition_matches_file,
)

from planner.warmup import (  # noqa: F401  (facade re-export)
    warmup_code,
    warmup_section,
    warmup_rounds,
    build_warmup_playlist,
    class_warmup_pool,
    build_class_warmup,
    entry_in_style,
    others_dance_from_path,
    others_dance_of,
)

from planner.models import (  # noqa: F401  (facade re-export)
    DANCE_NAMES,
    DANCE_PATTERNS,
    GENRE_TO_DANCE,
    OTHER_GENRE_LABELS,
    TEMPO_RANGES,
    TSO_BANDS,
    round_takt_target,
    takt_counts,
    tso_band_target,
    DEFAULT_DANCES,
    DANCE_STYLES,
    STYLE_FOLDERS,
    OTHERS_DANCES,
    fold_text,
    ROUND_NAMES,
    ALLOW_REPEAT,
    BELOW_TEMPO_EXT,
    SLOW_DANCES,
    FAST_DANCES,
    RoundConfig,
    rounds_from_pattern,
    merge_day_playlists,
    split_day_rounds,
    MusicEntry,
    ScanCancelled,
    Playlist,
)

from planner.parsing import (  # noqa: F401  (facade re-export)
    detect_playlist_meta,
)

from planner.scoring import (  # noqa: F401  (facade re-export)
    W_POPULARITY,
    W_BPM_FIT,
    W_TIMBRE,
    PENALTY_BELOW_TEMPO,
    BONUS_FRESH,
    BONUS_PROVEN,
    BONUS_CLASS_OK,
    PENALTY_CLASS_MISMATCH,
    RANDOM_TIEBREAK,
    STRATEGIES,
    STRATEGY_LABELS,
    STRATEGY_HELP,
    class_popularity,
    effective_popularity,
)






















































# ── "Past competitions" mode ─────────────────────────────────────────────────────
# Build a playlist from songs you have ALREADY played at a given competition class.
# A line like "U21 STD (50) 4-4-3-2-1" is matched to past per-class playlist files
# (U21_STD.m3u, MAS_I_*_LAT.m3u, RIS_STAR_LAT.m3u, …) purely by their FILENAME — the
# event / folder name is irrelevant. Every song in every matching M3U across
# PLAYLIST_DIR forms the candidate pool the suggester then draws from.











































































































































if __name__ == "__main__":
    main()
