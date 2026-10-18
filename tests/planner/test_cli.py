#!/usr/bin/env python3
"""The interactive planner CLI: prompts, the playlist printout and main().

Run:  py -m unittest tests.planner.test_cli -v

`planner.cli` asks for style, class, dances and the heats per round, prints the
suggested playlist, lets the operator re-roll single slots and saves an M3U per
iteration. Input is fed from a scripted answer list and the printout is
captured; the library, suggester and exporter of main() are mocks.
"""
import contextlib
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from planner import cli
from planner.models import MusicEntry, RoundConfig


def _entry(name, dance="CC", bpm=None, popularity=0, source_info="", classes_ok=None):
    return MusicEntry(path=Path(f"/music/{name}.mp3"), title=name, dance=dance, bpm=bpm,
                      popularity=popularity, source_info=source_info,
                      classes_ok=classes_ok or [])


class _CliTest(unittest.TestCase):

    def run_cli(self, answers, fn, *args, **kw):
        """Call `fn` with `answers` as the typed input; return (result, printout)."""
        feed = iter(answers)
        out = io.StringIO()
        with (mock.patch("builtins.input", lambda _prompt="": next(feed)),
              contextlib.redirect_stdout(out)):
            result = fn(*args, **kw)
        self.assertEqual(list(feed), [], "not every scripted answer was asked for")
        return result, out.getvalue()


class HelpersTest(_CliTest):

    def test_headers_and_separators(self):
        _, text = self.run_cli([], cli.hdr, "Title")
        self.assertEqual(text, f"\n{cli.DLINE}\n  Title\n{cli.DLINE}\n")
        _, text = self.run_cli([], cli.sep)
        self.assertEqual(text, cli.LINE + "\n")
        _, text = self.run_cli([], cli.sep, "Label")
        self.assertEqual(text, "── Label " + "─" * 55 + "\n")

    def test_a_choice_by_default_text_or_number(self):
        options = ["Standard", "Latin", "Others"]
        choice, text = self.run_cli([""], cli.ask_choice, "Style:", options, default="Latin")
        self.assertEqual(choice, "Latin")
        self.assertIn("2. Latin  ← default", text)
        self.assertEqual(self.run_cli(["others"], cli.ask_choice, "S:", options)[0], "Others")
        self.assertEqual(self.run_cli(["1"], cli.ask_choice, "S:", options)[0], "Standard")

    def test_a_wrong_choice_is_asked_again(self):
        choice, text = self.run_cli(["", "7", "Tango", "3"], cli.ask_choice, "S:",
                                    ["Standard", "Latin", "Others"])
        self.assertEqual(choice, "Others")
        self.assertEqual(text.count("Please enter 1–3 or the option text."), 3)

    def test_the_dances_stay_unless_modified(self):
        dances, text = self.run_cli(["n"], cli.ask_dances, "Latin", ["SA", "CC"])
        self.assertEqual(dances, ["SA", "CC"])
        self.assertIn("Dance selection: Samba, Cha-Cha", text)

    def test_modified_dances_are_picked_by_number(self):
        dances, text = self.run_cli(["y", "9", "x", "", "1, 3"], cli.ask_dances,
                                    "Latin", ["SA"])
        self.assertEqual(dances, ["SA", "RB"])
        self.assertEqual(text.count("Invalid, try again."), 3)
        self.assertIn("5. Jive", text)


class RoundsTest(_CliTest):

    def test_heats_name_the_rounds_and_set_their_strategy(self):
        rounds, text = self.run_cli(["abc", "0-2", "6-3-2-1", "", "5", "", "9"],
                                    cli.ask_rounds_with_heats)
        self.assertEqual(text.count("Please enter positive integers"), 2)
        self.assertEqual([(rc.name, rc.heats, rc.tier, rc.prefer_fresh, rc.strategy)
                          for rc in rounds],
                         [("Vorrunde", 6, "early", False, "proven"),
                          ("1. Zwischenrunde", 3, "pre_semi", True, "all"),
                          ("Semifinale", 2, "semi", False, "proven"),
                          ("Finale", 1, "final", False, "top_proven")])
        self.assertIn("Fresh", text)

    def test_more_rounds_than_named_ones_are_numbered(self):
        counts = "-".join(["1"] * 8)
        rounds, _ = self.run_cli([counts] + [""] * 8, cli.ask_rounds_with_heats)
        self.assertEqual([rc.name for rc in rounds], [f"Runde {i}" for i in range(1, 9)])


class DisplayTest(_CliTest):

    def test_a_playlist_printout(self):
        sim = mock.Mock(**{"similarity.return_value": 0.8})
        playlist = {
            "Vorrunde": [[_entry("Cha 1", bpm=20, popularity=4, source_info="Cup 2024")],
                         [None]],
            "Finale": [[_entry("Cha 2", classes_ok=["S", "A"], source_info="Cup 2025")]],
            "Extra": [[_entry("Cha 3")]],
        }
        rounds = [RoundConfig(name="Vorrunde", heats=2, tier="early"),
                  RoundConfig(name="Finale", heats=1, tier="final")]
        _, text = self.run_cli([], cli.display_playlist, playlist, ["CC"], rounds, "S", sim)
        self.assertIn("VORRUNDE  (2 heat(s), 1 songs)  [→ proven songs]", text)
        self.assertIn("    Heat 1:  Cha 1 [T20*] ★4 ≈", text)
        self.assertNotIn("Cup 2024", text)   # sources only show in semi and final
        self.assertIn("    Heat 2:  ⚠  No suitable song found!", text)
        self.assertIn("FINALE  (1 heat(s), 1 songs)  [→ top proven songs]", text)
        self.assertIn("    Cha 2 [?BPM]  ✦new ≈ [S,A]  ← Cup 2025", text)
        self.assertIn("EXTRA  (1 heat(s), 1 songs)\n", text)

    def test_without_a_suggester_nothing_is_marked_similar(self):
        _, text = self.run_cli([], cli.display_playlist, {"Finale": [[_entry("Cha 1")]]},
                               ["CC"], [])
        self.assertNotIn("≈", text)


