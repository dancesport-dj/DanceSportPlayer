"""ℹ About — which app, which version, whose, under which licence.

Opened from the ❔ button's menu. The version is the one the build baked in
(planner.version), so a screenshot of this dialog names the release a problem
was seen in.
"""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from planner import i18n
from planner.version import app_version
from shared.widgets import _app_icon

REPO_URL = "https://github.com/dancesport-dj/DanceSportPlayer"
AUTHOR = "marcelkb"
AUTHOR_URL = "https://github.com/marcelkb"
# The first line of LICENSE (tests.gui.test_about keeps the two in step).
LICENSE_NAME = "MIT License"
COPYRIGHT = "© 2026 marcelkb"


def _link(url: str) -> str:
    return f"<a href='{html.escape(url)}'>{html.escape(url.removeprefix('https://'))}</a>"


def about_html(name: str, version: str) -> str:
    """The dialog's text. Its labels are catalog keys; rich text does not go
    through the text hook, so they are translated here."""
    rows = (
        (i18n.t("Version"), html.escape(version)),
        (i18n.t("Project"), _link(REPO_URL)),
        (i18n.t("Author"), f"{html.escape(AUTHOR)} · {_link(AUTHOR_URL)}"),
        (i18n.t("License"), html.escape(LICENSE_NAME)),
    )
    body = "".join(f"<tr><td style='padding-right:12px;'><b>{label}</b></td>"
                   f"<td>{value}</td></tr>" for label, value in rows)
    return (f"<p style='font-size:15pt;'><b>{html.escape(name)}</b></p>"
            f"<table>{body}</table>"
            f"<p style='color:#666;'>{html.escape(COPYRIGHT)}</p>")


def about_dialog(parent, name: str) -> QDialog:
    """❔ → ℹ About. The ℹ is the menu entry's; the window title goes without."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("About")
    dlg.setWindowIcon(_app_icon())
    lyt = QVBoxLayout(dlg)
    lyt.setContentsMargins(24, 18, 24, 16)
    text = QLabel(about_html(name, app_version()))
    text.setObjectName("aboutText")
    text.setTextFormat(Qt.TextFormat.RichText)
    text.setOpenExternalLinks(True)
    text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    lyt.addWidget(text)
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.accept)
    lyt.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
    return dlg


def show_about(parent, name: str):
    about_dialog(parent, name).exec()
