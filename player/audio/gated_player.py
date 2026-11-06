"""⏯ The deck's media player with a gate in front of play().

Every way of starting the music (a double click, ⏯, the next title, a resume
after a pause, a held start being released) ends in `play()`. The gate sits
there, so nothing can start the sound before the headset check has had its say
(player.window.main_audio). A held play is the gate's to repeat, via `play()`
again once the operator has answered.
"""
from collections.abc import Callable

from PySide6.QtMultimedia import QMediaPlayer


class GatedMediaPlayer(QMediaPlayer):
    def __init__(self, *args):
        super().__init__(*args)
        self.gate: Callable[[], bool] | None = None   # True: hold this play back

    def play(self):
        if self.gate is not None and self.gate():
            return
        super().play()
