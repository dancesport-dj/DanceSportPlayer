"""A label built from a tag, a playlist line or a pack field shows as text.

Run:  py -m unittest tests.gui.test_plain_label_sinks -v

A QLabel reads text that looks like markup as markup, and an `<img src>` in it
opens that path (an SMB login for a UNC path). The title, the example value
of a tag frame, a path in a playlist and the profile name of a controller all
reach a label as typed. A LOCAL png stands in for the share: same resource
loader, and a loaded image makes the label taller. Security audit run-2 #3.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_plain_labels_"))

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QLabel

from gui.dialogs import MusicSpeedDialog
from gui.dialogs.duplicate_titles_dialog import DuplicateTitlesDialog
from gui.dialogs.tag_edit_dialog import CustomSourceDialog, TagEditDialog
from planner.models import MusicEntry
from planner.playing import cartwall as pc
from player.dialogs import cart_pad_dialog, controller_dialog
from tests.player.dialogs.test_controller_dialog import _DEVICES, _Host
from tests.qt_test_support import reap_widget

_HERE = os.getcwd()
_app = QApplication.instance() or QApplication([])

_TMP = tempfile.mkdtemp(prefix="dp_plain_labels_png_")
PNG = os.path.join(_TMP, "probe.png").replace("\\", "/")
_img = QImage(300, 400, QImage.Format.Format_RGB32)
_img.fill(QColor("red"))
_img.save(PNG)

# No slash in it: a path keeps only its last part as a "file name", and the
# image is found next to the test (the setUp below changes into that folder).
BAIT = 'Cha Cha <img src="probe.png"> (Remix)'
# The image is 400 high; one or two lines of text stay well under the limit.
PLAIN_HEIGHT_LIMIT = 200
IMAGE_MIN = 300


def bait_labels(widget):
    """The labels that show the bait, with the height Qt gives each."""
    out = []
    for lbl in widget.findChildren(QLabel):
        if "probe.png" in lbl.text():
            lbl.setMinimumWidth(0)
            lbl.adjustSize()
            out.append((lbl.sizeHint().height(), lbl.text()))
    return out


class CanaryTest(unittest.TestCase):

    def test_the_bait_is_tall_in_a_label_left_to_guess(self):
        # If this stops holding, the tests below prove nothing.
        os.chdir(_TMP)
        self.addCleanup(os.chdir, _HERE)
        lbl = QLabel(BAIT)
        self.addCleanup(reap_widget, lbl)
        lbl.adjustSize()
        self.assertGreater(lbl.sizeHint().height(), IMAGE_MIN)


class PlainLabelsTest(unittest.TestCase):

    def setUp(self):
        os.chdir(_TMP)
        self.addCleanup(os.chdir, _HERE)

    def assertShownAsText(self, dlg, what):
        found = bait_labels(dlg)
        self.assertTrue(found, f"{what}: no label shows the text")
        for height, text in found:
            with self.subTest(what=what, text=text[:40]):
                self.assertLess(height, PLAIN_HEIGHT_LIMIT)

    def test_the_title_in_the_tag_editor(self):
        entry = MusicEntry(path=Path(r"C:\m\x.mp3"), title=BAIT, dance="LW")
        dlg = TagEditDialog([entry], ())
        self.addCleanup(reap_widget, dlg)
        self.assertShownAsText(dlg, "tag editor title")

    def test_the_example_tag_value_in_the_custom_field_dialog(self):
        # What the look into some MP3s found is shown beside the frame picker.
        dlg = CustomSourceDialog(None, samples=(3, {("TXXX", "d"): (3, BAIT)}))
        self.addCleanup(reap_widget, dlg)
        dlg._frame.setCurrentIndex(dlg._frame.findData("TXXX"))
        dlg._desc.setCurrentText("d")
        self.assertShownAsText(dlg, "custom field example")

    def test_the_title_in_the_music_speed_dialog(self):
        dlg = MusicSpeedDialog(BAIT, "LW", 3, 29.0, 29, 29.0)
        self.addCleanup(reap_widget, dlg)
        self.assertShownAsText(dlg, "music speed title")

    def test_a_path_in_the_duplicate_titles_list(self):
        def e(name):
            return MusicEntry(path=Path("C:/m") / name, title="t", dance="LW", bpm=None)
        # A playlist line can be anything, so the "file name" is as free as a tag.
        gone = MusicEntry(path=Path(BAIT), title="t", dance="LW", bpm=None)
        dlg = DuplicateTitlesDialog(None, identical=[(gone, e("kept.mp3"))],
                                    groups=[], play_cb=None)
        self.addCleanup(reap_widget, dlg)
        self.assertShownAsText(dlg, "duplicate titles")

    def test_a_pad_path_in_the_pad_settings(self):
        dlg = cart_pad_dialog.CartPadDialog(pc.CartPad(path=BAIT))
        self.addCleanup(reap_widget, dlg)
        self.assertShownAsText(dlg, "pad settings")

    def test_a_controller_profile_name(self):
        with mock.patch.object(controller_dialog, "controller_devices",
                               return_value=list(_DEVICES)), \
                mock.patch.object(controller_dialog, "profile_dir",
                                  return_value=Path(tempfile.mkdtemp())):
            dlg = controller_dialog.ControllerDialog(_Host({"profile": BAIT}))
        self.addCleanup(reap_widget, dlg)
        self.assertShownAsText(dlg, "controller profile")


if __name__ == "__main__":
    unittest.main()
