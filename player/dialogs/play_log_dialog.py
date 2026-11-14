"""📜 Played titles: the evenings in the play log, each one's titles, and a CSV
of an evening for a music report (GEMA and the like). See planner.playing.play_log."""
import logging
import re
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from planner import i18n
from planner.playing import play_log
from planner.store import JsonStore
from planner.terms import dance_name
from shared.plain_text import plain_tip
from shared.widgets import app_icon

log = logging.getLogger("dancesport.gui.play_log")

# One long cell (a composer list of a hundred characters) must not size its whole
# column: a column fits its content up to this, longer text is cut and shows whole
# in the tooltip.
MAX_COLUMN_WIDTH = 240

EMPTY_HINT = ("Nothing has been played yet. A title is logged in playing mode\n"
              "once it has run for 10 seconds, the moment its row greys out.")


class PlayLogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📜 Played titles")
        self.setWindowIcon(app_icon())
        self.resize(900, 520)

        lay = QVBoxLayout(self)
        self.empty_hint = QLabel(EMPTY_HINT)
        lay.addWidget(self.empty_hint)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.evening_list = QListWidget()
        self.evening_list.currentRowChanged.connect(self._show_evening)
        split.addWidget(self.evening_list)
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        # Which list the titles came from (a deck, a wishlist, the cartwall).
        # The choice also decides what "Save as CSV" writes.
        self.list_filter = QComboBox()
        self.list_filter.setToolTip(
            "Show only the titles of one list. Save as CSV then writes just those.")
        self.list_filter.currentIndexChanged.connect(self._fill_table)
        right_lay.addWidget(self.list_filter)
        self._plays = []
        self.plays_table = QTableWidget(0, 7)
        self.plays_table.setHorizontalHeaderLabels(
            ["Start", "Artist", "Title", "Composer", "Dance", "List", "Duration"])
        self.plays_table.verticalHeader().setVisible(False)
        self.plays_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plays_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Draggable columns. A column the operator dragged keeps that width (also
        # the next time the dialog opens); every other one fits the evening shown.
        head = self.plays_table.horizontalHeader()
        head.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._store = JsonStore("play_log_dialog.json")
        self._dragged = self._saved_widths(self._store.read({}))
        self._fitting = False
        self._tracking = False
        head.sectionResized.connect(self._on_section_resized)
        right_lay.addWidget(self.plays_table, 1)
        split.addWidget(right)
        split.setSizes([260, 640])
        lay.addWidget(split, 1)

        row = QHBoxLayout()
        self.save_btn = QPushButton("💾  Save as CSV…")
        self.save_btn.setToolTip(
            "Save this evening as a table for Excel: date, start, artist, title,\n"
            "composer, dance, list and how long each title ran — e.g. for a GEMA report.")
        self.save_btn.clicked.connect(self._save_csv)
        row.addWidget(self.save_btn)
        self.delete_btn = QPushButton("🗑  Delete evening")
        self.delete_btn.clicked.connect(self._delete_evening)
        row.addWidget(self.delete_btn)
        row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addWidget(close)
        lay.addLayout(row)

        self._evenings = []
        self._reload()

    @staticmethod
    def _saved_widths(saved) -> dict[int, int]:
        """The dragged column widths, whatever the file holds (#50)."""
        widths = saved.get("widths") if isinstance(saved, dict) else None
        out = {}
        for col, width in (widths.items() if isinstance(widths, dict) else ()):
            try:
                if str(col).isdigit() and int(width) > 0:
                    out[int(col)] = int(width)
            except (TypeError, ValueError):
                continue
        return out

    def _reload(self):
        try:
            self._evenings = play_log.evenings()
        except sqlite3.Error as exc:
            log.warning("📜 Play log not readable\n"
                        "error: %s", exc)
            self._evenings = []
        self.evening_list.clear()
        for e in self._evenings:
            text = (f"{e.start:%d.%m.%Y}   {e.start:%H:%M}–{e.end:%H:%M}\n"
                    + i18n.t("%d title(s)") % e.count)
            self.evening_list.addItem(QListWidgetItem(text))
        has = bool(self._evenings)
        self.empty_hint.setVisible(not has)
        self.save_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)
        if has:
            self.evening_list.setCurrentRow(0)
        else:
            self.plays_table.setRowCount(0)
            self._set_list_filter([])

    def _current(self):
        i = self.evening_list.currentRow()
        return self._evenings[i] if 0 <= i < len(self._evenings) else None

    def _show_evening(self, _row=None):
        evening = self._current()
        try:
            plays = play_log.plays(evening) if evening else []
        except sqlite3.Error as exc:
            log.warning("📜 Evening not read from the play log\n"
                        "error: %s", exc)
            plays = []
        self._plays = plays
        self._set_list_filter(play_log.list_names(plays))
        self._fill_table()

    def _set_list_filter(self, names: list[str]):
        """The filter offers "All lists" and the evening's lists. The list that
        was chosen stays chosen on the next evening if that one has it too."""
        keep = self._chosen_list()
        self.list_filter.blockSignals(True)
        self.list_filter.clear()
        self.list_filter.addItem(i18n.t("All lists"))
        self.list_filter.addItems(names)
        self.list_filter.setCurrentIndex(names.index(keep) + 1 if keep in names else 0)
        self.list_filter.blockSignals(False)
        self.list_filter.setEnabled(bool(names))

    def _chosen_list(self) -> str | None:
        """The list the table is narrowed to, None for all."""
        i = self.list_filter.currentIndex()
        return self.list_filter.itemText(i) if i > 0 else None

    def _fill_table(self, _index=None):
        only = self._chosen_list()
        # Durations come from the whole evening: a title ran up to the next one
        # played, whichever list that was on.
        shown = [(p, secs) for p, secs in
                 zip(self._plays, play_log.durations(self._plays), strict=True)
                 if only is None or p.list_name == only]
        plays = [p for p, _ in shown]
        self.plays_table.setRowCount(len(shown))
        for r, (p, secs) in enumerate(shown):
            s = int(round(secs))
            cells = (f"{p.started_at:%H:%M:%S}", p.artist, p.title, p.composer,
                     dance_name(p.dance, p.dance) or "", p.list_name,
                     f"{s // 60}:{s % 60:02d}")
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(plain_tip(text))
                self.plays_table.setItem(r, c, item)
        if plays and self.isVisible():
            self._fit_columns()

    def showEvent(self, event):
        super().showEvent(event)
        if self.plays_table.rowCount():
            self._fit_columns()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._tracking:
            self._store.write({"widths": {str(c): w for c, w in self._dragged.items()}})

    def _on_section_resized(self, column, _old, new):
        if self._tracking and not self._fitting:
            self._dragged[column] = new

    def _fit_columns(self):
        """Every column the operator did not drag fits its content up to
        MAX_COLUMN_WIDTH; the room left over goes to the title (it used to stretch)."""
        table = self.plays_table
        head = table.horizontalHeader()
        self._fitting = True
        try:
            table.resizeColumnsToContents()
            for c in range(table.columnCount()):
                if c in self._dragged:
                    head.resizeSection(c, self._dragged[c])
                elif head.sectionSize(c) > MAX_COLUMN_WIDTH:
                    head.resizeSection(c, MAX_COLUMN_WIDTH)
            spare = table.viewport().width() - head.length()
            if spare > 0 and 2 not in self._dragged:
                head.resizeSection(2, head.sectionSize(2) + spare)
        finally:
            self._fitting = False
        self._tracking = True

    def _save_csv(self):
        evening = self._current()
        if evening is None:
            return
        title = i18n.t("Save played titles")
        only = self._chosen_list()
        suffix = "-" + re.sub(r"[^\w-]+", "_", only).strip("_") if only else ""
        chosen, _ = QFileDialog.getSaveFileName(
            self, title, str(Path.home() / f"played-{evening.start:%Y-%m-%d}{suffix}.csv"),
            i18n.t("CSV files (*.csv);;All files (*)"))
        if not chosen:
            return
        try:
            play_log.to_csv(play_log.plays(evening), Path(chosen), only_list=only)
        except OSError as exc:
            QMessageBox.warning(self, "Save played titles",
                                i18n.t("Could not write the file:") + "\n\n" + str(exc))
            return
        log.info("📜 Played titles saved\n"
                 "evening: %s\n"
                 "titles: %d\n"
                 "file: %s", evening.start, evening.count, chosen)

    def _delete_evening(self):
        evening = self._current()
        if evening is None:
            return
        answer = QMessageBox.question(
            self, "Delete evening",
            i18n.t("Delete the evening of %s with its %d title(s) from the play log?\n\n"
                   "Its daily backups still hold it for 7 days.")
            % (f"{evening.start:%d.%m.%Y}", evening.count))
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            play_log.delete(evening)
        except sqlite3.Error as exc:
            log.warning("📜 Evening not deleted from the play log\n"
                        "evening: %s\n"
                        "error: %s", evening.start, exc)
            QMessageBox.warning(self, "Delete evening",
                                i18n.t("Could not delete the evening:") + "\n\n" + str(exc))
            return
        log.info("🗑 Evening deleted from the play log\n"
                 "evening: %s\n"
                 "titles: %d", evening.start, evening.count)
        self._reload()
