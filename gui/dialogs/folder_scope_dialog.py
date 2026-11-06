"""📁 Which folders of the Favorites library ⚡ Generate draws from."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from planner import i18n
from planner.music.folder_scope import library_folders


def ask_library_folders(parent, root, entries, chosen=()) -> list[str] | None:
    """The folders ticked in a list of the library's folders, or None when the
    dialog is cancelled. Each folder stands for the titles directly in it."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(i18n.t("Draw from these folders"))
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel(i18n.t(
        "Each folder counts for the titles directly in it,\n"
        "not for the folders below it.")))
    lst = QListWidget()

    # One tri-state tick above the list, like "(Select All)" in a filter:
    # ticked = every folder, partly ticked = some, clear = none.
    all_chk = QCheckBox(i18n.t("Select all"))
    all_chk.setObjectName("select_all")
    lay.addWidget(all_chk)

    picked = {str(f).lower() for f in chosen}
    for name, count in library_folders(entries, root):
        shown = name or i18n.t("(main folder)")
        item = QListWidgetItem(i18n.t("📁 %s — %d titles") % (shown, count))
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if name in picked
                           else Qt.CheckState.Unchecked)
        lst.addItem(item)
    lay.addWidget(lst)

    def sync_all():
        states = {lst.item(i).checkState() for i in range(lst.count())}
        all_chk.blockSignals(True)
        all_chk.setCheckState(
            Qt.CheckState.Checked if states == {Qt.CheckState.Checked}
            else Qt.CheckState.Unchecked if Qt.CheckState.Checked not in states
            else Qt.CheckState.PartiallyChecked)
        all_chk.blockSignals(False)

    def tick_all(_checked=False):
        # Qt has already moved the box on: a partly ticked one became ticked
        # (everything), a fully ticked one became clear (nothing).
        state = (Qt.CheckState.Checked
                 if all_chk.checkState() == Qt.CheckState.Checked
                 else Qt.CheckState.Unchecked)
        lst.blockSignals(True)
        for i in range(lst.count()):
            lst.item(i).setCheckState(state)
        lst.blockSignals(False)
        sync_all()
    all_chk.setTristate(False)
    all_chk.clicked.connect(tick_all)
    lst.itemChanged.connect(lambda _item: sync_all())
    sync_all()

    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                           | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return [lst.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(lst.count())
            if lst.item(i).checkState() == Qt.CheckState.Checked]
