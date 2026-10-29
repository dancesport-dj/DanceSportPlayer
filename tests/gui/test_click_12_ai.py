#!/usr/bin/env python3
"""Click-through, chapter 12: AI helpers.

Run:  py -m unittest tests.gui.test_click_12_ai -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/12-ai-helpers.md

No model is asked: `llm._ask`, the one call that reaches a backend, is a
stand-in that answers both turns of the real exchange. Everything around it,
the search, the catalog, the parsing and the deck, runs as it ships.
"""

import json
import re
import threading
import unittest
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from gui.dialogs.ai_dialogs import AiPlaylistDialog, AiTranscriptDialog
from planner.generate import llm

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, printable

_ROW_RE = re.compile(r"^\s*(\d+) \| ", re.MULTILINE)


class FakeModel:
    """Answers `llm._ask`: the search turn with no queries (the app then
    sweeps the pool itself), the choice turn with the rows `choose` takes out
    of the numbers it was shown."""

    def __init__(self, choose=None, *, hold=None):
        self.choose = choose or (lambda shown: shown)
        self.hold = hold            # a threading.Event the search turn waits on
        self.calls = []             # (system, user, model) per turn

    def __call__(self, system, user, *, model, config_dir, timeout,
                 on_step=None, cancel=None):
        self.calls.append((system, user, model))
        if len(self.calls) == 1:
            if self.hold is not None:
                while not self.hold.wait(0.01):
                    if cancel is not None and cancel.is_set():
                        raise llm.Cancelled()
            return '{"queries": []}', f"fake ({model})"
        shown = [int(n) for n in _ROW_RE.findall(user)]
        picks = [{"n": n, "why": f"reason {n}"} for n in self.choose(shown)]
        return (json.dumps({"playlist": picks, "notes": "fake notes"}),
                f"fake ({model})")


