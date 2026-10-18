"""📱 The phone page's PIN field holds a whole 8-digit tunnel PIN, measured
in a real browser engine rather than read off the CSS."""
import json
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pinfield_"))

from shared.remote import remote_server as rs
from shared.remote.remote_page import DEFAULT_LABELS, page_html


def _render(js: str, width: int = 390):
    """Run `js` on the phone page in a QWebEngineView `width` px wide and
    return its result."""
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtWebEngineWidgets import QWebEngineView

    from tests.qt_test_support import qapp, reap_widget
    qapp()
    view = QWebEngineView()
    view.resize(width, 800)
    view.show()
    loop = QEventLoop()
    out = {}
    view.loadFinished.connect(lambda ok: view.page().runJavaScript(
        js, 0, lambda r: (out.setdefault("r", r), loop.quit())))
    QTimer.singleShot(20000, loop.quit)
    view.setHtml(page_html(DEFAULT_LABELS), QUrl("http://127.0.0.1/"))
    loop.exec()
    reap_widget(view)
    return json.loads(out["r"]) if out.get("r") else None


_FILL = """(() => {
  const i = document.getElementById("pin");
  document.getElementById("login").classList.remove("hidden");
  i.value = "%s";
  return JSON.stringify([i.scrollWidth, i.clientWidth, i.getBoundingClientRect().right,
                         document.documentElement.clientWidth]);
})()"""


class PinFieldTest(unittest.TestCase):

    def test_eight_digits_fit_without_scrolling(self):
        """📱 Marcel: "make sure phone remote pin box is wide enough for pin
        with 8 letters"."""
        pin = "8" * rs.TUNNEL_PIN_DIGITS
        r = _render(_FILL % pin)
        self.assertIsNotNone(r, "the page did not render")
        scroll_w, client_w, right, page_w = r
        self.assertLessEqual(scroll_w, client_w,
                             f"{pin} scrolls inside the field ({scroll_w} > {client_w})")
        self.assertLessEqual(right, page_w, "the field stays on a phone screen")

    def test_a_small_phone_keeps_the_field_on_screen(self):
        r = _render(_FILL % ("8" * rs.TUNNEL_PIN_DIGITS), width=320)
        self.assertIsNotNone(r, "the page did not render")
        scroll_w, client_w, right, page_w = r
        self.assertLessEqual(scroll_w, client_w)
        self.assertLessEqual(right, page_w)


class ConnectButtonTest(unittest.TestCase):

    def test_the_button_stands_in_the_middle_under_the_field(self):
        """📱 Marcel: "in the phone connect screen allign connect button in
        the middle"."""
        r = _render("""(() => {
  document.getElementById("login").classList.remove("hidden");
  const mid = (el) => { const b = el.getBoundingClientRect(); return (b.left + b.right) / 2; };
  return JSON.stringify([mid(document.getElementById("go")),
                         mid(document.getElementById("pin"))]);
})()""")
        self.assertIsNotNone(r, "the page did not render")
        button, field = r
        self.assertAlmostEqual(button, field, delta=1)


if __name__ == "__main__":
    unittest.main()
