"""💾 Writing playlists out: .m3u files, numbered folders and the USB bundle.

Split off gui/window/main_persist.py as a MainWindow mixin — everything that leaves the
app as a file the desk can carry to the hall.
"""
import logging

import os
import re
import shutil
import time
from collections import Counter
from datetime import date
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import QEventLoop, QThread, QTimer, Signal
from pathlib import Path
from planner import i18n
from planner.event import venue_pack
from planner.config import OUTPUT_DIR, playlist_dir
from planner.playlist.m3u import export_flat_m3u, export_m3u, m3u_suffix, numbered_folder_m3u
from planner.models import split_day_rounds
from planner.music.paths import PathRemapper
from planner.store import state_dir
from planner.terms import practice_name
from gui.common import (
    BusyDialog,
    _open_folder,
    _sanitize_filename,
)
from shared.widgets import (
    _show_toast,
)
from gui.dialogs import (  # auto-resolved
    AUTOSAVE,
    UsbBundleFolderDialog,
    UsbExportDialog,
    _default_save_dir,
)
from shared.stores import (
    CARTWALL,
    SETTINGS,
    save_settings,
)
from gui.table.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.export")


def _repaint():
    """Let a save's progress bar paint, and nothing else in. Its dialog only
    blocks the window once it shows, 250 ms in; before that a queued click
    (a second 💾 Save-all) would start a whole save inside this one."""
    QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)


_OFF_REFERENCE_SHOWN = 15


class _ReferenceMapper:
    """Re-roots track paths under the Referenzpfad and remembers every track
    that has no copy there (in first-seen order, once each)."""

    def __init__(self, root: str):
        self.root = root
        self._remapper = PathRemapper([root])
        self.missing: list[Path] = []

    def __call__(self, path: Path) -> Path:
        hit = self._remapper.remap(path)
        if hit is not None:
            return hit
        if path not in self.missing:
            self.missing.append(path)
        return path


def _off_reference_text(path_for: _ReferenceMapper | None) -> str:
    """The ⚠ paragraph naming the exported titles missing on the Referenzpfad,
    or "" when there are none."""
    if path_for is None or not path_for.missing:
        return ""
    missing = path_for.missing
    lines = [f"  • {p}" for p in missing[:_OFF_REFERENCE_SHOWN]]
    if len(missing) > _OFF_REFERENCE_SHOWN:
        lines.append(i18n.t("  … and %d more") % (len(missing) - _OFF_REFERENCE_SHOWN))
    return (i18n.t("⚠ %d title(s) are not on the Reference path\n%s\n"
                   "and were saved with their own path:") % (len(missing), path_for.root)
            + "\n" + "\n".join(lines))


def _bundle_name_guess(m3us) -> str:
    """The 🧳 bundle folder's name: the tournament's folder, guessed from the
    folders the exported playlists were loaded from or saved to (`m3us`, None
    for a deck that has no file). Lists in sibling folders name the folder
    above them; otherwise the folder most of them lie in. The app's own output
    folders, the playlist root and a year folder name nothing, and then the
    dated ``Turnier_<date>`` it always was."""
    root = playlist_dir()
    generic = {OUTPUT_DIR, OUTPUT_DIR.parent / "wishlists"}

    def tells(folder: Path) -> bool:
        return (bool(folder.name) and not folder.name.isdigit()
                and folder not in generic
                and folder != root and folder not in root.parents)

    folders = [Path(p).parent for p in m3us if p]
    try:
        common = Path(os.path.commonpath(folders)) if folders else None
    except ValueError:      # on different drives
        common = None
    if common is not None and tells(common):
        return common.name
    for folder, _n in Counter(folders).most_common():
        if tells(folder):
            return folder.name
    return f"Turnier_{date.today().isoformat()}"


