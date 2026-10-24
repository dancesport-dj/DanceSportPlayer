#!/usr/bin/env python3
"""The monkey's checks catch what they are there for. A walk that passes
says nothing unless a broken window would have failed it."""

import unittest

from tests.gui.monkey_support import LoadedWindow, Monkey, SEED

from planner.store import state_dir


class OracleTest(LoadedWindow):

    def test_a_list_out_of_step_with_its_rows_fails_the_walk(self):
        table = self.win._deckset.table
        with self.assertRaisesRegex(AssertionError, "row records"):
            with self.walking(Monkey(SEED, self._roots)) as trap:
                table.setRowCount(table.rowCount() + 1)
                self.check_step(trap)

    def test_a_state_file_that_no_longer_reads_fails_the_walk(self):
        broken = state_dir() / "monkey_oracle_test.json"
        broken.write_text('{"half": ', encoding="utf-8")
        self.addCleanup(broken.unlink)
        with self.assertRaisesRegex(AssertionError, "monkey_oracle_test.json no longer reads"):
            with self.walking(Monkey(SEED, self._roots)):
                pass


if __name__ == "__main__":
    unittest.main()
