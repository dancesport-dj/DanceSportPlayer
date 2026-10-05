"""🔗 Broken paths: finding the moved library again and rewriting what points at it.

Split off gui/main_import.py as a MainWindow mixin. A playlist written on
another machine names files that aren't there any more; this maps them onto the
search folders the operator picks — in the decks, in the 🎛 cartwall pads and in
dropped .m3u files.
"""
import logging

import html
from dataclasses import replace
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from planner.models import MusicEntry
from shared.widgets import (
    _show_toast,
)
from gui.dialogs import (  # auto-resolved
    FileDropCheckPanel,
)
from planner import cartwall, i18n
from planner.paths import PathRemapper, foreign_name, home_search_roots
from planner.playlist_text import rerooted, rewrite_playlist_paths

log = logging.getLogger("dancesport.gui.paths")


class PathFixMixin:
    """🔗 Re-pointing broken track paths at a reference folder."""

    def _fix_deck_paths(self):
        """🧭: open the path-fixer. Tab 1 re-roots broken references in the OPEN decks
        (live swap, Ctrl+Z undoes) the moment it opens and reports valid tracks off
        the Referenzpfad, which 🧭 Fix swaps onto their copy there; tab 2 lets you drag .m3u
        playlists in and rewrite their broken track paths on disk via the search folders."""
        dlg = QDialog(self)
        dlg.setWindowTitle("🧭  Fix paths")
        dlg.resize(720, 520)
        lyt = QVBoxLayout(dlg)
        tabs = QTabWidget()

        # Tab 1 — open decks: run the fix straight away (keeps the old one-click feel).
        deck_tab = QWidget()
        dv = QVBoxLayout(deck_tab)
        result = QLabel(self._run_deck_path_fix())
        result.setWordWrap(True)
        result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dv.addWidget(result)
        dv.addStretch(1)
        tabs.addTab(deck_tab, "🎚️  Open playlists")

        # Tab 2 — drag .m3u files in and rewrite their broken path lines on disk. The
        # Fix button + summary live in the dialog's shared bottom row (below), not in
        # the panel, so they sit next to Close.
        panel = FileDropCheckPanel(
            "Drag <b>.m3u playlists</b> here to check their track paths against the "
            "<b>search folders</b> (Settings). Broken references <b>and valid paths on a "
            "different root</b> (e.g. C:) that can be re-rooted there are listed per "
            "playlist; <b>🧭 Fix &amp; overwrite</b> rewrites those "
            "path lines <b>in place</b> — only the file path changes, every #EXTINF / "
            "comment line is kept exactly as-is.",
            run_fn=self._check_dropped_paths)
        tabs.addTab(panel, "📂  Drag files in")

        lyt.addWidget(tabs, stretch=1)

        # Bottom row: summary (left) + 🧭 Fix (overwrite) + Close. The Fix button only
        # applies to the dropped-files tab and lights up (orange) when fixes are pending.
        summary = QLabel("")
        summary.setWordWrap(True)
        fix_btn = QPushButton("🧭  Fix (overwrite)")
        fix_btn.setEnabled(False)

        def _on_fixable(info: dict):
            n = info.get("fixable", 0)
            on_drop_tab = tabs.currentWidget() is panel
            fix_btn.setEnabled(n > 0 and on_drop_tab)
            if not on_drop_tab:
                _deck_tab_state()
                return
            fix_btn.setText("🧭  Fix (overwrite)")
            n_pl = info.get("playlists", 0)
            counts = (i18n.t("%d valid · %d unresolved across %d playlist.") if n_pl == 1
                      else i18n.t("%d valid · %d unresolved across %d playlists.")) % (
                info.get("valid", 0), info.get("unresolved", 0), n_pl)
            if n:
                summary.setText(
                    "<b style='color:#e07b00;'>"
                    + (i18n.t("🔧 %d path line to fix") if n == 1
                       else i18n.t("🔧 %d path lines to fix")) % n
                    + "</b> · " + counts)
            elif n_pl:
                summary.setText(
                    "<span style='color:#2a7a45;'>" + i18n.t("✅ Nothing to fix")
                    + "</span> · " + counts)
            else:
                summary.setText("")

        def _deck_tab_state():
            # Tab 1: Fix swaps the deck tracks that have a copy on the Referenzpfad.
            n = len(self._deck_reference_rows()[0])
            fix_btn.setText("🧭  Fix (swap in playlists)")
            fix_btn.setEnabled(n > 0)
            summary.setText(
                "<b style='color:#e07b00;'>"
                + (i18n.t("🔧 %d track can be moved onto the Referenzpfad") if n == 1
                   else i18n.t("🔧 %d tracks can be moved onto the Referenzpfad")) % n
                + "</b>" if n else "")

        panel.resultsReady.connect(_on_fixable)
        # Off while a check runs — a click mid-check would rewrite the playlists
        # it is still reading; `_on_fixable` lights it again from the result.
        panel.checkStarted.connect(lambda: fix_btn.setEnabled(False))
        # Re-evaluate the summary/button when switching tabs.
        tabs.currentChanged.connect(lambda *_: panel.refresh())

        def _do_fix():
            if tabs.currentWidget() is deck_tab:
                self._swap_decks_to_reference()
                result.setText(self._run_deck_path_fix())
                _deck_tab_state()
                return
            self._fix_dropped_paths(panel.paths())
            panel.refresh()

        fix_btn.clicked.connect(_do_fix)

        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        row = QHBoxLayout()
        row.addWidget(summary, stretch=1)
        row.addWidget(fix_btn)
        row.addWidget(close)
        lyt.addLayout(row)
        _deck_tab_state()
        dlg.exec()

    def _remap_index(self):
        """(by_name, by_path, remapper) shared by deck and dropped-file path fixing:
        filename→library entries, full-path→entry, and the remapper built from the
        Referenzpfad, the extra search folders (Settings) and — away from Windows —
        the user's home folder, in that order."""
        by_name: dict[str, list[MusicEntry]] = {}
        by_path: dict[str, MusicEntry] = {}
        lib = self._lib
        if lib and lib.entries:
            for e in lib.entries:
                by_name.setdefault(Path(e.path).name.lower(), []).append(e)
                by_path[str(Path(e.path)).lower()] = e
        roots = [self._settings.get("reference_path") or ""]
        roots += self._settings.get("remap_paths") or []
        # Last: on a Mac the C:/F: paths of a carried-over playlist point at
        # drives that cannot exist, and a fresh install there has nothing
        # configured to try instead. Never on Windows, where those drives are
        # this PC's own.
        roots += home_search_roots()
        return by_name, by_path, PathRemapper(roots)

    def _path_fix_tables(self) -> list:
        """The tables the "Open playlists" tab checks: the visible decks, every
        wishlist, and the 🤸 Eintanzen panel.

        The panel is neither a deck nor a wishlist, and while it was left out the
        dialog answered a party list full of dead references with "all valid" —
        it had only ever looked at the decks."""
        tables = self._visible_deck_tables() + list(getattr(self, "_wishlists", []))
        if self._warmup_has_content():
            tables.append(self._warmup_table)
        return tables

    def _run_deck_path_fix(self) -> str:
        """Relocate broken track references in the visible deck(s) — first by re-rooting
        under the search folders, then by a same-named library file — applying the swaps
        live. Returns an HTML summary for the dialog."""
        lib = self._lib
        if not lib or not lib.entries:
            return "The library is still loading — try again in a moment."
        by_name, by_path, remapper = self._remap_index()
        checked = ok = fixed = 0
        unresolved: list[str] = []
        for table in self._path_fix_tables():
            changed = False
            for r, m in table._row_meta.numbered():
                e = m.entry
                checked += 1
                p = Path(e.path)
                try:
                    exists = p.exists()
                except OSError:
                    exists = False
                if exists:
                    ok += 1
                    continue
                repl = None
                # 1) Re-root under the search folders, keeping the subfolder + filename
                #    — handles the files living at a different base path on this PC.
                remapped = remapper.remap(p)
                if remapped is not None:
                    repl = (by_path.get(str(remapped).lower())
                            or self._external_entry(remapped))
                # 2) Else match a same-named file already in the library.
                if repl is None:
                    cands = by_name.get(foreign_name(p).lower(), [])
                    if len(cands) == 1:
                        repl = cands[0]
                    elif cands:
                        same = [c for c in cands
                                if getattr(c, "dance", None) == getattr(e, "dance", None)]
                        repl = same[0] if same else cands[0]
                if repl is not None and str(repl.path) != str(e.path):
                    if self._replace_occurrence(table, r, repl):
                        fixed += 1
                        changed = True
                else:
                    unresolved.append(e.title or foreign_name(p))
            if changed:
                table._notify_changed()
        pads = self._fix_cartwall_paths(remapper)

        if checked == 0:
            return ("No tracks in the visible playlists or the wishlists."
                    + (f"<br>{self._pad_fix_line(pads)}" if pads else ""))
        msg = [f"Checked {checked} tracks — {ok} already valid."]
        if pads:
            msg.append(self._pad_fix_line(pads))
        if fixed:
            msg.append(f"🧭  Relocated {fixed} broken reference"
                       f"{'s' if fixed != 1 else ''} to their real files "
                       f"(Ctrl+Z undoes).")
        if unresolved:
            msg.append(f"⚠  {len(unresolved)} still unresolved — no matching "
                       f"file in the library:")
            msg.extend("&nbsp;&nbsp;&nbsp;• " + html.escape(t) for t in unresolved[:20])
            if len(unresolved) > 20:
                msg.append(f"&nbsp;&nbsp;&nbsp;… and {len(unresolved) - 20} more.")
        # Valid tracks off the Referenzpfad are only reported here; 🧭 Fix swaps
        # the ones with a copy there (`_swap_decks_to_reference`).
        ref_copies, off_ref_none = self._deck_reference_rows()
        off_ref_copy = len(ref_copies)
        off_ref = off_ref_copy + len(off_ref_none)
        if off_ref:
            ref_root = self._settings.get("reference_path") or ""
            msg.append(f"⚠  {off_ref} valid track{' is' if off_ref == 1 else 's are'} "
                       f"not on the Referenzpfad {html.escape(ref_root)}")
            if off_ref_copy:
                msg.append(f"&nbsp;&nbsp;&nbsp;↪ {off_ref_copy} "
                           f"{'has' if off_ref_copy == 1 else 'have'} a copy there "
                           "— 🧭 Fix swaps them in the playlists.")
            if off_ref_none:
                msg.append(f"&nbsp;&nbsp;&nbsp;⚠ {len(off_ref_none)} "
                           f"{'has' if len(off_ref_none) == 1 else 'have'} no copy there:")
                msg.extend("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• " + html.escape(t)
                           for t in off_ref_none[:20])
                if len(off_ref_none) > 20:
                    msg.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;… and "
                               f"{len(off_ref_none) - 20} more.")
        if not unresolved and not fixed and not off_ref:
            msg.append("✅  All track paths are valid.")
        if fixed:
            _show_toast(self, (i18n.t("🧭  Fixed %d track path") if fixed == 1
                               else i18n.t("🧭  Fixed %d track paths")) % fixed)
        return "<br>".join(msg)

    def _deck_reference_rows(self) -> tuple[list, list[str]]:
        """The valid tracks in the visible decks that are not on the Referenzpfad:
        ([(table, row, copy path)] for those with a copy there, [title] for the
        rest). Both empty without a Referenzpfad."""
        root = (self._settings.get("reference_path") or "").strip()
        if not root:
            return [], []
        remapper = PathRemapper([root])
        copies: list = []
        no_copy: list[str] = []
        for table in self._path_fix_tables():
            for r, m in table._row_meta.numbered():
                p = Path(m.entry.path)
                try:
                    if not p.exists():
                        continue
                except OSError:
                    continue
                hit = remapper.remap(p)
                if hit is None:
                    no_copy.append(m.entry.title or p.name)
                elif str(hit).lower() != str(p).lower():
                    copies.append((table, r, hit))
        return copies, no_copy

    def _swap_decks_to_reference(self) -> int:
        """🧭 Fix on the "Open playlists" tab: point every valid deck track that has
        a copy on the Referenzpfad at that copy. The song stays the same entry
        (title, dance, BPM), only its path changes. Returns the number swapped."""
        copies, _no_copy = self._deck_reference_rows()
        swapped = 0
        changed = []
        for table, r, hit in copies:
            entry = table._row_meta[r].entry
            if self._replace_occurrence(table, r, replace(entry, path=hit)):
                swapped += 1
                if table not in changed:
                    changed.append(table)
        for table in changed:
            table._notify_changed()
        if swapped:
            log.info("🧭 Deck tracks moved onto the Referenzpfad\n"
                     "tracks: %s\n"
                     "first: %s", swapped, copies[0][2])
            _show_toast(self, (
                i18n.t("🧭  Moved %d track onto the Referenzpfad") if swapped == 1
                else i18n.t("🧭  Moved %d tracks onto the Referenzpfad")) % swapped)
        return swapped

    def _fix_cartwall_paths(self, remapper) -> list:
        """Re-point the 🎛 cartwall pads whose sample is gone, and save the wall.

        The pads are filled once and played by muscle memory, so they are worth
        as much as the decks on a new PC — and unlike a deck they are never
        rebuilt by a generate run."""
        wall = getattr(self, "_cartwall", None)
        if wall is None or not remapper:
            return []
        moved = cartwall.remap_pads(wall.pages(), remapper.remap)
        if moved:
            self._save_cartwall()
            wall.refresh_missing()
            log.info("🎛 Cartwall pads re-pointed\n"
                     "pads: %s\n"
                     "first: %s → %s", len(moved), moved[0][2], moved[0][3])
        return moved

    @staticmethod
    def _pad_fix_line(moved: list) -> str:
        n = len(moved)
        return (f"🎛  Re-pointed {n} cartwall pad{'s' if n != 1 else ''} "
                f"at {'their' if n != 1 else 'its'} real sample"
                f"{'s' if n != 1 else ''}.")

    def _check_dropped_paths(self, paths: list, progress_cb=None):
        """Tab 2 of Fix paths: per dropped .m3u, classify each track path as valid /
        re-rootable under the search folders / unresolved. Read-only — 🧭 Fix & overwrite
        is what actually rewrites them. Returns (results widget, summary dict) so the
        host dialog can drive its bottom summary + Fix button."""
        _, _, remapper = self._remap_index()
        m3us = [p for p in paths if p.suffix.lower() in (".m3u", ".m3u8")]
        box = QWidget()
        v = QVBoxLayout(box)
        if not remapper:
            v.addWidget(QLabel(
                "⚠  No <b>search folder</b> set — open Settings and name the base folder(s) "
                "the music lives in on this PC."))
        if not m3us:
            v.addWidget(QLabel("Drop <b>.m3u playlists</b> here — only playlists carry "
                               "track paths to fix."))
            v.addStretch(1)
            return box, {"valid": 0, "fixable": 0, "unresolved": 0, "playlists": 0}
        total = sum(len(self._m3u_track_paths(m)) for m in m3us)
        done = 0
        tot_valid = tot_fixable = tot_unresolved = 0
        for m3u in m3us:
            valid = fixable = 0
            unresolved: list[Path] = []
            for t in self._m3u_track_paths(m3u):
                try:
                    exists = t.exists()
                except OSError:
                    exists = False
                if rerooted(t, remapper) is not None:
                    fixable += 1
                elif exists:
                    valid += 1
                else:
                    unresolved.append(t)
                done += 1
                if progress_cb and (done == 1 or done % 5 == 0 or done == total):
                    progress_cb(done, total)
            tot_valid += valid
            tot_fixable += fixable
            tot_unresolved += len(unresolved)
            mark = "🔧  " if fixable else ("⚠  " if unresolved else "✅  ")
            grp = QGroupBox(f"{mark}📁  {m3u.name}")
            gv = QVBoxLayout(grp)
            gv.addWidget(QLabel(
                i18n.t("%d tracks — <span style='color:#2a7a45;'>%d valid</span> · "
                       "<b style='color:#e07b00; font-size:13px;'>🔧 %d to fix</b> · "
                       "<span style='color:#a33;'>%d unresolved</span>")
                % (valid + fixable + len(unresolved), valid, fixable, len(unresolved))))
            if unresolved:
                lst = QLabel(i18n.t("⚠  unresolved (no match under the search folders):")
                             + "<br>" + "<br>".join("&nbsp;&nbsp;• " + html.escape(str(u))
                                                    for u in unresolved[:15])
                             + ("<br>&nbsp;&nbsp;" + i18n.t("… and %d more") % (len(unresolved) - 15)
                                if len(unresolved) > 15 else ""))
                lst.setWordWrap(True)
                lst.setStyleSheet("color:#a33; font-size:11px;")
                gv.addWidget(lst)
            v.addWidget(grp)
        v.addStretch(1)
        return box, {"valid": tot_valid, "fixable": tot_fixable,
                     "unresolved": tot_unresolved, "playlists": len(m3us)}

    def _fix_dropped_paths(self, paths: list):
        """🧭 Fix & overwrite: rewrite the broken, re-rootable path lines of each dropped
        .m3u IN PLACE — only the file-path lines change. Confirms first (irreversible)."""
        _, _, remapper = self._remap_index()
        if not remapper:
            QMessageBox.information(
                self, "Fix paths",
                "Set a Referenzpfad or a search folder in Settings before fixing "
                "dropped playlists.")
            return
        m3us = [p for p in paths if p.suffix.lower() in (".m3u", ".m3u8")]
        fixable = 0
        for m3u in m3us:
            for t in self._m3u_track_paths(m3u):
                if rerooted(t, remapper) is not None:
                    fixable += 1
        if not fixable:
            QMessageBox.information(
                self, "Fix paths",
                "No track paths that can be re-rooted under the search folders.")
            return
        if QMessageBox.question(
                self, "Fix & overwrite",
                i18n.t("Rewrite %d path line(s) across %d playlist(s) in place?\n\n"
                       "Only the file-path lines change — #EXTINF and every other line stay "
                       "exactly as-is. This overwrites the .m3u files on disk; each "
                       "original is kept next to it as <name>.m3u.bak.") % (fixable, len(m3us)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        fixed = files_changed = 0
        errors: list[str] = []
        for m3u in m3us:
            try:
                n = rewrite_playlist_paths(m3u, remapper)
            except Exception as exc:
                errors.append(f"{m3u.name}: {exc}")
                continue
            if n:
                fixed += n
                files_changed += 1
        msg = [i18n.t("🧭  Rewrote %d path line(s) in %d playlist(s).") % (fixed, files_changed)]
        if errors:
            msg.append(i18n.t("⚠  Left unchanged:"))
            msg.extend("   • " + e for e in errors)
        QMessageBox.information(self, "Fix paths", "\n".join(msg))
        if fixed:
            # One fixed path lives in one file; more can share one or spread.
            if fixed == 1:
                done = i18n.t("🧭  Fixed 1 path in 1 file")
            elif files_changed == 1:
                done = i18n.t("🧭  Fixed %d paths in 1 file") % fixed
            else:
                done = i18n.t("🧭  Fixed %d paths in %d files") % (fixed, files_changed)
            _show_toast(self, done)
