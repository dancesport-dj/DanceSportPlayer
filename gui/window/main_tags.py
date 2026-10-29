"""🏷 A title's tags: re-read, rated, edited, and written into the MP3.

Split off gui/window/main_music.py: re-reading a file's tags, the ★ rating,
the tag dialog and what it writes (the library, every copy of the title and,
when the user says so, the MP3 itself), and the custom field's frame.
"""
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from mutagen import MutagenError
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QDialog

from gui.dialogs.tag_edit_dialog import (
    CustomSourceDialog,
    TagEditDialog,
    marker_suggestions,
    with_filename_title,
)
from gui.workers import CustomFieldReader
from planner import i18n
from planner.music import custom_field, id3_frames
from shared.widgets import WARN_TOAST_MS, show_toast

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.music")


# What a re-read tag field is called in the toast — the DB column names mean
# nothing to the user, and 'bpm' is the takt (bars/min) everywhere in the UI.
_TAG_FIELD_LABELS = {
    "title": "title", "dance": "dance", "bpm": "takt", "year": "year",
    "other_genre": "genre", "classes_ok": "classes",
    "is_instrumental": "instrumental", "is_xmas": "christmas",
    "tag_title": "ID3 title", "tag_artist": "artist", "duration": "length",
    "tag_album": "album", "comment_tags": "markers", "rating": "stars",
    "custom": "custom", "tag_comment": "comment",
}
# The app's own tag fields the 🏷 editor's "Also write these into the MP3 file"
# writes. Custom only while it is mapped to a frame (planner.music.custom_field).
_APP_TAG_FIELDS = ("rating", "classes_ok", "is_instrumental", "comment_tags", "custom")


def _write_summary(raw, form, app) -> str:
    """What one 🏷 write changed, for the log."""
    parts = []
    if raw:
        parts.append("table: changed %d, deleted %d, added %d" % (
            len(raw.get("sets") or {}), len(raw.get("deletes") or ()),
            len(raw.get("adds") or ())))
    if form:
        parts.append("form: " + ", ".join(form))
    if app:
        parts.append("app fields: " + ", ".join(app))
    return "\n".join(parts)


def _tag_value_text(value) -> str:
    """One tag value as the toast shows it ('—' for empty, so a field that was
    CLEARED still reads as a change and not as a half-written line)."""
    if isinstance(value, (list, tuple)):
        return "/".join(str(v) for v in value) if value else "—"
    if value is None or value == "" or value is False:
        return "—"
    return str(value)


def tag_change_summary(changed: dict, translate: bool = False) -> str:
    """'dance SF → RB, takt 29 → 25' for a rescan_tags result. `translate`
    names the fields in the UI language (the toast); the log stays English."""
    def label(col):
        name = _TAG_FIELD_LABELS.get(col, col)
        return i18n.t(name) if translate else name
    return ", ".join(
        f"{label(col)} {_tag_value_text(old)} → {_tag_value_text(new)}"
        for col, (old, new) in changed.items())


