#!/usr/bin/env python3
"""The CLI's "Replace a song?" puts a different title in the slot whenever the
library has one.

Run:  py -m unittest tests.planner.test_cli_reroll -v

The same trap as the deck's ↺ (tests/gui/test_reroll_new_title.py): the slot's
own song was dropped from the exclude set so it stayed a fallback, which made
it a full candidate of the draw — a replace could hand back the very title it
was asked to replace. It is now only offered when nothing else is free.
"""

import unittest
from pathlib import Path
from unittest import mock

from planner import cli
from planner.models import MusicEntry, RoundConfig


def _entry(name: str) -> MusicEntry:
    return MusicEntry(path=Path(f"/music/{name}.mp3"), title=name, dance="CC",
                      bpm=None, popularity=3)


class _FirstFree:
    """A suggester whose draw is the library in order, minus the excluded."""

    def __init__(self, library):
        self.library = library

    def regenerate(self, dance, dance_class, tier, exclude, **_kw):
        return next((e for e in self.library if str(e.path) not in exclude),
                    None)


class CliReplaceTest(unittest.TestCase):

    def replace(self, heat_song, library):
        playlist = {"Finale": [[heat_song]]}
        answers = iter(["y", "1", "1", "n"])   # replace: round 1, dance 1; done
        with (mock.patch("builtins.input", lambda _prompt="": next(answers)),
              mock.patch.object(cli, "display_playlist"),
              mock.patch("builtins.print")):
            cli.interactive_refine(
                playlist, ["CC"], "S",
                [RoundConfig(name="Finale", heats=1, tier="final")],
                _FirstFree(library))
        return playlist["Finale"][0][0]

    def test_the_slot_gets_another_title(self):
        current, other = _entry("Cha 1"), _entry("Cha 2")
        self.assertIs(self.replace(current, [current, other]), other)

    def test_the_slot_keeps_its_title_when_there_is_no_other(self):
        current = _entry("Cha 1")
        self.assertIs(self.replace(current, [current]), current)


if __name__ == "__main__":
    unittest.main(verbosity=2)
