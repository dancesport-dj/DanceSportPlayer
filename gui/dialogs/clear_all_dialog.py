"""🧹 What the Clear all button empties: playlists, wishlists, the party list."""

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from planner import i18n


class ClearAllDialog(QDialog):
    """Three ticks, one per kind of list. Only the playlists are ticked at the
    start, as before the dialog existed; a kind with nothing in it is greyed out."""

    def __init__(self, parent, n_playlists: int, n_wishlists: int, party_titles: int):
        super().__init__(parent)
        self.setWindowTitle(i18n.t("Clear all"))
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(i18n.t("What should be emptied? This can't be undone.")))
        self.playlists = self.addTick(
            lay, i18n.t("🧹  All playlists (%d filled)") % n_playlists, n_playlists, True)
        self.wishlists = self.addTick(
            lay, i18n.t("⭐  All wishlists (%d filled)") % n_wishlists, n_wishlists, False)
        self.party = self.addTick(
            lay, i18n.t("🤸  Party / competition list (%d titles)") % party_titles,
            party_titles, False)
        self.box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                    | QDialogButtonBox.StandardButton.Cancel)
        self.box.accepted.connect(self.accept)
        self.box.rejected.connect(self.reject)
        lay.addWidget(self.box)
        for tick in (self.playlists, self.wishlists, self.party):
            tick.toggled.connect(self.syncOk)
        self.syncOk()

    @staticmethod
    def addTick(lay, text: str, count: int, checked: bool) -> QCheckBox:
        tick = QCheckBox(text)
        tick.setEnabled(count > 0)
        tick.setChecked(checked and count > 0)
        lay.addWidget(tick)
        return tick

    def syncOk(self):
        """Nothing ticked, nothing to confirm."""
        self.box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            any(t.isChecked() for t in (self.playlists, self.wishlists, self.party)))

    def choice(self) -> tuple[bool, bool, bool]:
        """(playlists, wishlists, party list) as ticked."""
        return (self.playlists.isChecked(), self.wishlists.isChecked(),
                self.party.isChecked())


def ask_clear_all(parent, n_playlists: int, n_wishlists: int, party_titles: int):
    """The ticks as (playlists, wishlists, party), or None when cancelled."""
    dlg = ClearAllDialog(parent, n_playlists, n_wishlists, party_titles)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.choice()