class TagEditMixin(MainWindowHost):
    """🏷 Reading and writing a title's tags (MainWindow mixin)."""

    def _rescan_entry_tags(self, entry) -> dict:
        """Context-menu 🏷 'Re-read MP3 tags' for ONE track: drop what the scan
        cache holds for it, read its ID3 tags again and repaint every row that
        shows it. For tags edited (mp3tag & co.) while the app is running —
        a restart or a full library rebuild is otherwise the only way to see
        them. Returns the {field: (old, new)} the re-read changed."""
        lib, cache = self._library.lib, self._library.cache
        if entry is None or not getattr(entry, "path", None) or lib is None or cache is None:
            return {}
        p = Path(entry.path)
        if not p.exists():
            show_toast(self, i18n.t("🏷  %s is not on disk any more") % p.name, error=True)
            return {}
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            changed = lib.rescan_tags(entry, cache)
        except Exception as exc:
            log.warning("🏷 Couldn't re-read the tags of %s:\n%s", p.name, exc)
            show_toast(self, i18n.t("🏷  Couldn't re-read %s: %s") % (p.name, exc), error=True)
            return {}
        finally:
            QApplication.restoreOverrideCursor()

        for table in self._deckset.all_tables:
            table.refresh_paths([p])
        browser = getattr(self, "_lib_browser", None)
        if browser is not None:
            browser.set_entries(lib.entries)
        if changed:
            log.info("🏷 Tags re-read for %s:\n%s", p.name,
                     tag_change_summary(changed))
            show_toast(self, "🏷  %s: %s" % (p.name, tag_change_summary(changed, translate=True)))
        else:
            show_toast(self, i18n.t("🏷  %s: tags unchanged") % p.name)
        return changed

    def _set_entry_rating(self, entry, stars: int):
        """★ clicked in a deck or 📚 library row: store the rating as an in-app
        tag edit (the DB, not the MP3) and repaint every row showing the track,
        in the library one cell rather than the whole pane. Rows holding
        another MusicEntry object for the same file — an outside copy restored
        from an M3U — are handed in too, so they don't keep the old stars."""
        lib, cache = self._library.lib, self._library.cache
        if entry is None or lib is None or cache is None:
            return
        try:
            paths = lib.edit_tags(self._copies_of(entry), cache, {"rating": stars})
        except ValueError as exc:
            log.warning("★ Couldn't store the rating of %s:\n%s", Path(entry.path).name, exc)
            show_toast(self, i18n.t("★  Couldn't store the rating: %s") % exc, error=True)
            return
        for table in self._deckset.all_tables:
            table.refresh_paths(paths)
        browser = getattr(self, "_lib_browser", None)
        if browser is not None:
            browser.show_tag_cells(paths)

    def _copies_of(self, entry) -> list:
        """`entry` and every other MusicEntry object an open list holds for the
        same file — an edit must reach those rows too."""
        path = str(entry.path)
        out = [entry]
        for t in self._deckset.all_tables:
            for e in t._row_meta.entries():
                if str(e.path) == path and not any(e is x for x in out):
                    out.append(e)
        return out

    def _edit_entry_tags(self, entries, focus=None):
        """Context-menu 🏷 'Edit tags…' for one track or every selected one —
        or a double-click's ⚙ Edit tags, opened on the field of the column
        double-clicked (`focus`, see TagEditDialog)."""
        seen, todo = set(), []
        for e in entries:
            if e is not None and getattr(e, "path", None) and str(e.path) not in seen:
                seen.add(str(e.path))
                todo.append(e)
        lib = self._library.lib
        if not todo or lib is None or self._library.cache is None:
            return
        dlg = TagEditDialog(todo, marker_suggestions(lib.entries), self,
                            custom_source=custom_field.source(),
                            map_custom=self._set_custom_source, focus=focus)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._apply_tag_dialog(todo, dlg)

    def _apply_tag_dialog(self, entries, dlg):
        """Store what the 🏷 editor says each track becomes, then repaint every
        list showing one of them. What goes into the MP3 — the extended table,
        the form (into every selected MP3) and, with the editor's "Also write
        these into the MP3 file" ticked, stars, classes, instrumental, markers
        and, while it is mapped to a frame, Custom — is written first, one save
        per file. The app fields then go into the DB, keyed by the file's
        fingerprint as it is after the write, which keeps only what the file
        can't say (edit_tags drops a value equal to the file's)."""
        lib, cache = self._library.lib, self._library.cache
        if lib is None or cache is None:
            return
        paths = []
        form = dlg.form_changes()
        form_to = {id(e) for e in dlg.form_mp3s()} if form else set()
        # Asked before anything is stored: a half-ticked class reads the
        # track's own classes, which a write changes.
        todo = [] if dlg.reset_requested else [
            (e, c) for e in entries if (c := dlg.changes_for(e))]
        mapped = custom_field.writable()   # the old ID3v1 comment is read only
        writable = [f for f in _APP_TAG_FIELDS if mapped or f != "custom"]
        on_disk = [(e, mp3) for e, c in todo
                   if Path(e.path).suffix.lower() == ".mp3" and Path(e.path).is_file()
                   and (mp3 := {k: v for k, v in c.items() if k in writable})]
        app = {id(e): c for e, c in on_disk} if dlg.write_app_to_mp3() else {}
        for e in entries:
            raw = dlg.raw_edits(e)
            f = with_filename_title(form, e.path) if id(e) in form_to else None
            a = app.get(id(e))
            if raw or f or a:
                paths += self._write_into_mp3(
                    e, lambda p, r=raw, f=f, a=a: id3_frames.write_tags(p, r, f, a),
                    _write_summary(raw, f, a))
        try:
            if dlg.reset_requested:
                for e in entries:
                    paths += lib.reset_tag_edits(self._copies_of(e), cache)
            for e, changes in todo:
                paths += lib.edit_tags(self._copies_of(e), cache, changes)
        except ValueError as exc:
            log.warning("🏷 Couldn't store the tag edit:\n%s", exc)
            show_toast(self, i18n.t("🏷  Couldn't store the tags: %s") % exc,
                       WARN_TOAST_MS, error=True)
        if not paths:
            return
        for table in self._deckset.all_tables:
            table.refresh_paths(paths)
        browser = getattr(self, "_lib_browser", None)
        if browser is not None:
            browser.set_entries(lib.entries)   # a class edit may change the filter
        tree = getattr(self, "_tourney_tree", None)
        if tree is not None:
            tree.set_entries(lib.entries)      # its rows hold title and artist as text

    def _map_custom_field(self):
        """Header right-click "Map Custom to an MP3 tag…": ask which frame
        fills the Custom field, then read that frame of every track the
        library and the lists show — off the GUI thread, a whole library is
        some seconds of ID3 reads — and repaint."""
        if self._custom_reader is not None or self._library.cache is None:
            return
        answer = self._ask_custom_source()
        if answer is not None:
            self._set_custom_source(*answer)

    def _set_custom_source(self, frame, desc="") -> bool:
        """Map Custom to `frame` (None: the app only) and read it anew — from
        the header menu or a row of the 🏷 editor's Extended tab. False while
        a reading is still under way: the mapping is left as it was then."""
        lib = self._library.lib
        if self._custom_reader is not None or lib is None or self._library.cache is None:
            return False
        if not custom_field.set_source(frame, desc):
            return True
        entries = list(lib.entries)
        for t in self._deckset.all_tables:
            entries += t._row_meta.entries()
        paths = list(dict.fromkeys(str(e.path) for e in entries))
        reader = CustomFieldReader(paths, self)
        reader.done.connect(lambda values: self._on_custom_read(entries, values))
        reader.finished.connect(reader.deleteLater)
        self._custom_reader = reader
        reader.start()
        return True

    def _ask_custom_source(self):
        """(frame id or None, description) from the mapping dialog; None
        when it was cancelled."""
        # A look into some MP3s of the archive, for the descriptions they use.
        lib = self._library.lib
        paths = [e.path for e in lib.entries if str(e.path).lower().endswith(".mp3")] if lib else []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            samples = id3_frames.sample_custom(paths)
        finally:
            QApplication.restoreOverrideCursor()
        dlg = CustomSourceDialog(custom_field.source(), self, samples=samples)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        return dlg.source()

    def _on_custom_read(self, entries, values: dict):
        self._custom_reader = None
        lib, cache = self._library.lib, self._library.cache
        if lib is None or cache is None:
            return
        paths = lib.read_custom(entries, cache, values)
        src = custom_field.source()
        log.info("🏷 Custom field mapped\n"
                 "frame: %s\n"
                 "tracks changed: %d", ":".join(src) if src else "app only", len(paths))
        if not paths:
            return
        for table in self._deckset.all_tables:
            table.refresh_paths(paths)
        browser = getattr(self, "_lib_browser", None)
        if browser is not None:
            browser.show_tag_cells(paths)

    def _write_into_mp3(self, entry, write, what: str) -> list:
        """Run `write(path)` on the entry's file, then read its tags again onto
        every row showing it. Returns the paths to repaint.

        The write changes the file's content fingerprint, the key of its
        analysis and its in-app tag edits; `ensure_audio_fp` first puts the
        tag-free audio fingerprint on record, so the next hash finds those rows
        and moves them over (AudioCache.reattach_retagged).

        A title playing or paused in the player is refused: a tag that grows
        moves the audio under the decoder, mid-song. A title only cued there
        (every deck load cues its first one) is written and then loaded again,
        so ⏯ starts from where the audio now begins."""
        p = Path(entry.path)
        lib, cache = self._library.lib, self._library.cache
        if lib is None or cache is None:
            return []
        player = self._player if self._player_has_loaded(p) else None
        if player is not None and player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            show_toast(self, i18n.t("🏷  %s is in the player — stop it to write "
                                     "its MP3 tags") % p.name, WARN_TOAST_MS, error=True)
            return []
        try:
            cache.ensure_audio_fp(p)
            write(p)
        except (OSError, ValueError, MutagenError) as exc:
            log.warning("🏷 Couldn't write the MP3 tags of %s:\n%s", p.name, exc)
            show_toast(self, i18n.t("🏷  Couldn't write the MP3 tags: %s") % exc,
                       WARN_TOAST_MS, error=True)
            return []
        if player is not None:
            src = player.source()
            player.setSource(QUrl())
            player.setSource(src)
        try:
            for e in self._copies_of(entry):
                lib.rescan_tags(e, cache)
        except Exception as exc:
            log.warning("🏷 Couldn't re-read the tags of %s:\n%s", p.name, exc)
            show_toast(self, i18n.t("🏷  Couldn't re-read %s: %s") % (p.name, exc), error=True)
        cache.save()
        log.info("🏷 MP3 tags written\n"
                 "file: %s\n"
                 "%s", p.name, what)
        return [p]

    def _player_has_loaded(self, path: Path) -> bool:
        """Whether the main player has `path` loaded — playing, paused or cued."""
        player = getattr(self, "_player", None)
        if not player:
            return False
        src = player.source().toLocalFile()
        return bool(src) and (os.path.normcase(os.path.abspath(src))
                              == os.path.normcase(os.path.abspath(str(path))))
