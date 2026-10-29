#!/usr/bin/env python3
"""
Dancesport Playlist Planner
Suggests competition playlists based on dance class, age group, and rounds with heats.
Uses your music library, learns from past playlists, and optionally uses librosa for
audio-feature-based similarity (rhythm + timbre).
"""

import io
import json
import logging
import os
import random
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# ── UTF-8 fix for Windows console ─────────────────────────────────────────────
# A windowed (no-console) build — pythonw or a PyInstaller GUI .exe — has no
# stdout at all (sys.stdout is None), so guard before touching its encoding.
if (isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding
        and sys.stdout.encoding.lower() not in ('utf-8', 'utf-8-sig')):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Diagnostics go through logging; interactive CLI output (menus, prompts, result
# tables) stays on print. The CLI entry point installs a bare-message handler so
# console output looks unchanged; the GUI configures its own handler.
log = logging.getLogger("dancesport.planner")

# ── Optional dependencies ──────────────────────────────────────────────────────
# numpy/librosa availability is owned by planner.music.db (re-imported below with the
# rest of the shared names); only mutagen is used directly in this module.
try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3
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
from planner.cli import (  # facade re-export
    DLINE,
    LINE,
    ask_choice,
    ask_dances,
    ask_rounds_with_heats,
    display_playlist,
    hdr,
    interactive_refine,
    main,
    sep,
)
from planner.config import (
    APP_DIR,
    CACHE_FILE,
    GLOBAL_SCAN_CACHE_FILE,
    INSTALL_DIR,
    MUSIC_DIR,
    OUTPUT_DIR,
    PATH_CONFIG_FILE,
    SCAN_CACHE_FILE,
    build_flavor,
    player_build,
    set_playlist_dir,
    write_json_atomic,
)
from planner.event.competition import (  # facade re-export
    CompetitionSpec,
    competition_matches_file,
    parse_competition_schedule,
)
from planner.generate.ai import (  # facade re-export
    DEFAULT_API_BASE,
    FREE_MODELS_FALLBACK,
    OPENROUTER_MODELS_URL,
    OPENROUTER_URL,
    api_host,
    build_track_prompt,
    load_openrouter_config,
    match_suggestions_to_library,
    openrouter_chat,
    openrouter_free_models,
    parse_ai_suggestions,
    save_openrouter_config,
)
from planner.generate.scoring import (  # facade re-export
    BONUS_CLASS_OK,
    BONUS_FRESH,
    BONUS_PROVEN,
    PENALTY_BELOW_TEMPO,
    PENALTY_CLASS_MISMATCH,
    RANDOM_TIEBREAK,
    STRATEGIES,
    STRATEGY_HELP,
    STRATEGY_LABELS,
    W_BPM_FIT,
    W_POPULARITY,
    W_TIMBRE,
    class_popularity,
    effective_popularity,
)
from planner.generate.suggester import (  # facade re-export
    PlaylistSuggester,
    generate_hints,
    source_gap_hint,
)
from planner.generate.warmup import (  # facade re-export
    build_class_warmup,
    build_warmup_playlist,
    class_warmup_pool,
    entry_in_style,
    others_dance_from_path,
    others_dance_of,
    warmup_code,
    warmup_rounds,
    warmup_section,
)
from planner.models import (  # facade re-export
    ALLOW_REPEAT,
    BELOW_TEMPO_EXT,
    DANCE_NAMES,
    DANCE_PATTERNS,
    DANCE_STYLES,
    DEFAULT_DANCES,
    FAST_DANCES,
    GENRE_TO_DANCE,
    OTHER_GENRE_LABELS,
    OTHERS_DANCES,
    ROUND_NAMES,
    SLOW_DANCES,
    STYLE_FOLDERS,
    TEMPO_RANGES,
    TSO_BANDS,
    MusicEntry,
    Playlist,
    RoundConfig,
    ScanCancelled,
    Strategy,
    TsoBand,
    default_round_name,
    fold_text,
    merge_day_playlists,
    round_names,
    round_takt_target,
    rounds_from_pattern,
    split_day_rounds,
    takt_counts,
    tso_band_target,
)
from planner.music.analysis import (
    HAS_LIBROSA,
    HAS_NUMPY,
    PROBE_FAILED,
    PROBE_NO_BACKEND,
    PROBE_NO_LIBROSA,
    AudioFeatures,
    probe_decode_backend,
)
from planner.music.db import AudioCache
from planner.music.db_upkeep import cleanup_orphans, db_maintenance
from planner.music.gaps import (  # facade re-export
    GAP_MIN_POOL,
    GAP_MIN_PROVEN,
    ai_prompt,
    gap_reasons,
    gap_stats,
    last_played_year,
    shopping_list,
)
from planner.music.library import (  # facade re-export
    MusicLibrary,
)
from planner.music.parsing import (  # facade re-export
    detect_playlist_meta,
)
from planner.music.scan_caches import (
    GlobalScanCache,
    ScanCache,
    global_coverage,
    global_index_count,
)

# === split re-exports ===
from planner.playlist.m3u import (  # facade re-export
    export_flat_m3u,
    export_m3u,
    grid_from_running_order,
    import_playlist_m3u,
    m3u_marker_rounds,
    numbered_folder_m3u,
    read_m3u_tracks,
    running_order_rounds,
)
from planner.themes import (  # facade re-export
    THEMES,
    all_themes,
    load_user_themes,
)

# ── "Past competitions" mode ─────────────────────────────────────────────────────
# Build a playlist from songs you have ALREADY played at a given competition class.
# A line like "U21 STD (50) 4-4-3-2-1" is matched to past per-class playlist files
# (U21_STD.m3u, MAS_I_*_LAT.m3u, RIS_STAR_LAT.m3u, …) purely by their FILENAME — the
# event / folder name is irrelevant. Every song in every matching M3U across
# PLAYLIST_DIR forms the candidate pool the suggester then draws from.











































































































































if __name__ == "__main__":
    main()
