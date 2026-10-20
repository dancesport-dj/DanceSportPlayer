"""🗑 Reset database: which parts of the DB to empty (planner reset_database).

Nothing is ticked when it opens, and the reset button stays grey until
something is: emptying a part is a click the operator has to mean. Each box
says what comes back how - the next scan, ⚗ Analysis, or only ♻ Restore.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from planner import i18n

# The parts in the order shown, keyed like planner RESET_GROUPS.
_PARTS = (
    ("scan", "🏷  Tags read from the music files",
     "Dance, BPM, class and title of every file, the file list and the learned "
     "playlist index. The next library scan reads them again (minutes)."),
    ("analysis", "🎚  Audio analysis",
     "Features, AI embeddings, loudness, silences, waveforms, vocal shares and "
     "detected PD highlights. ⚗ Analysis builds them again (hours)."),
    ("user", "✋  My own data",
     "Your tag edits, hand-set PD marks and the 📜 play log. Nothing rebuilds "
     "them; only ♻ Restore user data backup brings them back."),
)


class ResetDatabaseDialog(QDialog):
    """Pick the parts; `chosen()` names them once the dialog is accepted."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🗑  Reset database")
        self.setMinimumWidth(520)
        lyt = QVBoxLayout(self)
        intro = QLabel(i18n.t(
            "Empty the chosen parts of the database. Your own data is backed up "
            "first either way, and the app restarts afterwards."))
        intro.setWordWrap(True)
        lyt.addWidget(intro)
        self.boxes: dict[str, QCheckBox] = {}
        for key, title, detail in _PARTS:
            box = QCheckBox(title)
            box.toggled.connect(self._sync)
            note = QLabel(i18n.t(detail))
            note.setWordWrap(True)
            note.setContentsMargins(24, 0, 0, 6)
            lyt.addWidget(box)
            lyt.addWidget(note)
            self.boxes[key] = box
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.reset_btn = buttons.addButton(i18n.t("Reset and restart"),
                                           QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lyt.addWidget(buttons)
        self._sync()

    def chosen(self) -> set[str]:
        return {key for key, box in self.boxes.items() if box.isChecked()}

    def _sync(self):
        self.reset_btn.setEnabled(bool(self.chosen()))
