"""▶ Picking the evening up after a crash or a restart.

planner.playing.play_session keeps which titles the evening has played; this
mixin writes that list each time a title greys and offers it once at start.
Picked up, the titles already heard grey out again. The title that was on air
is the crash note's (TrackLoadMixin._offer_crash_resume): after a crash both
come in one question, after a restart this one asks on its own. Nothing
starts by itself: after a crash the hall may be in the middle of a speech,
and only the operator knows.

Split off player/window/main_player.py as a MainWindow mixin.
"""
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from planner import i18n
from planner.playing import play_session
from player.audio.on_air_note import OnAirNote

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.resume")

# ▶ The evening's list goes to disk off the GUI thread, like the crash note:
# a JsonStore write can wait out a virus scanner for up to ¾ s.
EVENING = OnAirNote(play_session.STORE)


class ResumeSessionMixin(MainWindowHost):
    """▶ The evening's played titles on disk, and the offer to grey them again."""

    def _note_session(self):
        """A title has just greyed: write down every title the evening has
        played so far, in the background."""
        played = sorted({p for t in self._deckset.all_tables for p in t._played_paths})
        EVENING.write(play_session.to_json(play_session.Session(datetime.now(), played)))

    def _evening_to_offer(self) -> play_session.Session | None:
        """The evening a crash or a restart broke off, if it is still this one."""
        return play_session.load(datetime.now())

    def _offer_evening(self, session: play_session.Session):
        """No title was on air: ask on its own whether to grey the evening's
        titles again. The question does not block the window."""
        mins = int((datetime.now() - session.saved_at).total_seconds() // 60)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("▶ Pick up the evening?")
        box.setText(i18n.t("The evening stopped %d min ago, with %d titles played.") % (
            mins, len(session.played))
            + "\n\n" + i18n.t("Grey them out again? Nothing starts by itself."))
        pick = box.addButton("▶  Pick up", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Start fresh", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(pick)
        box.finished.connect(
            lambda _r: self._evening_answered(session, box.clickedButton() is pick))
        box.open()   # the window holds it

    def _evening_answered(self, session: play_session.Session, pick: bool):
        if not pick:
            play_session.clear()
            log.info("▶ Evening not picked up\n"
                     "played list cleared")
            return
        if not self._is_playing_mode():
            self._set_play_mode(True)
        for t in self._deckset.all_tables:
            t.restore_played_paths(session.played)
        self.statusBar().showMessage(
            i18n.t("▶ Evening picked up — %d titles played.") % len(session.played), 8000)
        log.info("▶ Evening picked up\n"
                 "played: %d", len(session.played))
