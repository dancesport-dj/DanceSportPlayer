"""📜 Played titles: the evenings in the play log, each one's titles, and a CSV
of an evening for a music report (GEMA and the like). See planner.playing.play_log."""
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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
)

from planner import i18n
from planner.playing import play_log
from planner.terms import dance_name
from shared.widgets import app_icon

log = logging.getLogger("dancesport.gui.play_log")

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
        self.plays_table = QTableWidget(0, 7)
        self.plays_table.setHorizontalHeaderLabels(
            ["Start", "Artist", "Title", "Composer", "Dance", "List", "Duration"])
        self.plays_table.verticalHeader().setVisible(False)
        self.plays_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plays_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Draggable columns, sized to their content once (in _show_evening) —
        # after that the widths are the operator's, whichever evening is shown.
        self.plays_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self._sized = False
        split.addWidget(self.plays_table)
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

    def _reload(self):
        self._evenings = play_log.evenings()
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

    def _current(self):
        i = self.evening_list.currentRow()
        return self._evenings[i] if 0 <= i < len(self._evenings) else None

    def _show_evening(self, _row=None):
        evening = self._current()
        plays = play_log.plays(evening) if evening else []
        self.plays_table.setRowCount(len(plays))
        for r, (p, secs) in enumerate(zip(plays, play_log.durations(plays), strict=True)):
            s = int(round(secs))
            cells = (f"{p.started_at:%H:%M:%S}", p.artist, p.title, p.composer,
                     dance_name(p.dance, p.dance) or "", p.list_name,
                     f"{s // 60}:{s % 60:02d}")
            for c, text in enumerate(cells):
                self.plays_table.setItem(r, c, QTableWidgetItem(text))
        if plays and not self._sized and self.isVisible():
            self._fit_columns()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._sized and self.plays_table.rowCount():
            self._fit_columns()

    def _fit_columns(self):
        """Content widths, and the room left over to the title (it used to
        stretch) — once; after that the widths are the operator's."""
        table = self.plays_table
        table.resizeColumnsToContents()
        head = table.horizontalHeader()
        spare = table.viewport().width() - head.length()
        if spare > 0:
            head.resizeSection(2, head.sectionSize(2) + spare)
        self._sized = True

    def _save_csv(self):
        evening = self._current()
        if evening is None:
            return
        title = i18n.t("Save played titles")
        chosen, _ = QFileDialog.getSaveFileName(
            self, title, str(Path.home() / f"played-{evening.start:%Y-%m-%d}.csv"),
            i18n.t("CSV files (*.csv);;All files (*)"))
        if not chosen:
            return
        try:
            play_log.to_csv(play_log.plays(evening), Path(chosen))
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
        play_log.delete(evening)
        log.info("🗑 Evening deleted from the play log\n"
                 "evening: %s\n"
                 "titles: %d", evening.start, evening.count)
        self._reload()
