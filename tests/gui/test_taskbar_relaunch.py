#!/usr/bin/env python3
"""📌 A taskbar pin of the app shows the app's icon, not a white box.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_taskbar_relaunch -v

The app gives itself an explicit AppUserModelID so its windows group under
their own icon. With that ID the shell no longer pins "the exe that runs": it
looks for a shortcut carrying the same ID, or for relaunch properties on the
window — and with neither, the pin it makes has no icon. So the main window
names its relaunch command, icon and name, and the installer's shortcuts carry
the same ID.
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_relaunch_"))

from gui import common

ROOT = Path(__file__).resolve().parents[2]


class RelaunchPropertiesTest(unittest.TestCase):

    def test_a_build_relaunches_its_own_exe_and_wears_its_icon(self):
        exe = r"C:\Program Files\DanceSport Player\DanceSport-Player.exe"
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", exe):
            props = common.relaunch_properties("DanceSport Player")
        self.assertEqual(props["command"], f'"{exe}"')
        self.assertEqual(props["icon"], f"{exe},0")
        self.assertEqual(props["name"], "DanceSport Player")

    def test_a_source_run_relaunches_the_script_under_its_python(self):
        script = ROOT / "dancesport_gui.py"
        with mock.patch.object(sys, "argv", [str(script)]):
            props = common.relaunch_properties("DanceSport Planner")
        self.assertIn(f'"{script}"', props["command"])
        self.assertTrue(props["command"].startswith('"'))
        self.assertTrue(props["icon"].endswith("icon.ico,0"))
        self.assertTrue(Path(props["icon"][:-2]).exists())

    def test_the_installer_shortcuts_carry_the_apps_id(self):
        iss = (ROOT / "installer" / "dancesport.iss").read_text(encoding="utf-8")
        icons = iss.split("[Icons]", 1)[1].split("\n[", 1)[0]
        lines = [ln for ln in icons.splitlines() if ln.startswith("Name:")]
        self.assertTrue(lines)
        for ln in lines:
            self.assertRegex(ln, r'AppUserModelID: "\{#AppUserModelID\}"')
        defined = re.search(r'#define AppUserModelID "([^"]+)"', iss)
        self.assertIsNotNone(defined)
        self.assertEqual(defined.group(1), common.APP_USER_MODEL_ID)


@unittest.skipUnless(sys.platform == "win32", "Windows shell only")
class NativeWindowTest(unittest.TestCase):
    """The properties really land: set on a real HWND, read back through the
    shell's own property store."""

    def setUp(self):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        ctypes.windll.ole32.CoInitializeEx(None, 2)   # STA, as Qt's GUI thread
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        self.hwnd = user32.CreateWindowExW(0, "STATIC", "relaunch test",
                                           0x00CF0000, 0, 0, 100, 100,
                                           None, None, None, None)
        self.assertTrue(self.hwnd)
        self.addCleanup(user32.DestroyWindow, wintypes.HWND(self.hwnd))

    def test_the_window_carries_id_command_icon_and_name(self):
        from shared import taskbar_win32 as tw

        props = {"command": '"C:\\x\\DanceSport.exe"',
                 "icon": "C:\\x\\DanceSport.exe,0",
                 "name": "DanceSport Player"}
        self.assertTrue(tw.set_relaunch_properties(
            self.hwnd, common.APP_USER_MODEL_ID, **props))
        self.assertEqual(tw.window_property(self.hwnd, tw.PID_ID),
                         common.APP_USER_MODEL_ID)
        self.assertEqual(tw.window_property(self.hwnd, tw.PID_RELAUNCH_COMMAND),
                         props["command"])
        self.assertEqual(tw.window_property(self.hwnd, tw.PID_RELAUNCH_ICON),
                         props["icon"])
        self.assertEqual(tw.window_property(self.hwnd, tw.PID_RELAUNCH_NAME),
                         props["name"])


if __name__ == "__main__":
    unittest.main()
