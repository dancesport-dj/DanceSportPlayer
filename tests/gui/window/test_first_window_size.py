"""The first window fits the screen: 1500 × 900 overflowed a 1366 × 768
laptop, whose taskbar then hid the status bar and the deck's last rows."""
import unittest

from PySide6.QtCore import QRect

from gui.window.main_persist import first_window_rect


class FirstWindowRectTest(unittest.TestCase):
    # ===== Acceptance criteria =====
    def test_a_small_screen_gets_a_window_that_fits_its_free_area(self):
        free = QRect(0, 0, 1366, 728)        # 1366 × 768 less the taskbar
        rect = first_window_rect(free)
        self.assertTrue(free.contains(rect), rect)
        self.assertEqual((rect.width(), rect.height()), (1366, 728))

    def test_a_big_screen_keeps_1500_by_900_centred(self):
        free = QRect(0, 0, 2560, 1400)
        rect = first_window_rect(free)
        self.assertEqual((rect.width(), rect.height()), (1500, 900))
        self.assertEqual((rect.x(), rect.y()), (530, 250))

    # ===== Core behavior =====
    def test_a_second_screen_left_of_the_first_is_respected(self):
        free = QRect(-1280, 0, 1280, 760)
        rect = first_window_rect(free)
        self.assertTrue(free.contains(rect), rect)
        self.assertEqual(rect.width(), 1280)


if __name__ == "__main__":
    unittest.main()
