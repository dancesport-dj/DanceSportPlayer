"""The duplicate-resolve dialog (🔁 Check duplicates across the decks).

Extracted 1:1 from gui/dialogs.py in the big-module split; gui.dialogs
re-exports the class(es), so existing importers keep working unchanged."""
import html
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QComboBox, QGroupBox,
    QHeaderView, QAbstractItemView, QMessageBox,
    QScrollArea, QDialog, QProgressBar, QFileDialog, QTabWidget,
)
from PySide6.QtCore import (
    Qt, QTimer,
)
from PySide6.QtGui import (
    QColor, QShortcut, QKeySequence,
)


from planner import i18n
from planner.config import replacing_text
from planner.parsing import _detect_bpm, _detect_dance
from planner.terms import dance_name
from planner.planned import path_key
from gui.workers import adopt_running
from gui.common import (  # noqa: F401  (shared primitives)
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


class DuplicateResolveDialog(QDialog):
    """Resolve songs that appear more than once across the playlist decks.

    Each duplicate set lists its occurrences; the user keeps the ones they want
    and switches the rest to **Replace**, picking a similar track for each from
    the standard Similar-Tracks picker. On accept, `resolutions` holds the
    `(slot, new_entry)` swaps the caller should apply — a slot being the copy
    number the report gave each occurrence, which only the caller can turn back
    into a deck and a row."""

    def __init__(self, deck_report: dict, parent, pick_fn, drop_check_fn=None,
                 ref_clean_factory=None, play_cb=None, seek_cb=None):
        super().__init__(parent)
        self.setWindowTitle("Check duplicates")
        self.resize(900, 300)
        self.setMinimumWidth(760)
        self._pick_fn       = pick_fn      # pick_fn(entry) -> MusicEntry | None
        self._drop_check_fn = drop_check_fn  # drop_check_fn(paths) -> [ {title, files} ]
        self._ref_clean_factory = ref_clean_factory  # () -> ReferenceCleanWorker
        self._play_cb       = play_cb      # play_cb(path|None): preview / stop a file
        self._play_btn      = None         # the ▶ button currently showing ■ (playing)
        self._occ_state     = []           # one record per resolvable occurrence
        self._occ_seen      = {}           # slot → state, dedup across sections
        self._cross_cliques = {}           # clique root → member copies (built per report)
        self._slot_clique   = {}           # slot → clique root
        self._drop_busy     = False        # a tab-2 check is running
        self._drop_dirty    = False        # files arrived mid-check → re-run after
        self._ref_path      = None         # tab-3 reference .m3u
        self._ref_worker    = None         # running ReferenceCleanWorker (kept alive)
        self._ref_result    = None         # last comparison result (awaiting export)
        self.resolutions    = []           # filled on accept
        self.finished.connect(lambda _=0: self._stop_preview())
        self.finished.connect(self._let_ref_worker_go)

        # Ctrl+←/→ seek the previewed file ∓30 s — window-level so it fires even when
        # a row's ▶ button (not the dialog) holds keyboard focus.
        if seek_cb is not None:
            QShortcut(QKeySequence("Ctrl+Left"), self,
                      activated=lambda: seek_cb(-30000)).setContext(
                          Qt.ShortcutContext.WindowShortcut)
            QShortcut(QKeySequence("Ctrl+Right"), self,
                      activated=lambda: seek_cb(30000)).setContext(
                          Qt.ShortcutContext.WindowShortcut)

        deck_report = deck_report or {"within": [], "cross": []}
        self._has_dups = bool(deck_report.get("within") or deck_report.get("cross"))
        self._drop_tab_w = None
        self._ref_tab_w = None

        root = QVBoxLayout(self)
        self._tabs = QTabWidget()
        self._decks_tab_w = self._build_decks_tab(deck_report)
        self._tabs.addTab(self._decks_tab_w, "🎚️  Open playlists")
        if drop_check_fn is not None:
            self._drop_tab_w = self._build_drop_tab()
            self._tabs.addTab(self._drop_tab_w, "📂  Drag files in")
        if ref_clean_factory is not None:
            self._ref_tab_w = self._build_reference_tab()
            self._tabs.addTab(self._ref_tab_w, "🧹  Reference base")
        self._tabs.currentChanged.connect(self._update_tab_action)
        self._tabs.currentChanged.connect(self._sync_modality)
        root.addWidget(self._tabs, stretch=1)

        # The right-hand button is context-sensitive per tab: Apply (resolve open-deck
        # duplicates), OK (read-only Drag-files tab) or Export unused (Reference base).
        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("Cancel" if self._has_dups else "Close")
        close.clicked.connect(self.reject)
        btns.addWidget(close)
        self._action_btn = QPushButton()
        self._action_btn.clicked.connect(self._on_tab_action)
        btns.addWidget(self._action_btn)
        root.addLayout(btns)
        self._update_tab_action()
        self._sync_modality()

    def _sync_modality(self, *_):
        """Block the windows below only on the 🎚️ Open playlists tab: its report
        names each copy by its deck row, so the decks must hold still under it.
        The other tabs check files dragged in from outside and never touch a
        deck — there the decks stay usable beside the window."""
        want = (Qt.WindowModality.ApplicationModal
                if self._tabs.currentWidget() is self._decks_tab_w
                else Qt.WindowModality.NonModal)
        if self.windowModality() == want:
            return
        # Qt applies a new modality only when the window is shown again.
        shown = self.isVisible()
        if shown:
            self.hide()
        self.setWindowModality(want)
        if shown:
            self.show()

    def _update_tab_action(self, *_):
        """Relabel / enable the bottom-right action button for the active tab."""
        w = self._tabs.currentWidget()
        btn = self._action_btn
        if w is self._ref_tab_w and w is not None:
            btn.setText("🧹  Export unused")
            btn.setVisible(True)
            # Exportable once a compare has produced tracks — even with 0 duplicates
            # removed, the user may still want the dance-sorted list written out.
            btn.setEnabled(bool(self._ref_result and self._ref_result.get("kept_blocks")))
        elif w is self._drop_tab_w and w is not None:
            btn.setText("OK")
            btn.setVisible(True)
            btn.setEnabled(True)
        elif w is self._decks_tab_w and self._has_dups:
            btn.setText("✅  Apply")
            btn.setVisible(True)
            btn.setEnabled(True)
        else:
            btn.setVisible(False)

    def _on_tab_action(self):
        w = self._tabs.currentWidget()
        if w is self._ref_tab_w and w is not None:
            self._on_ref_export_now()
        elif w is self._decks_tab_w and self._has_dups:
            self._on_apply()
        else:
            self.accept()

    def _build_decks_tab(self, report: dict) -> QWidget:
        """Tab 1 — duplicate songs across the open playlist decks, listed in each deck's
        running order: 🔁 doubled inside one deck, 🔀 shared between two decks. Each real
        occurrence carries a Keep / Replace control so duplicates can be resolved here."""
        w = QWidget()
        lyt = QVBoxLayout(w)
        within = report.get("within", [])
        cross  = report.get("cross", [])
        head = QLabel(
            "Duplicate songs across your open playlist(s), in playlist order."
            "<br><span style='color:#666'>🟰 <b>Exact</b> = identical audio. "
            "≈ <b>Similar</b> = same title, a different recording. Keep the ones you "
            "want; switch the others to <b>Replace</b> and pick a track for each, or "
            "to <b>Remove</b>.</span>")
        head.setWordWrap(True)
        lyt.addWidget(head)
        if not within and not cross:
            ok = QLabel("✅  No duplicate songs across your open playlist(s).")
            ok.setWordWrap(True)
            lyt.addWidget(ok)
            lyt.addStretch(1)
            return w

        self._cross_cliques, self._slot_clique = self._build_cross_cliques(cross)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(2, 2, 2, 2)
        self._fill_report_layout(iv, within, cross,
                                 "🔁  Doubled inside one playlist",
                                 "🔀  Shared between playlists", resolvable=True)
        iv.addStretch(1)
        scroll.setWidget(inner)
        lyt.addWidget(scroll, stretch=1)
        return w

    def _fill_report_layout(self, iv, within, cross, within_label, shared_label,
                            resolvable: bool = False):
        """Render a within/cross duplicate report into layout `iv`. Shared by tab 1
        (open decks, resolvable) and tab 2 (dropped files, read-only)."""
        if within:
            iv.addWidget(self._section_heading(within_label))
            for fe in within:
                iv.addWidget(self._within_box(fe, resolvable))
        if cross:
            iv.addWidget(self._section_heading(shared_label))
            for pe in cross:
                iv.addWidget(self._cross_box(pe, resolvable))

    def _build_drop_tab(self) -> QWidget:
        """Tab 2 — drag loose files in and report which are duplicates of each other."""
        w = QWidget()
        lyt = QVBoxLayout(w)
        info = QLabel("Drag <b>.m3u playlists</b> here (audio files work too) to check "
                      "whether any of their tracks are duplicates of <b>each other</b> — "
                      "across the dropped playlists, by audio content, else title.")
        info.setWordWrap(True)
        lyt.addWidget(info)

        self._drop_zone = _MultiFileDropZone()
        self._drop_zone.filesDropped.connect(lambda ps: self._drop_files.add_paths(ps))
        lyt.addWidget(self._drop_zone)

        self._drop_files = _DroppedFilesList()
        self._drop_files.changed.connect(self._refresh_drop_results)
        lyt.addWidget(self._drop_files)

        self._drop_pbar = QProgressBar()
        self._drop_pbar.setVisible(False)
        lyt.addWidget(self._drop_pbar)

        self._drop_results = QScrollArea()
        self._drop_results.setWidgetResizable(True)
        lyt.addWidget(self._drop_results, stretch=1)
        self._refresh_drop_results()
        return w

    def _drop_progress(self, done: int, total: int):
        # Only bother showing the bar for sizeable loads — short ones finish instantly.
        if total <= 12:
            return
        self._drop_pbar.setVisible(True)
        self._drop_pbar.setRange(0, total)
        self._drop_pbar.setValue(done)
        QApplication.processEvents()

    def _refresh_drop_results(self):
        # processEvents() during the check can deliver another drop, re-entering here;
        # defer it instead so the running pass finishes first.
        if self._drop_busy:
            self._drop_dirty = True
            return
        self._drop_busy = True
        try:
            self._run_drop_check()
        finally:
            self._drop_busy = False
            self._drop_pbar.setVisible(False)
        if self._drop_dirty:
            self._drop_dirty = False
            QTimer.singleShot(0, self._refresh_drop_results)

    def _run_drop_check(self):
        paths = self._drop_files.paths()
        n = len(paths)
        report = (self._drop_check_fn([Path(p) for p in paths],
                                      progress_cb=self._drop_progress)
                  if n and self._drop_check_fn else {"within": [], "cross": []})
        within, cross = report.get("within", []), report.get("cross", [])
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(2, 2, 2, 2)
        if not n:
            iv.addWidget(QLabel("Drop some files above to check them."))
        elif not within and not cross:
            iv.addWidget(QLabel((i18n.t("✅  No duplicates among the %d file added.") if n == 1
                                 else i18n.t("✅  No duplicates among the %d files added.")) % n))
        else:
            self._fill_report_layout(iv, within, cross,
                                     "🔁  Doubled inside a playlist",
                                     "🔀  Shared between playlists")
        iv.addStretch(1)
        self._drop_results.setWidget(inner)

    # ── Tab 3 — reference base (export unused) ────────────────────────────────
    def _build_reference_tab(self) -> QWidget:
        """Tab 3 — the old TurnierCheck 'Referenzbasis': drop one reference .m3u and the
        tournament files it should be compared against, then export the reference minus
        every hard (byte-identical) duplicate that already appears in the tournament
        files. Paso Doble is left untouched (excluded from the comparison)."""
        w = QWidget()
        lyt = QVBoxLayout(w)
        info = QLabel(
            "Drop a <b>reference playlist</b> (.m3u) and the <b>tournament files</b> "
            "(.m3u playlists or audio) below. The reference is compared against the "
            "tournament tracks and every <b>hard duplicate</b> (byte-identical audio) is "
            "removed; the leftover <b>unused</b> tracks are exported to a new .m3u. "
            "<span style='color:#666'>Paso Doble is excluded from the comparison and "
            "always kept.</span>")
        info.setWordWrap(True)
        lyt.addWidget(info)

        lyt.addWidget(self._section_heading("📌  Reference base (single .m3u)"))
        self._ref_zone = _MultiFileDropZone()
        self._ref_zone.filesDropped.connect(self._on_ref_dropped)
        lyt.addWidget(self._ref_zone)
        self._ref_lbl = QLabel("No reference playlist yet.")
        self._ref_lbl.setStyleSheet("color:#556; font-size:11px;")
        lyt.addWidget(self._ref_lbl)

        lyt.addWidget(self._section_heading("🎯  Tournament files (compared against)"))
        self._ref_tour_zone = _MultiFileDropZone()
        self._ref_tour_zone.filesDropped.connect(
            lambda ps: self._ref_tour_files.add_paths(ps))
        lyt.addWidget(self._ref_tour_zone)
        self._ref_tour_files = _DroppedFilesList(clear_hook=self._reset_reference_base)
        self._ref_tour_files.changed.connect(self._on_ref_inputs_changed)
        lyt.addWidget(self._ref_tour_files)

        self._ref_pbar = QProgressBar()
        self._ref_pbar.setVisible(False)
        lyt.addWidget(self._ref_pbar)

        self._ref_compare_btn = QPushButton("🔍  Compare")
        self._ref_compare_btn.setEnabled(False)
        self._ref_compare_btn.clicked.connect(self._on_ref_compare)
        lyt.addWidget(self._ref_compare_btn)

        self._ref_summary = QLabel("")
        self._ref_summary.setWordWrap(True)
        lyt.addWidget(self._ref_summary)

        # Overview of what the export will drop / keep — a playlist-style table,
        # shown after a comparison.
        self._ref_overview = QTableWidget(0, 5)
        self._ref_overview.setHorizontalHeaderLabels(["", "Dance", "Title", "Takt", "File"])
        self._ref_overview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._ref_overview.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._ref_overview.setAlternatingRowColors(True)
        self._ref_overview.verticalHeader().setVisible(False)
        hh = self._ref_overview.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._ref_overview.setVisible(False)
        lyt.addWidget(self._ref_overview, stretch=1)

        # Export action lives on the dialog's bottom button row (see _update_tab_action).
        lyt.addStretch(0)
        return w

    def _on_ref_dropped(self, paths: list):
        m3us = [p for p in paths if str(p).lower().endswith((".m3u", ".m3u8"))]
        if not m3us:
            QMessageBox.warning(self, "Reference base",
                                "The reference base must be a single .m3u playlist.")
            return
        self._ref_path = Path(m3us[0])
        self._ref_lbl.setText(f"📌  {self._ref_path.name}")
        self._on_ref_inputs_changed()

    def _reset_reference_base(self):
        """Clear the chosen reference .m3u (used as the 🗑 Clear hook on the tournament
        list, so one Clear wipes both the reference base and the tournament files)."""
        self._ref_path = None
        self._ref_lbl.setText("No reference playlist yet.")
        self._on_ref_inputs_changed()

    def _on_ref_inputs_changed(self):
        # Inputs changed → any earlier comparison is stale; hide the overview.
        self._ref_result = None
        self._ref_summary.setText("")
        self._ref_overview.setVisible(False)
        self._update_tab_action()
        self._ref_compare_btn.setEnabled(
            bool(self._ref_path) and bool(self._ref_tour_files.paths())
            and self._ref_worker is None)

    def _on_ref_progress(self, done: int, total: int):
        self._ref_pbar.setVisible(True)
        self._ref_pbar.setRange(0, total)
        self._ref_pbar.setValue(done)

    def _on_ref_compare(self):
        tour = self._ref_tour_files.paths()
        if not (self._ref_path and tour) or self._ref_worker is not None:
            return
        self._ref_summary.setText("⏳  Comparing…")
        self._ref_overview.setVisible(False)
        self._update_tab_action()
        self._ref_compare_btn.setEnabled(False)
        worker = self._ref_clean_factory(self._ref_path, tour)
        worker.progress.connect(self._on_ref_progress)
        worker.done.connect(self._on_ref_done)
        worker.failed.connect(self._on_ref_failed)
        worker.finished.connect(self._on_ref_worker_finished)
        self._ref_worker = worker
        worker.start()

    def _let_ref_worker_go(self, _result=0):
        """The compare has no parent, only this dialog holds it — and the
        dialog goes when the main window does. Destroying it mid-run aborts
        the process, and `_stop_workers` only finds children."""
        if self._ref_worker is not None:
            adopt_running(self._ref_worker)

    def _on_ref_worker_finished(self):
        self._ref_worker = None
        self._ref_pbar.setVisible(False)
        self._ref_compare_btn.setEnabled(
            bool(self._ref_path) and bool(self._ref_tour_files.paths()))

    def _on_ref_failed(self, msg: str):
        self._ref_summary.setText("")
        QMessageBox.critical(self, "Reference base", i18n.t("Comparison failed:\n%s") % msg)

    def _on_ref_done(self, result: dict):
        removed = result.get("removed", [])
        kept_blocks = result.get("kept_blocks", [])
        ref_total = result.get("ref_total", 0)
        pd_kept = result.get("pd_kept", 0)
        self._ref_result = result
        self._ref_summary.setText(
            i18n.t("✅  %d hard duplicate(s) to remove, %d unused track(s) to export "
                   "(of %d; %d Paso Doble kept). Review below, then export.")
            % (len(removed), len(kept_blocks), ref_total, pd_kept))
        # Overview: the tracks that will be removed, then the ones that will be kept.
        rows = [("🗑", "#b3261e", Path(p), title) for p, title in removed]
        rows += [("✅", "#1b7f3b", blk["path"], blk.get("title") or blk["path"].stem)
                 for blk in kept_blocks]
        self._fill_ref_overview(rows)
        self._update_tab_action()
        if not removed:
            QMessageBox.information(
                self, "Reference base",
                "No hard duplicates of the tournament files were found in the "
                "reference — nothing to remove.")

    def _fill_ref_overview(self, rows: list):
        """Render the overview table from rows of (mark, colour_hex, Path, title)."""
        self._ref_overview.setRowCount(len(rows))
        for r, (mark, colour, path, title) in enumerate(rows):
            dance = _detect_dance(path.name.replace("_", " ")) or ""
            bpm = _detect_bpm(path.name)
            takt = str(bpm) if bpm else ""
            cells = [mark, dance, title, takt, path.name]
            for c, text in enumerate(cells):
                it = QTableWidgetItem(text)
                it.setForeground(QColor(colour))
                if c == 4:
                    it.setToolTip(str(path))
                self._ref_overview.setItem(r, c, it)
        self._ref_overview.resizeColumnsToContents()
        hh = self._ref_overview.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._ref_overview.setVisible(True)

    def _on_ref_export_now(self):
        result = self._ref_result
        if not result:
            return
        kept_blocks = result.get("kept_blocks", [])
        removed = result.get("removed", [])
        ref_path = Path(result.get("ref_path"))
        default = ref_path.with_name(f"{ref_path.stem}_cleaned.m3u")
        out, _ = QFileDialog.getSaveFileName(
            self, "Export unused tracks", str(default),
            "Playlists (*.m3u *.m3u8);;All files (*)")
        if not out:
            return
        sort_by_dance = QMessageBox.question(
            self, "Export unused tracks",
            "Sort the exported tracks by dance?\n\n"
            "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes) == QMessageBox.StandardButton.Yes
        blocks = kept_blocks
        if sort_by_dance:
            # Tournament dance order; underscores normalised so 'PD_58_…' is detected.
            order = ["LW", "TG", "WW", "SF", "QS", "SA", "CC", "RB", "PD", "JI"]
            rank = {d: i for i, d in enumerate(order)}
            blocks = sorted(kept_blocks, key=lambda b: rank.get(
                _detect_dance(b["path"].name.replace("_", " ")) or "",
                len(order)))  # stable: unknown dances keep their order, at the end
        try:
            lines = ["#EXTM3U"]
            for blk in blocks:
                lines.extend(blk["raw"])
            with replacing_text(Path(out)) as f:
                f.write("\n".join(lines) + "\n")
        except Exception as exc:
            QMessageBox.critical(self, "Reference base", i18n.t("Could not write file:\n%s") % exc)
            return
        # Only claim the reference is untouched when it really is a different file.
        try:
            overwrote_ref = Path(out).resolve() == ref_path.resolve()
        except Exception:
            overwrote_ref = path_key(out) == path_key(ref_path)
        note = (i18n.t("The reference playlist itself was overwritten with the cleaned list.")
                if overwrote_ref else i18n.t("The reference playlist was left unchanged."))
        # Reflect what was actually written: drop the removed rows and adopt the exported
        # (possibly re-sorted) order in both the table and the stored result.
        result["kept_blocks"] = blocks
        result["removed"] = []
        self._fill_ref_overview(
            [("✅", "#1b7f3b", blk["path"], blk.get("title") or blk["path"].stem)
             for blk in blocks])
        self._ref_summary.setText(
            (i18n.t("📤  Exported %d track(s) (sorted by dance) → %s") if sort_by_dance
             else i18n.t("📤  Exported %d track(s) → %s")) % (len(blocks), Path(out).name))
        QMessageBox.information(
            self, "Reference base",
            i18n.t("Exported %d unused track(s) to:\n%s\n\n%d hard duplicate(s) removed. %s")
            % (len(blocks), out, len(removed), note))

    @staticmethod
    def _section_heading(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight:bold; font-size:13px; color:#2c3e60;"
                          " margin-top:8px;")
        return lbl

    @staticmethod
    def _dup_badge(kind: str) -> str:
        if kind == "exact":
            return "<span style='color:#b3261e; font-weight:bold;'>🟰 Exact copy</span>"
        return "<span style='color:#1565c0; font-weight:bold;'>≈ Similar title</span>"

    def _within_box(self, fe: dict, resolvable: bool = False) -> QGroupBox:
        box = QGroupBox(f"📁  {fe['file']}")
        bv = QVBoxLayout(box)
        for cl in fe["clusters"]:
            idxs = " ↔ ".join(f"#{m['idx']}" for m in cl["members"])
            head = QLabel(f"{self._dup_badge(cl['kind'])} &nbsp; {idxs}")
            bv.addWidget(head)
            # Similar (not exact) → the files differ, so show each filename to compare.
            similar = cl["kind"] == "similar"
            for m in cl["members"]:
                bv.addWidget(self._dup_track_widget(m, show_file=similar,
                                                    resolvable=resolvable))
        return box

    def _cross_box(self, pe: dict, resolvable: bool = False) -> QGroupBox:
        """Songs shared between two playlists, side by side: one column per playlist
        (📁 its name, then '#position  filename' per shared song) and — when the decks
        are live — an Action column to Keep both or Replace the copy in either one."""
        box = QGroupBox()
        grid = QGridLayout(box)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        grid.addWidget(self._col_header(f"📁  {pe['file_a']}"), 0, 0)
        grid.addWidget(self._col_header(f"📁  {pe['file_b']}"), 0, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 3)
        if resolvable:
            grid.addWidget(self._col_header("Action"), 0, 2)
            grid.setColumnStretch(2, 2)
        r = 1
        for kind, pairs in (("exact", pe["exact"]), ("similar", pe["similar"])):
            if not pairs:
                continue
            badge = QLabel(f"{self._dup_badge(kind)} &nbsp; "
                           f"<span style='color:#556;'>({len(pairs)})</span>")
            grid.addWidget(badge, r, 0, 1, 3 if resolvable else 2)
            r += 1
            for pr in pairs:
                a, b = pr["a"], pr["b"]
                grid.addWidget(self._pair_cell(a), r, 0)
                grid.addWidget(self._pair_cell(b), r, 1)
                if resolvable:
                    grid.addWidget(self._pair_action_cell(a, b, pe), r, 2)
                r += 1
        return box

    @staticmethod
    def _col_header(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight:bold; font-size:11px; color:#2c3e60;")
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def _short(name: str, n: int = 16) -> str:
        return name if len(name) <= n else name[:n - 1] + "…"

    def _pair_cell(self, rec: dict) -> QWidget:
        """'#position  filename' for one shared song, with the title + path as tooltip
        and a ▶ button to preview the file (when a player callback is available)."""
        name = Path(rec["path"]).name if rec.get("path") else rec.get("title", "")
        lbl = QLabel(f"<b>#{rec.get('idx', '')}</b>&nbsp; {html.escape(name)}")
        lbl.setWordWrap(True)
        # Escaped like every other tooltip built from track metadata (see
        # _entry_tooltip): a tooltip is rich text too, so an <img> in a title
        # would be fetched.
        lbl.setToolTip(html.escape(
            f"{rec.get('title', '')}\n{rec.get('path', '')}".strip()))
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setStyleSheet("font-size:11px;")
        btn = self._make_play_btn(rec.get("path", ""))
        if btn is None:
            return lbl
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(btn, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(lbl, 1)
        return w

    def _make_play_btn(self, path: str) -> QPushButton | None:
        """A ▶ preview button wired to _toggle_play, or None when there's no player
        callback / path. Shared by the shared-pair cells and the within-playlist rows.
        (Named _make_play_btn — _play_btn is the instance attr for the playing button.)"""
        if not (self._play_cb and path):
            return None
        btn = QPushButton("▶")
        btn.setFixedSize(26, 20)
        btn.setStyleSheet("padding:0;")
        btn.setToolTip("Play / stop this file")
        btn.setProperty("path", path)
        btn.clicked.connect(lambda _=False, p=path, b=btn: self._toggle_play(p, b))
        return btn

    def _toggle_play(self, path: str, btn: QPushButton):
        """Preview one file, or stop it if it's the one already playing."""
        if not self._play_cb:
            return
        if self._play_btn is btn:                 # same file → stop
            self._stop_preview()
            return
        if self._play_btn is not None:            # switch from another file
            self._play_btn.setText("▶")
        self._play_btn = btn
        btn.setText("■")
        self._release_decks()
        self._play_cb(Path(path))

    def _release_decks(self):
        """The preview takes the decks' shared player over — the row that was
        running has to give its ■ back, or it keeps claiming the music (as in
        SimilarTracksDialog)."""
        host = self.parentWidget()
        release = getattr(host.window(), "release_play_markers", None) if host else None
        if release is not None:
            release()

    def _stop_preview(self):
        """Stop the preview (its ■, or the dialog closing) — but only while the
        player is still on it. The decks share the player and stay usable beside
        the drag-in tabs, so a title started there since is the live music."""
        btn, self._play_btn = self._play_btn, None
        if btn is None or not self._play_cb:
            return
        btn.setText("▶")
        host = self.parentWidget()
        deck_path = getattr(host.window(), "deck_path", None) if host else None
        if deck_path is not None and deck_path() != Path(btn.property("path")):
            return
        self._play_cb(None)

    @staticmethod
    def _build_cross_cliques(cross):
        """Group cross-playlist duplicate slots into cliques (a song in N playlists is
        one clique of N copies, however the pairwise rows split it up). Returns
        (cliques, slot_root): `cliques[root]` is the member list [{slot,entry,
        playlist,idx,path}, …]; `slot_root[slot]` maps each slot to its clique
        root. Slots are unioned whenever they share a duplicate pair."""
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            r = x
            while parent[r] != r:
                r = parent[r]
            while parent[x] != r:
                parent[x], x = r, parent[x]
            return r

        occ = {}
        for pe in cross or []:
            for kind in ("exact", "similar"):
                for pr in pe.get(kind, []):
                    keys = []
                    for side, fname in ((pr.get("a"), pe.get("file_a")),
                                        (pr.get("b"), pe.get("file_b"))):
                        if (not side or side.get("entry") is None
                                or side.get("slot") is None):
                            continue
                        k = side["slot"]
                        occ[k] = {"slot": k, "entry": side["entry"],
                                  "playlist": fname or "", "idx": side.get("idx"),
                                  "path": side.get("path", "")}
                        find(k)
                        keys.append(k)
                    if len(keys) == 2:
                        parent[find(keys[1])] = find(keys[0])

        cliques, slot_root = {}, {}
        for k in occ:
            r = find(k)
            cliques.setdefault(r, []).append(occ[k])
            slot_root[k] = r
        for members in cliques.values():
            members.sort(key=lambda m: (str(m["playlist"]), m["idx"] or 0))
        return cliques, slot_root

    def _pair_action_cell(self, a: dict, b: dict, pe: dict) -> QWidget:
        """A Keep / Replace combo for the song shared on this row. It lists EVERY
        playlist the song is in (so a 3- or 4-playlist duplicate is reachable from any
        row), and the SAME combo is repeated on each row the song occupies: pick a
        different copy on each row to replace several at once. The per-row choices are
        merged — deduped by slot — when Apply is pressed. Copies already controlled by
        the within-playlist section are skipped (no double control)."""
        root = None
        for side in (a, b):
            if side.get("slot") is not None:
                root = self._slot_clique.get(side["slot"])
                if root is not None:
                    break
        members = [m for m in self._cross_cliques.get(root, [])
                   if m["slot"] not in self._occ_seen]
        if not members:
            return self._resolved_above_label()
        return self._clique_control(members)

    @staticmethod
    def _resolved_above_label() -> QLabel:
        lbl = QLabel("↑ resolved above")
        lbl.setStyleSheet("color:#aaa; font-size:11px;")
        lbl.setToolTip(
            "Every copy of this song is already controlled by the within-playlist\n"
            "section above, so there is nothing left to resolve on this row.")
        return lbl

    def _clique_control(self, members: list) -> QWidget:
        """One Keep-all / Replace-in / Remove-from-<playlist> combo covering every copy
        of a song. 'Keep all' is a no-op for this row; Replace in a playlist opens the
        track picker for that one copy, Remove from it takes the copy out. One such
        combo is built per row the song occupies, each an independent 'clique'
        state; Apply merges them (dedup by slot). The chosen
        slots are NOT registered in `_occ_seen` — the within-playlist section owns that
        dedup, and several rows pointing at the same copy is resolved at Apply, not here."""
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        combo = QComboBox()
        combo.addItem("✅  Keep all", -1)
        for i, m in enumerate(members):
            combo.addItem(i18n.t("🔁  Replace in %s") % self._short(m['playlist']), i)
        for i, m in enumerate(members):
            combo.addItem(i18n.t("🗑  Remove from %s") % self._short(m['playlist']),
                          ("remove", i))
        combo.setMinimumWidth(170)
        row.addWidget(combo)
        # 3+ playlists → flag the row to the RIGHT of the combo (so the combo keeps its
        # size/position): replacing one copy still leaves the rest, so the user must act
        # on more than this single row to clear the song everywhere.
        if len(members) > 2:
            mark = QLabel("❗")
            mark.setStyleSheet("color:#c62828; font-weight:bold;")
            mark.setToolTip(
                i18n.t("This song is in %d open playlists. Replacing it on one\n"
                       "row leaves the other copies — pick a copy on each of its rows to\n"
                       "replace them all (the choices are merged when you press Apply).")
                % len(members))
            row.addWidget(mark)
        repl_lbl = QLabel("")
        repl_lbl.setTextFormat(Qt.TextFormat.PlainText)   # _repl_text carries a track title
        repl_lbl.setStyleSheet("color:#1565c0; font-size:11px;")
        repl_lbl.setToolTip("Pick a playlist again to choose a different track")
        row.addWidget(repl_lbl, stretch=1)

        state = {"kind": "clique", "combo": combo, "repl_lbl": repl_lbl,
                 "replacement": None, "members": members}
        self._occ_state.append(state)

        def on_action(_idx, st=state):
            st["replacement"] = None
            st["repl_lbl"].setText("")
            i = st["combo"].currentData()
            if not isinstance(i, int) or i < 0:   # Keep all, or a Remove
                return
            new = self._pick_fn(st["members"][i]["entry"])
            if new is not None:
                st["replacement"] = new
                st["repl_lbl"].setText(self._repl_text(new))
            else:
                st["combo"].setCurrentIndex(0)        # cancelled → back to Keep all
        combo.activated.connect(on_action)
        return w

    def _dup_track_widget(self, rec: dict, show_file: bool, resolvable: bool):
        """One track line in the duplicate report. Read-only → a plain label; resolvable
        and backed by a real deck slot → the same line plus a Keep / Replace control
        (created once per occurrence, deduped across sections via `_occ_seen`)."""
        title = self._title_with_file(rec) if show_file else html.escape(rec.get("title", ""))
        prefix = f"#{rec.get('idx', '')}"
        key = rec.get("slot")
        if (not resolvable or key is None or rec.get("entry") is None
                or key in self._occ_seen):
            lbl = self._track_line(title, rec.get("path", ""), prefix=prefix)
            btn = self._make_play_btn(rec.get("path", ""))
            if btn is None:
                return lbl
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            row.addWidget(btn, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(lbl, 1)
            return w
        return self._resolve_row(rec, title, prefix, key)

    def _resolve_row(self, rec: dict, title: str, prefix: str, key) -> QWidget:
        """A track line with a Keep / Replace combo, registered for the Apply step."""
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        btn = self._make_play_btn(rec.get("path", ""))
        if btn is not None:
            row.addWidget(btn, 0, Qt.AlignmentFlag.AlignTop)
        lbl = QLabel(f"<b>{prefix}</b> &nbsp; {title}")
        lbl.setWordWrap(True)
        lbl.setToolTip(rec.get("path", ""))
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setStyleSheet("font-size:11px; margin-left:10px;")
        row.addWidget(lbl, stretch=2)

        combo = QComboBox()
        combo.addItem("✅  Keep", "keep")
        combo.addItem("🔁  Replace…", "replace")
        combo.addItem("🗑  Remove", "remove")
        combo.setFixedWidth(130)
        row.addWidget(combo)

        repl_lbl = QLabel("")
        repl_lbl.setTextFormat(Qt.TextFormat.PlainText)   # _repl_text carries a track title
        repl_lbl.setStyleSheet("color:#1565c0; font-size:11px;")
        repl_lbl.setToolTip("Pick “Replace…” again to choose a different track")
        row.addWidget(repl_lbl, stretch=1)

        state = {"kind": "single",
                 "occ": {"entry": rec["entry"], "slot": rec["slot"]},
                 "combo": combo, "repl_lbl": repl_lbl, "replacement": None}
        self._occ_state.append(state)
        self._occ_seen[key] = state

        def on_action(_idx, st=state):
            if st["combo"].currentData() != "replace":
                st["replacement"] = None
                st["repl_lbl"].setText("")
                return
            self._choose_replacement(st, auto=True)
        combo.activated.connect(on_action)
        return w

    @staticmethod
    def _title_with_file(rec: dict) -> str:
        """'Title · filename.mp3' — the filename muted, so similar (different-file)
        matches can be told apart at a glance."""
        fname = html.escape(Path(rec["path"]).name)
        return (f"{html.escape(rec['title'])}"
                f"  <span style='color:#777;'>· {fname}</span>")

    @staticmethod
    def _track_line(title: str, path_tip: str, prefix: str = "") -> QLabel:
        head = f"<b>{prefix}</b> &nbsp; " if prefix else ""
        lbl = QLabel(f"{head}{title}")
        lbl.setWordWrap(True)
        lbl.setToolTip(path_tip)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setStyleSheet("font-size:11px; margin-left:10px;")
        return lbl

    @staticmethod
    def _repl_text(entry) -> str:
        genre = dance_name(entry.dance, entry.dance or "")
        prefix = f"[{genre}] " if genre else ""
        return f"→ {prefix}{entry.title[:40]}"

    def _choose_replacement(self, st: dict, auto: bool = False):
        new = self._pick_fn(st["occ"]["entry"])
        if new is not None:
            st["replacement"] = new
            st["repl_lbl"].setText(self._repl_text(new))
        elif auto and st["replacement"] is None:
            # Auto-opened picker was cancelled with nothing chosen → revert to Keep.
            st["combo"].setCurrentIndex(0)

    def pending_replacements(self) -> list:
        """The tracks picked as replacements so far, not yet applied."""
        return [st["replacement"] for st in self._occ_state
                if st["replacement"] is not None]

    @staticmethod
    def _chosen_occ(st: dict):
        """(occurrence, action) a state resolves to — the occurrence is its entry +
        slot, the action "replace" or "remove" — or None when set to Keep. A
        within-playlist 'single' state acts on its one slot; a cross-playlist
        'clique' state on the slot of the playlist picked in its combo."""
        data = st["combo"].currentData()
        if st.get("kind") == "clique":
            if isinstance(data, int) and data >= 0:
                return st["members"][data], "replace"
            if isinstance(data, tuple):
                return st["members"][data[1]], "remove"
            return None
        return (st["occ"], data) if data in ("replace", "remove") else None

    def _on_apply(self):
        # A song in N playlists shows the same Keep / Replace combo on each of its N
        # rows, so the user may target the same copy from more than one row. Consolidate:
        # collect every Replace / Remove choice keyed by deck slot, so each slot is
        # changed at most once. Two rows asking to replace the SAME slot with
        # DIFFERENT tracks, or to replace one copy another row removes, is a genuine
        # conflict the user must settle. A removal travels as (slot, None).
        chosen = {}          # slot → (slot, replacement or None)
        missing = 0
        conflicts = 0
        for st in self._occ_state:
            picked = self._chosen_occ(st)
            if picked is None:
                continue
            occ, action = picked
            new = st["replacement"] if action == "replace" else None
            if action == "replace" and new is None:
                missing += 1
                continue
            slot = occ["slot"]
            prev = chosen.get(slot)
            if prev is not None and not self._same_entry(prev[1], new):
                conflicts += 1
                continue
            chosen[slot] = (slot, new)
        if missing:
            QMessageBox.warning(
                self, "Resolve duplicates",
                i18n.t("%d occurrence(s) are set to Replace but have no replacement "
                       "track yet.\nPick a track for each, or switch them back to Keep.") % missing)
            return
        if conflicts:
            QMessageBox.warning(
                self, "Resolve duplicates",
                i18n.t("%d copy/copies are set to two different changes on "
                       "different rows.\nChoose the same on each, or set one back "
                       "to Keep all.") % conflicts)
            return
        resolutions = list(chosen.values())
        if not resolutions:
            QMessageBox.information(
                self, "Resolve duplicates",
                "Nothing to change — no occurrence is set to Replace or Remove.")
            return
        self.resolutions = resolutions
        self.accept()

    @staticmethod
    def _same_entry(a, b) -> bool:
        """Whether two replacement entries point at the same track (by path, falling
        back to identity for entries without a path)."""
        pa = getattr(a, "path", None)
        pb = getattr(b, "path", None)
        if pa is not None and pb is not None:
            return str(pa) == str(pb)
        return a is b


