"""📥 Which parts of a venue pack this PC takes over."""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from planner import i18n
from planner.event import venue_pack

# What each document of a pack is, in the words of the desk.
PART_LABELS = {
    venue_pack.SETTINGS_FILE: "⚙ Settings",
    "autosave_playlist.json": "🎼 Decks and playlists",
    "cartwall.json": "🎛 Cartwall — pads and keys",
}


class PackPartsDialog(QDialog):
    """A tick for every document the pack carries; OK needs at least one."""

    def __init__(self, parent, names):
        super().__init__(parent)
        self.setWindowTitle(i18n.t("Import venue pack"))
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(i18n.t("What should this pack replace on this PC?")))
        self._ticks = {}
        for name in names:
            chk = QCheckBox(i18n.t(PART_LABELS.get(name, name)))
            chk.setChecked(True)
            chk.toggled.connect(self._sync)
            lay.addWidget(chk)
            self._ticks[name] = chk
        self._box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                     | QDialogButtonBox.StandardButton.Cancel)
        self._box.accepted.connect(self.accept)
        self._box.rejected.connect(self.reject)
        lay.addWidget(self._box)

    def _sync(self, _on=False):
        self._box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.chosen()))

    def chosen(self) -> list[str]:
        """The documents ticked, in the pack's order."""
        return [n for n, chk in self._ticks.items() if chk.isChecked()]


def ask_pack_parts(parent, names) -> list[str] | None:
    """The documents ticked, or None when the dialog is cancelled."""
    dlg = PackPartsDialog(parent, names)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.chosen()
