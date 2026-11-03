"""🎯 The ✖ on the Paso Doble highlights asks before it forgets the marks.

Run:  py -m unittest tests.player.window.test_pd_clear_confirm -v
"""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PySide6.QtWidgets import QMessageBox

from player.window.main_pd import PdStopMixin

YES = QMessageBox.StandardButton.Yes
NO = QMessageBox.StandardButton.No


class ClearPdHighlightTest(unittest.TestCase):

    def host(self):
        cache = mock.Mock()
        return SimpleNamespace(
            _playback=SimpleNamespace(path=Path("a.mp3"), dance="PD"),
            _library=SimpleNamespace(cache=cache),
            _pd_highlights={"a.mp3": [1.0]}, _pd_stop_at=3.0,
            _refresh_pd_chips=mock.Mock(), statusBar=mock.Mock(),
            _pd_highlight=lambda: (None,), _ensure_pd_highlights=mock.Mock(),
            _sync_big_player_limit=mock.Mock()), cache

    def run_clear(self, host, answer):
        with mock.patch("player.window.main_pd.QMessageBox.question",
                        return_value=answer) as ask:
            PdStopMixin._clear_pd_highlight(host)
        return ask

    def test_no_keeps_the_marks(self):
        host, cache = self.host()
        ask = self.run_clear(host, NO)
        ask.assert_called_once()
        cache.clear_pd_highlights.assert_not_called()
        self.assertEqual(host._pd_highlights, {"a.mp3": [1.0]})

    def test_yes_clears_them(self):
        host, cache = self.host()
        self.run_clear(host, YES)
        cache.clear_pd_highlights.assert_called_once_with(Path("a.mp3"))
        self.assertEqual(host._pd_highlights, {})


if __name__ == "__main__":
    unittest.main()
