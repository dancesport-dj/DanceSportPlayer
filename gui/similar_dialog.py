"""The Similar-Tracks dialog (timbre / embedding ranked matches for one song).

Extracted 1:1 from gui/dialogs.py in the big-module split; gui.dialogs
re-exports the class(es), so existing importers keep working unchanged."""
import logging
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QPushButton, QLabel,
    QComboBox, QCheckBox, QHeaderView, QAbstractItemView, QMessageBox,
    QDialog,
)
from PySide6.QtCore import (
    Qt, QThread,
)
from PySide6.QtGui import (
    QShortcut, QKeySequence,
)

import planner.config

from planner.parsing import _song_title_key
from planner.db import HAS_LIBROSA
from planner.models import MusicEntry
from planner.terms import dance_name
from planner.vocals import entry_is_instrumental
from planner import i18n
from planner.event_plan import sounds_alike_text
from gui.workers import (
    EmbeddingIndexWorker, EmbeddingRankWorker, SimilarFromFileWorker,
    adopt_running,
)
from gui.common import (  # noqa: F401  (shared primitives)
    stopwatch_header,
    _PROVEN_MIN_PLAYS,
    _sanitize_filename,
    apply_taskbar_icon,
    _lbl,
    LoadingDialog,
    _fmt_duration,
    BusyDialog,
    _C_ROUND_BG,
    _C_ROUND_FG,
    _C_DANCE_BG,
    _C_DANCE_FG,
    _C_ROW_EVEN,
    _C_ROW_ODD,
    _C_POP_FG,
    _C_NEW_FG,
    _C_SIM_FG,
    _C_WARN_FG,
    _C_DEFAULT,
    _fmt_track_secs,
    _entry_tooltip,
    _open_in_default_player,
    _open_folder,
    reveal_in_explorer,
    _DragTable,
    DropZone,
    _PathListWidget,
    _DroppedFilesList,
    _MultiFileDropZone,
)

log = logging.getLogger("dancesport.gui")


