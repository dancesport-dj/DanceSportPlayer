"""ℹ About — which app, which version, whose, under which licence — and
📖 the manual.

Opened from the ❔ button's menu. The version is the one the build baked in
(planner.version), so a screenshot of this dialog names the release a problem
was seen in.
"""
import html
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from planner import i18n
from planner.version import app_version
from shared.widgets import _app_icon

REPO_URL = "https://github.com/dancesport-dj/DanceSportPlayer"
AUTHOR = "marcelkb"
AUTHOR_URL = "https://github.com/marcelkb"
# The app icon is Icons8's "Swing"; the free licence asks for a link to icons8.com in the About section (ICONS-LICENSE.txt).
ICONS8_URL = "https://icons8.com"
# The announcements are ElevenLabs free-plan voices: non-commercial use, with
# the credit "Voices: elevenlabs.io" (speech/LICENSE-AUDIO.md).
ELEVENLABS_URL = "https://elevenlabs.io"
# Every bundled library and its licence; the About dialog names the copyleft ones.
THIRD_PARTY_URL = f"{REPO_URL}/blob/main/THIRD_PARTY_LICENSES.md"
# The first line of LICENSE (tests.gui.test_about keeps the two in step).
LICENSE_NAME = "MIT License"
COPYRIGHT = "© 2026 marcelkb"
# The repo root from source; in a build, the bundle folder, where the spec
# puts the manual under the same docs/manual path.
ROOT = Path(__file__).resolve().parents[1]


def _link(url: str, text: str | None = None) -> str:
    text = text if text is not None else url.removeprefix("https://")
    return f"<a href='{html.escape(url)}'>{html.escape(text)}</a>"


def about_html(name: str, version: str) -> str:
    """The dialog's text. Its labels are catalog keys; rich text does not go
    through the text hook, so they are translated here."""
    rows = (
        (i18n.t("Version"), html.escape(version)),
        (i18n.t("Project"), _link(REPO_URL)),
        (i18n.t("Author"), f"{html.escape(AUTHOR)} · {_link(AUTHOR_URL)}"),
        (i18n.t("License"), html.escape(LICENSE_NAME)),
        (i18n.t("App icon"), f"Swing · Icons8 · {_link(ICONS8_URL)}"),
        (i18n.t("Icons"), "Bootstrap Icons (MIT) · Twemoji (CC-BY 4.0)"),
        (i18n.t("Voices"), f"{html.escape(i18n.t('AI-generated, non-commercial use'))}"
                           f" · {_link(ELEVENLABS_URL)}"),
        (i18n.t("Libraries"), "Qt / PySide6 (LGPL-3.0) · mutagen (GPL-2.0+) · "
                              f"FFmpeg (GPL-3.0) · {_link(THIRD_PARTY_URL, i18n.t('all licences'))}"),
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


def manual_pdf(lang: str | None = None) -> Path | None:
    """The manual as a PDF in the app's language, else the English one; None
    without either (a source checkout that never ran tools.build_manual_pdf)."""
    manual = ROOT / "docs" / "manual"
    lang = lang or i18n.active_language()
    return next((pdf for pdf in (manual / lang / "manual.pdf", manual / "manual.pdf")
                 if pdf.is_file()), None)


def open_manual(pdf: Path) -> bool:
    """❔ → 📖 Manual: the PDF in the system's viewer."""
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf)))
