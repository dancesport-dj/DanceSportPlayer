#!/usr/bin/env python3
"""The drop-and-check panel: the second tab of the Check-music and Fix-paths
dialogs. Drop .m3u playlists or audio files in, curate the list, and see the
check's results below, with a progress bar and a Cancel for long passes."""

import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QProgressBar,
)
from PySide6.QtCore import Signal, QTimer

from gui.common import (
    _DroppedFilesList,
    _MultiFileDropZone,
)


class _DropCheckCancelled(Exception):
    """Raised from FileDropCheckPanel's progress tick when Cancel was pressed."""


class FileDropCheckPanel(QWidget):
    """Reusable 'drag .m3u playlists / audio files in and check them' panel: the drop
    zone, a curatable list of the files added so far (➕ add / ➖ remove / 🗑 clear,
    like the Check-duplicates window), a progress bar and a results area. Used as
    the second tab of the Check-music and Fix-paths dialogs.

    `run_fn(paths, progress_cb)` renders the results for the current files; it returns
    either a `QWidget` or a `(QWidget, summary_dict)` tuple. `summary_dict` is re-emitted
    via `resultsReady` so a host dialog can drive its own bottom summary / action button.
    When `action_label`/`action_fn` are given, an in-panel action button runs
    `action_fn(paths)` and then re-runs the check so the results update.

    The check pumps events on every `progress_cb` tick, so a click can land mid-run:
    the action button is off until the pass ends, and `checkStarted` tells a host to
    do the same with an action button of its own (`resultsReady` follows). A pass
    with many tracks, or one running past 250 ms, shows a Cancel next to the bar;
    it stops the pass at the next tick."""
    resultsReady = Signal(dict)
    checkStarted = Signal()

    def __init__(self, info_html: str, run_fn, action_label: str = "",
                 action_fn=None, parent=None):
        super().__init__(parent)
        self._run_fn    = run_fn
        self._action_fn = action_fn
        self._busy  = False
        self._dirty = False
        self._cancelled = False
        self._started = 0.0

        lyt = QVBoxLayout(self)
        info = QLabel(info_html)
        info.setWordWrap(True)
        lyt.addWidget(info)

        self._zone = _MultiFileDropZone()
        self._zone.filesDropped.connect(lambda ps: self._files.add_paths(ps))
        lyt.addWidget(self._zone)

        self._files = _DroppedFilesList()
        self._files.changed.connect(self._refresh)
        lyt.addWidget(self._files)

        self._action_btn = None
        if action_label and action_fn is not None:
            bar = QHBoxLayout()
            bar.addStretch(1)
            self._action_btn = QPushButton(action_label)
            self._action_btn.setEnabled(False)
            self._action_btn.clicked.connect(self._on_action)
            bar.addWidget(self._action_btn)
            lyt.addLayout(bar)

        self._pbar = QProgressBar()
        self._pbar.setVisible(False)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        pbar_row = QHBoxLayout()
        pbar_row.addWidget(self._pbar, stretch=1)
        pbar_row.addWidget(self._cancel_btn)
        lyt.addLayout(pbar_row)

        self._results = QScrollArea()
        self._results.setWidgetResizable(True)
        lyt.addWidget(self._results, stretch=1)
        self._refresh()

    def _on_action(self):
        if self._action_fn is not None:
            paths = self.paths()
            if paths:
                self._action_fn(paths)
                self._refresh()

    def _on_cancel(self):
        self._cancelled = True

    def _progress(self, done: int, total: int):
        # A short load finishes instantly — no bar flicker — unless its tracks are
        # slow (🔇 noise probes take seconds each).
        if total > 12 or time.monotonic() - self._started >= 0.25:
            self._pbar.setVisible(True)
            self._cancel_btn.setVisible(True)
            self._pbar.setRange(0, total)
            self._pbar.setValue(done)
        QApplication.processEvents()
        if self._cancelled:
            raise _DropCheckCancelled()

    def paths(self) -> list[Path]:
        """The files currently dropped into the panel."""
        return [Path(p) for p in self._files.paths()]

    def refresh(self):
        """Re-run the check (e.g. after a host-driven action rewrote files)."""
        self._refresh()

    def _refresh(self):
        # processEvents() during the check can deliver another drop, re-entering here;
        # defer it so the running pass finishes first.
        if self._busy:
            self._dirty = True
            return
        self._busy = True
        self._cancelled = False
        self._started = time.monotonic()
        self.checkStarted.emit()
        summary: dict = {}
        n = 0
        if self._action_btn is not None:
            self._action_btn.setEnabled(False)
        try:
            paths = self.paths()
            n = len(paths)
            try:
                out = (self._run_fn(paths, self._progress)
                       if n else QLabel("Drop playlists above to check them."))
            except _DropCheckCancelled:
                out = QLabel("Check cancelled — drop or ➕ add files to run it again.")
            widget, summary = out if isinstance(out, tuple) else (out, {})
            summary.setdefault("files", n)
            self._results.setWidget(widget)
        finally:
            self._busy = False
            self._pbar.setVisible(False)
            self._cancel_btn.setVisible(False)
            if self._action_btn is not None:
                self._action_btn.setEnabled(n > 0)
        self.resultsReady.emit(summary)
        if self._dirty:
            self._dirty = False
            QTimer.singleShot(0, self._refresh)
