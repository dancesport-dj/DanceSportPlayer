#!/usr/bin/env python3
"""🏆 Event in the main window: start the plan, keep it, wait out a limit.

Run:  py -m unittest tests.gui.test_event_plan_glue -v

The window keeps the last plan and its candidates — the comparison window and
every later question start from them. A run the AI's limit held back offers to
wait and asks again by itself, about those competitions only.
"""

import os
import shutil
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_event_glue_"))

from PySide6.QtCore import QObject, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

from gui.main_generate import GenerateMixin  # noqa: E402
from planner import event_plan  # noqa: E402
from planner.competition import parse_competition_schedule  # noqa: E402


class FakeWindow(GenerateMixin, QObject):

    def __init__(self):
        QObject.__init__(self)
        self.shown = []
        self._ai_log = mock.Mock()
        self._lib = object()
        self.runs = []
        self.store = mock.Mock()

    def statusBar(self):
        return types.SimpleNamespace(showMessage=self.shown.append)

    def _event_run(self, worker, intro):
        self.runs.append((worker, intro))

    def _play_or_stop(self, path, start=True):
        pass

    def _seek(self, delta_ms):
        pass

    def _embedding_store(self):
        return self.store


def _cands(labels):
    return [types.SimpleNamespace(spec=types.SimpleNamespace(label=label))
            for label in labels]


class EventGlueTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = FakeWindow()
        self.addCleanup(self.win.deleteLater)
        self.cands = _cands(["HGR S STD", "SEN I S STD"])
        self.describe = mock.patch.object(event_plan, "describe_result",
                                          return_value="summary")
        self.describe.start()
        self.addCleanup(self.describe.stop)
        compare = mock.patch("gui.main_generate.EventCompareDialog")
        self.compare = compare.start()
        self.addCleanup(compare.stop)

    def done(self, result, answer=QMessageBox.StandardButton.Yes):
        with mock.patch("gui.main_generate.QMessageBox") as box:
            box.StandardButton = QMessageBox.StandardButton
            box.question.return_value = answer
            self.win._on_event_plan_done(result, self.cands)
        return box

    def test_the_plan_is_kept_and_summed_up(self):
        result = event_plan.RefineResult({"variety": []})
        box = self.done(result)
        self.assertIs(self.win._event_result, result)
        self.assertIs(self.win._event_cands, self.cands)
        self.win._ai_log.add_step.assert_called_once_with("note", "The plan", "summary")
        self.win._ai_log.finish.assert_called_once()
        box.question.assert_not_called()

    def test_the_plan_opens_side_by_side(self):
        result = event_plan.RefineResult({"variety": []})
        self.done(result)
        self.compare.assert_called_once_with(result, self.cands, self.win,
                                             play_cb=self.win._play_or_stop,
                                             seek_cb=self.win._seek)
        dlg = self.win._event_compare
        dlg.continueRequested.connect.assert_called_once_with(
            self.win._continue_event_plan)
        dlg.applyRequested.connect.assert_called_once_with(self.win._apply_event_plan)
        dlg.show.assert_called_once()

    def test_the_answer_to_asking_again_updates_the_window(self):
        self.done(event_plan.RefineResult({"variety": []}))
        again = event_plan.RefineResult({"variety": []})
        self.done(again)
        self.compare.assert_called_once()
        self.win._event_compare.set_result.assert_called_once_with(again, self.cands)

    def test_a_minimized_window_comes_back_with_the_answer(self):
        """Minimized while the second round ran, the window stayed down:
        show() and raise_() leave a minimized window minimized, and all
        Marcel saw at the end was the transcript. A maximized one stays so."""
        class Compare(QDialog):
            def set_result(self, result, cands):
                pass

        dlg = self.win._event_compare = Compare()
        self.addCleanup(dlg.deleteLater)
        dlg.show()
        dlg.setWindowState(Qt.WindowState.WindowMaximized
                           | Qt.WindowState.WindowMinimized)
        self.done(event_plan.RefineResult({"variety": []}))
        self.assertTrue(dlg.isVisible())
        self.assertFalse(dlg.isMinimized())
        self.assertTrue(dlg.isMaximized())

    def test_the_window_is_not_edited_while_the_ai_is_asked(self):
        self.win._event_compare = dlg = mock.Mock()
        worker = mock.Mock()
        with mock.patch("gui.main_generate.AiTranscriptDialog"):
            self.win._cfg = mock.Mock()
            GenerateMixin._event_run(self.win, worker, "intro")
        dlg.set_busy.assert_called_once_with(True)
        done = [c.args[0] for c in worker.finished.connect.call_args_list]
        for slot in done:
            slot()
        dlg.set_busy.assert_called_with(False)

    def test_a_limit_offers_to_wait_and_asks_again_by_itself(self):
        result = event_plan.RefineResult({"variety": []}, pending=[1],
                                         limit="usage limit reached",
                                         reset_at=time.time() + 600)
        box = self.done(result)
        self.assertIn("SEN I S STD", box.question.call_args.args[2])
        timer = self.win._event_retry
        self.assertTrue(timer.isActive())
        self.assertAlmostEqual(timer.interval() / 1000, 660, delta=5)
        asked = []
        self.win._continue_event_plan = asked.append
        timer.timeout.emit()
        self.assertEqual(asked, [[1]])

    def test_no_wait_no_timer(self):
        result = event_plan.RefineResult({"variety": []}, pending=[0])
        self.done(result, answer=QMessageBox.StandardButton.No)
        self.assertIsNone(getattr(self.win, "_event_retry", None))

    def test_asking_again_starts_from_the_kept_plan(self):
        self.win._event_result = event_plan.RefineResult({"variety": ["plan"]})
        self.win._event_cands = self.cands
        self.win._event_opts = dict(rules="r", model="m", config_dir="")
        self.win._continue_event_plan([1])
        worker, intro = self.win.runs[0]
        self.addCleanup(worker.deleteLater)
        self.assertEqual(worker._only, [1])
        self.assertIs(worker._variants, self.win._event_result.variants)
        self.assertIs(worker._cands_list, self.cands)
        self.assertIn("SEN I S STD", intro)

    def test_a_run_still_going_puts_the_question_off(self):
        self.win._event_worker = mock.Mock(isRunning=lambda: True)
        self.win._event_retry = timer = mock.Mock()
        self.win._continue_event_plan([1])
        self.assertEqual(self.win.runs, [])
        timer.start.assert_called_once_with(5 * 60 * 1000)


