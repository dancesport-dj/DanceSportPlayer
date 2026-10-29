"""📝 Export log — copies the app's log files into a folder the user picks.

Opened from the ❔ button's menu. The logs sit next to the app
(planner.config.APP_DIR), where a user rarely finds them: session.log for the
running session, session.prev.log for the one before, crash.log for a hard
crash. Each copy carries the export time in its name, so a second export into
the same folder keeps the first.
"""
import shutil
import time
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

import planner.config
from gui.dialogs import user_docs_dir
from planner import i18n

LOG_FILES = ("session.log", "session.prev.log", "crash.log")


def export_logs(source: Path, target: Path, stamp: str) -> list[Path]:
    """Copy every non-empty log in `source` into `target` as `<stem>_<stamp>.log`;
    → the copies written."""
    written = []
    for name in LOG_FILES:
        log_file = source / name
        if not log_file.is_file() or log_file.stat().st_size == 0:
            continue
        copy = target / f"{log_file.stem}_{stamp}{log_file.suffix}"
        shutil.copy2(log_file, copy)
        written.append(copy)
    return written


def export_log(parent):
    """Ask for a folder, copy the logs there and say what was written."""
    folder = QFileDialog.getExistingDirectory(
        parent, i18n.t("Export log — pick a folder"), str(user_docs_dir()))
    if not folder:
        return
    try:
        written = export_logs(planner.config.APP_DIR, Path(folder),
                              time.strftime("%Y-%m-%d_%H%M%S"))
    except OSError as exc:
        QMessageBox.warning(parent, i18n.t("Export log"),
                            i18n.t("The log could not be exported:\n%s") % exc)
        return
    if not written:
        QMessageBox.information(parent, i18n.t("Export log"),
                                i18n.t("There is no log to export yet."))
        return
    QMessageBox.information(
        parent, i18n.t("Export log"),
        i18n.t("Log exported to:\n%s") % folder + "\n\n"
        + "\n".join(p.name for p in written))
