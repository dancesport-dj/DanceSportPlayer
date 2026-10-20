"""🏷 The app was DancePlaylist; what the operator and the phone see says
DanceSport Player now: the presenter's title bar and the remote's page title,
in every language.

Run:  py -m unittest tests.app.test_new_name_on_screen -v
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_newname_"))

from planner import i18n
from tests.qt_test_support import qapp, reap_widget

PRESENTER = "🖥  Presenter — DanceSport Player"
REMOTE = "DanceSport Player remote"


class NewNameOnScreenTest(unittest.TestCase):
    def test_presenter_title(self):
        from player.presenter.presenter import PresenterWindow
        qapp()
        w = PresenterWindow(lambda: ("LW", "Titel", ("00:10", "− 02:00", False, 0.1),
                                     [("TG", "Zweiter")], ("", "")))
        self.addCleanup(reap_widget, w)
        self.assertIn("DanceSport Player", w.windowTitle())
        self.assertNotIn("DancePlaylist", w.windowTitle())

    def test_remote_page_title(self):
        from shared.remote.remote_page import DEFAULT_LABELS
        self.assertEqual(DEFAULT_LABELS["title"], REMOTE)

    def test_every_catalog_says_the_new_name(self):
        self.addCleanup(i18n.apply_settings, {"language": "en"})
        for code in ("de", "es", "nl", "ru"):
            i18n.apply_settings({"language": code})
            for key in (PRESENTER, REMOTE):
                with self.subTest(language=code, key=key):
                    text = i18n.t(key)
                    self.assertNotEqual(text, key)
                    self.assertIn("DanceSport Player", text)
                    self.assertNotIn("DancePlaylist", text)


if __name__ == "__main__":
    unittest.main()
