#!/usr/bin/env python3
"""The system's own programs started from the Linux build load the system's
libraries, not ours.

The PyInstaller bootloader points LD_LIBRARY_PATH at the bundled libraries
(keeping the old value as LD_LIBRARY_PATH_ORIG), and every child inherits it.
gsettings (🔕 system sounds), a system ffmpeg (loudness, PD highlights,
silences), xdg-open and the claude CLI would then pick up the Ubuntu 22.04
glib or Qt's trimmed FFmpeg libraries out of the bundle and fail, silently.

Run:  py -m unittest tests.app.test_child_library_path -v
"""

import unittest

from planner.config import restore_system_library_path

_BUNDLE = "/opt/DanceSport-Player/_internal"


class ChildLibraryPathTest(unittest.TestCase):

    def test_the_original_path_comes_back(self):
        env = {"LD_LIBRARY_PATH": _BUNDLE + ":/usr/local/lib",
               "LD_LIBRARY_PATH_ORIG": "/usr/local/lib"}
        restore_system_library_path(env, frozen=True, platform="linux")
        self.assertEqual(env["LD_LIBRARY_PATH"], "/usr/local/lib")

    def test_without_an_original_the_variable_goes(self):
        """The bootloader keeps an _ORIG only when there was a value to keep:
        none means the variable holds nothing but the bundle."""
        env = {"LD_LIBRARY_PATH": _BUNDLE}
        restore_system_library_path(env, frozen=True, platform="linux")
        self.assertNotIn("LD_LIBRARY_PATH", env)

    def test_a_source_run_is_left_alone(self):
        env = {"LD_LIBRARY_PATH": "/home/me/lib"}
        restore_system_library_path(env, frozen=False, platform="linux")
        self.assertEqual(env, {"LD_LIBRARY_PATH": "/home/me/lib"})

    def test_other_systems_are_left_alone(self):
        for platform in ("win32", "darwin"):
            env = {"LD_LIBRARY_PATH": _BUNDLE}
            restore_system_library_path(env, frozen=True, platform=platform)
            self.assertEqual(env, {"LD_LIBRARY_PATH": _BUNDLE})

    def test_the_launcher_does_it_before_anything_runs(self):
        """At import of the launcher, so no child can start before it."""
        import inspect
        import dancesport_gui
        src = inspect.getsource(dancesport_gui)
        self.assertLess(src.index("restore_system_library_path("),
                        src.index("def run_gui("))


if __name__ == "__main__":
    unittest.main(verbosity=2)