class AiClickTest(ClickThrough):
    """12 AI helpers."""

    def ask(self, op, fill):
        """🤖 AI Playlist… → `fill(dialog)` → 🤖 Build, then wait for the run."""
        def build(dlg):
            fill(dlg)
            self.click(self.button_text("🤖  Build", dlg))
        op.answer(lambda w: isinstance(w, AiPlaylistDialog), build)
        self.click(self.win._cfg.ai_playlist_btn)
        self.wait_for_run()

    def wait_for_run(self):
        worker = getattr(self.win, "_ai_worker", None)
        self.assertTrue(self.wait_until(
            lambda: worker is not None and worker.isFinished()
            and self.win._cfg.ai_playlist_btn.isEnabled(), 10000),
            "the AI run never finished")
        QTest.qWait(20)

    def button_text(self, text, root):
        found = [b for b in root.findChildren(QPushButton) if b.text() == text]
        self.assertTrue(found, f"no button '{printable(text)}'")
        return found[0]

    def flat(self, count, brief=""):
        def fill(dlg):
            dlg._rb_flat.setChecked(True)
            dlg._count_spin.setValue(count)
            dlg._brief.setPlainText(brief)
        return fill

    def test_a_competition_run_fills_the_heats_and_counts_the_slots(self):
        def all_but_one_dance(shown):
            pool = self.win._ai_ctx["candidates"]
            return [n for n in shown if pool[n - 1].dance != dropped]
        model = FakeModel(all_but_one_dance)        # one slot left open
        with self.clicking() as op, mock.patch.object(llm, "_ask", model):
            self.type_into(self.win._cfg.rounds_edit, "1")
            dropped = self.win._cfg.get_config()[3][-1]

            def fill(dlg):
                dlg._rb_comp.setChecked(True)
                dlg._model.setCurrentText("sonnet")
            self.ask(op, fill)
            dances = self.win._dances
            self.assertEqual(len(model.calls), 2, "a search turn and a choice turn")
            self.assertEqual({m for _s, _u, m in model.calls}, {"sonnet"})
            self.assertIn(f"{self.win._dance_class}-class", model.calls[0][1])
            filled = len(self.song_rows())
            self.assertEqual(filled, len(dances) - 1)
            self.assertNotIn(dropped, {self.entry_at(r).dance for r in self.song_rows()})
            hint = self.win._hints_lbl.text()
            self.assertIn(f"🤖 {filled}/{len(dances)} slots filled by fake (sonnet)",
                          hint)
            self.assertIn("fake notes", hint)

    def test_a_flat_list_lands_in_free_order_in_the_models_order(self):
        model = FakeModel(lambda shown: list(reversed(shown))[:5])
        with self.clicking() as op, mock.patch.object(llm, "_ask", model):
            self.generate(rounds="1")
            planned = set(self.titles())
            self.ask(op, self.flat(5, "club evening, keep it modern"))
            self.assertIn("club evening, keep it modern", model.calls[0][1])
            # The open deck's titles were marked as used in the catalog.
            rows = [line for line in model.calls[1][1].splitlines()
                    if _ROW_RE.match(line)]
            used = {line.rsplit(" | ", 1)[1] for line in rows if " | yes | " in line}
            self.assertEqual(used, planned)
            table = self.win._deckset.table
            self.assertEqual(self.win.deck(table).name, "🤖 AI playlist")
            self.assertTrue(table.plays_flat(), "not handed over in free order")
            shown = [int(n) for n in _ROW_RE.findall(model.calls[1][1])]
            pool = self.win._ai_ctx["candidates"]
            self.assertEqual(self.titles(),
                             [pool[n - 1].title for n in list(reversed(shown))[:5]])

    def test_an_empty_wish_list_asks_nothing_a_full_one_keeps_its_label(self):
        model = FakeModel(lambda shown: shown[:2])
        with self.clicking() as op, mock.patch.object(llm, "_ask", model):
            told = []
            with mock.patch.object(QMessageBox, "information",
                                   lambda _p, title, text, *_a, **_kw:
                                   told.append(text) or QMessageBox.StandardButton.Ok):
                def empty(dlg):
                    dlg._rb_wish.setChecked(True)
                    dlg._wishes.setPlainText("")
                op.answer(lambda w: isinstance(w, AiPlaylistDialog),
                          lambda dlg: (empty(dlg),
                                       self.click(self.button_text("🤖  Build", dlg))))
                self.click(self.win._cfg.ai_playlist_btn)
            self.assertEqual(len(told), 1)
            self.assertIn("wish list is empty", told[0])
            self.assertEqual(model.calls, [], "an empty wish list was sent")

            def wishes(dlg):
                dlg._rb_wish.setChecked(True)
                dlg._wishes.setPlainText("lw  White wings\nqs  youre so fine !!")
            self.ask(op, wishes)
            self.assertIn("youre so fine !!", model.calls[0][1])
            table = self.win._deckset.table
            self.assertEqual(self.win.deck(table).name, "📝 Wish list")
            self.assertTrue(table.plays_flat())
            self.assertEqual(len(self.song_rows()), 2)

    def test_stop_cancels_the_run_and_leaves_the_deck_alone(self):
        model = FakeModel(hold=threading.Event())
        with self.clicking() as op, mock.patch.object(llm, "_ask", model):
            self.generate(rounds="1")
            before = self.titles()
            op.answer(lambda w: isinstance(w, AiPlaylistDialog),
                      lambda dlg: (self.flat(5)(dlg),
                                   self.click(self.button_text("🤖  Build", dlg))))
            self.click(self.win._cfg.ai_playlist_btn)
            log = self.win._ai_log
            self.assertTrue(self.wait_until(lambda: model.calls, 5000))
            self.assertFalse(self.win._cfg.ai_playlist_btn.isEnabled(),
                             "a second run could start on top of this one")
            self.click(log._stop_btn)
            self.wait_for_run()
            self.assertEqual(len(model.calls), 1, "the choice turn was still asked")
            self.assertEqual(self.titles(), before)
            self.assertEqual(self.win.statusBar().currentMessage(),
                             "AI playlist stopped.")
            self.assertEqual(log._status.text(), "Stopped — nothing was changed.")
            log.close()

    def test_the_conversation_ends_with_why_copies_hides_and_comes_back(self):
        model = FakeModel(lambda shown: shown[:3])
        with self.clicking() as op, mock.patch.object(llm, "_ask", model):
            self.ask(op, self.flat(5))
            log = self.win._ai_log
            self.assertIsInstance(log, AiTranscriptDialog)
            self.assertIsNone(log.parent(), "an owned window has no taskbar button")
            role, title, text = log._steps[-1]
            self.assertEqual(title, "Why these tracks")
            self.assertIn("reason", text)
            self.assertIn("fake notes", text)

            self.click(self.button_text("📋  Copy", log))
            copied = QApplication.clipboard().text()
            self.assertEqual(copied, log.transcript())
            self.assertIn("Why these tracks", copied)

            self.click(self.button_text("Close", log))
            self.assertFalse(log.isVisible())
            self.assertTrue(self.win._cfg.ai_log_btn.isVisible())
            self.click(self.win._cfg.ai_log_btn)
            self.assertIs(self.win._ai_log, log)
            self.assertTrue(log.isVisible(), "💬 did not bring the conversation back")

            # Kept until the next run starts: that one has a window of its own.
            self.ask(op, self.flat(5))
            self.assertIsNot(self.win._ai_log, log)
            self.win._ai_log.close()

    def test_rules_model_and_brief_are_remembered_and_rules_reset(self):
        model = FakeModel(lambda shown: shown[:3])
        with self.clicking() as op, mock.patch.object(llm, "_ask", model):
            def fill(dlg):
                self.flat(7, "no covers")(dlg)
                dlg._rules.setPlainText("Only waltzes from the 90s.")
                dlg._model.setCurrentText("sonnet")
            self.ask(op, fill)
            self.assertIn("Only waltzes from the 90s.", model.calls[0][0])

            seen = {}

            def look(dlg):
                seen.update(flat=dlg._rb_flat.isChecked(),
                            count=dlg._count_spin.value(),
                            brief=dlg._brief.toPlainText(),
                            rules=dlg._rules.toPlainText(),
                            model=dlg._model.currentText())
                self.click(self.button_text("↺  Default rules", dlg))
                seen["reset"] = dlg._rules.toPlainText()
                dlg.reject()
            op.answer(lambda w: isinstance(w, AiPlaylistDialog), look)
            self.click(self.win._cfg.ai_playlist_btn)
            self.assertEqual(seen["count"], 7)
            self.assertEqual(seen["brief"], "no covers")
            self.assertEqual(seen["rules"], "Only waltzes from the 90s.")
            self.assertEqual(seen["model"], "sonnet")
            self.assertEqual(seen["reset"], llm.DEFAULT_RULES)
            self.assertEqual(len(model.calls), 2, "Cancel started a run")

    def test_the_answer_goes_to_the_deck_that_had_the_focus_at_build(self):
        go = threading.Event()
        model = FakeModel(lambda shown: shown[:4], hold=go)
        with self.clicking() as op, mock.patch.object(llm, "_ask", model):
            self.click(self.button("Cycle 1 "))
            deck_a, deck_b = self.win._visible_deck_tables()[:2]
            self.click_cell_free(deck_a)
            self.assertIs(self.win._deckset.table, deck_a)
            op.answer(lambda w: isinstance(w, AiPlaylistDialog),
                      lambda dlg: (self.flat(5)(dlg),
                                   self.click(self.button_text("🤖  Build", dlg))))
            self.click(self.win._cfg.ai_playlist_btn)
            self.assertTrue(self.wait_until(lambda: model.calls, 5000))
            self.click_cell_free(deck_b)            # the user looks elsewhere
            self.assertIs(self.win._deckset.table, deck_b)
            go.set()
            self.wait_for_run()
            self.assertEqual(len(self.song_rows(deck_a)), 4)
            self.assertEqual(self.song_rows(deck_b), [])
            self.assertIs(self.win._deckset.table, deck_a)
            self.win._ai_log.close()

    def click_cell_free(self, table):
        """A click into an empty deck: it takes the focus. A real click
        activates the main window first, the transcript window has it now."""
        self.win.activateWindow()
        self.wait_until(self.win.isActiveWindow, 1000)
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton)
        QTest.qWait(5)


if __name__ == "__main__":
    unittest.main()
