"""📚 The library scan's progress in the status bar, and what waits for it.

The window opens before the scan of the library folder is done (a first start
on a big ~/Music used to sit behind the splash for minutes). While it runs,
this bar says how far it is, and every widget marked with the Qt property
`needs_library` is greyed out; when it is done, each gets back the state it
had before. Two buttons pause the scan and stop it early; the loader acts on
them, this bar only says what was asked.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QToolButton, QWidget

from planner import i18n

NEEDS_LIBRARY = "needs_library"


class LibraryLoadBar(QWidget):
    """A label, a bar and pause/stop buttons, for QStatusBar.addPermanentWidget.
    Hidden when idle."""

    paused = Signal(bool)
    stop_requested = Signal()

    def __init__(self, parent=None, repository: bool = False):
        """`repository`: the bar of 🔄 the whole-repository walk instead, which
        says so and greys nothing out (the favorites library is loaded)."""
        super().__init__(parent)
        self._repository = repository
        self.label = QLabel(self)
        self.progress = QProgressBar(self)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(160)
        self.progress.setMaximumHeight(14)
        self.pause_btn = QToolButton(self)
        self.pause_btn.setCheckable(True)
        self.pause_btn.setAutoRaise(True)
        self.pause_btn.toggled.connect(self._on_pause)
        self.stop_btn = QToolButton(self)
        self.stop_btn.setText("⏹")
        self.stop_btn.setAutoRaise(True)
        self.stop_btn.setToolTip(
            i18n.t("Stop the repository scan and use the titles read so far; "
                   "the next scan reads the rest") if repository else
            i18n.t("Stop the library scan and use the titles read so far; "
                   "the next start scans the rest"))
        self.stop_btn.clicked.connect(self._on_stop)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 6, 0)
        row.addWidget(self.label)
        row.addWidget(self.progress)
        row.addWidget(self.pause_btn)
        row.addWidget(self.stop_btn)
        # Only as wide as what it shows: the status bar would otherwise hand it
        # half its width, and the text would sit mid-window, apart from the bar.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.running = False
        self._done = 0
        self._total = 0
        self._stopping = False
        self._show_pause_state(False)
        self._was_enabled: list[tuple[QWidget, bool]] = []
        self.hide()

    def start(self, root: QWidget | None = None) -> None:
        """Grey out what under `root` needs the library, and show the bar."""
        self._was_enabled = ([] if root is None else
                             [(w, w.isEnabled()) for w in root.findChildren(QWidget)
                              if w.property(NEEDS_LIBRARY)])
        for w, _ in self._was_enabled:
            w.setEnabled(False)
        self.running = True
        self._stopping = False
        self.pause_btn.blockSignals(True)
        self.pause_btn.setChecked(False)
        self.pause_btn.blockSignals(False)
        self._show_pause_state(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.set_progress(0, 0)
        self.show()

    def set_progress(self, done: int, total: int) -> None:
        self._done, self._total = done, total
        repo = self._repository
        if self._stopping:
            self.label.setText(i18n.t("⏹ Stopping the repository scan…") if repo
                               else i18n.t("⏹ Stopping the library scan…"))
            return
        if self.pause_btn.isChecked():
            self.label.setText((i18n.t("⏸ Repository scan paused: %s / %s files") if repo
                                else i18n.t("⏸ Library scan paused: %s / %s files"))
                               % (f"{done:,}", f"{total:,}" if total else "…"))
            return
        if not total:   # still listing the folder: no count yet, a busy bar
            self.progress.setRange(0, 0)
            self.label.setText(i18n.t("🌐 Listing the repository folder…") if repo
                               else i18n.t("📚 Listing the library folder…"))
            return
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.label.setText((i18n.t("🌐 Repository: %s / %s files") if repo
                            else i18n.t("📚 Library: %s / %s files"))
                           % (f"{done:,}", f"{total:,}"))

    def finish(self) -> None:
        """Give every greyed-out widget back the state it had, and hide."""
        for w, enabled in self._was_enabled:
            w.setEnabled(enabled)
        self._was_enabled = []
        self.running = False
        self.hide()

    def _show_pause_state(self, on: bool) -> None:
        self.pause_btn.setText("▶" if on else "⏸")
        if self._repository:
            self.pause_btn.setToolTip(i18n.t("Go on with the repository scan") if on
                                      else i18n.t("Pause the repository scan"))
            return
        self.pause_btn.setToolTip(i18n.t("Go on with the library scan") if on
                                  else i18n.t("Pause the library scan"))

    def _on_pause(self, on: bool) -> None:
        self._show_pause_state(on)
        self.set_progress(self._done, self._total)
        self.paused.emit(on)

    def _on_stop(self) -> None:
        self._stopping = True
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.set_progress(self._done, self._total)
        self.stop_requested.emit()
