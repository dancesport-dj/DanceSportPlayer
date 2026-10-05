"""📏 The presenter screen's fitting pass: that it measures the sizes it just
set, rather than shrinking the screen against a number that never moves.
"""
import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication, state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_presfit_"))

from tests.qt_test_support import reap_widget   # noqa: E402


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


_STATE = ("Langsamer Walzer", "Fascination", ("01:12", "− 01:48", False, 0.4),
          [("Tango", "Jealousy"), ("Rumba", "Besame Mucho")],
          ("Cha Cha Cha", "Sway"))


def _presenter():
    from player.presenter import PresenterWindow
    _app()
    w = PresenterWindow(lambda: _STATE)
    w.resize(1280, 720)
    w.set_last_played_shown(True)
    w.set_controls_shown(True)
    w.show()
    w._refresh()
    return w


class FittingPassTest(unittest.TestCase):
    """The loop that steps the whole screen down until it stands in the
    window."""

    def test_the_pass_measures_what_it_just_set(self):
        """Smaller fonts have to read back as a smaller screen.

        They did not: a font change reaches the outer layout through a posted
        LayoutRequest, which is never delivered inside a synchronous loop, so
        `activate()` alone handed back the first guess on every iteration. The
        loop then shrank to its floor without ever seeing that it already fit
        — measured on the real platform, the hero line dropped from 97 px to
        58 px the moment the first title arrived.
        """
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w._apply_fonts(720, 1.0)
        w._size_column()
        big = w._measure_h()
        w._apply_fonts(720, 0.6)
        w._size_column()
        small = w._measure_h()
        self.assertLess(small, big,
                        "the fitting pass cannot see its own work")

    def test_the_measurement_is_what_the_layout_settles_at(self):
        """Dropping the cached hints by hand has to agree with letting the
        event loop deliver the same invalidations — otherwise the loop is
        fitting against a number the screen will not actually have."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        app = _app()
        for scale in (1.0, 0.8, 0.6):
            w._apply_fonts(720, scale)
            w._size_column()
            measured = w._measure_h()
            for _ in range(6):
                app.processEvents()
            self.assertEqual(measured,
                             w.layout().minimumSize().height(),
                             f"measurement disagrees at scale {scale}")

    def test_a_screen_with_room_keeps_its_nominal_size(self):
        """Nothing shrinks while everything fits — the hero keeps the full
        fraction of the window height it is specified at."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w._font_h = None
        w._scale_fonts()
        self.assertLessEqual(w._measure_h(), w.height())
        self.assertEqual(w.dance_lbl.font().pixelSize(),
                         int(w.height() * 0.135))


if __name__ == "__main__":
    unittest.main()
