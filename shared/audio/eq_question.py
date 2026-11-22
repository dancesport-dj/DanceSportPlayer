"""🎚 The question before the music's equalizer goes on.

With the music EQ on, the player is tapped: the app makes the tempo itself
(player.audio.stretch_engines) instead of Qt's own stretch; with "Qt
(standard)" chosen that is Signalsmith, the same stretch. The pitch stays
either way; what changes is the engine and a little more CPU. Asked from the
🎚 EQ card (player) and from ⚙ Settings (gui), hence here.

The operator can tick "Don't ask again"; that is kept under
planner.playing.equalizer.PITCH_OK_KEY, at the top of the settings (it is the
operator's, not the venue's: it stays out of the 🧳 pack). The caller saves.
"""
from PySide6.QtWidgets import QCheckBox, QMessageBox

from planner import i18n
from planner.playing.equalizer import PITCH_OK_KEY

_ENGINE_NAMES = {"rubberband": "Rubber Band", "signalsmith": "Signalsmith"}


def engine_name(settings: dict) -> str:
    """The tempo engine a tapped player uses, as the texts name it: Qt's own
    (the default) is Signalsmith there."""
    return _ENGINE_NAMES.get(settings.get("tapped_tempo_engine") or "", "Signalsmith")


class MusicEqQuestion(QMessageBox):
    """Yes turns the EQ on; No, Esc or closing the box leaves it off."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.t("Music equalizer"))
        self.setIcon(QMessageBox.Icon.Question)
        self.setText(i18n.t("Turn the music's equalizer on?"))
        self.setInformativeText(i18n.t(
            "With the EQ on, the app makes the music's tempo itself, with the "
            "stretch chosen under ⚙ Settings → ⏩ Tempo (now: %s). The pitch "
            "stays when the tempo fader moves, at a little more CPU; Rubber Band "
            "takes clearly more.\n\nIt starts at once, after a short gap.")
            % engine_name(settings))
        self.remember = QCheckBox(i18n.t("Don't ask again"))
        self.remember.setChecked(True)
        self.setCheckBox(self.remember)
        self.on_btn = self.addButton(i18n.t("Turn it on"), QMessageBox.ButtonRole.YesRole)
        self.off_btn = self.addButton(i18n.t("Leave it off"), QMessageBox.ButtonRole.NoRole)
        self.setDefaultButton(self.on_btn)
        self.setEscapeButton(self.off_btn)

    def ask(self) -> tuple[bool, bool]:
        """(turn it on, don't ask again)."""
        self.exec()
        on = self.clickedButton() is self.on_btn
        return on, on and self.remember.isChecked()


def confirm_music_eq(settings: dict, parent=None) -> bool:
    """Whether the music's EQ may go on: accepted before, or Yes now. A Yes
    with "Don't ask again" ticked sets PITCH_OK_KEY in `settings`."""
    if settings.get(PITCH_OK_KEY) is True:
        return True
    on, remember = MusicEqQuestion(settings, parent).ask()
    if remember:
        settings[PITCH_OK_KEY] = True
    return on
