"""🖨 The printed running order's HTML, compared whole with a golden file.

Run:  .venv/Scripts/python.exe -m pytest tests/gui/test_print_golden.py -n0
      (UPDATE_GOLDEN=1 in front rewrites tests/gui/golden/)
"""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from gui.decks.running_order import Row
from gui.print_sheet import deck_print_html
from tests.golden_support import assert_golden

GOLDEN = Path(__file__).parent / "golden"


def entry(title, bpm=None, duration=180, artist="", album=""):
    return SimpleNamespace(path=Path(f"C:/Musik/{title}.mp3"), title=title, bpm=bpm, duration=duration,
                           tag_artist=artist, tag_album=album)


class PrintGoldenTest(unittest.TestCase):
    def test_a_deck_with_heats_a_spare_and_an_unnamed_tail(self):
        rows = [
            Row(entry=entry("Moon River", 29, artist="Andy Williams", album="Moon <River>"), dance="LW",
                round_name="Vorrunde", h_idx=0, multi=True),
            Row(entry=entry("Por Una Cabeza", 32, artist="Carlos Gardel"), dance="TG",
                round_name="Vorrunde", h_idx=1, multi=True),
            Row(entry=entry("Fly Me & You", 50, duration=0), dance="QS", round_name="Finale"),
            Row(entry=entry("Spare", None), dance="QS", round_name="Finale", backup=True, backup_n=1),
            Row(entry=entry("Encore", 28), dance="", round_name=""),
        ]
        with mock.patch("gui.print_sheet.time.strftime", return_value="12.11.2026 20:00"):
            html = "\n".join(deck_print_html("Deck A & B", rows))
        assert_golden(self, GOLDEN / "deck_print.html", html.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