class ReopenPlanTest(unittest.TestCase):
    """The AI dialog brings the kept plan back after its window was closed."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = FakeWindow()
        self.addCleanup(self.win.deleteLater)
        self.win._lib = types.SimpleNamespace(entries=[object()])
        self.win._settings = {}
        self.win._show_event_compare = mock.Mock()
        self.win._plan_event = mock.Mock()
        for target in ("gui.main_generate.save_settings",):
            patcher = mock.patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_dialog(self, code):
        from gui.ai_dialogs import AiPlaylistDialog
        with mock.patch("gui.main_generate.AiPlaylistDialog") as cls:
            cls.REOPEN_PLAN = AiPlaylistDialog.REOPEN_PLAN
            dlg = cls.return_value
            dlg.exec.return_value = code
            dlg.values.return_value = dict(
                mode="event", rules="r", model="m", brief="", wishes="", count=60,
                config_dir="", event=dict(schedule="", series_name="", new_share=0.2,
                                          rare_share=0.15,
                                          variants=[], use_event=True,
                                          use_class=True, ai_check=True))
            self.win._generate_ai_playlist()
        return cls

    def test_the_dialog_knows_whether_a_plan_is_kept(self):
        cls = self.run_dialog(QDialog.DialogCode.Rejected)
        self.assertFalse(cls.call_args.kwargs["event_plan_kept"])
        self.win._event_result = event_plan.RefineResult({"variety": []})
        cls = self.run_dialog(QDialog.DialogCode.Rejected)
        self.assertTrue(cls.call_args.kwargs["event_plan_kept"])

    def test_reopen_shows_the_kept_plan_and_plans_nothing(self):
        from gui.ai_dialogs import AiPlaylistDialog
        self.win._event_result = event_plan.RefineResult({"variety": []})
        self.run_dialog(AiPlaylistDialog.REOPEN_PLAN)
        self.win._show_event_compare.assert_called_once_with()
        self.win._plan_event.assert_not_called()


class PlanEventTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = FakeWindow()
        self.addCleanup(self.win.deleteLater)
        self.root = Path(tempfile.mkdtemp(prefix="dp_event_glue_root_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        for name in ("DanceConvention 2025", "DanceConvention 2026"):
            (self.root / name).mkdir()
        orig = event_plan.PLAYLIST_DIR
        event_plan.PLAYLIST_DIR = self.root
        self.addCleanup(setattr, event_plan, "PLAYLIST_DIR", orig)

    def opts(self, **event):
        ev = dict(schedule="", specs=parse_competition_schedule("HGR S STD 2-1"),
                  series="danceconvention", series_name="DanceConvention",
                  year=2026, use_event=True, use_class=True, new_share=0.2,
                  rare_share=0.15,
                  variants=["variety"], ai_check=False)
        ev.update(event)
        return dict(mode="event", event=ev, rules="r", model="m", config_dir="")

    def plan(self, **event):
        with mock.patch("gui.main_generate.QMessageBox") as box:
            self.win._plan_event(self.opts(**event))
        for worker, _intro in self.win.runs:
            self.addCleanup(worker.deleteLater)
        return box

    def test_the_earlier_editions_are_the_history(self):
        self.plan()
        worker, intro = self.win.runs[0]
        self.assertEqual([d.name for d in worker._editions], ["DanceConvention 2025"])
        self.assertIn("DanceConvention 2025", intro)
        self.assertEqual(worker._profiles, ["variety"])
        self.assertEqual(worker._new_share, 0.2)
        self.assertEqual(worker._rare_share, 0.15)
        self.assertFalse(worker._ask_ai)

    def test_sound_alikes_hear_timbre_groove_and_melody(self):
        """Marcel: the chroma cover match counts too, from its built index."""
        from planner import embeddings as ae
        from planner.similarity import SoundAlike
        self.plan()
        sound = self.win.runs[0][0]._similar
        self.assertIsInstance(sound, SoundAlike)
        entry = types.SimpleNamespace(path=Path("a.mp3"))
        self.assertIs(sound._chroma(entry), self.win.store.recorded.return_value)
        self.win.store.recorded.assert_called_once_with(entry.path, ae.MODEL_CHROMA)

    def test_without_the_event_no_editions(self):
        self.plan(use_event=False)
        worker, _intro = self.win.runs[0]
        self.assertEqual(worker._editions, [])

    def test_nothing_read_from_the_schedule_plans_nothing(self):
        box = self.plan(specs=[])
        box.information.assert_called_once()
        self.assertEqual(self.win.runs, [])

    def test_no_variant_ticked_plans_nothing(self):
        box = self.plan(variants=[])
        box.information.assert_called_once()
        self.assertEqual(self.win.runs, [])


class ApplyEventTest(unittest.TestCase):
    """📅 A variant into the day decks, a deck per competition."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        w = self.win = FakeWindow()
        self.addCleanup(w.deleteLater)
        w._day_decks = [mock.Mock(name=f"day{k}") for k in range(8)]
        self.filled = set()
        w._serialize_playlist_state = lambda t: {} if t in self.filled else None
        self.loaded = []
        w._load_day_deck = lambda deck, parts, timbre: self.loaded.append(
            (deck, [p["label"] for p in parts]))
        for name in ("_blank_deck", "_stash_active_replay", "_clear_replay_sources",
                     "_set_day_tab_title", "_apply_deck_view", "_set_active_table",
                     "_autosave_playlist"):
            setattr(w, name, mock.Mock())
        w._cfg = mock.Mock()
        w._cfg.get_config.return_value = ("Standard", "HGR", "S", [], "", True)
        w._deck_tabs = mock.Mock()
        w._day_tabs = mock.Mock()
        w._event_opts = {"event": {"series_name": "DanceConvention", "year": 2026}}
        for target in ("gui.main_generate._show_toast",
                       "gui.main_generate.PlaylistSuggester"):
            patcher = mock.patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def day(self, n):
        comps = [types.SimpleNamespace(
            spec=types.SimpleNamespace(label=f"C{k}", dances=["LW"],
                                       dance_class="S", style="Standard"),
            rounds=[], playlist=dict) for k in range(n)]
        self.win._event_result = event_plan.RefineResult({"variety": comps})

    def apply(self, answer=QMessageBox.StandardButton.Yes):
        with mock.patch("gui.main_generate.QMessageBox") as box:
            box.StandardButton = QMessageBox.StandardButton
            box.question.return_value = answer
            self.win._apply_event_plan(["variety"] * len(
                self.win._event_result.variants["variety"]))
        return box

    def test_each_competition_comes_from_its_own_variant(self):
        """Marcel: choose the variant per tab, then copy everything in."""
        self.day(2)
        other = [types.SimpleNamespace(
            spec=types.SimpleNamespace(label=f"V{k}", dances=["LW"],
                                       dance_class="S", style="Standard"),
            rounds=[], playlist=dict) for k in range(2)]
        self.win._event_result.variants["like_last_year"] = other
        with mock.patch("gui.main_generate.QMessageBox"):
            self.win._apply_event_plan(["like_last_year", "variety"])
        decks = self.win._day_decks
        self.assertEqual(self.loaded, [(decks[0], ["V0"]), (decks[1], ["C1"])])

    def test_a_deck_per_competition(self):
        self.day(3)
        box = self.apply()
        box.question.assert_not_called()
        decks = self.win._day_decks
        self.assertEqual(self.loaded, [(decks[0], ["C0"]), (decks[1], ["C1"]),
                                       (decks[2], ["C2"])])
        self.win._set_day_tab_title.assert_called_once_with("DanceConvention 2026")
        self.win._deck_tabs.setCurrentIndex.assert_called_once_with(2)
        self.win._set_active_table.assert_called_with(decks[0])

    def test_more_than_eight_share_decks(self):
        self.day(10)
        self.apply()
        self.assertEqual(len(self.loaded), 8)
        self.assertEqual(self.loaded[0][1], ["C0", "C1"])
        self.assertEqual(self.loaded[2][1], ["C4"])

    def test_an_earlier_day_plan_is_replaced_only_on_yes(self):
        self.day(2)
        self.filled = {self.win._day_decks[5]}
        self.apply(answer=QMessageBox.StandardButton.No)
        self.assertEqual(self.loaded, [])
        self.apply()
        self.win._blank_deck.assert_called_once_with(self.win._day_decks[5])
        self.assertEqual(len(self.loaded), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
