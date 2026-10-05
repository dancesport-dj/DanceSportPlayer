"""The column indices of a playlist table. The desk builds the tables; the
evening reads the play, title and regen cells of the ones it is handed.
"""

# Table column indices  (▶ is left of Title)
_COL_DANCE = 0
_COL_HEAT = 1
_COL_PLAY = 2   # ← left of title
_COL_ARTIST = 3 # artist tag, sits LEFT of Title and shares its width (like the library)
_COL_TITLE = 4
_COL_BPM = 5
_COL_LEN = 6    # ⏱ track duration
_COL_POP = 7
_COL_CLASS = 8
_COL_RATING = 9 # ★ stars, added later: saved ticks are shifted (migrate_column_settings)
_COL_CUSTOM = 10 # the free Custom field (planner.custom_field), added after ★
_COL_REGEN = 11 # stays last: a deck's header rows span every column left of it
_N_COLS = 12