def _folder_name(name: str) -> str:
    """A typed folder name made safe on every drive: the signs Windows forbids
    become ``_``; spaces stay, a tournament's name has them."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(". ")


def _is_bundle_dir(folder: Path) -> bool:
    """Whether `folder` holds no more than a USB export writes — playlist
    folders, each with its M3U — so Replace deletes nothing else. Hidden
    entries (a Mac's ``._`` files) don't count."""
    try:
        for p in folder.iterdir():
            if p.name.startswith("."):
                continue
            if not p.is_dir() or not any(f.suffix.lower() in (".m3u", ".m3u8")
                                         for f in p.iterdir()):
                return False
    except OSError:
        return False
    return True


class _BundleAbort(Exception):
    """Raised inside the USB-export progress callback when the user hit Cancel."""


class _BundleWriter(QThread):
    """Writes the USB-export jobs into the bundle off the GUI thread — every
    track is copied to the stick, seconds per file on a slow one. The outcome
    is read from its attributes once it has finished."""

    message = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, bundle: Path, jobs: list, parent=None):
        super().__init__(parent)
        self._bundle = bundle
        self._jobs = jobs
        self._cancelled = False
        self.aborted = False
        self.copied_files: list[Path] = []
        self.created: list[Path] = []   # the playlist folders made, for an abort
        self.written: list[str] = []
        self.errors: list[str] = []
        self.missing_total = 0

    def cancel(self):
        self._cancelled = True

    def _prog(self, i, total, name=""):
        if self._cancelled:
            raise _BundleAbort()
        self.progress.emit(i, total, name)

    def run(self):
        used_names = set()

        def _uniq_name(title: str, fallback: str) -> str:
            base = _sanitize_filename(title) or fallback
            uniq = base
            k = 2
            # Never into a folder already there: in a picked folder that may
            # be an older export the new copies would mix with.
            while uniq.lower() in used_names or (self._bundle / uniq).exists():
                uniq = f"{base}_{k}"
                k += 1
            used_names.add(uniq.lower())
            return uniq

        try:
            for title, write_fn in self._jobs:
                self.message.emit(title)
                if self._cancelled:
                    raise _BundleAbort()
                try:
                    uniq = _uniq_name(title, "Playlist")
                    folder = self._bundle / uniq
                    folder.mkdir(parents=True)
                    self.created.append(folder)
                    out = write_fn(folder / f"{uniq}{m3u_suffix()}")
                    files, miss = numbered_folder_m3u(out, progress_cb=self._prog)
                    self.copied_files += files
                    self.missing_total += miss
                    self.written.append(uniq)
                except _BundleAbort:
                    raise
                except Exception as exc:
                    self.errors.append(f"{title}: {exc}")
        except _BundleAbort:
            self.aborted = True


class _VenueJob(QThread):
    """Runs one venue-pack write or unpack off the GUI thread — with the music
    it copies hundreds of MB. `fn(progress, cancelled)`; the outcome is read
    from `result` / `error` once it has finished."""

    progress = Signal(int, int)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._cancelled = False
        self.result: Any = None   # what fn returned
        self.error: BaseException | None = None

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self.result = self._fn(self.progress.emit, lambda: self._cancelled)
        except BaseException as exc:    # handed to the GUI thread, raised there
            self.error = exc


class ExportMixin(MainWindowHost):
    """💾 Playlists out to disk: single .m3u, day folders, USB bundle."""

    # ── 📦 Venue pack (⚙ Settings) ─────────────────────────────────────────────
    def _run_venue_job(self, message: str, fn):
        """Run `fn(progress, cancelled)` behind an abortable progress dialog and
        return what it returns; raises what it raised."""
        dlg = BusyDialog(self, message=message, cancelable=True)
        dlg.show_after(250)
        job = _VenueJob(fn, self)
        job.progress.connect(dlg.set_progress)
        dlg.cancel_requested.connect(job.cancel)
        loop = QEventLoop()
        job.finished.connect(loop.quit)
        job.start()
        loop.exec()
        dlg.finish()
        if job.error is not None:
            raise job.error
        return job.result

    def _export_venue_pack(self):
        """📦 This desk — settings, decks, cartwall and keys, the music if
        wanted — to one file for another PC."""
        title = "Export venue pack"
        # What is on screen, not what was last written.
        self._autosave_playlist()
        self._save_cartwall(edit=False)
        save_settings(self._settings)
        docs = {}
        for store in (SETTINGS, AUTOSAVE, CARTWALL):
            obj = store.read()
            if obj is not None:
                docs[store.name] = obj
        tracks = venue_pack.track_paths(*docs.values())
        present = [t for t in tracks if Path(t).is_file()]
        size_mb = sum(Path(t).stat().st_size for t in present) / 1e6
        ans = QMessageBox.question(
            self, title,
            i18n.t("Include the music files?\n\n"
                   "Yes: the %d track(s) the decks and the cartwall use go into "
                   "the pack too (%s MB) — the other PC needs nothing else.\n"
                   "No: settings, decks and cartwall only — the other PC has the "
                   "music already.") % (len(present), f"{size_mb:.0f}"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No)
        if ans not in (QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No):
            return
        with_music = ans == QMessageBox.StandardButton.Yes
        # The name tells a pack with music apart on the stick, before anyone opens it.
        mark = "-with-music" if with_music else ""
        chosen, _ = QFileDialog.getSaveFileName(
            self, title,
            str(Path.home() / f"venue-{date.today().isoformat()}{mark}{venue_pack.SUFFIX}"),
            i18n.t("Venue packs") + f" (*{venue_pack.SUFFIX});;"
            + i18n.t("All files") + " (*)")
        if not chosen:
            return
        dest = Path(chosen)
        try:
            res = self._run_venue_job(
                "📦 Writing the venue pack…",
                lambda progress, cancelled: venue_pack.write_pack(
                    dest, docs, with_music, progress, cancelled))
        except venue_pack.VenuePackCancelled:
            self.statusBar().showMessage("📦 Venue pack cancelled — nothing was written.")
            return
        except OSError as exc:
            QMessageBox.warning(self, title, i18n.t("Could not write the file:") + "\n\n" + str(exc))
            return
        lines = [i18n.t("📦 Venue pack saved to:\n%s") % dest]
        if with_music:
            lines.append(i18n.t("%d track(s) included.") % res.tracks)
        if res.missing:
            lines.append(i18n.t("⚠ %d track(s) were missing on disk and are not "
                                "in the pack.") % len(res.missing))
        QMessageBox.information(self, title, "\n\n".join(lines))

    def _import_venue_pack(self):
        """📥 A venue pack from another PC: staged now, put in place at the
        next start (closing the window would write over it otherwise)."""
        title = "Import venue pack"
        chosen, _ = QFileDialog.getOpenFileName(
            self, title, str(Path.home()),
            i18n.t("Venue packs") + f" (*{venue_pack.SUFFIX});;"
            + i18n.t("All files") + " (*)")
        if not chosen:
            return
        src = Path(chosen)
        try:
            pack = venue_pack.read_pack(src)
        except venue_pack.VenuePackError as exc:
            QMessageBox.warning(self, title, i18n.t("This is no venue pack:") + "\n\n" + str(exc))
            return
        music_dir = None
        if pack.music:
            ans = QMessageBox.question(
                self, title,
                i18n.t("The pack carries %d music file(s).\n\n"
                       "Yes: unpack them into a folder of this PC — the decks and "
                       "the cartwall then play them from there.\n"
                       "No: leave them in the pack — this PC has the music "
                       "already (🧭 Fix paths finds it if it lives elsewhere).")
                % len(pack.music),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes)
            if ans not in (QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No):
                return
            if ans == QMessageBox.StandardButton.Yes:
                folder = QFileDialog.getExistingDirectory(
                    self, i18n.t("Folder for the venue pack's music"), str(Path.home()))
                if not folder:
                    return
                music_dir = Path(folder)
        try:
            self._run_venue_job(
                "📥 Unpacking the venue pack…",
                lambda progress, cancelled: venue_pack.stage_import(
                    src, state_dir(), music_dir, progress, cancelled))
        except venue_pack.VenuePackCancelled:
            self.statusBar().showMessage("📥 Venue pack import cancelled.")
            return
        except (OSError, venue_pack.VenuePackError) as exc:
            QMessageBox.warning(self, title, i18n.t("The import did not run:") + "\n\n" + str(exc))
            return
        log.info("📥 Venue pack staged\n"
                 "file: %s\n"
                 "music: %s", src, music_dir or "not unpacked")
        # After ⚙ Settings has closed and applied what it holds — the restart
        # closes the main window, which must not happen under an open dialog.
        QTimer.singleShot(0, lambda: self._offer_restart(
            title,
            "The venue pack takes over at the next start: settings, decks and "
            "cartwall are replaced then, and what they replace is kept in a "
            "before-venue-import folder.\n\n"
            "Anything you change before that is lost.\n\n"
            "Restart now?"))

    def _export_path_for(self) -> "_ReferenceMapper | None":
        """The track-path mapper a saved .m3u is written through: every title
        with a copy under the Referenzpfad (Settings) is named by that copy, so
        a list gathered from the C: and the F: library leaves on one drive. A
        title with no copy there keeps its own path and is noted in the
        mapper's `missing`. None without a Referenzpfad."""
        root = ((getattr(self, "_settings", None) or {}).get("reference_path") or "").strip()
        return _ReferenceMapper(root) if root else None

    def _warn_off_reference(self, path_for: "_ReferenceMapper | None"):
        """⚠ After a single save: name the titles that are not on the Referenzpfad."""
        text = _off_reference_text(path_for)
        if text:
            QMessageBox.warning(self, "Not on the Reference path", text)

    def _save_all_playlists(self, decks=None):
        """💾 Save-all: export every non-empty playlist deck to its own .m3u in the
        playlist folder in one go. Each file is named after the deck's title (dated, so
        repeated saves don't clobber). The 🤸 Eintanzen panel goes out with them, flat.
        Wishlists are saved too, into a separate ``wishlists`` sub-folder (also name +
        date/time). Given `decks` (a Group tab's page), only those are saved."""
        only = decks is not None
        decks = [t for t in (decks if only else self._deckset.decks + self._deckset.day_decks)
                 if t.rowCount() > 0]
        wishes = [] if only else [t for t in self._deckset.wishlists
                                  if t.wishlist_entries()]
        # The 🤸 Eintanzen panel is neither a deck nor a wishlist, and it is the
        # one list an evening is actually run from — it saves along with them,
        # flat and with its rounds, into the playlist folder.
        warmup = (self._deckset.warmup_table
                  if not only and self._warmup_has_content()
                  and self._deckset.warmup_table._row_meta.entries()
                  else None)
        if not decks and not wishes and warmup is None:
            self.statusBar().showMessage("Nothing to save — all playlists are empty.")
            return
        saved, skipped, errors = [], [], []
        used_names = set()
        path_for = self._export_path_for()
        # One determinate dialog ticking over the decks (appears only if it takes a moment).
        dlg = BusyDialog(self, message="💾 Saving all playlists…")
        dlg.show_after(250)
        def _uniq_name(title: str, fallback: str) -> str:
            # Two decks / competitions sharing a name would collide → suffix later ones.
            # Case-blind: "Final" and "final" are one file on Windows and macOS.
            base = _sanitize_filename(title) or fallback
            uniq = base
            n = 2
            while uniq.casefold() in used_names:
                uniq = f"{base}_{n}"
                n += 1
            used_names.add(uniq.casefold())
            return uniq

        for i, t in enumerate(decks, 1):
            title = (self.deck(t).name or "Playlist").replace("·", "-")
            dlg.set_progress(i, len(decks), title)
            _repaint()
            try:
                data = self._serialize_playlist_state(t)
                if not data:
                    skipped.append(title)
                    continue
                if data.get("mode") == "Theme":
                    entries = [e for e in (self._resolve_entry(p)
                                           for p in data.get("theme_entries", [])) if e]
                    if not entries:
                        skipped.append(title)
                        continue
                    out = export_flat_m3u(entries, _uniq_name(title, "Playlist"),
                                          path_for=path_for)
                    t._m3u_path = Path(out)
                    saved.append(Path(out).name)
                    continue
                # A stacked 📅 day-plan deck splits into one M3U per competition.
                for comp, playlist, c_dances, c_cls in self._deck_export_jobs(data):
                    name = _uniq_name((comp or title).replace("·", "-"), "Playlist")
                    out = export_m3u(playlist, c_dances, name, c_cls, path_for=path_for)
                    t._m3u_path = Path(out)
                    saved.append(Path(out).name)
            except Exception as exc:
                errors.append(f"{title}: {exc}")
        if warmup is not None:
            title = (self.deck(warmup).name or practice_name()).replace("·", "-")
            dlg.set_progress(1, 1, title)
            _repaint()
            try:
                out = export_flat_m3u(warmup._row_meta.entries(),
                                      _uniq_name(title, practice_name()),
                                      path_for=path_for)
                warmup._m3u_path = Path(out)
                saved.append(Path(out).name)
            except Exception as exc:
                errors.append(f"{title}: {exc}")
        wish_dir, saved_wish = self._save_wishlists(wishes, dlg, path_for, errors)
        dlg.finish()
        if saved or saved_wish:
            n_total = len(saved) + len(saved_wish)
            self.statusBar().showMessage(
                (i18n.t("💾 Saved %d playlist → %s") if n_total == 1
                 else i18n.t("💾 Saved %d playlists → %s")) % (n_total, OUTPUT_DIR))
        self._report_save_all(saved, saved_wish, wish_dir, skipped, errors, path_for)

    def _report_save_all(self, saved, saved_wish, wish_dir, skipped, errors,
                         path_for):
        """The summary box after 💾 Save-all, with 📂 Open folder."""
        lines = []
        if saved:
            lines.append(i18n.t("Saved %d playlist(s) to:\n%s") % (len(saved), OUTPUT_DIR)
                         + "\n\n" + "\n".join(f"  • {n}" for n in saved))
        if saved_wish:
            lines.append(i18n.t("Saved %d wishlist(s) to:\n%s") % (len(saved_wish), wish_dir)
                         + "\n\n" + "\n".join(f"  • {n}" for n in saved_wish))
        if skipped:
            lines.append(i18n.t("Skipped (empty): %s") % ", ".join(skipped))
        off_reference = _off_reference_text(path_for)
        if off_reference:
            lines.append(off_reference)
        if errors:
            lines.append(i18n.t("Errors:") + "\n" + "\n".join(f"  • {e}" for e in errors))
        box = QMessageBox(self)
        box.setWindowTitle("Save all playlists")
        box.setIcon(QMessageBox.Icon.Warning if (errors or off_reference)
                    else QMessageBox.Icon.Information)
        box.setText("\n\n".join(lines))
        # Offer to jump straight to the folder when at least one file was written.
        open_btn = None
        if saved or saved_wish:
            open_btn = box.addButton("📂  Open folder", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if open_btn is not None and box.clickedButton() is open_btn:
            _open_folder(OUTPUT_DIR, self)

    def _save_wishlists(self, wishes, dlg, path_for, errors):
        """Each wishlist into its own file in the ``wishlists`` folder."""
        # Wishlists go to their own dated files in a sibling folder of the playlists dir.
        wish_dir = OUTPUT_DIR.parent / "wishlists"
        saved_wish = []
        wish_names = set()
        for i, t in enumerate(wishes, 1):
            title = (self.deck(t).name or "Wishlist").replace("·", "-")
            dlg.set_progress(i, len(wishes), title)
            _repaint()
            basename = _sanitize_filename(title) or "Wishlist"
            uniq = basename
            n = 2
            while uniq.casefold() in wish_names:   # case-blind, as in save-all
                uniq = f"{basename}_{n}"
                n += 1
            wish_names.add(uniq.casefold())
            try:
                out = export_flat_m3u(t.wishlist_entries(), uniq, out_dir=wish_dir,
                                      path_for=path_for)
                t._m3u_path = Path(out)
                saved_wish.append(Path(out).name)
            except Exception as exc:
                errors.append(f"{title}: {exc}")
        return wish_dir, saved_wish

    def _export_bundle(self):
        """🧳 USB export: each exported playlist becomes its own sub-folder holding
        the tracks copied in numbered play order (``0_0_1 - Title WW29.mp3``) plus
        the playlist's M3U pointing at those copies — so each folder plays in
        order even without the M3U (imported file-by-file on a USB player /
        UltraMixer at the venue, no 🧭 path fixing needed there).

        Asks first WHAT to bundle: all open decks, only the 📅 tournament day, or
        saved .m3u files dragged in. The ⭐ wishlists with titles go along with
        the decks, each into a folder of its own, when their box is ticked. The
        📦 venue pack is offered there too, and runs `_export_venue_pack` instead."""
        decks = [t for t in self._deckset.decks if t.rowCount() > 0]
        day = [t for t in self._deckset.day_decks if t.rowCount() > 0]
        wishes = [t for t in self._deckset.wishlists if t.wishlist_entries()]
        ask = UsbExportDialog(
            self, n_decks=len(decks), n_day=len(day),
            day_selected=self._grid.deck_tabs.currentWidget() is self._grid.day_tabs,
            n_wish=len(wishes))
        if ask.exec() != QDialog.DialogCode.Accepted:
            return
        if ask.mode() == "venue":
            self._export_venue_pack()
            return
        if ask.mode() == "dropped":
            # Pre-saved playlists: each dropped .m3u is copied into its folder
            # as-is, then the copy is rewritten to the numbered track names.
            jobs = [(p.stem, lambda out, src=p: Path(shutil.copyfile(src, out)))
                    for p in ask.dropped_paths()]
            skipped = []
            sources = ask.dropped_paths()
        else:
            selected = day if ask.mode() == "day" else decks + day
            jobs, skipped = self._bundle_jobs_for_decks(selected)
            if ask.include_wishlists():
                selected = selected + wishes
                for t in wishes:
                    jobs.append(((self.deck(t).name or "Wishlist").replace("·", "-"),
                                 lambda out, e=t.wishlist_entries():
                                 Path(export_flat_m3u(e, out.stem, out_path=out))))
            sources = [getattr(t, "_m3u_path", None) for t in selected]
        if not jobs:
            self.statusBar().showMessage("Nothing to export — all playlists are empty.")
            return
        picked = self._pick_bundle_dir(_bundle_name_guess(sources))
        if picked is None:
            return
        bundle, own_folder = picked
        self._write_bundle(bundle, jobs, skipped, own_folder=own_folder)

    def _bundle_jobs_for_decks(self, decks) -> tuple[list, list[str]]:
        """(title, write_fn) bundle jobs for the given decks — ``write_fn(out)``
        writes the playlist's M3U at `out` and returns its path. A stacked 📅
        day-plan deck yields one job per competition. Second value: the titles
        skipped because their deck had nothing to export."""
        jobs, skipped = [], []
        for t in decks:
            title = (self.deck(t).name or "Playlist").replace("·", "-")
            data = self._serialize_playlist_state(t)
            if not data:
                skipped.append(title)
                continue
            if data.get("mode") == "Theme":
                entries = [e for e in (self._resolve_entry(p)
                                       for p in data.get("theme_entries", [])) if e]
                if not entries:
                    skipped.append(title)
                    continue
                jobs.append((title, lambda out, e=entries:
                             Path(export_flat_m3u(e, out.stem, out_path=out))))
                continue
            for comp, playlist, c_dances, c_cls in self._deck_export_jobs(data):
                jobs.append(((comp or title).replace("·", "-"),
                             lambda out, pl=playlist, dl=c_dances, cl=c_cls:
                             Path(export_m3u(pl, dl, out.stem, cl, out_path=out))))
        return jobs, skipped

    def _pick_bundle_dir(self, guess: str) -> tuple[Path, bool] | None:
        """Pick the target drive / folder, then the bundle folder in it, named
        after the tournament (`guess` filled in): on a drive's top level
        always, in a sub folder only if wanted, else straight into it. A
        folder to make that already exists asks Replace / Keep both / Cancel,
        so nothing is ever silently overwritten.
        → (bundle, whether the bundle folder was made for it); None: cancelled."""
        root = QFileDialog.getExistingDirectory(
            self, "USB export — pick the target drive / folder",
            str(_default_save_dir()))
        if not root:
            return None
        root = Path(root)
        ask = UsbBundleFolderDialog(self, root, guess, os.path.ismount(root))
        if ask.exec() != QDialog.DialogCode.Accepted:
            return None
        if ask.into_root():
            return root, False
        name = _folder_name(ask.name()) or guess
        bundle = root / name
        if bundle.exists():
            # Only an older export can be replaced: a folder of that name
            # with anything else in it is the user's, and stays.
            replaceable = _is_bundle_dir(bundle)
            box = QMessageBox(self)
            box.setWindowTitle("USB export")
            box.setIcon(QMessageBox.Icon.Question)
            if replaceable:
                box.setText(i18n.t("“%s” already exists in the target folder.\n"
                                   "Replace it, or keep both?") % bundle)
                replace_btn = box.addButton("Replace",
                                            QMessageBox.ButtonRole.DestructiveRole)
            else:
                box.setText(i18n.t("“%s” already exists in the target folder and "
                                   "holds more than a USB export, so it cannot be "
                                   "replaced.\nKeep both?") % bundle)
                replace_btn = None
            keep_btn = box.addButton("Keep both", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.setDefaultButton(keep_btn)
            box.exec()
            if replace_btn is not None and box.clickedButton() is replace_btn:
                try:
                    shutil.rmtree(bundle)
                except OSError as exc:
                    log.warning("⚠️ USB export could not remove the old bundle\n"
                                "folder: %s\n"
                                "error: %s", bundle, exc)
                    QMessageBox.critical(self, "USB export", i18n.t(
                        "Could not remove “%s”:\n%s\n\n"
                        "It may be partly deleted; nothing was exported.")
                        % (bundle, exc))
                    return None
            elif box.clickedButton() is keep_btn:
                n = 2
                while bundle.exists():
                    bundle = root / f"{name}_{n}"
                    n += 1
            else:
                return None
        try:
            bundle.mkdir(parents=True)
        except OSError as exc:
            log.warning("⚠️ USB export could not create the bundle folder\n"
                        "folder: %s\n"
                        "error: %s", bundle, exc)
            QMessageBox.critical(self, "USB export", i18n.t(
                "Could not create “%s”:\n%s") % (bundle, exc))
            return None
        return bundle, True

    def _write_bundle(self, bundle: Path, jobs: list, skipped: list[str],
                      own_folder: bool = True):
        """Write the (title, write_fn) jobs into the bundle — one numbered folder
        per playlist — behind an abortable progress dialog. Cancel (or ESC) stops
        the copy and removes the incomplete bundle folder; written into a folder
        the user picked (`own_folder` False), only the playlist folders made."""
        dlg = BusyDialog(self, message="🧳 Exporting venue bundle…", cancelable=True)
        dlg.show_after(250)
        worker = _BundleWriter(bundle, jobs, self)
        worker.message.connect(lambda title: dlg.set_message(f"🧳 {title}"))
        worker.progress.connect(dlg.set_progress)
        dlg.cancel_requested.connect(worker.cancel)
        # Queued from the worker's thread, so a quit posted before exec()
        # starts still ends the loop.
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        worker.start()
        loop.exec()

        copied_files = worker.copied_files
        written, errors = worker.written, worker.errors
        missing_total = worker.missing_total
        if worker.aborted:
            dlg.finish()
            for folder in ([bundle] if own_folder else worker.created):
                shutil.rmtree(folder, ignore_errors=True)
            log.info("🧳 USB export aborted by the user\n"
                     "removed incomplete bundle: %s", bundle)
            self.statusBar().showMessage(
                "🧳 USB export aborted — incomplete bundle removed.")
            return
        dlg.finish()

        size_mb = sum(p.stat().st_size for p in copied_files) / 1e6
        log.info("🧳 Venue bundle written\n"
                 "folder: %s\n"
                 "playlist folders: %d\n"
                 "tracks copied: %d (%.0f MB)\n"
                 "missing: %d", bundle, len(written), len(copied_files),
                 size_mb, missing_total)
        self.statusBar().showMessage(
            i18n.t("🧳 Bundle: %d playlist folder(s), %d track(s), %s MB → %s")
            % (len(written), len(copied_files), f"{size_mb:.0f}", bundle))
        lines = [i18n.t("Bundle written to:\n%s") % bundle,
                 i18n.t("%d playlist folder(s) · %d track(s) · %s MB — each folder "
                        "holds the tracks numbered in play order plus the playlist's "
                        "M3U, so it plays even without the M3U.")
                 % (len(written), len(copied_files), f"{size_mb:.0f}")]
        if missing_total:
            lines.append(i18n.t("⚠ %d track(s) were missing on disk and kept "
                                "their original absolute path.") % missing_total)
        if skipped:
            lines.append(i18n.t("Skipped (empty): %s") % ", ".join(skipped))
        if errors:
            lines.append(i18n.t("Errors:") + "\n" + "\n".join(f"  • {e}" for e in errors))
        box = QMessageBox(self)
        box.setWindowTitle("USB export")
        box.setIcon(QMessageBox.Icon.Warning if (errors or missing_total)
                    else QMessageBox.Icon.Information)
        box.setText("\n\n".join(lines))
        open_btn = None
        if written:
            open_btn = box.addButton("📂  Open folder", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if open_btn is not None and box.clickedButton() is open_btn:
            _open_folder(bundle, self)

    def _save_day_plan_m3us(self, file_in_tree: bool = False):
        """Right-click on the 📅 tab → save every competition held in the day
        decks to its own .m3u (a stacked deck splits into one file per
        competition, like 💾 Save-all). Asks for the target folder first and
        puts the files into a sub-folder named after the tab / the day.
        `file_in_tree` then files them in 🏆 Tournaments, in a folder named
        like that sub-folder."""
        decks = [t for t in self._deckset.day_decks if t.rowCount() > 0]
        if not decks:
            self.statusBar().showMessage("Nothing to save — the day decks are empty.")
            return
        root = QFileDialog.getExistingDirectory(
            self, "Save tournament day — pick the target folder",
            str(_default_save_dir()))
        if not root:
            return
        title = getattr(self, "_day_tab_title", "").strip()
        sub = (_sanitize_filename(title) if title
               else f"Tournament_day_{date.today().isoformat()}")
        target = Path(root) / sub
        target.mkdir(parents=True, exist_ok=True)
        saved, errors = [], []
        written: list[Path] = []
        used_names = set()
        path_for = self._export_path_for()
        dlg = BusyDialog(self, message="💾 Saving tournament-day playlists…")
        dlg.show_after(250)
        for i, t in enumerate(decks, 1):
            title = (self.deck(t).name or "Playlist").replace("·", "-")
            dlg.set_progress(i, len(decks), title)
            _repaint()
            try:
                data = self._serialize_playlist_state(t)
                if not data:
                    continue
                for comp, playlist, c_dances, c_cls in self._deck_export_jobs(data):
                    base = _sanitize_filename(
                        (comp or title).replace("·", "-")) or "Playlist"
                    uniq = base
                    n = 2
                    # The file system ignores case, so "Final" and "final" collide.
                    while uniq.casefold() in used_names:
                        uniq = f"{base}_{n}"
                        n += 1
                    used_names.add(uniq.casefold())
                    out = export_m3u(playlist, c_dances, uniq, c_cls,
                                     out_path=target / f"{uniq}{m3u_suffix()}",
                                     path_for=path_for)
                    t._m3u_path = Path(out)
                    saved.append(Path(out).name)
                    written.append(Path(out))
            except Exception as exc:
                errors.append(f"{title}: {exc}")
        dlg.finish()
        if file_in_tree and written:
            self._file_in_tournaments(written, sub)
        elif saved:
            self.statusBar().showMessage(
                (i18n.t("💾 Saved %d competition playlist → %s") if len(saved) == 1
                 else i18n.t("💾 Saved %d competition playlists → %s"))
                % (len(saved), target))
        lines = []
        if saved:
            lines.append(i18n.t("Saved %d competition playlist(s) to:\n%s")
                         % (len(saved), target)
                         + "\n\n" + "\n".join(f"  • {n}" for n in saved))
        off_reference = _off_reference_text(path_for)
        if off_reference:
            lines.append(off_reference)
        if errors:
            lines.append(i18n.t("Errors:") + "\n" + "\n".join(f"  • {e}" for e in errors))
        box = QMessageBox(self)
        box.setWindowTitle("Save tournament day")
        box.setIcon(QMessageBox.Icon.Warning if (errors or off_reference)
                    else QMessageBox.Icon.Information)
        box.setText("\n\n".join(lines) or i18n.t("Nothing to save."))
        open_btn = None
        if saved:
            open_btn = box.addButton("📂  Open folder", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if open_btn is not None and box.clickedButton() is open_btn:
            _open_folder(target, self)

    def _deck_export_jobs(self, data: dict) -> list[tuple[str | None, dict, list[str], str]]:
        """(label, playlist, dances, class) export jobs for one serialized deck —
        a stacked 📅 day-plan deck yields one job per competition (plain round
        names, own dance columns), an ordinary deck one job with label None."""
        dances = data.get("dances") or []
        cls = data.get("dance_class", "S")
        groups = split_day_rounds(data.get("rounds") or [], dances)
        if not groups:
            playlist = self._playlist_from_grid(data.get("rounds") or [], len(dances))
            return [(None, playlist, dances, cls)]
        return [(g["comp"],
                 self._playlist_from_grid(g["rounds"], len(g["dances"])),
                 g["dances"], g.get("cls") or cls)
                for g in groups]

    def _on_table_save_requested(self, table: PlaylistTable, file_in_tree: bool = False):
        """Right-click → 'Save as M3U…' on a deck / wishlist: pick a destination file
        (the chooser opens in the configured save folder, default the Documents folder,
        and remembers wherever you last saved) and export the table's contents there.
        `file_in_tree` then files the saved playlist in 🏆 Tournaments."""
        default = (self.deck(table).name or "Playlist").replace("·", "-")
        basename = _sanitize_filename(default) or "Playlist"
        # Resolve the export work first, so empty decks/wishlists are caught before
        # the user picks a file.
        is_wish = table in self._deckset.wishlists
        # The 🤸 Eintanzen panel is flat like a wishlist, and it is neither a deck
        # nor a wishlist — without this it fell through to the grid branch and a
        # party list came out wrapped in a competition draw's heat comments.
        is_flat = is_wish or getattr(table, "_warmup", False)
        path_for = self._export_path_for()
        if is_flat:
            entries = table._row_meta.entries()
            if not entries:
                QMessageBox.information(
                    self, "Save as M3U",
                    "This wishlist is empty." if is_wish else "This list is empty.")
                return
            export = lambda out: self._run_export(
                "💾 Saving wishlist…" if is_wish else "💾 Saving playlist…",
                lambda cb: export_flat_m3u(entries, basename, progress_cb=cb, out_path=out,
                                           path_for=path_for))
        else:
            data = self._serialize_playlist_state(table)
            if not data:
                QMessageBox.information(self, "Save as M3U", "This deck is empty.")
                return
            # Both branches resolve their tracks INSIDE the export closure: on a
            # long imported list that is the slow half of the save (tags read off
            # the disk per unknown path), and out here it would freeze the window
            # before the file chooser even opened, with nothing to look at.
            if data.get("mode") == "Theme":
                paths = list(data.get("theme_entries", []))
                export = lambda out: self._run_export(
                    "💾 Saving playlist…",
                    lambda cb: export_flat_m3u(self._resolve_paths(paths, cb),
                                               basename, progress_cb=cb,
                                               out_path=out, path_for=path_for))
            else:
                dances = data["dances"]
                rounds = data["rounds"]
                export = lambda out: self._run_export(
                    "💾 Saving playlist…",
                    lambda cb: export_m3u(
                        self._playlist_from_grid(rounds, len(dances), cb),
                        dances, basename, data["dance_class"],
                        progress_cb=cb, out_path=out, path_for=path_for))

        settings = getattr(self, "_settings", None) or {}
        start_dir = settings.get("save_dir") or str(_default_save_dir())
        try:
            Path(start_dir).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            log.debug("📁 Could not create the save folder %s: %s", start_dir, exc)
        suggested = str(Path(start_dir) / f"{basename}{m3u_suffix()}")
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save as M3U", suggested,
            "M3U playlists (*.m3u *.m3u8);;All files (*)")
        if not chosen:
            return
        out_path = Path(chosen)
        if out_path.suffix.lower() not in (".m3u", ".m3u8"):
            out_path = out_path.with_suffix(m3u_suffix())
        # Remember the folder the user chose for next time.
        if isinstance(getattr(self, "_settings", None), dict):
            self._settings["save_dir"] = str(out_path.parent)
            save_settings(self._settings)
        try:
            out = export(out_path)
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return
        table._m3u_path = Path(out)
        self.statusBar().showMessage(i18n.t("Saved → %s") % out)
        _show_toast(self, i18n.t("💾  Saved → %s") % Path(out).name)
        if file_in_tree:
            self._file_in_tournaments([Path(out)])
        self._warn_off_reference(path_for)

    def _file_in_tournaments(self, paths: list[Path], folder: str | None = None):
        """File just-saved playlists in the 🏆 Tournaments tree — into its
        selected folder, like "Add playlists…"; a day as folder `folder` — and
        bring that tab to the front, the pane unfolded."""
        tree = getattr(self, "_tourney_tree", None)
        if tree is None:
            return
        n = tree.file_saved(paths, folder)
        if getattr(self, "_lib_pane_folded", False):
            self._toggle_lib_pane_fold(False)
        self._lib_tabs.setCurrentWidget(tree)
        self.statusBar().showMessage(
            ((i18n.t("🏆 Saved and added %d playlist to Tournaments") if n == 1
              else i18n.t("🏆 Saved and added %d playlists to Tournaments")) % n)
            if n else i18n.t("🏆 Saved — already in Tournaments"))

    def _save_focused(self):
        """Ctrl+S — save the currently focused playlist/wishlist as M3U, falling back
        to the active deck when nothing has been focused yet."""
        table = getattr(self, "_focused_table", None) or self._deckset.table
        if table is None:
            self.statusBar().showMessage("Nothing to save yet.")
            return
        self._on_table_save_requested(table)

    def _clear_focused(self):
        """Ctrl+Shift+Del — empty the focused playlist/wishlist, after the
        same question Del asks."""
        table = getattr(self, "_focused_table", None) or self._deckset.table
        if table is not None:
            table._clear_entire()

    def _run_export(self, message: str, fn):
        """Run a single export `fn(progress_cb)` behind a determinate progress dialog.

        The dialog only appears if the write takes longer than a moment (so small lists
        don't flash it). The export runs on the main thread; each tick repaints the bar
        — but only about twenty times a second: repainting per track cost more than
        writing the file did (600 tracks: 4 ms of writing, 250 ms of bar)."""
        dlg = BusyDialog(self, message=message)
        dlg.show_after(250)
        last = 0.0

        def _prog(done: int, total: int, name: str = ""):
            nonlocal last
            now = time.monotonic()
            if done < total and now - last < 0.05:
                return
            last = now
            dlg.set_progress(done, total, name)
            _repaint()

        try:
            return fn(_prog)
        finally:
            dlg.finish()

    def _save_m3u(self):
        # A focused wishlist is saved directly (flat M3U with a name prompt).
        focused = getattr(self, "_focused_table", None)
        if focused is not None and focused in self._deckset.wishlists:
            self._on_table_save_requested(focused)
            return
        if self._mode == "Theme":
            if not self._theme_entries:
                return
            safe = re.sub(r"[^\w]+", "_", self._theme_label).strip("_") or "Theme"
            path_for = self._export_path_for()
            out  = self._run_export(
                "💾 Saving playlist…",
                lambda cb: export_flat_m3u(self._theme_entries, f"Theme_{safe}",
                                           progress_cb=cb, path_for=path_for))
            self.statusBar().showMessage(i18n.t("Saved → %s") % out)
            _show_toast(self, i18n.t("💾  Saved → %s") % Path(out).name)
            self._warn_off_reference(path_for)
            return

        grid = self._playlist
        if not grid:
            return
        # A stacked 📅 day-plan deck saves one M3U per competition it holds.
        comps = {c.get("comp") for c in getattr(self._deckset.table, "_round_ctx", {}).values()
                 if c.get("comp")}
        if len(comps) > 1:
            data = self._serialize_playlist_state(self._deckset.table)
            outs = []
            path_for = self._export_path_for()
            for comp, playlist, c_dances, c_cls in self._deck_export_jobs(data or {}):
                base = _sanitize_filename((comp or "Playlist").replace("·", "-")) or "Playlist"
                out = self._run_export(
                    i18n.t("💾 Saving %s…") % comp,
                    lambda cb, pl=playlist, dl=c_dances, b=base, cl=c_cls:
                        export_m3u(pl, dl, b, cl, progress_cb=cb, path_for=path_for))
                outs.append(Path(out).name)
            self.statusBar().showMessage(
                i18n.t("Saved %d competition playlist(s) → %s") % (len(outs), OUTPUT_DIR))
            _show_toast(self, i18n.t("💾  Saved %d competition playlist(s)") % len(outs))
            self._warn_off_reference(path_for)
            return
        suffix = f"_v{self._iteration}" if self._iteration > 1 else ""
        if self._replay_label:
            # Seeded from a past competition → name the export after that class
            dances   = self._dances
            cls      = self._dance_class
            basename = f"{self._replay_label}{suffix}"
        else:
            # What the playlist was generated with, not the live checkboxes: a
            # dance ticked since then has no song in any heat.
            dances = self._dances
            cls = self._dance_class
            basename = f"{self._age.replace(' ', '_')}_{cls}_{self._style}{suffix}"
        path_for = self._export_path_for()
        out = self._run_export(
            "💾 Saving playlist…",
            lambda cb: export_m3u(grid, dances, basename, cls, progress_cb=cb,
                                  path_for=path_for))
        self.statusBar().showMessage(i18n.t("Saved → %s") % out)
        _show_toast(self, i18n.t("💾  Saved → %s") % Path(out).name)
        self._warn_off_reference(path_for)