class RefineTest(_CliTest):

    def setUp(self):
        patcher = mock.patch.object(cli, "display_playlist")
        self.display = patcher.start()
        self.addCleanup(patcher.stop)

    def test_wrong_round_heat_or_dance_numbers_start_over(self):
        playlist = {"Vorrunde": [[_entry("Cha 1")], [_entry("Cha 2")]]}
        rounds = [RoundConfig(name="Vorrunde", heats=2, tier="early")]
        suggester = mock.Mock(**{"regenerate.return_value": None})
        answers = ["y", "x", "y", "5", "y", "1", "3", "y", "1", "x",
                   "y", "1", "2", "4", "n"]
        _, text = self.run_cli(answers, cli.interactive_refine, playlist, ["CC"], "S",
                               rounds, suggester)
        self.assertEqual(text.count("  Invalid."), 5)
        suggester.regenerate.assert_not_called()

    def test_no_alternative_leaves_the_slot(self):
        current = _entry("Cha 1")
        playlist = {"Finale": [[current]]}
        suggester = mock.Mock(**{"regenerate.return_value": None})
        result, text = self.run_cli(["y", "1", "1", "n"], cli.interactive_refine, playlist,
                                    ["CC"], "S", [], suggester)
        self.assertIs(result["Finale"][0][0], current)
        self.assertIn("No alternative found.", text)
        self.assertEqual(suggester.regenerate.call_count, 2)
        self.assertEqual(suggester.regenerate.call_args.args[2], "early")
        self.display.assert_called_once()

    def test_an_empty_slot_is_filled(self):
        playlist = {"Finale": [[None]]}
        new = _entry("Cha 9", bpm=31)
        suggester = mock.Mock(**{"regenerate.return_value": new})
        _, text = self.run_cli(["y", "1", "1", "n"], cli.interactive_refine, playlist,
                               ["CC"], "S", [RoundConfig(name="Finale", heats=1,
                                                         tier="final")], suggester)
        self.assertIs(playlist["Finale"][0][0], new)
        self.assertIn("1. Cha-Cha: (none)", text)
        self.assertIn("Replaced with: Cha 9 [T31]", text)


class MainTest(_CliTest):

    def setUp(self):
        self.lib = mock.Mock()
        self.lib.entries = [SimpleNamespace(features=[1.0]), SimpleNamespace(features=None)]
        self.lib.summary.return_value = {"SA": 12, "CC": 0, "?": 5}
        self.lib.other_genre_summary.return_value = {"Disco": 3}
        self.suggester = mock.Mock()
        self.suggester.suggest.side_effect = (
            lambda dance_class, rounds, dances, style: {"Finale": [[None] * len(dances)]})
        for name, value in (("AudioCache", mock.Mock()),
                            ("MusicLibrary", mock.Mock(return_value=self.lib)),
                            ("PlaylistSuggester", mock.Mock(return_value=self.suggester)),
                            ("note_class_tag_use", mock.Mock())):
            patcher = mock.patch.object(cli, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(cli, "export_m3u", return_value=Path("/out/x.m3u"))
        self.export = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(cli.logging, "basicConfig")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_iterations_save_and_a_new_config_until_quit(self):
        config = ["", "", "", "n", "1", ""]   # Latin, Hauptgruppe, S, dances kept, 1 heat
        answers = (config + ["n", "", ""]         # no refine, save, next iteration
                   + ["n", "y", "c"]              # no refine, save as _v2, new config
                   + config + ["n", "n", "n"])    # no refine, no save, quit
        _, text = self.run_cli(answers, cli.main)
        self.lib.scan.assert_called_once()
        self.assertRegex(text, r"Samba +12  ██\n")
        self.assertNotRegex(text, r"Cha-Cha +0")   # a dance without songs is not listed
        self.assertIn("Other genres (not used for playlists):", text)
        self.assertIn("No dance detected           2", text)
        self.assertIn("Audio features available: 1/2 files", text)
        self.assertIn("(iteration 2)", text)
        self.assertIn("Suggested Playlist  ·  Hauptgruppe S Latin  #2", text)
        self.assertEqual([c.args[2] for c in self.export.call_args_list],
                         ["Hauptgruppe_S_Latin", "Hauptgruppe_S_Latin_v2"])
        self.assertIn("Saved: ", text)
        self.assertIn("Good luck with your tournament!", text)

    def test_a_library_without_extras_skips_their_lines(self):
        self.lib.entries = []
        self.lib.summary.return_value = {}
        self.lib.other_genre_summary.return_value = {}
        _, text = self.run_cli(["", "", "", "n", "1", "", "n", "n", "n"], cli.main)
        self.assertNotIn("Other genres", text)
        self.assertNotIn("No dance detected", text)
        self.assertNotIn("Audio features available", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
