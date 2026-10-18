#!/usr/bin/env python3
"""The window tests hand MainWindow settings of their own, and give the real
`load_settings` back afterwards.

Run:  py -m unittest tests.gui.test_no_settings_leak -v

A test that swaps `dancesport_gui.load_settings` and never restores it leaves
its settings to every test after it in the same process — which tests those are
depends on the order and on which xdist worker drew them.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import dancesport_gui as gui
from gui import dialogs
from tests.gui import (test_build_env_failure, test_error_reports_setting,
                       test_phone_remote_setting, test_settings_apply_merge)


class NoSettingsLeakTest(unittest.TestCase):

    def test_each_window_test_gives_load_settings_back(self):
        for case in (test_build_env_failure.BuildEnvFailureTest,
                     test_error_reports_setting.SaveAppliesTest,
                     test_phone_remote_setting.SaveAppliesTest,
                     test_settings_apply_merge.SettingsApplyMergeTest):
            with self.subTest(case.__module__):
                result = unittest.TestResult()
                suite = unittest.defaultTestLoader.loadTestsFromTestCase(case)
                suite.run(result)
                self.assertTrue(result.wasSuccessful(),
                                result.errors + result.failures)
                self.assertIs(gui.load_settings, dialogs.load_settings)


if __name__ == "__main__":
    unittest.main()
