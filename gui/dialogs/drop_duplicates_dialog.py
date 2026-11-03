"""Several titles dropped onto a list that holds them already: decide before anything is added.

One row per dropped title, laid out like the Check duplicates dialog: the two
files on the left, a Skip / Replace / Keep both choice on the right. Nothing has
been added yet, so Cancel leaves the list as it was.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.row_keys import RowKeys
from planner import i18n

REPLACE, ADD, SKIP = "replace", "add", "skip"
_KEYS = {Qt.Key.Key_S: SKIP, Qt.Key.Key_R: REPLACE, Qt.Key.Key_E: ADD, Qt.Key.Key_B: ADD}


def _name(entry) -> str:
    path = getattr(entry, "path", None)
    return Path(str(path)).name if path else (getattr(entry, "title", "") or "?")


def _html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;")


class DropDuplicatesDialog(QDialog):
    """`pairs`: [(dropped entry, entry already in the list, same_audio), …]."""

    def __init__(self, parent, pairs: list):
        super().__init__(parent)
        self.setWindowTitle(i18n.t("Already in this list"))
        self.setMinimumWidth(640)
        self._pairs = pairs
        self._keys = RowKeys(self, _KEYS)
        self._combos: list[QComboBox] = []
        outer = QVBoxLayout(self)
        head = QLabel(i18n.t("These dropped titles are in the list already. "
                             "What should happen to each?"))
        head.setWordWrap(True)
        outer.addWidget(head)
        hint = QLabel(i18n.t("Tab moves through the titles · S = skip · R = replace · E / B = keep both"))
        hint.setStyleSheet("color:#666; font-size:11px;")
        outer.addWidget(hint)
        body = QWidget()
        lyt = QVBoxLayout(body)
        for dropped, held, same_audio in pairs:
            lyt.addWidget(self._row(dropped, held, same_audio))
        lyt.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        if self._combos:
            self._combos[0].setFocus()

    def _row(self, dropped, held, same_audio: bool) -> QFrame:
        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        row = QHBoxLayout(box)
        kind = (i18n.t("🟰  Same audio") if same_audio
                else i18n.t("≈  Same title or recording"))
        info = QLabel(f"<b>{kind}</b><br>"
                      + i18n.t("In the list: %s") % _html(_name(held))
                      + "<br>"
                      + i18n.t("Dropped: %s") % _html(_name(dropped)))
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.setStyleSheet("font-size:11px;")
        row.addWidget(info, stretch=2)
        combo = QComboBox()
        combo.addItem("⏭  " + i18n.t("Skip"), SKIP)
        combo.addItem("🔁  " + i18n.t("Replace"), REPLACE)
        combo.addItem("➕  " + i18n.t("Keep both"), ADD)
        combo.setFixedWidth(150)
        row.addWidget(combo, 0, Qt.AlignmentFlag.AlignVCenter)
        self._keys.add(combo, box)
        self._combos.append(combo)
        return box

    def choices(self) -> list[str]:
        """One of REPLACE / ADD / SKIP per pair, in the order given."""
        return [c.currentData() for c in self._combos]
