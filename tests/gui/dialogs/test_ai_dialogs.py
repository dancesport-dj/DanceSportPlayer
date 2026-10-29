#!/usr/bin/env python3
"""Tests for the 🤖 AI dialogs (gui.dialogs.ai_dialogs): the rules dialog, the
event dialog, the Claude login, the transcript window and its thinking bubble.

Run:  py -m unittest tests.gui.dialogs.test_ai_dialogs -v

The pure halves (planner.generate.llm: the prompt, the reply parsing, the
catalog) are in tests.planner.test_ai_playlist. No network and no claude CLI.
"""

import datetime
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ai_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from gui.dialogs.ai_dialogs import (
    AiPlaylistDialog,
    AiSuggestDialog,
    AiTranscriptDialog,
    Bubble,
    ThinkingBubble,
)
from planner import config as planner_config
from planner import i18n
from planner.event import event_plan
from planner.generate import llm
from tests.qt_test_support import reap_widget


class DialogTest(unittest.TestCase):
    """The rules are the user's — they come back exactly as typed, and the
    default set is one click away again."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings=None):
        dlg = AiPlaylistDialog(settings if settings is not None else {})
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_defaults(self):
        vals = self._dlg().values()
        self.assertEqual(vals["mode"], "competition")
        self.assertEqual(vals["rules"], llm.DEFAULT_RULES.strip())
        self.assertEqual(vals["model"], llm.CLAUDE_MODEL)

    def test_the_default_model_is_the_latest_opus(self):
        # Marcel: "use latest opus model not a specific one" — the CLI's alias
        # follows each new Opus without a code change.
        self.assertEqual(llm.CLAUDE_MODEL, "opus")

    def test_the_model_is_picked_from_opus_and_sonnet_or_typed(self):
        # Marcel: "show a combobox and make it editable, so the user can choose
        # between sonnet and opus".
        dlg = self._dlg()
        box = dlg._model
        self.assertTrue(box.isEditable())
        self.assertEqual([box.itemText(i) for i in range(box.count())],
                         ["opus", "sonnet"])
        box.setCurrentIndex(1)
        self.assertEqual(dlg.values()["model"], "sonnet")
        box.setEditText("claude-opus-5")
        self.assertEqual(dlg.values()["model"], "claude-opus-5")

    def test_saved_rules_come_back(self):
        dlg = self._dlg({"ai_rules": "Only Tango.", "ai_model": "claude-sonnet-5",
                         "ai_flat_count": 25})
        vals = dlg.values()
        self.assertEqual(vals["rules"], "Only Tango.")
        self.assertEqual(vals["model"], "claude-sonnet-5")
        self.assertEqual(vals["count"], 25)

    def test_reset_button_restores_the_default_rules(self):
        dlg = self._dlg({"ai_rules": "Only Tango."})
        self.assertEqual(dlg.values()["rules"], "Only Tango.")
        reset = next(b for b in dlg.findChildren(QPushButton)
                     if b.text().startswith("↺"))
        reset.click()
        self.assertEqual(dlg.values()["rules"], llm.DEFAULT_RULES.strip())

    def test_an_untouched_rule_set_is_not_frozen_into_the_settings(self):
        """Saving the shipped words would shadow every later change to them —
        which is exactly how the rules came to say nothing about the round
        columns. Empty means "whatever the app ships"."""
        self.assertEqual(
            llm.rules_to_remember(self._dlg().values()["rules"]), "")

    def test_what_the_user_typed_is_remembered_word_for_word(self):
        self.assertEqual(llm.rules_to_remember("Only Tango."), "Only Tango.")

    def test_flat_mode_reports_its_count(self):
        dlg = self._dlg()
        dlg._rb_flat.setChecked(True)
        dlg._count_spin.setValue(40)
        vals = dlg.values()
        self.assertEqual(vals["mode"], "flat")
        self.assertEqual(vals["count"], 40)

    def test_the_chosen_login_comes_back(self):
        dlg = self._dlg({"ai_claude_config_dir": r"C:\Users\x\.claude-profil1"})
        self.assertEqual(dlg.values()["config_dir"],
                         r"C:\Users\x\.claude-profil1")

    def test_no_login_set_means_the_cli_decides(self):
        old = os.environ.pop("CLAUDE_CONFIG_DIR", None)
        try:
            self.assertEqual(self._dlg().values()["config_dir"], "")
        finally:
            if old is not None:
                os.environ["CLAUDE_CONFIG_DIR"] = old

    def test_wish_mode_hands_over_the_pasted_titles(self):
        dlg = self._dlg()
        dlg._rb_wish.setChecked(True)
        dlg._wishes.setPlainText("White wings lw\nmelancolia lw!!\n")
        vals = dlg.values()
        self.assertEqual(vals["mode"], "wishes")
        self.assertEqual(vals["wishes"], "White wings lw\nmelancolia lw!!")

    def test_the_wish_list_comes_back_next_time(self):
        dlg = self._dlg({"ai_wishes": "hey ya qs"})
        self.assertEqual(dlg._wishes.toPlainText(), "hey ya qs")

    def test_the_wish_box_is_only_on_screen_in_wish_mode(self):
        dlg = self._dlg()
        self.assertFalse(dlg._wishes.isVisibleTo(dlg))
        dlg._rb_wish.setChecked(True)
        self.assertTrue(dlg._wishes.isVisibleTo(dlg))
        self.assertFalse(dlg._count_spin.isEnabled())
        dlg._rb_flat.setChecked(True)
        self.assertFalse(dlg._wishes.isVisibleTo(dlg))

    def test_the_brief_takes_more_than_one_line(self):
        """It is the free prompt now — a paragraph has to survive it."""
        dlg = self._dlg()
        dlg._brief.setPlainText("club evening\nkeep it modern")
        self.assertEqual(dlg.values()["brief"], "club evening\nkeep it modern")

    def test_the_track_count_only_applies_to_a_flat_list(self):
        dlg = self._dlg()
        self.assertFalse(dlg._count_spin.isEnabled())
        dlg._rb_flat.setChecked(True)
        self.assertTrue(dlg._count_spin.isEnabled())


class SuggestPreviewTest(unittest.TestCase):
    """🤖 AI suggestions' ▶ plays on the desk; leaving the window stops it."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_close_and_esc_stop_the_preview(self):
        # BUG_REVIEW B4.2: "Close" accepts and Esc rejects, and neither sends
        # the closeEvent that stopped it.
        for close in ("accept", "reject"):
            with self.subTest(close=close):
                calls = []
                dlg = AiSuggestDialog(None, play_cb=calls.append)
                self.addCleanup(reap_widget, dlg)
                dlg._row_paths[:] = [Path("a.mp3")]
                dlg._toggle_play(0)
                getattr(dlg, close)()
                self.assertEqual(calls, [Path("a.mp3"), None])

    def test_new_suggestions_stop_the_preview_and_their_play_plays(self):
        # BUG_REVIEW B4.7: the old playing row stayed current, so the new
        # list's ▶ in that row stopped instead of playing.
        from types import SimpleNamespace

        calls = []
        dlg = AiSuggestDialog(None, play_cb=calls.append)
        self.addCleanup(reap_widget, dlg)
        a = SimpleNamespace(path=Path("a.mp3"), title="A")
        b = SimpleNamespace(path=Path("b.mp3"), title="B")
        dlg._populate([{"suggestion": {"artist": "x", "title": "A"}, "entry": a}])
        dlg._toggle_play(0)
        dlg._populate([{"suggestion": {"artist": "y", "title": "B"}, "entry": b}])
        self.assertEqual(calls, [Path("a.mp3"), None])
        dlg._toggle_play(0)
        self.assertEqual(calls, [Path("a.mp3"), None, Path("b.mp3")])


