#!/usr/bin/env python3
"""The Rundenstrategie combo — captions AND per-item tooltips speak German.

Run:  py -m unittest tests.gui.test_strategy_combo_i18n -v

This combo is built the way the ⚙ Mode combo had to be rebuilt: addItem
carries the caption, the STRATEGIES key rides in the data role, and every
reader uses currentData(). So the captions needed nothing but catalog
entries.

The tooltips are the interesting half. They do not go through setToolTip —
they go through

    combo.setItemData(j, STRATEGY_HELP[key], Qt.ItemDataRole.ToolTipRole)

and setItemData is not in the hook's patch table, nor could it sensibly be:
it carries arbitrary data for arbitrary roles, and translating whatever
happens to pass through it is exactly the data-into-chrome mistake the
catalog exists to avoid. So that one call site has to ask for the
translation itself. The widget-level tooltip two lines below it (the one
showing the SELECTED strategy's help) does go through a patched setToolTip,
which is why only one of the two was ever broken — and why the bug is easy
to miss by hovering the combo instead of its open list.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_strat_i18n_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from planner import i18n  # noqa: E402
from planner.scoring import STRATEGIES, STRATEGY_HELP, STRATEGY_LABELS  # noqa: E402


class StrategyComboI18nTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def combo(self, language):
        """One round's strategy combo, built the way the panel builds it."""
        i18n.set_active(language)
        i18n.install_text_hook()
        from gui.config_panel import ConfigPanel
        panel = ConfigPanel()
        self.addCleanup(panel.deleteLater)
        panel.rounds_edit.setText("3")
        panel._parse_rounds()
        combos = list(panel._strategy_combos.values())
        self.assertTrue(combos, "no strategy combo was built")
        return combos[0]

    def _tips(self, combo):
        return [combo.itemData(i, Qt.ItemDataRole.ToolTipRole)
                for i in range(combo.count())]

    def test_the_key_behind_every_entry_stays_english(self):
        """What _resolve_strategy, the re-roll and the saved config compare
        against — translating this would lose a restored round's strategy."""
        combo = self.combo("de")
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         list(STRATEGIES))

    def test_english_is_unchanged(self):
        combo = self.combo("en")
        self.assertEqual([combo.itemText(i) for i in range(combo.count())],
                         [STRATEGY_LABELS[k] for k in STRATEGIES])
        self.assertEqual(self._tips(combo),
                         [STRATEGY_HELP[k] for k in STRATEGIES])

    def test_german_captions(self):
        shown = [self.combo("de").itemText(i)
                 for i in range(len(STRATEGIES))]
        english = [STRATEGY_LABELS[k] for k in STRATEGIES]
        self.assertNotEqual(shown, english, "the captions stayed English")
        for caption in shown:
            self.assertTrue(caption.strip())

    def test_german_per_item_tooltips(self):
        """The half that setItemData does not translate on its own."""
        tips = self._tips(self.combo("de"))
        english = [STRATEGY_HELP[k] for k in STRATEGIES]
        for key, tip, en in zip(STRATEGIES, tips, english):
            self.assertTrue(tip, f"{key} has no tooltip at all")
            self.assertNotEqual(tip, en, f"{key} kept its English tooltip")

    def test_no_german_caption_outgrows_the_english_it_replaces(self):
        """Five of these combos sit stacked in a panel laid out around the
        English captions, and the two longest German ones were half again
        as wide as anything English: "Gleichmäßig gemischt" 240px against
        "Mostly Proven"'s 156px. What each strategy does is in the tooltip
        the line above already guards, so the caption only has to name it.
        """
        combo = self.combo("de")
        fm = combo.fontMetrics()
        budget = max(fm.horizontalAdvance(STRATEGY_LABELS[k])
                     for k in STRATEGIES)
        for i in range(combo.count()):
            with self.subTest(caption=combo.itemText(i)):
                self.assertLessEqual(fm.horizontalAdvance(combo.itemText(i)),
                                     budget)

    def test_the_selected_entrys_tooltip_moves_too(self):
        """The widget-level one, which the hook does handle — guards that the
        two halves did not drift apart."""
        combo = self.combo("de")
        self.assertNotIn(combo.toolTip(), [STRATEGY_HELP[k] for k in STRATEGIES])
        self.assertTrue(combo.toolTip().strip())


if __name__ == "__main__":
    unittest.main()
