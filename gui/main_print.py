"""🖨 The running order on paper: the HTML for it and the PDF it is written to.

Split off gui/main_import.py as a MainWindow mixin — what the desk hands the
chairman, and what the same builder makes of dropped .m3u files.
"""
import logging

import time
from PySide6.QtCore import (
    QMarginsF,
    QSizeF,
)
from PySide6.QtGui import (
    QFont,
    QPageLayout,
    QPageSize,
    QPdfWriter,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
)
from pathlib import Path
from planner import i18n
from planner.config import OUTPUT_DIR
from gui.common import (
    _open_in_default_player,
    _sanitize_filename,
)
from gui.print_sheet import deck_print_html
from gui.running_order import Row
from gui.dialogs import (  # auto-resolved
    PrintExportDialog,
)

log = logging.getLogger("dancesport.gui.print")


class PrintMixin:
    """🖨 The printed running order: HTML per deck, then a PDF."""

    def _print_running_order(self):
        """🖨: export playlists as a PDF — one section per round, songs in play order
        with dance / heat / artist / title / album / BPM / length. A small dialog picks
        the source: the focused deck, every open deck, or .m3u/audio files dragged in."""
        dlg = PrintExportDialog(self, deck_count=len(self._visible_deck_tables()))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        mode = dlg.mode()
        if mode == "all":
            decks = [(self.deck(t).name or "Playlist",
                      t._row_meta.songs())
                     for t in self._visible_deck_tables()]
            decks = [(n, ms) for n, ms in decks if ms]
            default_name = "Playlists"
        elif mode == "dropped":
            decks = self._dropped_print_decks(dlg.dropped_paths())
            default_name = "Dropped"
        else:
            table = self._table
            metas = table._row_meta.songs()
            decks = [(self.deck(table).name or "Playlist", metas)] if metas else []
            default_name = self.deck(table).name or "Playlist"

        if not decks:
            QMessageBox.information(self, "Print playlist",
                                    "Nothing to print — no songs found.")
            return

        parts: list[str] = []
        for di, (name, metas) in enumerate(decks):
            if di:
                parts.append("<div style='page-break-before:always;'></div>")
            parts.extend(deck_print_html(name, metas))

        name = decks[0][0] if len(decks) == 1 else default_name
        self._write_print_pdf(parts, name)

    def _dropped_print_decks(self, paths: list) -> list:
        """Build (name, metas) sections from dragged-in .m3u/audio files: one section
        per dropped .m3u (its tracks in file order), plus a 'Dropped files' section for
        any raw audio. Metas are flat (no round/heat) so the print loop renders them as
        a single table."""
        if not self._lib or self._cache is None:
            return []
        decks: list[tuple] = []
        loose: list[Row] = []
        for p in paths:
            p = Path(p)
            if p.suffix.lower() in (".m3u", ".m3u8"):
                metas = [Row(entry=e, dance=getattr(e, "dance", ""))
                         for e in (self._external_entry(t)
                                   for t in self._m3u_track_paths(p)) if e]
                if metas:
                    decks.append((p.stem, metas))
            else:
                e = self._external_entry(p)
                if e:
                    loose.append(Row(entry=e, dance=getattr(e, "dance", "")))
        if loose:
            decks.append(("Dropped files", loose))
        return decks

    def _external_entry(self, path: Path):
        return self._lib.entry_for(path, self._cache)

    def _write_print_pdf(self, parts: list, name: str):
        target = OUTPUT_DIR / (f"{time.strftime('%Y-%m-%d')}_"
                               f"{_sanitize_filename(name)}.pdf")
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            writer = QPdfWriter(str(target))
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageMargins(QMarginsF(12, 12, 12, 12),
                                  QPageLayout.Unit.Millimeter)
            # 96 dpi: the document lays out in CSS-pixel terms, so the 100%-
            # wide table really spans the printable width (at the default
            # 1200 dpi it rendered into a tiny corner of the page).
            writer.setResolution(96)
            doc = QTextDocument()
            font = QFont("Segoe UI")
            font.setPointSize(11)
            doc.setDefaultFont(font)
            doc.setHtml("".join(parts))
            doc.setPageSize(QSizeF(writer.width(), writer.height()))
            doc.print_(writer)
        except Exception as exc:
            QMessageBox.critical(self, "Print playlist",
                                 i18n.t("Could not write the PDF:\n%s") % exc)
            return
        self.statusBar().showMessage(i18n.t("🖨 Playlist saved — %s") % target.name)
        if QMessageBox.question(
                self, "Print playlist",
                i18n.t("Playlist saved as\n%s\n\nOpen it now?") % target.name
        ) == QMessageBox.StandardButton.Yes:
            # The shared helper, not os.startfile: off Windows that attribute
            # does not exist at all and the AttributeError would sail straight
            # past an `except OSError`.
            _open_in_default_player(target, self)