# ─────────────────────────────────────────────────────────────────────────────
# Similar Tracks Dialog
# ─────────────────────────────────────────────────────────────────────────────
class SimilarTracksDialog(QDialog):
    """Shows the tracks most similar (by timbre) to a chosen song.

    Each row has a ▶ play button to preview the track, and the result table
    is drag-enabled so rows can be dropped straight into VLC / Explorer / etc.
    If `lib` and `cache` are supplied, a drop field lets you drop another file
    to refresh the results in place.
    """

    _COLS = ["▶", "Sim", "Dance", "Title", "BPM", "⏱", "Pop"]

    # Methods served by the cached-vector ranking path (embedding_similar), as opposed
    # to the in-memory timbre metrics (gaussian_kl / librosa) served by similar_tracks.
    _EMBED_METHODS = ("openl3", "chroma2dftm")

    def __init__(self, source: MusicEntry, results, parent=None, play_cb=None,
                 lib=None, cache=None, same_dance=True, seek_cb=None, is_global=False,
                 wishlist_paths=None, wishlist_only=False, pick_cb=None,
                 history_title=None, fresh_only=False, round_history_cb=None,
                 round_name=None, hide_fn=None):
        super().__init__(parent)
        # Tall by default so a long result list (up to 100 rows) is mostly visible without
        # scrolling — capped to ~90% of the screen so it still fits on smaller displays.
        screen = self.screen() or QApplication.primaryScreen()
        avail_h = screen.availableGeometry().height() if screen else 900
        self.resize(560, max(480, int(avail_h * 0.9)))
        self.setMinimumHeight(480)
        self._play_cb = play_cb
        self._seek_cb = seek_cb
        # Pick mode: when set, the dialog is a one-shot replacement picker — double-
        # clicking a row (or the "Use this track" button) calls pick_cb(entry) and
        # closes, instead of opening the file in the system player.
        self._pick_cb = pick_cb
        # The caller's own filter, results → results kept (🔁 Check duplicates
        # hides what its next check would flag). Applied on every render: the
        # window ranks anew as it opens and on each method switch.
        self._hide_fn = hide_fn
        # History mode ('find planned before'): a static list of tracks used in past
        # competitions for one dance + round. No source track, no similarity re-ranking
        # — just preview / drag onto the slot. `history_title` is its window title.
        self._history_title = history_title
        self._row_entries: list = []
        self._cur_row = -1
        self._lib = lib
        self._cache = cache
        self._source = source
        self._same_dance = same_dance
        self._is_global = is_global
        # Paths currently in the user's wishlist(s) — lets the dialog narrow results
        # to that curated set so they can pick the best-matching one to add next.
        # We also key the set by normalised song title and content fingerprint so a
        # DIFFERENT file copy of a wishlisted song still counts as "in the wishlist".
        self._wishlist_paths = {str(p) for p in (wishlist_paths or [])}
        self._wishlist_keys = set()
        self._wishlist_fps  = set()
        for p in self._wishlist_paths:
            try:
                k = _song_title_key(p)
                if k:
                    self._wishlist_keys.add(k)
            except Exception as exc:
                log.debug("🔑 No title key for %s: %s", p, exc)
            if cache is not None:
                try:
                    fp = cache.known_fingerprint(Path(p))   # in-memory only, no I/O
                    if fp:
                        self._wishlist_fps.add(fp)
                except Exception as exc:
                    log.debug("🔑 No cached fingerprint for %s: %s", p, exc)
        # 📜 Round history: called once, on the first tick of the checkbox, for the
        # (paths, title keys) past competitions played in the source slot's round.
        self._round_history_cb = round_history_cb
        self._round_history: tuple[set, set] | None = None
        self._all_results = list(results)   # unfiltered; dedup is applied on render
        self._paths = []
        self._base_playing = False
        self._started: Path | None = None   # the title this window put on the player
        self._worker: SimilarFromFileWorker | None = None
        self._busy: BusyDialog | None = None
        # Deep-embedding (OpenL3 / Chroma) ranking state
        self._method = "gaussian_kl"        # "gaussian_kl" | "librosa" | "openl3" | "chroma2dftm" | "combined"
        self._sound = None                  # the SoundAlike behind "combined", built on first use
        self._method_lbl: QLabel | None = None
        self._reindex_btn: QPushButton | None = None
        self._emb_store = None
        self._idx_worker: EmbeddingIndexWorker | None = None
        self._rank_worker: EmbeddingRankWorker | None = None
        self._emb_busy: BusyDialog | None = None

        lyt = QVBoxLayout(self)

        # Header row: a small ▶ button (like the table) left of the base-track label
        self._head = QLabel()
        self._head.setWordWrap(True)
        self._base_btn = QPushButton("▶")
        self._base_btn.setFixedSize(26, 20)
        self._base_btn.setStyleSheet("padding: 0;")
        self._base_btn.setToolTip("Play / stop the base track these results are based on")
        self._base_btn.clicked.connect(self._toggle_play_base)
        self._base_btn.setEnabled(bool(self._play_cb and source and source.path))
        head_row = QHBoxLayout()
        head_row.setContentsMargins(0, 0, 0, 0)
        head_row.addWidget(self._base_btn, 0, Qt.AlignmentFlag.AlignTop)
        head_row.addWidget(self._head, 1)
        lyt.addLayout(head_row)

        # Mode switch: timbre (sound-alike) vs. behaviour (played together).
        # Only meaningful when we have the library to query playlist history.
        self._behavior_chk: QCheckBox | None = None
        if lib is not None:
            self._behavior_chk = QCheckBox(
                "📋  Based on my playlist history (tracks I play together)")
            self._behavior_chk.setToolTip(
                "Off: sound-alike tracks (audio timbre).\n"
                "On: tracks that keep appearing in the same old playlists as this one.")
            self._behavior_chk.toggled.connect(self._on_mode_toggled)
            lyt.addWidget(self._behavior_chk)

        # Restrict the matches to songs already in the wishlist(s), so you can find
        # the best-matching track from your curated list to add next. Only useful
        # when the wishlist isn't empty.
        self._wishlist_chk = QCheckBox("⭐  Only tracks in my wishlist(s)")
        n_wl = len(self._wishlist_paths)
        if n_wl:
            self._wishlist_chk.setToolTip(
                i18n.t("Show only the %d track(s) currently in your wishlist(s),\n"
                       "ranked by how well they match this song — pick the best one to add.\n"
                       "Matches by song (title / fingerprint), so a different copy still counts.")
                % n_wl)
        else:
            self._wishlist_chk.setEnabled(False)
            self._wishlist_chk.setToolTip(
                "Your wishlist is empty — add tracks to a wishlist first.")
        # Opened via the "Find similar (in my wishlist only)" context entry → start
        # already restricted to the wishlist. Ticked before the handler is wired:
        # the list is drawn once the window is built, not through filters that
        # do not exist yet.
        if wishlist_only and n_wl:
            self._wishlist_chk.setChecked(True)
        self._wishlist_chk.toggled.connect(self._on_wishlist_toggled)
        lyt.addWidget(self._wishlist_chk)

        # Narrow the matches to what past competitions played in this slot's round
        # (a final: other finals; round 2: any heat of past second rounds). Only a
        # deck slot has a round, so the library pane and history mode go without.
        self._round_chk: QCheckBox | None = None
        if round_history_cb is not None and history_title is None:
            self._round_chk = QCheckBox(
                i18n.t("📜  Only titles I played in this round before (%s)") % round_name)
            self._round_chk.setToolTip(
                "Show only titles your past competitions played in this round —\n"
                "any heat of it, from lists of a class and age category that fit\n"
                "this deck (the same history as 📜 Find planned before).\n"
                "Still ranked by how much they sound like this one.")
            self._round_chk.toggled.connect(self._on_round_toggled)
            lyt.addWidget(self._round_chk)

        # Similarity method: librosa timbre+rhythm vector vs. OpenL3 deep embedding.
        # OpenL3 is optional (heavy ML dep) — only offered when it can be used.
        self._method_combo: QComboBox | None = None
        if lib is not None and cache is not None and history_title is None:
            from planner import embeddings as ae
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            self._method_lbl = QLabel("Method:")
            row.addWidget(self._method_lbl)
            self._method_combo = QComboBox()
            self._method_combo.addItem("🔬  Timbre Gaussian / KL (Mandel-Ellis)", "gaussian_kl")
            self._method_combo.addItem("🎚️  Timbre + Rhythm (librosa)", "librosa")
            # A frozen .exe hides methods whose backend isn't bundled (a pip
            # hint is useless there); a dev install keeps the hint items.
            dev = planner.config.build_flavor() == "dev"
            if dev or ae.chroma_available():
                chroma_label = i18n.t("🎼  Chroma cover / remix (melody/harmony, same tune)")
                if not ae.chroma_available():
                    chroma_label += i18n.t("  – not installed")
                self._method_combo.addItem(chroma_label, "chroma2dftm")
            if dev or ae.openl3_available():
                ol3_label = i18n.t("🧠  OpenL3 (deep embedding)")
                if not ae.openl3_available():
                    ol3_label += i18n.t("  – not installed")
                self._method_combo.addItem(ol3_label, "openl3")
            self._method_combo.addItem(
                i18n.t("⚖️  Combined: timbre + groove + melody (mean)"), "combined")
            # Combined is the default: the titles all three methods rank high.
            self._method = "combined"
            self._method_combo.setCurrentIndex(self._method_combo.findData("combined"))
            self._method_combo.setToolTip(
                "Gaussian/KL: per-song MFCC distribution (mean+covariance)\n"
                "compared by symmetric KL — the Mandel-Ellis model, like the old Java\n"
                "app. Cleanest sound-alike ranking; genuine matches read ≳ 80 %.\n"
                "Librosa: fast hand-crafted timbre+rhythm vector (cosine).\n"
                "OpenL3: a pretrained neural music embedding — often closer to\n"
                "perceived 'sounds-alike'. Needs:  pip install openl3 tensorflow\n"
                "Chroma cover/remix: matches MELODY/harmony, not timbre — finds\n"
                "remixes & covers of the same tune even with a different sound,\n"
                "key or tempo. librosa only; build its index once like the others.\n"
                "Combined (default): where a title ranks by Gaussian/KL, librosa and chroma,\n"
                "averaged — the ones all three rank high come first.")
            self._method_combo.currentIndexChanged.connect(self._on_method_changed)
            row.addWidget(self._method_combo, 1)
            # Index (re)building lives in ⚙ Settings now — no per-window button here.
            lyt.addLayout(row)

        # Libraries surface several copies of the same song under slightly different
        # names ('… DJ Ice', 'jive(43) - …', '16 …'). Offer to collapse them. Shown in
        # both scopes; defaults ON for the whole-repo search (where copies are rife).
        self._dedup_chk = QCheckBox(
            "🧹  Hide duplicate copies (same song, ignoring DJ / dance / BPM tags)")
        self._dedup_chk.setToolTip(
            "Several copies of a song often exist under slightly different names\n"
            "(e.g. '… DJ Ice', 'jive(43) - Bim Bam', '16 Bim Bam'). When on, only the\n"
            "first copy of each song title is shown.")
        self._dedup_chk.setChecked(bool(is_global))   # default: hide for global searches
        self._dedup_chk.toggled.connect(self._on_dedup_toggled)
        lyt.addWidget(self._dedup_chk)

        # Restrict the matches to instrumental tracks (no vocals) — handy when the
        # tournament calls for neutral music.
        self._instr_chk = QCheckBox("🎙️  Only instrumental tracks (no vocals)")
        self._instr_chk.setToolTip(
            "Show only tracks considered instrumental: an explicit 'instr' tag /\n"
            "'(Instr.)' filename marker, a Demucs-measured vocal share (🎙️ Analyze\n"
            "vocals), or the learned audio probability. Unknown tracks count as\n"
            "vocal, so they are hidden while this is on.")
        self._instr_chk.toggled.connect(self._on_instr_toggled)
        lyt.addWidget(self._instr_chk)

        # Narrow the matches to music the floor hasn't heard from you — the
        # point of a similarity search when the old title is simply worn out.
        self._fresh_combo = QComboBox()
        self._fresh_combo.addItem("🌱  Freshness: all tracks", "")
        self._fresh_combo.addItem("✦  Only never played", "never")
        self._fresh_combo.addItem(
            i18n.t("★  Only rarely played (1–%d playlists)") % (_PROVEN_MIN_PLAYS - 1), "rare")
        self._fresh_combo.addItem("📅  Only not since 1 y", "stale1")
        self._fresh_combo.setToolTip(
            i18n.t("The same three picks as 📚 the library's ★ Plays selector.\n"
                   "'Never played': the track is in none of your old playlists.\n"
                   "'Rarely played': in 1–%d of them — %d+ is a proven title.\n"
                   "'Not since 1 y': it is played, but the newest playlist carrying\n"
                   "it is from an earlier year — the year comes from the playlist's\n"
                   "path, so lists without a date never count as old.")
            % (_PROVEN_MIN_PLAYS - 1, _PROVEN_MIN_PLAYS))
        if fresh_only:
            self._fresh_combo.setCurrentIndex(1)
        self._fresh_combo.currentIndexChanged.connect(self._on_fresh_changed)
        lyt.addWidget(self._fresh_combo)

        self._table = _DragTable(self._paths)
        table = self._table
        table.setColumnCount(len(self._COLS))
        table.setHorizontalHeaderLabels(self._COLS)
        stopwatch_header(table, 5)
        if history_title is not None:
            # No similarity score here — column 1 shows the matched competition class.
            hi = table.horizontalHeaderItem(1)
            if hi is not None:
                hi.setText("Class")
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setShowGrid(False)
        table.setDragEnabled(True)
        table.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        table.setToolTip(
            "Space: play / stop the selected track\n"
            "Ctrl + ← / → : seek 30 s back / forward")
        # Keyboard playback control (Space toggles, Ctrl+←/→ seeks the player)
        table._seek_cb = seek_cb
        table._play_toggle_cb = self._toggle_play
        # Window-level seek shortcuts so Ctrl+←/→ works even when a row's ▶ button
        # (not the table) holds keyboard focus — fires for any focused child widget.
        if seek_cb is not None:
            QShortcut(QKeySequence("Ctrl+Left"), self,
                      activated=lambda: seek_cb(-30000)).setContext(
                          Qt.ShortcutContext.WindowShortcut)
            QShortcut(QKeySequence("Ctrl+Right"), self,
                      activated=lambda: seek_cb(30000)).setContext(
                          Qt.ShortcutContext.WindowShortcut)
        # Double-click a row → open the file in the system's default music player
        table.cellDoubleClicked.connect(self._on_row_double_clicked)
        lyt.addWidget(table)

        # Drop field for chaining to another file (only if we can analyze)
        if lib is not None and cache is not None and HAS_LIBROSA and history_title is None:
            self._drop = DropZone(
                text="🎵  Drop another file here (or click to browse) for its similar tracks")
            self._drop.setMinimumHeight(44)
            self._drop.fileDropped.connect(self._on_dropped)
            lyt.addWidget(self._drop)

        self._status = QLabel("")
        self._status.setStyleSheet("color:#666; font-size:11px;")
        lyt.addWidget(self._status)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        if self._pick_cb is not None:
            self._pick_btn = QPushButton("✅  Use this track as replacement")
            self._pick_btn.setToolTip("Replace the duplicate with the selected track "
                                      "(Enter, or double-click a row)")
            self._pick_btn.clicked.connect(self._pick_selected)
            btn_row.addWidget(self._pick_btn)
            # Enter / Return (incl. numpad) confirms the selected row, no matter which
            # child widget holds focus (window-context shortcut, like the seek keys).
            for _key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                QShortcut(QKeySequence(_key), self,
                          activated=self._pick_selected).setContext(
                              Qt.ShortcutContext.WindowShortcut)
        btn_row.addStretch(1)
        close = QPushButton("Cancel" if self._pick_cb is not None else "Close")
        close.clicked.connect(self.reject if self._pick_cb is not None else self.accept)
        btn_row.addWidget(close)
        lyt.addLayout(btn_row)

        self._populate_ranked(source, results)

    # ── Pick mode (replacement chooser) ──────────────────────────────────────────
    def _pick_selected(self):
        """Confirm the table's current row as the replacement and close."""
        if self._pick_cb is None:
            return
        row = self._table.currentRow()
        self._pick_row(row)

    def _pick_row(self, row: int):
        if self._pick_cb is None or not (0 <= row < len(self._row_entries)):
            return
        entry = self._row_entries[row]
        if entry is None:
            return
        self._stop_own_preview()
        try:
            self._pick_cb(entry)
        finally:
            self.accept()

    # ── Duplicate filtering (whole-repository searches) ──────────────────────────
    def _visible_results(self, results):
        """Collapse re-encoded copies of the same song.

        Keys on the normalised song title (`_song_title_key`, which strips
        DJ tags and dance/BPM codes) so e.g. 'Upside Down DJ Ice' and 'Upside Down
        (JI43)' count as one. The first hit (highest similarity, list is sorted)
        is kept. Score is intentionally NOT part of the key — different encodings
        of the same song get slightly different similarity scores."""
        if self._dedup_chk is None or not self._dedup_chk.isChecked():
            return list(results), 0
        seen = set()
        out = []
        for sim, e in results:
            key = _song_title_key(str(e.path) if e.path else (e.title or ""))
            if key in seen:
                continue
            seen.add(key)
            out.append((sim, e))
        return out, len(results) - len(out)

    def _without_source(self, source, results):
        """Drop the title the window was opened for — its own file and every copy
        of its song. The rankings leave the anchor out by identity only, so the
        library's entry for a playlist row's file came back at 100 %. The
        'planned before' history lists past picks, the current one included."""
        if self._history_title is not None or source is None or not source.path:
            return list(results)
        own = str(source.path)
        key = _song_title_key(own)
        return [(sim, e) for sim, e in results
                if not (e.path and str(e.path) == own)
                and not (key and _song_title_key(
                    str(e.path) if e.path else (e.title or "")) == key)]

    def _on_dedup_toggled(self, _checked: bool):
        self._populate(self._source, self._all_results)

    # ── Wishlist scoping ─────────────────────────────────────────────────────────
    def _in_wishlist(self, e) -> bool:
        """True if `e` is a wishlisted track — matched by exact path, normalised song
        title (so '… DJ Ice' / '(JI43)' copies count), or content fingerprint."""
        if e is None:
            return False
        if e.path and str(e.path) in self._wishlist_paths:
            return True
        try:
            key = _song_title_key(str(e.path) if e.path else (e.title or ""))
        except Exception:
            key = ""
        if key and key in self._wishlist_keys:
            return True
        if self._wishlist_fps and self._cache is not None and e.path:
            try:
                fp = self._cache.known_fingerprint(Path(e.path))
            except Exception:
                fp = None
            if fp and fp in self._wishlist_fps:
                return True
        return False

    def _filter_to_wishlist(self, results):
        """Keep only results whose track is in the current wishlist(s)."""
        if self._wishlist_chk is None or not self._wishlist_chk.isChecked():
            return list(results), 0
        out = [(sim, e) for (sim, e) in results if self._in_wishlist(e)]
        return out, len(results) - len(out)

    def _on_wishlist_toggled(self, _checked: bool):
        self._populate(self._source, self._all_results)

    def _round_only(self) -> bool:
        return self._round_chk is not None and self._round_chk.isChecked()

    def _limits(self) -> tuple[int, float]:
        """(n, min_display) for a similarity query. The 📜 round filter keeps
        a few dozen titles out of the whole dance, so it must see all of them —
        not only the top 100 above 50 %."""
        return (1_000_000, 0.0) if self._round_only() else (100, 0.5)

    def _filter_to_round_history(self, results):
        """Keep only results past competitions played in this slot's round,
        matched by path or by song title (another copy counts too)."""
        if not self._round_only():
            return list(results), 0
        if self._round_history is None:
            self._round_history = self._round_history_cb()
        paths, keys = self._round_history

        def keep(e) -> bool:
            if e.path and str(e.path) in paths:
                return True
            key = _song_title_key(str(e.path) if e.path else (e.title or ""))
            return bool(key) and key in keys

        out = [(sim, e) for (sim, e) in results if keep(e)]
        return out, len(results) - len(out)

    def _on_round_toggled(self, _checked: bool):
        # The unfiltered list is capped at 100, so switching re-queries.
        if self._lib is None:
            self._populate(self._source, self._all_results)
        else:
            self._recompute()

    def _filter_to_instrumental(self, results):
        """Keep only results whose track reads as instrumental (see planner.vocals)."""
        if not self._instr_chk.isChecked():
            return list(results), 0
        out = [(sim, e) for (sim, e) in results if entry_is_instrumental(e)]
        return out, len(results) - len(out)

    def _on_instr_toggled(self, _checked: bool):
        self._populate(self._source, self._all_results)

    def _filter_to_fresh(self, results):
        """Keep only results matching the 🌱 freshness pick (see the combo)."""
        mode = self._fresh_combo.currentData() or ""
        if not mode:
            return list(results), 0
        cutoff = (date.today().year - int(mode[-1])
                  if mode.startswith("stale") else None)

        def keep(e) -> bool:
            pop = getattr(e, "popularity", 0) or 0
            if cutoff is not None:
                last = getattr(e, "last_played", None)
                return bool(pop) and bool(last) and last <= cutoff
            if mode == "never":
                return not pop
            return 1 <= pop < _PROVEN_MIN_PLAYS

        out = [(sim, e) for (sim, e) in results if keep(e)]
        return out, len(results) - len(out)

    def _on_fresh_changed(self, _index: int):
        self._populate(self._source, self._all_results)

    # ── Open in default player (double-click) ────────────────────────────────────
    def _on_row_double_clicked(self, row: int, _col: int):
        # In pick mode a double-click confirms the replacement instead of opening it.
        if self._pick_cb is not None:
            self._pick_row(row)
            return
        if not (0 <= row < len(self._paths)):
            return
        path = self._paths[row]
        if not path:
            return
        _open_in_default_player(Path(path), self)

    # ── Populate / refresh ──────────────────────────────────────────────────────
    def _populate(self, source: MusicEntry, results):
        self._stop_own_preview()
        self._cur_row = -1
        self._reset_base_btn()
        self._source = source
        self._all_results = list(results)
        self._base_btn.setEnabled(bool(self._play_cb and source and source.path))
        behavior = self._behavior_chk is not None and self._behavior_chk.isChecked()
        head_tpl = (i18n.t("%d %s tracks most often played together with this one — ▶ to preview, double-click to open, drag rows into another app") if behavior
                    else i18n.t("%d %s tracks most similar (sound-alike) to this one — ▶ to preview, double-click to open, drag rows into another app"))
        if self._hide_fn is not None:
            results = self._hide_fn(results)
        results = self._without_source(source, results)
        results, off_wishlist = self._filter_to_wishlist(results)
        results, _off_round = self._filter_to_round_history(results)
        results, off_instr = self._filter_to_instrumental(results)
        results, off_fresh = self._filter_to_fresh(results)
        results, hidden = self._visible_results(results)
        notes = []
        if self._wishlist_chk is not None and self._wishlist_chk.isChecked():
            notes.append(i18n.t("⭐ wishlist only"))
        if self._round_only():
            notes.append(i18n.t("📜 played in this round before"))
        if self._instr_chk.isChecked():
            notes.append(i18n.t("🎙 instrumental only (%d vocal hidden)") % off_instr)
        if self._fresh_combo.currentData():
            notes.append(i18n.t("%s (%d hidden)")
                          % (self._fresh_combo.currentText().strip(), off_fresh))
        if hidden:
            notes.append((i18n.t("%d duplicate hidden") if hidden == 1
                          else i18n.t("%d duplicates hidden")) % hidden)
        hidden_note = (f" <span style='color:#999'>({', '.join(notes)})</span>"
                       if notes else "")
        if self._history_title is not None:
            self.setWindowTitle(self._history_title)
            self._head.setText(
                f"<b>{self._history_title}</b>"
                f"<br><span style='color:#666'>"
                + i18n.t("%d track(s) you planned for this dance &amp; round in past "
                         "competitions — best competition match first (see Class) — ▶ to preview, "
                         "drag a row onto the slot, double-click to open") % len(results)
                + f"</span>{hidden_note}"
            )
        else:
            self.setWindowTitle(i18n.t("Similar to: %s") % source.title[:50])
            self._head.setText(
                f"<b>{source.title[:60]}</b>"
                f"<br><span style='color:#666'>"
                + head_tpl % (len(results), dance_name(source.dance, source.dance or ''))
                + f"</span>{hidden_note}"
            )
        self._paths = [e.path for _, e in results]
        self._row_entries = [e for _, e in results]
        self._table._paths = self._paths

        table = self._table
        table.clearContents()
        table.setRowCount(len(results))
        ctr = Qt.AlignmentFlag.AlignCenter
        sim_label = "Played together" if behavior else "Match"
        for r, (sim, e) in enumerate(results):
            tip = _entry_tooltip(e, None if self._history_title is not None else sim,
                                 sim_label)
            if not behavior and self._method == "combined" and self._sound is not None:
                views = self._sound.views(source, e, self._same_dance)
                if views:
                    tip += "\n" + sounds_alike_text(views)
            play_btn = QPushButton("▶")
            play_btn.setFixedSize(26, 20)
            play_btn.setStyleSheet("padding: 0;")
            play_btn.setToolTip(tip)
            if self._play_cb:
                play_btn.clicked.connect(lambda _, rr=r: self._toggle_play(rr))
            else:
                play_btn.setEnabled(False)
            table.setCellWidget(r, 0, play_btn)
            if self._history_title is not None:
                # `sim` carries the matched competition class string in history mode.
                sim_it = QTableWidgetItem(str(sim) if sim else "")
            else:
                sim_it = QTableWidgetItem(f"{sim * 100:.2f}%")
            sim_it.setTextAlignment(ctr)
            sim_it.setForeground(_C_SIM_FG)
            table.setItem(r, 1, sim_it)
            d_it = QTableWidgetItem(dance_name(e.dance, e.dance or ""))
            d_it.setTextAlignment(ctr)
            table.setItem(r, 2, d_it)
            table.setItem(r, 3, QTableWidgetItem(e.title[:60]))
            bpm_it = QTableWidgetItem("" if e.bpm is None else f"T{e.bpm}")
            bpm_it.setTextAlignment(ctr)
            table.setItem(r, 4, bpm_it)
            secs = int(getattr(e, "duration", 0) or 0)
            len_it = QTableWidgetItem(_fmt_track_secs(secs) if secs else "")
            len_it.setTextAlignment(ctr)
            table.setItem(r, 5, len_it)
            pop_it = QTableWidgetItem(f"★{e.popularity}" if e.popularity
                                      else i18n.t("new"))
            pop_it.setTextAlignment(ctr)
            table.setItem(r, 6, pop_it)
            for c in range(1, 7):
                it = table.item(r, c)
                if it is not None:
                    it.setToolTip(tip)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for c in (0, 1, 2, 4, 5, 6):
            table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

    # ── Mode switch (timbre ↔ playlist behaviour) ───────────────────────────────
    def _on_mode_toggled(self, behavior: bool):
        # Playlist-history mode uses ONLY the playlists (no audio method at all),
        # so grey out the method picker + its rebuild button while it's active.
        # setEnabled(False) alone is barely visible in Fusion, so also restyle the
        # combo (greyed text/background + "not used" hint) for an obvious off-state.
        if self._method_lbl is not None:
            self._method_lbl.setEnabled(not behavior)
            self._method_lbl.setText(
                "Method <span style='color:#b00'>(not used in playlist mode)</span>:"
                if behavior else "Method:")
            self._method_lbl.setTextFormat(Qt.TextFormat.RichText)
        if self._method_combo is not None:
            self._method_combo.setEnabled(not behavior)
            self._method_combo.setStyleSheet(
                "QComboBox:disabled { color:#999; background:#e6e6e6; "
                "font-style:italic; border:1px solid #cfcfcf; }"
                if behavior else "")
        if self._reindex_btn is not None:
            self._reindex_btn.setEnabled(
                not behavior and self._method in self._EMBED_METHODS)
        self._recompute()

    def _recompute(self):
        """Recompute and repopulate results for the current method + mode."""
        if self._lib is None:
            return
        behavior = self._behavior_chk is not None and self._behavior_chk.isChecked()
        # Playlist history wins over the audio method — it ignores timbre entirely.
        if not behavior and self._method in self._EMBED_METHODS:
            self._rank_embedding()
            return
        n, min_display = self._limits()
        if behavior:
            results = self._lib.similar_by_playlists(
                self._source, n=n, same_dance=self._same_dance)
            if not results:
                self._status.setText(
                    "This track isn't in any of your old playlists yet — "
                    "nothing to learn from. Switch the toggle off for sound-alike tracks.")
            else:
                self._status.setText(
                    i18n.t("📋 Learned from your playlists — %d often played together.") % len(results))
        elif self._method == "combined":
            results = self._sound_alike()(
                self._source, n=n, same_dance=self._same_dance, min_display=min_display)
            self._status.setText(i18n.t(
                "⚖️ Combined — the mean of where each title ranks by timbre, "
                "groove and melody."))
        else:
            # librosa (cosine) or gaussian_kl (Mandel-Ellis) — both vector/Gaussian
            # methods served by similar_tracks; the embedding methods returned above.
            results = self._lib.similar_tracks(
                self._source, n=n, same_dance=self._same_dance,
                min_display=min_display, method=self._method)
            self._status.setText("")
        self._populate(self._source, results)

    def _populate_ranked(self, source: MusicEntry, results):
        """Show `source`'s matches by the current method. The callers and the
        drop worker rank by Gaussian/KL, so "combined" ranks anew — and keeps
        their list when no view can place the title (not analysed yet)."""
        if self._method != "combined":
            self._populate(source, results)
            return
        self._source = source
        self._recompute()
        if not self._all_results and results:
            self._set_method("gaussian_kl")
            self._status.setText("")
            self._populate(source, results)

    def _sound_alike(self):
        """Timbre, groove and — where its index is built — the chroma melody."""
        if self._sound is None:
            from planner import embeddings as ae
            from planner.similarity import SoundAlike
            store = self._get_store()
            chroma = (lambda e: store.recorded(e.path, ae.MODEL_CHROMA)) if store else None
            self._sound = SoundAlike(self._lib, chroma=chroma)
        return self._sound

    # ── Deep-embedding ranking (OpenL3 / Chroma) ───────────────────────────────────
    def _set_method(self, key: str):
        """Set the method combo without re-triggering the change handler."""
        self._method = key
        if self._method_combo is not None:
            idx = self._method_combo.findData(key)
            if idx >= 0 and idx != self._method_combo.currentIndex():
                self._method_combo.blockSignals(True)
                self._method_combo.setCurrentIndex(idx)
                self._method_combo.blockSignals(False)
        # Rebuild-index button only applies to the embedding methods (and only when
        # the audio method is actually in use, i.e. playlist-history mode is off).
        if self._reindex_btn is not None:
            behavior = self._behavior_chk is not None and self._behavior_chk.isChecked()
            is_emb = key in self._EMBED_METHODS
            self._reindex_btn.setEnabled(is_emb and not behavior)
            if is_emb:
                _, _, name = self._emb_info(key)
                self._reindex_btn.setText(i18n.t("🧠  Rebuild %s index…") % name)
            else:
                self._reindex_btn.setText("🧠  Rebuild index…")

    def _on_reindex_clicked(self):
        """Force a (re)build of the current embedding method's index over the pool."""
        if self._method not in self._EMBED_METHODS:
            return
        from planner import embeddings as ae
        model, available, name = self._emb_info(self._method)
        if not available:
            QMessageBox.information(self, i18n.t("%s not installed") % name, ae.install_hint(model))
            return
        self._build_embedding(self._emb_pool())

    def _on_method_changed(self, _idx: int):
        key = self._method_combo.currentData() if self._method_combo else "librosa"
        if key == self._method:
            return
        self._set_method(key)
        self._recompute()

    def _get_store(self):
        if self._emb_store is None and self._cache is not None:
            from planner import embeddings as ae
            self._emb_store = ae.EmbeddingStore(self._cache)
        return self._emb_store

    def _emb_info(self, method: str):
        """(ae_model_id, available, pretty_name) for an embedding method key."""
        from planner import embeddings as ae
        if method == "chroma2dftm":
            return ae.MODEL_CHROMA, ae.chroma_available(), "Chroma cover-match"
        return ae.MODEL_OPENL3, ae.openl3_available(), "OpenL3"

    def _emb_pool(self):
        """Candidate entries the embedding ranks over (same dance when filter on)."""
        if self._same_dance and self._source.dance:
            return self._lib.by_dance(self._source.dance)
        return self._lib.entries

    def _rank_embedding(self):
        from planner import embeddings as ae
        model, available, name = self._emb_info(self._method)
        if not available:
            QMessageBox.information(self, i18n.t("%s not installed") % name, ae.install_hint(model))
            self._set_method("librosa"); self._recompute(); return
        if self._cache is None or self._lib is None:
            QMessageBox.information(self, name,
                                    "Audio cache/library not available for this search.")
            self._set_method("librosa"); self._recompute(); return
        store = self._get_store()
        pool = self._emb_pool()
        # Count how many of the candidate pool already have this embedding. It
        # only decides whether to offer a build, so the fingerprint on record
        # will do — no stat, and no hashing of never-seen files on the GUI thread.
        have = sum(1 for e in pool
                   if store.get_by_fp(self._cache.recorded_fingerprint(e.path), model))
        if have < 2:
            ans = QMessageBox.question(
                self, i18n.t("Build %s index") % name,
                i18n.t("%s vectors for these %d tracks haven't been built yet.\n\n"
                       "Building analyses each track once (slow the first time, then cached).\n"
                       "Build now?") % (name, len(pool)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans != QMessageBox.StandardButton.Yes:
                self._set_method("librosa"); self._recompute(); return
            self._build_embedding(pool); return
        self._run_embedding_rank()

    def _build_embedding(self, pool):
        model, _, name = self._emb_info(self._method)
        self._status.setText(i18n.t("Building %s index…") % name)
        self._emb_busy = BusyDialog(self, i18n.t("Building %s embedding index…") % name, cancelable=True)
        self._idx_worker = EmbeddingIndexWorker(self._get_store(), model, pool, self)
        self._idx_worker.progress.connect(
            lambda d, t, n, eta: self._emb_busy and self._emb_busy.set_progress(d, t, "🧠 " + n, eta))
        self._idx_worker.done.connect(self._on_embedding_indexed)
        self._idx_worker.cancelled.connect(self._on_embedding_index_cancelled)
        self._idx_worker.error.connect(self._on_embed_error)
        self._emb_busy.cancel_requested.connect(self._idx_worker.cancel)
        self._idx_worker.start()
        self._emb_busy.show_after(300)

    def _on_embedding_indexed(self, computed: int, errors: int, first_error: str = ""):
        _, _, name = self._emb_info(self._method)
        if self._emb_busy:
            self._emb_busy.finish(); self._emb_busy = None
        if computed == 0 and errors > 0:
            QMessageBox.critical(
                self, i18n.t("%s indexing failed") % name,
                i18n.t("All %d file(s) failed to embed.\n\nFirst error:\n%s\n\n"
                       "Common causes: the neural model couldn't load, or the deps "
                       "are mismatched. See the console log for the full traceback.")
                % (errors, first_error or i18n.t("unknown")))
            self._set_method("librosa"); self._recompute()
            return
        self._status.setText(
            (i18n.t("🧠 %s index ready (%d embedded, %d failed).") % (name, computed, errors)
             if errors else i18n.t("🧠 %s index ready (%d embedded).") % (name, computed)))
        self._run_embedding_rank()

    def _on_embedding_index_cancelled(self, computed: int):
        _, _, name = self._emb_info(self._method)
        if self._emb_busy:
            self._emb_busy.finish(); self._emb_busy = None
        self._status.setText(i18n.t("%s indexing cancelled — showing librosa results.") % name)
        self._set_method("librosa"); self._recompute()

    def _run_embedding_rank(self):
        from planner import embeddings as ae
        model, _, name = self._emb_info(self._method)
        store = self._get_store()
        pool = self._emb_pool()
        self._emb_busy = BusyDialog(self, i18n.t("Ranking by %s embedding…") % name)
        self._rank_worker = EmbeddingRankWorker(
            lambda: (self._source,
                     ae.embedding_similar(self._source, pool, store, model,
                                          n=self._limits()[0],
                                          same_dance=self._same_dance)),
            self)
        self._rank_worker.done.connect(self._on_embedding_ranked)
        self._rank_worker.error.connect(self._on_embed_error)
        self._rank_worker.start()
        self._emb_busy.show_after(300)

    def _on_embedding_ranked(self, source, results):
        _, _, name = self._emb_info(self._method)
        if self._emb_busy:
            self._emb_busy.finish(); self._emb_busy = None
        if not results:
            self._status.setText(
                i18n.t("No %s matches yet — try building the index over more tracks.") % name)
        else:
            self._status.setText(i18n.t("🧠 %s — %d deep-embedding matches.") % (name, len(results)))
        self._populate(source, results)

    def _on_embed_error(self, msg: str):
        if self._emb_busy:
            self._emb_busy.finish(); self._emb_busy = None
        self._set_method("librosa")
        QMessageBox.critical(self, "Embedding error", msg)
        self._recompute()

    # ── Chained drop ────────────────────────────────────────────────────────────
    def _on_dropped(self, path: str):
        if self._worker and self._worker.isRunning():
            return
        self._status.setText(i18n.t("Analyzing %s …") % Path(path).name)
        self._busy = BusyDialog(self, i18n.t("Analyzing %s …") % Path(path).name)
        self._busy.show_after(500)
        n, min_display = self._limits() if self._round_only() else (50, 0.5)
        self._worker = SimilarFromFileWorker(
            self._lib, self._cache, path, n=n, min_display=min_display, parent=self)
        self._worker.done.connect(self._on_worker_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_done(self, source, results):
        if self._busy:
            self._busy.finish()
        # A freshly dropped external file has no playlist history → force timbre mode.
        if self._behavior_chk is not None and self._behavior_chk.isChecked():
            self._behavior_chk.blockSignals(True)
            self._behavior_chk.setChecked(False)
            self._behavior_chk.blockSignals(False)
        if not results:
            self._status.setText("No similar tracks found for that file.")
            return
        self._populate_ranked(source, results)
        self._status.setText(i18n.t("Refreshed — %d similar to %s")
                             % (len(self._all_results), source.title[:40]))

    def _on_worker_error(self, msg: str):
        if self._busy:
            self._busy.finish()
        self._status.setText("Analysis failed.")
        QMessageBox.critical(self, "Analysis Error", msg)

    def _toggle_play(self, row: int):
        if not self._play_cb:
            return
        if row == self._cur_row:                      # same row → stop
            self._set_btn(row, "▶")
            self._cur_row = -1
            self._stop_own_preview()
            return
        if self._cur_row >= 0:                         # switch from another row
            self._set_btn(self._cur_row, "▶")
        self._reset_base_btn()                         # row playback supersedes base
        self._cur_row = row
        self._set_btn(row, "■")
        if 0 <= row < len(self._paths):
            self._started = self._paths[row]
            self._release_decks()
            self._play_cb(self._paths[row])

    def _toggle_play_base(self):
        """Play / stop the analysed base track these results were built from."""
        if not self._play_cb or not self._source or not self._source.path:
            return
        if self._base_playing:                         # playing → stop
            self._reset_base_btn()
            self._stop_own_preview()
            return
        if self._cur_row >= 0:                          # stop any row first
            self._set_btn(self._cur_row, "▶")
            self._cur_row = -1
        self._base_playing = True
        self._base_btn.setText("■")
        self._started = self._source.path
        self._release_decks()
        self._play_cb(self._source.path)

    def _release_decks(self):
        """The preview takes the decks' shared player over — the row that was
        running has to give its ■ back, or it keeps claiming the music."""
        host = self.parentWidget()
        release = getattr(host.window(), "release_play_markers", None) if host else None
        if release is not None:
            release()

    def _stop_own_preview(self):
        """Stop the player, but only while it is still on the title this window
        started. The decks share the player, so a title the operator started
        since then is the live music and has to keep playing."""
        started, self._started = self._started, None
        if started is None or not self._play_cb:
            return
        host = self.parentWidget()
        deck_path = getattr(host.window(), "deck_path", None) if host else None
        if deck_path is not None and deck_path() != started:
            return
        self._play_cb(None)

    def _reset_base_btn(self):
        if self._base_playing:
            self._base_playing = False
            self._base_btn.setText("▶")

    def _set_btn(self, row: int, text: str):
        w = self._table.cellWidget(row, 0)
        if isinstance(w, QPushButton):
            w.setText(text)

    def closeEvent(self, event):
        self._stop_own_preview()                       # stop preview on close
        # The window deletes itself on close, and a rank / index / drop worker
        # still running would go down with it.
        for worker in self.findChildren(QThread):
            adopt_running(worker)
        super().closeEvent(event)


