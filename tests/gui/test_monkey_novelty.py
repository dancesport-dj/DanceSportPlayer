"""tests/gui/monkey_novelty.py: the keys, the weights, and the visits file."""
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.gui.monkey_novelty import VISITS_ENV, Novelty, report, target_key


class Window:
    def __init__(self, title):
        self.title = title

    def windowTitle(self):  # noqa: N802 - Qt's name
        return self.title


class Button:
    def __init__(self, win, text="", name=""):
        self.win, self.label, self.name = win, text, name

    def window(self):
        return self.win

    def objectName(self):  # noqa: N802 - Qt's name
        return self.name

    def text(self):
        return self.label


class Shortcut:
    """A QShortcut: no window() of its own, only the widget it hangs on."""

    def __init__(self, parent):
        self.host = parent

    def parent(self):
        return self.host

    def objectName(self):  # noqa: N802 - Qt's name
        return ""


class TargetKeyTest(unittest.TestCase):
    def test_the_window_widget_and_kind_make_the_key(self):
        win = Window("Settings")
        self.assertEqual(target_key("click", Button(win, text="  Apply\n now ")),
                         "Window:Settings | Button:Apply now | click")

    def test_the_object_name_wins_over_the_label(self):
        key = target_key("click", Button(Window("x"), text="OK", name="okButton"))
        self.assertIn("Button:okButton", key)

    def test_two_buttons_of_one_dialog_get_two_keys(self):
        win = Window("Export")
        self.assertNotEqual(target_key("click", Button(win, "OK")), target_key("click", Button(win, "Cancel")))

    def test_a_shortcut_is_keyed_by_its_parents_window(self):
        key = target_key("shortcut", Shortcut(Button(Window("Main"))))
        self.assertTrue(key.startswith("Window:Main | Shortcut:"))

    def test_a_shortcut_without_a_parent_has_no_window(self):
        self.assertTrue(target_key("shortcut", Shortcut(None)).startswith("? | "))


class NoveltyTest(unittest.TestCase):
    def test_a_control_never_worked_weighs_most(self):
        n = Novelty()
        n.mark("a")
        n.mark("a")
        n.mark("b")
        self.assertEqual(n.weights(["a", "b", "c"]), [1 / 3, 1 / 2, 1.0])

    def test_the_least_worked_control_gets_picked_far_more_often(self):
        n = Novelty()
        for _ in range(9):
            n.mark("busy")
        rng = random.Random(1)
        picks = [rng.choices(["busy", "new"], weights=n.weights(["busy", "new"]))[0] for _ in range(1000)]
        self.assertGreater(picks.count("new"), 800)
        self.assertGreater(picks.count("busy"), 0)   # still possible, just rare

    def test_never_hit_lists_what_was_offered_and_not_worked_most_offered_first(self):
        n = Novelty()
        n.weights(["a", "b", "c"])
        n.weights(["b", "c"])
        n.weights(["c"])
        n.mark("a")
        self.assertEqual(n.never_hit(), ["c", "b"])

    def test_without_a_file_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ):
            os.environ.pop(VISITS_ENV, None)
            n = Novelty.from_env()
            n.mark("a")
            n.save()
            self.assertIsNone(n.path)
            self.assertEqual(os.listdir(tmp), [])

    def test_the_counts_come_back_from_the_visits_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deep" / "visits.json"
            with mock.patch.dict(os.environ, {VISITS_ENV: str(path)}):
                n = Novelty.from_env()
                n.weights(["Fenster:Größe | Button:Ä | click", "b"])
                n.mark("b")
                n.save()
                again = Novelty.from_env()
            self.assertEqual(again.worked, n.worked)
            self.assertEqual(again.offered, n.offered)
            self.assertEqual(again.never_hit(), ["Fenster:Größe | Button:Ä | click"])
            self.assertEqual(os.listdir(path.parent), ["visits.json"])   # no .tmp left

    def test_the_report_counts_and_lists_the_never_hit(self):
        n = Novelty()
        n.weights(["a", "b"])
        n.mark("a")
        out = report(n)
        self.assertTrue(out.startswith("1 controls worked, 1 offered and never worked"))
        self.assertIn("1x offered  b", out)


if __name__ == "__main__":
    unittest.main()
