"""🚦 Ready? — one traffic light per pre-flight check (planner/event/readiness.py).

The dialog only shows the grading and hands each "fix" back to the window:
the fixes are the existing actions (🧭 Fix paths, the 📊 / 🔇 / 🐂 library
passes, 🔁 Check duplicates), several of which run in the background. So it
stays open beside them, and ↻ Check again grades anew once they are done.
The headings of the 📁 files, 🔁 duplicates and 🎵 music lines are links that
open the whole tool — also on a green line, where there is nothing to fix.
"""

import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from planner import i18n
from planner.event.readiness import FAIL, OK, WARN, overall

_LIGHT = {OK: "🟢", WARN: "🟡", FAIL: "🔴"}

# The caption of each fix, by the action key a finding names.
_FIX_TEXT = {
    "paths": "🧭  Fix paths…",
    "loudness": "📊  Measure loudness…",
    "silences": "🔇  Probe silences…",
    "pd": "🐂  Find highlights…",
    "duplicates": "🔁  Resolve duplicates…",
    "music": "🎵  Show the report…",
    "outputs": "⚙  Choose outputs…",
    "controller": "🎛  Open the controller…",
    "awake": "☀  Keep it awake",
}

# Lines whose heading opens the whole tool behind them, green or not.
_TOOL = {"files": "paths", "duplicates": "duplicates", "music": "music"}


class ReadinessDialog(QDialog):
    """`grade()` returns the findings; `fixes` maps a finding's fix key to the
    window action that runs it."""

    def __init__(self, grade, fixes: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.t("🚦  Ready for the event?"))
        self.setMinimumWidth(560)
        self._grade = grade
        self._fixes = fixes
        self.level = OK
        self.fix_buttons: dict[str, QPushButton] = {}
        self.tool_links: dict[str, QLabel] = {}   # finding key → its linked heading

        lyt = QVBoxLayout(self)
        self._headline = QLabel()
        font = QFont(self._headline.font())
        font.setPointSizeF(font.pointSizeF() * 1.4)
        font.setBold(True)
        self._headline.setFont(font)
        lyt.addWidget(self._headline)
        self._body = QWidget()
        self._grid = QGridLayout(self._body)
        self._grid.setColumnStretch(1, 1)
        lyt.addWidget(self._body)
        lyt.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.recheck_btn = buttons.addButton(i18n.t("↻  Check again"),
                                             QDialogButtonBox.ButtonRole.ActionRole)
        self.recheck_btn.clicked.connect(self.refresh)
        buttons.rejected.connect(self.reject)
        lyt.addWidget(buttons)
        self.refresh()

    def refresh(self):
        """Grade anew and redraw every line."""
        findings = self._grade()
        self.level = overall(findings)
        # Red is a title that will not play — or, with every file there, a
        # card the hall would not hear the evening on.
        files_red = any(f.key == "files" and f.level == FAIL for f in findings)
        self._headline.setText({
            OK: i18n.t("🟢  Ready — every check is green."),
            WARN: i18n.t("🟡  Playable, with loose ends."),
            FAIL: (i18n.t("🔴  Not ready — some titles will not play.") if files_red
                   else i18n.t("🔴  Not ready — a sound output is not connected.")),
        }[self.level])
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        self.fix_buttons = {}
        self.tool_links = {}
        self.paths_btn = None
        for row, f in enumerate(findings):
            light = QLabel(_LIGHT[f.level])
            light.setAlignment(Qt.AlignmentFlag.AlignTop)
            heading = f"<b>{html.escape(f.title)}</b>"
            tool = self._fixes.get(_TOOL.get(f.key))
            if tool is not None:
                heading = f'<a href="#">{heading}</a>'
            detail = html.escape(f.detail).replace("\n", "<br>")
            head = text = QLabel(heading + "<br>" + detail)
            text.setWordWrap(True)
            text.setTextFormat(Qt.TextFormat.RichText)
            paths = self._fixes.get("paths") if f.key == "files" else None
            if paths is not None:
                # 🧭 Fix paths stands in the button column, green or not,
                # so the path fixer is a button away before every event.
                self.paths_btn = QPushButton(i18n.t(_FIX_TEXT["paths"]))
                self.paths_btn.clicked.connect(lambda _c=False, a=paths: a())
                self._grid.addWidget(self.paths_btn, row, 2, Qt.AlignmentFlag.AlignTop)
                if f.level != OK:
                    self.fix_buttons["paths"] = self.paths_btn
            if tool is not None:
                head.setToolTip(i18n.t("Click the heading to open the full tool."))
                head.linkActivated.connect(lambda _href, a=tool: a())
                self.tool_links[f.key] = head
            self._grid.addWidget(light, row, 0)
            self._grid.addWidget(text, row, 1)
            action = self._fixes.get(f.fix) if f.level != OK else None
            if action is not None and f.fix not in self.fix_buttons:
                btn = QPushButton(i18n.t(_FIX_TEXT[f.fix]))
                btn.clicked.connect(lambda _c=False, a=action: a())
                self._grid.addWidget(btn, row, 2, Qt.AlignmentFlag.AlignTop)
                self.fix_buttons[f.fix] = btn