class EventDialogTest(unittest.TestCase):
    """🏆 Event: a pasted schedule becomes the day's competitions, read back
    from the table the user may correct; the rest says where the titles come
    from and which variants to plan."""

    SCHEDULE = ("Sa: 10:00 HGR S STD 2-1\n"
                "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6\n")

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_event_dlg_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        for name in ("DanceConvention 2024", "DanceConvention 2025", "WiDaFe 2014"):
            (self.root / name).mkdir()
        self.addCleanup(planner_config.set_playlist_dir, planner_config.playlist_dir())
        planner_config.set_playlist_dir(self.root)

    def _dlg(self, settings=None):
        dlg = AiPlaylistDialog(settings if settings is not None else {})
        self.addCleanup(reap_widget, dlg)
        dlg._rb_event.setChecked(True)
        return dlg

    def test_the_schedule_becomes_the_competitions(self):
        dlg = self._dlg()
        dlg._event._schedule.setPlainText(self.SCHEDULE)
        vals = dlg.values()
        self.assertEqual(vals["mode"], "event")
        specs = vals["event"]["specs"]
        self.assertEqual([s.label for s in specs], ["HGR S STD", "J & J"])
        self.assertEqual(specs[1].dances, ["LW", "TG", "CC", "RB"])
        self.assertEqual(specs[1].heats, [2, 1, 1])
        self.assertEqual(dlg._event._table.rowCount(), 2)
        self.assertEqual(dlg._event._table.item(0, 3).text(), "2-1")

    def test_a_corrected_row_is_what_gets_planned(self):
        dlg = self._dlg()
        dlg._event._schedule.setPlainText(self.SCHEDULE)
        table = dlg._event._table
        table.item(0, 1).setText("a")
        table.item(0, 2).setText("LW TG QS")
        table.item(0, 3).setText("3 - 2 - 1")
        spec = dlg.values()["event"]["specs"][0]
        self.assertEqual(spec.dance_class, "A")
        self.assertEqual(spec.dances, ["LW", "TG", "QS"])
        self.assertEqual(spec.heats, [3, 2, 1])

    def test_a_cell_that_makes_no_sense_keeps_what_was_read(self):
        dlg = self._dlg()
        dlg._event._schedule.setPlainText(self.SCHEDULE)
        table = dlg._event._table
        table.item(0, 1).setText("X")
        table.item(0, 2).setText("waltz")
        table.item(0, 3).setText("")
        spec = dlg.values()["event"]["specs"][0]
        self.assertEqual((spec.dance_class, spec.heats), ("S", [2, 1]))
        self.assertEqual(spec.dances, ["LW", "TG", "WW", "SF", "QS"])

    def test_a_variant_added_since_the_last_choice_starts_on(self):
        """The choice saved before "last year, renewed" existed leaves it on;
        one made since keeps it off."""
        old = self._dlg({"ai_event_variants": ["like_last_year", "variety"]})
        self.assertEqual(old.values()["event"]["variants"],
                         ["like_last_year", "last_year_renewed", "variety"])
        new = self._dlg({"ai_event_variants": ["like_last_year", "variety"],
                         "ai_event_variants_offered": list(event_plan.PROFILE_ORDER)})
        self.assertEqual(new.values()["event"]["variants"],
                         ["like_last_year", "variety"])

    def test_the_defaults(self):
        ev = self._dlg().values()["event"]
        self.assertEqual(ev["variants"], list(event_plan.PROFILE_ORDER))
        self.assertEqual(ev["new_share"], 0.2)
        self.assertEqual(ev["rare_share"], 0.15)
        self.assertTrue(ev["use_event"])
        self.assertTrue(ev["use_class"])
        self.assertTrue(ev["ai_check"])
        self.assertEqual(ev["year"], datetime.date.today().year)

    def test_the_series_in_the_playlist_folder_are_offered(self):
        dlg = self._dlg()
        combo = dlg._event._series
        names = [combo.itemText(i) for i in range(combo.count())]
        self.assertEqual(names, ["DanceConvention", "WiDaFe"])
        combo.setCurrentText("DanceConvention")
        self.assertEqual(dlg.values()["event"]["series"], "danceconvention")

    def test_a_typed_series_counts_too(self):
        dlg = self._dlg()
        dlg._event._series.setCurrentText("Blue Ribbon 2026")
        self.assertEqual(dlg.values()["event"]["series"], "blue ribbon")

    def test_the_choices_come_back_next_time(self):
        dlg = self._dlg({"ai_event_schedule": "HGR S STD 2-1",
                         "ai_event_series": "WiDaFe",
                         "ai_event_new_share": 35,
                         "ai_event_rare_share": 5,
                         "ai_event_variants": ["variety"],
                         "ai_event_variants_offered": list(event_plan.PROFILE_ORDER),
                         "ai_event_use_event": False,
                         "ai_event_use_class": False,
                         "ai_event_ai_check": False})
        ev = dlg.values()["event"]
        self.assertEqual(ev["schedule"], "HGR S STD 2-1")
        self.assertEqual(ev["series_name"], "WiDaFe")
        self.assertEqual(ev["new_share"], 0.35)
        self.assertEqual(ev["rare_share"], 0.05)
        self.assertEqual(ev["variants"], ["variety"])
        self.assertFalse(ev["use_event"])
        self.assertFalse(ev["use_class"])
        self.assertFalse(ev["ai_check"])

    def test_the_last_plan_can_be_opened_again(self):
        dlg = AiPlaylistDialog({}, event_plan_kept=True)
        self.addCleanup(reap_widget, dlg)
        self.assertFalse(dlg._reopen_btn.isVisibleTo(dlg))
        dlg._rb_event.setChecked(True)
        self.assertTrue(dlg._reopen_btn.isVisibleTo(dlg))
        dlg._reopen_btn.click()
        self.assertEqual(dlg.result(), AiPlaylistDialog.REOPEN_PLAN)

    def test_the_new_share_can_be_typed(self):
        dlg = self._dlg()
        dlg._event._new_share_box.setValue(33)
        self.assertEqual(dlg._event._new_share.value(), 33)
        self.assertEqual(dlg.values()["event"]["new_share"], 0.33)
        dlg._event._new_share.setValue(10)
        self.assertEqual(dlg._event._new_share_box.value(), 10)

    def test_the_rare_share_can_be_typed(self):
        dlg = self._dlg()
        dlg._event._rare_share_box.setValue(25)
        self.assertEqual(dlg._event._rare_share.value(), 25)
        self.assertEqual(dlg.values()["event"]["rare_share"], 0.25)
        dlg._event._rare_share.setValue(0)
        self.assertEqual(dlg._event._rare_share_box.value(), 0)

    def test_the_column_heads_are_not_cut_off(self):
        """'Gruppen pro Runde' showed as 'Gruppen pro Rund' in the German panel."""
        dlg = self._dlg()
        dlg.show()
        QApplication.processEvents()
        head = dlg._event._table.horizontalHeader()
        for col in (1, 2, 3):
            text = dlg._event._table.horizontalHeaderItem(col).text()
            self.assertGreaterEqual(head.sectionSize(col),
                                    head.fontMetrics().horizontalAdvance(text), text)

    def test_the_login_hint_speaks_german(self):
        """The hint reaches its label through a variable, so the coverage scan
        never flagged it and it stayed English in the German dialog."""
        i18n.set_active("de")
        i18n.install_text_hook()
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.addCleanup(i18n._restore_text_hook)
        for available in (True, False):
            with mock.patch.object(llm, "claude_available", return_value=available):
                dlg = self._dlg()
            texts = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
            self.assertNotIn("Runs through the claude CLI", texts)
            self.assertNotIn("claude CLI not found", texts)

    def test_no_plan_kept_no_button(self):
        dlg = self._dlg()
        self.assertFalse(dlg._reopen_btn.isVisibleTo(dlg))

    def test_the_panel_is_only_on_screen_in_event_mode(self):
        dlg = self._dlg()
        self.assertTrue(dlg._event.isVisibleTo(dlg))
        self.assertFalse(dlg._brief.isVisibleTo(dlg))
        dlg._rb_comp.setChecked(True)
        self.assertFalse(dlg._event.isVisibleTo(dlg))
        self.assertTrue(dlg._brief.isVisibleTo(dlg))


