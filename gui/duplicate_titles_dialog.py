"""♊ Which file of a title to keep — the choice behind "Remove duplicate titles".

A copy of the very same bytes can simply go: it doesn't matter which of two
identical files stays. Another file of the same title — a tournament '_cut', a
re-encode, a second release — is a different recording, so for each such title
the user picks the one to keep, or keeps them all.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QScrollArea, QVBoxLayout, QWidget,
)

from gui.common import _fmt_track_secs
from planner import i18n


def _describe(entry) -> str:
    """The file name and length, its folder on a second line."""
    p = Path(str(entry.path))
    secs = int(getattr(entry, "duration", 0) or 0)
    length = f"   {_fmt_track_secs(secs)}" if secs else ""
    return f"{p.name}{length}\n{p.parent}"


class DuplicateTitlesDialog(QDialog):
    """`identical`: (removed entry, kept entry) pairs, shown for information only.
    `groups`: per title, the (row, entry) of every file holding it, in list order.
    After exec, `removed_rows()` gives the group rows the user chose away.
    `play_cb(path | None)` plays / stops a file: each file gets a ▶ to hear it."""

    def __init__(self, parent, identical, groups, play_cb=None):
        super().__init__(parent)
        self.setWindowTitle("Duplicate titles")
        self.resize(820, 520)
        self._groups = [list(g) for g in groups]
        self.radios: list[list[QRadioButton]] = []   # per group: one per file, then "Keep all"
        self.play_buttons: list[QPushButton] = []
        self._button_groups = []
        self._play_cb = play_cb
        self._playing = None                         # the ▶ button now showing ■
        self.finished.connect(lambda _=0: self._stop_preview())

        root = QVBoxLayout(self)
        head = QLabel(
            "This list holds some titles more than once.<br>"
            "<span style='color:#666'>For each title, pick the file to keep — the "
            "others are removed. <b>Keep all</b> leaves that title alone.</span>")
        head.setWordWrap(True)
        root.addWidget(head)

        body = QWidget()
        lyt = QVBoxLayout(body)
        if identical:
            box = QGroupBox(
                i18n.t("🟰  Identical files — the earlier copy is removed, the last stays (%d)")
                % len(identical))
            b = QVBoxLayout(box)
            for gone, _kept in identical[:8]:
                b.addWidget(QLabel(_describe(gone)))
            if len(identical) > 8:
                b.addWidget(QLabel(i18n.t("… and %d more") % (len(identical) - 8)))
            lyt.addWidget(box)
        for group in self._groups:
            first = group[0][1]
            box = QGroupBox(f"≈  {first.title}" + (f"   ({first.dance})" if first.dance else ""))
            b = QVBoxLayout(box)
            bg = QButtonGroup(box)
            row_radios = []
            for _row, entry in group:
                rb = QRadioButton(_describe(entry))
                rb.setToolTip(str(entry.path))
                bg.addButton(rb)
                row_radios.append(rb)
                if play_cb is None:
                    b.addWidget(rb)
                    continue
                line = QHBoxLayout()
                play = QPushButton("▶")
                play.setFixedSize(26, 20)
                play.setStyleSheet("padding:0;")
                play.setToolTip("Play / stop this file")
                play.clicked.connect(
                    lambda _=False, p=entry.path, btn=play: self._toggle_play(p, btn))
                self.play_buttons.append(play)
                line.addWidget(play, 0, Qt.AlignmentFlag.AlignVCenter)
                line.addWidget(rb, 1)
                b.addLayout(line)
            keep_all = QRadioButton("Keep all")
            keep_all.setChecked(True)
            bg.addButton(keep_all)
            b.addWidget(keep_all)
            row_radios.append(keep_all)
            self.radios.append(row_radios)
            self._button_groups.append(bg)
            lyt.addWidget(box)
        lyt.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        apply = QPushButton("🧹  Remove")
        apply.clicked.connect(self.accept)
        cancel.setDefault(True)          # an accidental Enter removes nothing
        btns.addWidget(cancel)
        btns.addWidget(apply)
        root.addLayout(btns)

    def _toggle_play(self, path, btn: QPushButton):
        """Play one file, or stop it when it is the one already playing."""
        if self._playing is btn:
            self._stop_preview()
            return
        if self._playing is not None:
            self._playing.setText("▶")
        self._playing = btn
        btn.setText("■")
        self._play_cb(Path(str(path)))

    def _stop_preview(self):
        """Stop the file still playing — also when the dialog closes."""
        if self._playing is not None:
            self._play_cb(None)
            self._playing.setText("▶")
            self._playing = None

    def removed_rows(self) -> set[int]:
        """The rows of every file not picked in a group that has a pick."""
        out: set[int] = set()
        for group, radios in zip(self._groups, self.radios):
            kept = next((row for (row, _e), rb in zip(group, radios) if rb.isChecked()), None)
            if kept is not None:
                out |= {row for row, _e in group if row != kept}
        return out
