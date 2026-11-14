"""📝 Export log — zips the app's log files into a file the user saves.

Opened from the ❔ button's menu. The logs sit next to the app
(planner.config.APP_DIR), where a user rarely finds them: session.log for the
running session, session.prev.log for the one before, crash.log for a hard
crash. They go into one zip whose name carries the export time, so a second
export keeps the first and there is one file to send.

A Save dialog, not a folder picker: the native macOS folder panel offers
"Open" and no Save.
"""
import time
import zipfile
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

import planner.config
from gui.dialogs import user_docs_dir
from planner import i18n

LOG_FILES = ("session.log", "session.prev.log", "crash.log")


def existing_logs(source: Path) -> list[Path]:
    """The non-empty logs in `source`, in LOG_FILES order."""
    return [f for f in (source / name for name in LOG_FILES)
            if f.is_file() and f.stat().st_size > 0]


def zip_logs(source: Path, target: Path) -> list[str]:
    """Write every non-empty log in `source` into the zip `target`, each under
    its own name; → those names. No log: no zip is written."""
    logs = existing_logs(source)
    if not logs:
        return []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for log_file in logs:
            z.write(log_file, log_file.name)
    return [f.name for f in logs]


def export_log(parent):
    """Ask where to save the zip, write the logs there and say what went in."""
    if not existing_logs(planner.config.APP_DIR):
        QMessageBox.information(parent, i18n.t("Export log"),
                                i18n.t("There is no log to export yet."))
        return
    proposed = Path(user_docs_dir()) / time.strftime("dancesport-log_%Y-%m-%d_%H%M%S.zip")
    chosen, _ = QFileDialog.getSaveFileName(
        parent, i18n.t("Export log"), str(proposed), i18n.t("Zip archive (*.zip)"))
    if not chosen:
        return
    target = Path(chosen)
    if target.suffix.lower() != ".zip":
        target = target.with_name(target.name + ".zip")
    try:
        written = zip_logs(planner.config.APP_DIR, target)
    except OSError as exc:
        QMessageBox.warning(parent, i18n.t("Export log"),
                            i18n.t("The log could not be exported:\n%s") % exc)
        return
    QMessageBox.information(
        parent, i18n.t("Export log"),
        i18n.t("Log exported to:\n%s") % target + "\n\n" + "\n".join(written))