class ClaudeLoginTest(unittest.TestCase):
    """Which `claude` login the CLI is pointed at.

    A shell exports CLAUDE_CONFIG_DIR; the GUI started from the desktop has no
    such variable and would take ~/.claude, which need not be the profile that
    is logged in — so the login is a setting, offered from what is on disk.
    """

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="dp_home_")

    def _make(self, name, marker="settings.json"):
        d = Path(self.home) / name
        d.mkdir(parents=True, exist_ok=True)
        if marker:
            (d / marker).write_text("{}", encoding="utf-8")
        return str(d)

    def test_the_profiles_beside_the_plain_one_are_found(self):
        plain = self._make(".claude")
        one = self._make(".claude-profil1", ".credentials.json")
        two = self._make(".claude-profil2")
        self.assertEqual(llm.claude_config_dirs(self.home),
                         [plain, one, two])

    def test_the_plain_login_comes_first_even_when_it_sorts_later(self):
        self._make(".claude-alpha")
        plain = self._make(".claude")
        self.assertEqual(llm.claude_config_dirs(self.home)[0], plain)

    def test_a_dotfolder_without_a_login_in_it_is_not_offered(self):
        self._make(".claude-empty", marker="")
        self._make(".claudemind", marker="")
        self.assertEqual(llm.claude_config_dirs(self.home), [])

    def test_unrelated_folders_are_left_alone(self):
        self._make(".config")
        self._make("Documents")
        self.assertEqual(llm.claude_config_dirs(self.home), [])

    def test_a_home_that_cannot_be_listed_is_no_crash(self):
        self.assertEqual(
            llm.claude_config_dirs(self.home + "_gone"), [])

    def test_the_environment_is_the_default_when_there_is_one(self):
        old = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = r"C:\Users\x\.claude-profil1"
        try:
            self.assertEqual(llm.default_claude_config_dir(),
                             r"C:\Users\x\.claude-profil1")
        finally:
            if old is None:
                del os.environ["CLAUDE_CONFIG_DIR"]
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = old


