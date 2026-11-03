"""📁 The folder tree beside the library table: titles are stored in folders.

The tree is built from the folders of the titles it is given. Folders are told
apart by `path_key`, so a capital letter does not split one into two, and a
folder holding nothing but one subfolder shares that subfolder's line.
"""
from collections.abc import Iterator
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

from planner import i18n
from planner.models import MusicEntry
from planner.playlist.planned import path_key

_KEY_ROLE = Qt.ItemDataRole.UserRole
_NAME_ROLE = Qt.ItemDataRole.UserRole + 1


def _glyph_icon(glyph: str) -> QIcon:
    """A small icon drawn from one emoji, so every platform gets the same pair."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setFont(QFont("Segoe UI Emoji", 18))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    p.end()
    return QIcon(pix)


def funnel_icon() -> QIcon:
    """The filter funnel, in the text colour of the current palette."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    app = QApplication.instance()
    color = QApplication.palette().text().color() if app is not None else QColor("black")
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF([QPointF(4, 6), QPointF(28, 6), QPointF(19, 17),
                             QPointF(19, 27), QPointF(13, 24), QPointF(13, 17)]))
    p.end()
    return QIcon(pix)


class _Folder:
    """One folder while the tree is put together."""

    def __init__(self, key: str = "", name: str = "", path: Path | None = None):
        self.key = key
        self.name = name
        self.path = path
        self.count = 0
        self.children: dict[str, _Folder] = {}

    def total(self) -> int:
        """Titles in this folder and everything below it."""
        return self.count + sum(c.total() for c in self.children.values())

    def sorted_children(self, by_count: bool = False) -> list[_Folder]:
        names = sorted(self.children)
        if by_count:
            names.sort(key=lambda k: -self.children[k].total())
        return [self.children[k] for k in names]

    def merged(self) -> _Folder:
        """This folder, joined with its subfolder while it holds nothing else."""
        node = self
        while node.count == 0 and len(node.children) == 1:
            child = next(iter(node.children.values()))
            child.name = str(Path(node.name, child.name))
            node = child
        return node


class FolderTree(QTreeWidget):
    """📁 Choosing a folder narrows the library to the titles directly in it."""

    folderChosen = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setMinimumWidth(120)
        self._source: list[MusicEntry] | None = None
        self._titles: dict[str, list[MusicEntry]] = {}
        self._root = _Folder()
        self._search = ""
        self._sort = "name"
        self._folder_icon = _glyph_icon("📁")
        self.currentItemChanged.connect(lambda *_: self.folderChosen.emit())

    def shows(self, entries: list[MusicEntry]) -> bool:
        """Was the tree built from this very list?"""
        return self._source is entries

    def set_titles(self, entries: list[MusicEntry]):
        """Build the tree from `entries`; the chosen folder stays if it still exists."""
        kept = self.folder()
        self._source = entries
        self._titles = {}
        folders: dict[str, Path] = {}
        for e in entries:
            key = path_key(e.path.parent)
            self._titles.setdefault(key, []).append(e)
            folders.setdefault(key, e.path.parent)
        root = _Folder()
        for key, folder in folders.items():
            node = root
            for depth, part in enumerate(folder.parts, 1):
                node = node.children.setdefault(
                    part.lower(), _Folder(path_key(Path(*folder.parts[:depth])), part,
                                          Path(*folder.parts[:depth])))
            node.count = len(self._titles[key])
        self._root = root
        self._rebuild(kept)

    def set_search(self, text: str):
        """Show only the folders whose name has `text`, and the ones above them."""
        self._search = text.strip().lower()
        self._applySearch()

    def set_sort(self, mode: str):
        """'name' or 'count' (the biggest folder first)."""
        if mode == self._sort:
            return
        self._sort = mode
        self._rebuild(self.folder())

    def sort_mode(self) -> str:
        return self._sort

    def _tops(self) -> list[_Folder]:
        """The first lines: a bare drive or root is left out, its folders stand in its place."""
        out = []
        for top in self._root.sorted_children(self._sort == "count"):
            node = top.merged()
            if node.count == 0 and len(node.children) > 1 and len(Path(node.name).parts) == 1:
                out.extend(c.merged() for c in node.sorted_children(self._sort == "count"))
            else:
                out.append(node)
        return out

    def _rebuild(self, kept: str):
        self.blockSignals(True)
        self.clear()
        everything = QTreeWidgetItem([i18n.t("📁 All folders")])
        everything.setData(0, _KEY_ROLE, "")
        self.addTopLevelItem(everything)
        for top in self._tops():
            self._add(top, None)
        chosen = next((i for i in self.all_items() if i.data(0, _KEY_ROLE) == kept),
                      everything)
        self.setCurrentItem(chosen)
        self.blockSignals(False)
        self._applySearch()

    def _applySearch(self):
        def visit(item: QTreeWidgetItem) -> bool:
            kids = [visit(c) for c in (item.child(i) for i in range(item.childCount()))
                    if c is not None]
            own = not self._search or self._search in str(item.data(0, _NAME_ROLE)).lower()
            show = own or any(kids)
            item.setHidden(not show)
            if self._search and any(kids):
                item.setExpanded(True)
            return show

        for i in range(1, self.topLevelItemCount()):
            top = self.topLevelItem(i)
            if top is not None:
                visit(top)

    def _add(self, node: _Folder, parent: QTreeWidgetItem | None):
        # A line with no titles of its own is a heading: its last folder name will do,
        # the tooltip has the whole path.
        name = (Path(node.name).name or node.name) if parent is None and not node.count             else node.name
        item = QTreeWidgetItem([f"{name}  ({node.count})" if node.count else name])
        item.setData(0, _KEY_ROLE, node.key)
        item.setData(0, _NAME_ROLE, name)
        item.setToolTip(0, str(node.path) if node.path else node.name)
        item.setIcon(0, self._folder_icon)
        if not node.count:
            # Nothing of its own: a click would only empty the table.
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        if parent is None:
            self.addTopLevelItem(item)
            item.setExpanded(True)
        else:
            parent.addChild(item)
        for child in node.sorted_children(self._sort == "count"):
            self._add(child.merged(), item)

    def all_items(self) -> Iterator[QTreeWidgetItem]:
        stack = [it for i in range(self.topLevelItemCount())
                 if (it := self.topLevelItem(i)) is not None]
        while stack:
            item = stack.pop()
            yield item
            stack.extend(it for i in range(item.childCount())
                         if (it := item.child(i)) is not None)

    def folder(self) -> str:
        """The chosen folder's key; '' = all of them."""
        item = self.currentItem()
        return (item.data(0, _KEY_ROLE) or "") if item is not None else ""

    def titles(self, key: str) -> list[MusicEntry]:
        """The titles directly in folder `key`."""
        return self._titles.get(key, [])

    def choose_all(self):
        """Back to every folder, without a signal: the caller filters anyway."""
        self.blockSignals(True)
        first = self.topLevelItem(0)
        if first is not None:
            self.setCurrentItem(first)
        self.blockSignals(False)