class TranscriptWindowTest(unittest.TestCase):
    """The window the steps are written into while the worker is thinking."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self):
        dlg = AiTranscriptDialog()
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def _bubbles(dlg):
        """Every chat bubble in the thread, oldest first."""
        return dlg.findChildren(Bubble)

    def test_a_step_lands_with_its_title_and_its_text(self):
        dlg = self._dlg()
        dlg.add_step("sent", "1 · What the model is asked to search", "summary")
        bubble = self._bubbles(dlg)[0]
        labels = " ".join(w.text() for w in bubble.findChildren(QLabel))
        self.assertIn("1 · What the model is asked to search", labels)
        self.assertIn("summary", labels)
        self.assertIn("Planner", labels)              # the app's own side

    def test_the_steps_stay_in_order(self):
        dlg = self._dlg()
        dlg.add_step("sent", "first", "a")
        dlg.add_step("received", "second", "b")
        text = dlg.transcript()
        self.assertLess(text.index("first"), text.index("second"))
        self.assertIn("Model", text)                  # 'it answered'

    def test_each_speaker_gets_its_own_side(self):
        """Like any chat client: what we send is right, the answer is left."""
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        dlg.add_step("received", "answer", "b")
        sent_row, recv_row = (b.parentWidget() for b in self._bubbles(dlg))
        # A stretch BEFORE the bubble pushes it right, one after it pushes left.
        self.assertIsNotNone(sent_row.layout().itemAt(0).spacerItem())
        self.assertIsNone(recv_row.layout().itemAt(0).spacerItem())

    def test_a_note_is_a_line_between_them_not_a_bubble(self):
        dlg = self._dlg()
        dlg.add_step("note", "What the queries found", "3 queries → 40 tracks")
        self.assertEqual(self._bubbles(dlg), [])
        self.assertIn("3 queries → 40 tracks", dlg.transcript())

    def test_a_long_turn_opens_folded(self):
        """600 catalog rows must not bury the shape of the conversation."""
        dlg = self._dlg()
        body = "\n".join(f"{i}. Track {i}" for i in range(1, 61))
        dlg.add_step("sent", "2 · The tracks it may pick from", body)
        bubble = self._bubbles(dlg)[0]
        self.assertIn("more lines", bubble._more.text())
        self.assertNotIn("60. Track 60", bubble._body.text())
        bubble._more.click()
        self.assertIn("60. Track 60", bubble._body.text())
        # Folded or not, 📋 Copy hands over every line.
        self.assertIn("60. Track 60", dlg.transcript())

    def test_an_unfolded_turn_folds_back_up(self):
        """Unfolding the catalog buries whatever came after it — the same link
        has to put it away again."""
        dlg = self._dlg()
        body = "\n".join(f"{i}. Track {i}" for i in range(1, 61))
        dlg.add_step("sent", "2 · The tracks it may pick from", body)
        bubble = self._bubbles(dlg)[0]
        bubble._more.click()                      # unfold
        self.assertIn("fold back", bubble._more.text())
        bubble._more.click()                      # and back up
        self.assertNotIn("60. Track 60", bubble._body.text())
        self.assertIn("46 more lines", bubble._more.text())
        self.assertFalse(bubble._more.isHidden())

    def test_the_transcript_is_a_window_of_its_own(self):
        """Minimising an owned dialog on Windows loses it: no taskbar button.
        The transcript outlives a long run, so it is a real window."""
        dlg = self._dlg()
        flags = dlg.windowFlags()
        self.assertTrue(flags & Qt.WindowType.Window)
        self.assertTrue(flags & Qt.WindowType.WindowMinimizeButtonHint)
        self.assertIsNone(dlg.parent())

    def test_a_closed_transcript_keeps_everything_and_can_come_back(self):
        """Closing the window only puts it away: 💬 reopens the same thread,
        and only the next run throws it out."""
        from gui.window.main_generate import GenerateMixin

        dlg = self._dlg()
        dlg.add_step("received", "Why these tracks", "because")
        dlg.show()
        dlg.close()
        self.assertFalse(dlg.isVisible())

        win = SimpleNamespace(_ai_log=dlg)
        GenerateMixin._show_ai_log(win)
        self.assertTrue(dlg.isVisible())
        self.assertIn("because", dlg.transcript())

    def test_reopening_nothing_is_not_a_crash(self):
        from gui.window.main_generate import GenerateMixin

        GenerateMixin._show_ai_log(SimpleNamespace(_ai_log=None))

    def test_the_status_bar_counts_what_the_run_moves(self):
        """Nothing else says how much of the context window a run eats."""
        dlg = self._dlg()
        dlg.add_step("sent", "the catalog", "x" * 8000)
        dlg.add_step("received", "the picks", "y" * 400)
        text = dlg._usage.text()
        self.assertIn("8.0k chars", text)          # sent
        self.assertIn("400 chars", text)           # and back
        self.assertIn("2.0k tok", text)            # 8000 / 4
        self.assertIn("2.1k tok", text)            # the turn: prompt + reply

    def test_a_note_is_not_context(self):
        # Notes are the planner talking to itself; the model never sees them.
        dlg = self._dlg()
        dlg.add_step("note", "Pool", "z" * 500)
        self.assertEqual(dlg._usage.text(), "")
        self.assertIn("📤 0 chars", dlg.usage_text())


class ThinkingIndicatorTest(unittest.TestCase):
    """A turn takes minutes. While one is out, the thread carries a live
    "the model is typing" bubble — a window that has died looks exactly like a
    window with a finished prompt in it."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self):
        dlg = AiTranscriptDialog()
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def _thinking(dlg):
        return dlg.findChildren(ThinkingBubble)

    def test_a_question_leaves_the_model_visibly_thinking(self):
        dlg = self._dlg()
        dlg.add_step("sent", "1 · What to search for", "summary")
        bubble = self._thinking(dlg)[0]
        self.assertTrue(bubble._timer.isActive())
        self.assertIn("thinking", bubble._label.text())

    def test_the_dots_move_and_the_clock_counts(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        bubble = self._thinking(dlg)[0]
        first = bubble._label.text()
        bubble._tick()
        self.assertNotEqual(bubble._label.text(), first)
        for _ in range(4):                 # 5 ticks × 400 ms = 2 s
            bubble._tick()
        self.assertEqual(bubble.elapsed_text(), "0:02")

    def test_it_sits_at_the_end_of_the_thread_on_the_model_side(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        row = dlg._open[0][1]
        self.assertIs(dlg._thread.itemAt(dlg._thread.count() - 2).widget(), row)
        self.assertIsNone(row.layout().itemAt(0).spacerItem())

    def test_the_answer_takes_it_away(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        bubble = self._thinking(dlg)[0]
        dlg.add_step("received", "answer", "b")
        self.assertEqual(dlg._open, [])
        self.assertFalse(bubble._timer.isActive())

    def test_a_note_after_the_answer_does_not_leave_two_of_them(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        dlg.add_step("received", "answer", "b")
        dlg.add_step("note", "What the queries found", "40 tracks")
        self.assertEqual(len(self._thinking(dlg)), 0)
        dlg.add_step("sent", "ask again", "c")
        self.assertEqual(len(self._thinking(dlg)), 1)

    def test_a_retry_note_keeps_the_waiting_visible(self):
        """A note while the question is still out means the backend wobbled and
        we are waiting again — one indicator, not none and not two."""
        dlg = self._dlg()
        dlg.add_step("sent", "1 · What to search for", "a")
        dlg.add_step("note", "⏳ claude -p — attempt 1 of 4", "HTTP 529")
        self.assertEqual(len(self._thinking(dlg)), 1)
        self.assertIn("1 · What to search for",
                      self._thinking(dlg)[0].findChildren(QLabel)[0].text())
        dlg.add_step("received", "its answer", "b")
        self.assertEqual(len(self._thinking(dlg)), 0)

    def test_a_failure_note_ends_the_lone_turn(self):
        """The search round's failure note was taken for a retry: its bubble
        ran on, and turn 2's reply then closed turn 1's (BUG_REVIEW B4.4)."""
        dlg = self._dlg()
        dlg.add_step("sent", "1 · What the model is asked to search", "a")
        dlg.add_step("note", "1 · The search round failed", "HTTP 500")
        self.assertEqual(self._thinking(dlg), [])
        dlg.add_step("sent", "2 · What the model is asked to pick", "b")
        dlg.add_step("received", "2 · Its picks — stub", "c")
        self.assertEqual(self._thinking(dlg), [])
        self.assertEqual(dlg._open, [])

    def test_parallel_questions_each_keep_their_own_clock(self):
        """The event planner sends every competition's question at once and
        the answers come back in any order: each question out is one bubble,
        and an answer takes away its own — not the last one sent."""
        dlg = self._dlg()
        dlg.add_step("sent", "HGR S STD — the drafts to check", "a")
        first = self._thinking(dlg)[0]
        first._tick()
        dlg.add_step("sent", "SEN I S STD — the drafts to check", "b")
        dlg.add_step("sent", "HGR A LAT — the drafts to check", "c")
        self.assertEqual(len(self._thinking(dlg)), 3)
        self.assertTrue(first._timer.isActive())
        self.assertEqual(first._frame, 1)             # its clock ran on
        self.assertEqual(dlg._status.text(), "Waiting for the model… (3)")
        dlg.add_step("received", "SEN I S STD — its swaps — stub", "[]")
        titles = [b.findChildren(QLabel)[0].text() for b in self._thinking(dlg)]
        self.assertEqual(len(titles), 2)
        self.assertFalse(any("SEN I S STD" in t for t in titles))
        self.assertEqual(dlg._status.text(), "Waiting for the model… (2)")
        dlg.add_step("note", "HGR A LAT — the plan stands", "HTTP 500")
        self.assertEqual(len(self._thinking(dlg)), 1)
        self.assertEqual(dlg._status.text(), "Waiting for the model…")
        dlg.add_step("received", "HGR S STD — its swaps — stub", "[]")
        self.assertEqual(self._thinking(dlg), [])
        self.assertEqual(dlg._status.text(), "Working…")

    def test_new_rows_go_above_the_waiting(self):
        dlg = self._dlg()
        dlg.add_step("sent", "A — the drafts to check", "a")
        dlg.add_step("sent", "B — the drafts to check", "b")
        dlg.add_step("received", "B — its swaps — stub", "[]")
        last = dlg._thread.itemAt(dlg._thread.count() - 2).widget()
        self.assertTrue(last.findChildren(ThinkingBubble))

    def test_a_parallel_turn_pairs_the_answer_with_its_own_question(self):
        """The biggest turn is a prompt plus ITS reply, not the last prompt
        sent plus whichever reply landed first."""
        dlg = self._dlg()
        dlg.add_step("sent", "A — the drafts to check", "x" * 8000)
        dlg.add_step("sent", "B — the drafts to check", "x" * 400)
        dlg.add_step("received", "A — its swaps — stub", "y" * 400)
        dlg.add_step("received", "B — its swaps — stub", "y" * 400)
        self.assertEqual(dlg._turn_max, 8400)

    def test_the_end_of_the_run_stops_it(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        bubble = self._thinking(dlg)[0]
        dlg.finish("🤖 Done")
        self.assertEqual(self._thinking(dlg), [])
        self.assertFalse(bubble._timer.isActive())
        self.assertEqual(dlg._status.text(), "🤖 Done")

    def test_the_indicator_is_not_part_of_the_transcript(self):
        """📋 Copy hands over the conversation, not the waiting."""
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        self.assertNotIn("thinking", dlg.transcript())

    def test_finishing_stops_the_bar_and_says_how_it_went(self):
        dlg = self._dlg()
        dlg.add_step("sent", "asking", "…")
        self.assertEqual(dlg._bar.maximum(), 0)       # indeterminate: still busy
        dlg.finish("🤖 18/18 slots filled by stub")
        self.assertEqual(dlg._bar.maximum(), 1)
        self.assertIn("18/18", dlg._status.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
