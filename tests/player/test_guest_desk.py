"""📨 Guest requests, desk side: the inbox, the ⭐ wishlist, the badge and the window."""
import http.client
import json
import os
import types
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from planner.terms import dance_name
from player.dialogs import remote_dialog
from player.dialogs.guest_dialog import GuestDialog, guest_qr_url, inbox_row
from player.window import main_guest
from player.window.main_guest import GuestDesk, GuestMixin, song_id, song_label
from shared.remote.guest_page import GUEST_CODE_HEADER


def _entry(name, dance="LW", artist="Someone"):
    return types.SimpleNamespace(path=Path(rf"F:\music\{name}.mp3"), title=name,
                                 tag_artist=artist, dance=dance, other_genre="")


class _Wishlist:
    """A wishlist table as far as the inbox uses it: skips a title it holds."""

    def __init__(self):
        self.entries = []

    def rowCount(self):
        return len(self.entries)

    def _append_entry(self, entry):
        if entry not in self.entries:
            self.entries.append(entry)


class _Window(GuestMixin, QMainWindow):
    def __init__(self, entries):
        super().__init__()
        self._settings = {"guest_port": 0}
        self._library = cast(Any, types.SimpleNamespace(
            lib=types.SimpleNamespace(entries=entries)))
        self.wishlist = _Wishlist()
        self._deckset = cast(Any, types.SimpleNamespace(wishlists=[self.wishlist]))

    def _presenter_state(self):
        return "Slow Waltz", "Moon River", ("", "", False, 0.0), [], ("", "")

    def _presenter_upcoming(self, count):
        return [("Tango", "Hernando's Hideaway"), ("Samba", "Senorita")][:count]


class GuestDeskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.moon = _entry("Moon River")
        self.samba = _entry("Senorita", dance="SA")
        self.win = _Window([self.moon, self.samba])
        self.addCleanup(self.win.deleteLater)
        self.desk = self.win.guest_desk()
        self.addCleanup(self.win._guest_shutdown)

    def _start(self):
        real = main_guest.gs.GuestServer
        # Loopback only: binding every interface from a test run would raise
        # the Windows firewall prompt.
        local = lambda *a, **k: real(*a, **{**k, "host": "127.0.0.1"})  # noqa: E731
        with mock.patch.object(main_guest.gs, "GuestServer", side_effect=local):
            self.desk.set_running(True)
        self.assertIsNotNone(self.desk.server)

    def _server(self):
        srv = self.desk.server
        if srv is None:
            self.fail("the guest server is not running")
        return srv

    def _post(self, body):
        srv = self._server()
        conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
        conn.request("POST", "/api/request", body=json.dumps(body),
                     headers={GUEST_CODE_HEADER: srv.code, "Content-Type": "application/json"})
        status = conn.getresponse().status
        conn.close()
        return status

    def _wait_for_inbox(self, n):
        loop = QEventLoop()
        QTimer.singleShot(2000, loop.quit)
        self.desk.changed.connect(lambda: len(self.desk.inbox) >= n and loop.quit())
        if len(self.desk.inbox) < n:
            loop.exec()

    def test_the_same_file_keeps_its_id(self):
        self.assertEqual(song_id(self.moon), song_id(_entry("Moon River", dance="TG")))
        self.assertNotEqual(song_id(self.moon), song_id(self.samba))
        self.assertEqual(len(song_id(self.moon)), 10)

    def test_guests_get_the_library_and_what_is_playing(self):
        self._start()
        rows = json.loads(self._server().catalog_json())["songs"]
        self.assertIn([song_id(self.samba), "Senorita", "Someone", dance_name("SA", "SA")], rows)
        self.assertEqual(self._server().now(), {
            "dance": "Slow Waltz", "title": "Moon River",
            "next": [["Tango", "Hernando's Hideaway"], ["Samba", "Senorita"]]})
        st = self.desk.status()
        self.assertTrue(st["running"])
        self.assertEqual(st["code"], self._server().code)

    def test_a_request_lands_in_the_inbox_and_counts_up(self):
        self._start()
        self.assertEqual(self._post({"song": song_id(self.moon)}), 204)
        self.assertEqual(self._post({"text": "Dancing Queen"}), 204)
        self._wait_for_inbox(2)
        self.assertEqual(self._post({"song": song_id(self.moon)}), 204)
        self.assertEqual(self._post({"text": "dancing queen"}), 204)
        loop = QEventLoop()
        QTimer.singleShot(2000, loop.quit)
        self.desk.changed.connect(
            lambda: sum(i["count"] for i in self.desk.inbox) >= 4 and loop.quit())
        if sum(i["count"] for i in self.desk.inbox) < 4:
            loop.exec()
        self.assertEqual([(i.get("entry"), i.get("text"), i["count"]) for i in self.desk.inbox],
                         [(self.moon, None, 2), (None, "Dancing Queen", 2)])
        self.app.processEvents()
        self.assertTrue(any(song_label(self.moon) in line for line in self.desk.log),
                        list(self.desk.log))

    def test_taking_puts_the_title_on_the_wishlist(self):
        self.desk._catalog()
        self.desk._on_arrived({"song": song_id(self.moon)})
        self.desk._on_arrived({"text": "Something Latin"})
        self.assertTrue(self.desk.take(self.desk.inbox[0]))
        self.assertEqual(self.win.wishlist.entries, [self.moon])
        self.assertEqual([i.get("text") for i in self.desk.inbox], ["Something Latin"])
        self.assertFalse(self.desk.take(self.desk.inbox[0]))   # words: nothing to take
        self.desk.drop(self.desk.inbox[0])
        self.assertEqual(self.desk.inbox, [])

    def test_a_title_on_the_wishlist_already_is_not_added_twice(self):
        self.desk._catalog()
        self.win.wishlist.entries.append(self.moon)
        self.desk._on_arrived({"song": song_id(self.moon)})
        self.assertFalse(self.desk.take(self.desk.inbox[0]))
        self.assertEqual(self.win.wishlist.entries, [self.moon])
        self.assertEqual(self.desk.inbox, [])

    def test_unknown_titles_are_ignored(self):
        self.desk._catalog()
        self.desk._on_arrived({"song": "nothere"})
        self.assertEqual(self.desk.inbox, [])

    def test_the_badge_counts_what_waits_and_opens_the_window(self):
        self._start()
        badge = self.desk._badge
        if badge is None:
            self.fail("no badge")
        self.assertFalse(badge.isHidden())
        self.assertEqual(badge.text(), "📨")
        self.desk._on_arrived({"song": song_id(self.moon)})
        self.desk._on_arrived({"song": song_id(self.moon)})
        self.assertEqual(badge.text(), "📨 2")
        with mock.patch.object(self.win, "open_guest_window") as opened:
            badge.click()
        opened.assert_called_once_with()
        self.desk.set_running(False)
        self.assertFalse(badge.isHidden())       # requests still wait
        self.desk.drop(self.desk.inbox[0])
        self.assertTrue(badge.isHidden())

    def test_a_new_request_flashes_the_badge_and_says_what_came(self):
        self._start()
        badge = self.desk._badge
        if badge is None:
            self.fail("no badge")
        calm = badge.styleSheet()
        with mock.patch.object(main_guest, "show_toast") as toast:
            self.desk._on_arrived({"song": song_id(self.moon)})
            self.desk._on_arrived({"text": "Dancing Queen"})
        self.assertEqual([c.args[1] for c in toast.call_args_list],
                         ["📨 Guest request: " + song_label(self.moon),
                          "📨 Guest wish: Dancing Queen"])
        self.assertTrue(self.desk._flash.isActive())
        self.desk._flash.timeout.emit()
        lit = badge.styleSheet()
        self.desk._flash.timeout.emit()
        self.assertNotEqual(lit, badge.styleSheet())
        self.win.open_guest_window()             # seen: the badge calms down
        self.assertFalse(self.desk._flash.isActive())
        self.assertEqual(badge.styleSheet(), calm)

    def test_nothing_flashes_while_the_inbox_is_open(self):
        self._start()
        dlg = self.win.open_guest_window()
        self.addCleanup(dlg.close)
        with mock.patch.object(main_guest, "show_toast") as toast:
            self.desk._on_arrived({"song": song_id(self.moon)})
        toast.assert_not_called()
        self.assertFalse(self.desk._flash.isActive())

    def test_a_wish_is_shown_as_the_text_it_is(self):
        """R6: the toast label took a guest's '<b>' or '<img>' as markup."""
        self._start()
        self.desk._on_arrived({"text": '<b>big</b> <img src="x.png">'})
        lbl = getattr(self.win, "_toast_lbl")
        self.assertEqual(lbl.textFormat(), Qt.TextFormat.PlainText)
        self.assertIn('<b>big</b> <img src="x.png">', lbl.text())

    def test_stop_closes_the_server(self):
        self._start()
        srv = self._server()
        self.desk.set_running(False)
        self.assertIsNone(self.desk.server)
        self.assertFalse(srv.running)
        self.assertFalse(self.desk.status()["running"])

    def test_a_new_code_reaches_the_server(self):
        self._start()
        old = self._server().code
        self.desk.new_code()
        self.assertNotEqual(self._server().code, old)

    def test_a_taken_port_is_reported_not_raised(self):
        self._start()
        self.win._settings["guest_port"] = self._server().port
        other = GuestDesk(self.win)
        real = main_guest.gs.GuestServer
        local = lambda *a, **k: real(*a, **{**k, "host": "127.0.0.1"})  # noqa: E731
        with mock.patch.object(main_guest.gs, "GuestServer", side_effect=local):
            other.set_running(True)
        self.assertIsNone(other.server)
        self.assertIn("⚠", other.log[-1])


class GuestDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.moon = _entry("Moon River")
        self.win = _Window([self.moon])
        self.addCleanup(self.win.deleteLater)
        self.desk = self.win.guest_desk()
        self.desk._catalog()
        self.dlg = GuestDialog(self.desk)
        self.addCleanup(self.dlg.deleteLater)

    def test_a_requested_title_reads_dance_artist_and_title(self):
        """Marcel: "show me for find title in the inbox more information artist
        and title and dance" — the guest picked it by all three."""
        self.assertEqual(song_label(self.moon), f"{dance_name('LW')} — Someone – Moon River")
        self.assertEqual(song_label(_entry("Moon River", artist="")),
                         f"{dance_name('LW')} — Moon River")

    def test_the_qr_code_holds_the_event_code(self):
        self.assertEqual(guest_qr_url("http://192.168.1.20:8766", "ABC234"),
                         "http://192.168.1.20:8766/#e=ABC234")

    def test_rows_read_when_what_and_how_often(self):
        self.desk._on_arrived({"song": song_id(self.moon)})
        self.desk._on_arrived({"song": song_id(self.moon)})
        self.desk._on_arrived({"text": "Dancing Queen"})
        items = self.desk.inbox
        self.assertEqual(inbox_row(items[0]), f"{items[0]['at']}  {song_label(self.moon)}  ×2")
        self.assertEqual(inbox_row(items[1]), f"{items[1]['at']}  💬 Dancing Queen")
        self.assertEqual(self.dlg._inbox.count(), 2)

    def test_only_titles_go_to_the_wishlist(self):
        self.desk._on_arrived({"song": song_id(self.moon)})
        self.desk._on_arrived({"text": "Dancing Queen"})
        self.dlg._inbox.setCurrentRow(1)
        self.assertFalse(self.dlg._take_btn.isEnabled())
        self.assertTrue(self.dlg._drop_btn.isEnabled())
        self.dlg._inbox.setCurrentRow(0)
        self.assertTrue(self.dlg._take_btn.isEnabled())
        self.dlg._take_btn.click()
        self.assertEqual(self.win.wishlist.entries, [self.moon])
        self.assertEqual(self.dlg._inbox.count(), 1)
        self.dlg._inbox.setCurrentRow(0)
        self.dlg._drop_btn.click()
        self.assertEqual(self.dlg._inbox.count(), 0)
        self.assertFalse(self.dlg._drop_btn.isEnabled())

    def test_closed_shows_no_code(self):
        self.assertFalse(self.dlg._new_code_btn.isEnabled())
        self.assertIn("—", self.dlg._code.text())


class _FakeTunnel:
    """A Tunnel without cloudflared: the test plays its address and its end."""

    def __init__(self, binary, port, on_url, on_line=None, on_exit=None):
        self.port = port
        self.on_url = on_url
        self.on_exit = on_exit
        self.stopped = False

    def start(self):
        pass

    def stop(self):
        self.stopped = True


class GuestTunnelTest(unittest.TestCase):
    """🌐 Tunnel mode: the public address first, gone again when cloudflared ends."""

    URL = "https://moon-river-tango-waltz.trycloudflare.com"

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.moon = _entry("Moon River")
        self.win = _Window([self.moon])
        self.addCleanup(self.win.deleteLater)
        self.desk = self.win.guest_desk()
        self.addCleanup(self.win._guest_shutdown)
        self.tunnels = []

        def make(*a, **k):
            t = _FakeTunnel(*a, **k)
            self.tunnels.append(t)
            return t
        real = main_guest.gs.GuestServer
        local = lambda *a, **k: real(*a, **{**k, "host": "127.0.0.1"})  # noqa: E731
        for patch in (mock.patch.object(main_guest.gs, "GuestServer", side_effect=local),
                      mock.patch.object(main_guest.tn, "Tunnel", side_effect=make),
                      mock.patch.object(main_guest.tn, "find_cloudflared",
                                        return_value=Path("cloudflared.exe"))):
            patch.start()
            self.addCleanup(patch.stop)
        saving = mock.patch.object(main_guest, "save_settings")
        self.saved = saving.start()
        self.addCleanup(saving.stop)

    def _open_in_tunnel_mode(self):
        self.win._settings["guest_mode"] = "tunnel"
        self.desk.set_running(True)
        self.assertEqual(len(self.tunnels), 1)
        return self.tunnels[0]

    def test_wifi_mode_starts_no_tunnel(self):
        self.desk.set_running(True)
        self.assertEqual(self.tunnels, [])
        self.assertEqual(self.desk.status()["mode"], "wifi")

    def test_a_saved_relay_mode_falls_back_to_wifi(self):
        """Marcel: "remove that option. so only give wifi or cloudflare tunnel"
        — a setting saved by an older version still opens, on the Wi-Fi."""
        self.win._settings["guest_mode"] = "relay"
        self.desk.set_running(True)
        self.assertEqual(self.tunnels, [])
        self.assertEqual(self.desk.status()["mode"], "wifi")
        dlg = GuestDialog(self.desk)
        self.addCleanup(dlg.deleteLater)
        self.assertEqual([dlg._mode.itemData(i) for i in range(dlg._mode.count())],
                         ["wifi", "tunnel"])

    def test_the_public_address_comes_first(self):
        t = self._open_in_tunnel_mode()
        self.assertEqual(t.port, self.desk.status()["port"])
        self.assertTrue(self.desk.status()["waiting"])
        self.assertEqual(self.desk.server.tunnel_host, "")
        t.on_url(self.URL)
        self.assertEqual(self.desk.server.tunnel_host,
                         "moon-river-tango-waltz.trycloudflare.com")
        st = self.desk.status()
        self.assertFalse(st["waiting"])
        self.assertEqual(st["public"], self.URL)
        self.assertEqual(st["urls"][0], self.URL)
        self.assertIn(self.URL, self.desk.log[-1])

    def test_an_ended_tunnel_takes_its_address_along(self):
        t = self._open_in_tunnel_mode()
        t.on_url(self.URL)
        t.on_exit(1)
        self.assertEqual(self.desk.server.tunnel_host, "")
        st = self.desk.status()
        self.assertTrue(st["running"])          # the Wi-Fi way stays open
        self.assertEqual(st["public"], "")
        self.assertNotIn(self.URL, st["urls"])
        self.assertIn("⚠", self.desk.log[-1])

    def test_a_stopped_tunnel_is_not_heard_any_more(self):
        t = self._open_in_tunnel_mode()
        self.desk.set_running(False)
        self.assertTrue(t.stopped)
        t.on_url(self.URL)
        t.on_exit(1)
        self.assertEqual(self.desk.public_url, "")
        self.assertNotIn("⚠", self.desk.log[-1])

    def test_no_cloudflared_leaves_the_wifi_way_open(self):
        self.win._settings["guest_mode"] = "tunnel"
        with mock.patch.object(main_guest.tn, "find_cloudflared", return_value=None):
            self.desk.set_running(True)
        self.assertTrue(self.desk.status()["running"])
        self.assertEqual(self.tunnels, [])
        self.assertIn("cloudflared", self.desk.log[-1])

    def test_a_tunnel_that_cannot_start_is_reported(self):
        self.win._settings["guest_mode"] = "tunnel"
        with mock.patch.object(_FakeTunnel, "start", side_effect=OSError("access denied")):
            self.desk.set_running(True)
        self.assertIsNone(self.desk.tunnel)
        self.assertIn("access denied", self.desk.log[-1])

    def test_a_new_mode_is_saved_and_restarts_the_server(self):
        self.desk.set_running(True)
        before = self.desk.server
        self.desk.set_mode("tunnel")
        self.assertEqual(self.win._settings["guest_mode"], "tunnel")
        self.saved.assert_called_once_with(self.win._settings)
        self.assertIsNotNone(self.desk.server)
        self.assertIsNot(self.desk.server, before)
        self.assertEqual(len(self.tunnels), 1)
        self.desk.set_mode("bogus")
        self.assertEqual(self.desk.mode(), "tunnel")

    def test_the_window_picks_the_mode_and_shows_the_public_address(self):
        dlg = GuestDialog(self.desk)
        self.addCleanup(dlg.deleteLater)
        self.assertEqual(dlg._mode.currentData(), "wifi")
        dlg._mode.setCurrentIndex(dlg._mode.findData("tunnel"))
        self.assertEqual(self.win._settings["guest_mode"], "tunnel")
        self.assertIn("mobile data", dlg._hint.text())
        dlg._toggle_btn.click()
        self.assertIn("Cloudflare", dlg._status.text())
        self.tunnels[0].on_url(self.URL)
        self.assertEqual(dlg._addr.currentText(), self.URL)
        self.assertNotIn("Cloudflare", dlg._status.text())

    def test_no_code_while_the_tunnel_connects(self):
        """Marcel: "if i switch the connection method with the server running the
        qr code is lazily replaced, it should show that we are reconnecting so
        the user doesn't copy a wrong qr code"."""
        self.win._settings["guest_mode"] = "tunnel"
        dlg = GuestDialog(self.desk)
        self.addCleanup(dlg.deleteLater)
        dlg._toggle_btn.click()
        self.assertTrue(dlg._qr.pixmap().isNull())
        self.assertIn("Connecting", dlg._qr.text())
        self.tunnels[0].on_url(self.URL)
        self.assertFalse(dlg._qr.pixmap().isNull())
        self.assertIn(self.URL, dlg._link.text())

    def test_switching_the_way_hides_the_old_code_at_once(self):
        dlg = GuestDialog(self.desk)
        self.addCleanup(dlg.deleteLater)
        dlg._toggle_btn.click()
        self.assertFalse(dlg._qr.pixmap().isNull())
        dlg._mode.setCurrentIndex(dlg._mode.findData("tunnel"))
        self.assertTrue(dlg._qr.pixmap().isNull())
        self.assertIn("Connecting", dlg._qr.text())

    def _toggle_without_cloudflared(self, answer):
        self.win._settings["guest_mode"] = "tunnel"
        dlg = GuestDialog(self.desk)
        self.addCleanup(dlg.deleteLater)
        box = remote_dialog.QMessageBox
        with mock.patch.object(main_guest.tn, "find_cloudflared", return_value=None), \
                mock.patch.object(box, "question", return_value=answer) as asked, \
                mock.patch.object(box, "information") as told, \
                mock.patch.object(box, "warning") as warned:
            dlg._toggle_btn.click()
        asked.assert_called_once()
        return told, warned

    def test_without_cloudflared_no_says_where_to_put_it(self):
        told, _warned = self._toggle_without_cloudflared(remote_dialog.QMessageBox.StandardButton.No)
        told.assert_called_once()
        self.assertIn(remote_dialog.CLOUDFLARED_PAGE, told.call_args.args[2])
        self.assertIsNone(self.desk.server)

    def test_without_cloudflared_yes_downloads_then_opens(self):
        fetch = lambda: self.desk.fetch_done.emit(r"C:\data\cloudflared.exe", "")  # noqa: E731
        with mock.patch.object(self.desk, "fetch_cloudflared", side_effect=fetch):
            self._toggle_without_cloudflared(remote_dialog.QMessageBox.StandardButton.Yes)
        self.assertIsNotNone(self.desk.server)

    def test_a_failed_download_is_shown(self):
        fetch = lambda: self.desk.fetch_done.emit("", "connection reset")  # noqa: E731
        box = remote_dialog.QMessageBox
        texts, by_hand = [], remote_dialog._install_by_hand
        with mock.patch.object(self.desk, "fetch_cloudflared", side_effect=fetch),                 mock.patch.object(remote_dialog, "_install_by_hand",
                                  side_effect=lambda e: texts.append(by_hand(e)) or texts[-1]),                 mock.patch.object(box, "exec") as shown:
            self._toggle_without_cloudflared(box.StandardButton.Yes)
        shown.assert_called_once()
        self.assertIn("connection reset", texts[0])
        self.assertIn(remote_dialog.CLOUDFLARED_PAGE, texts[0])
        self.assertIsNone(self.desk.server)


class _FakePresenter:
    """The presenter screen as far as the guests use it: the code it shows."""

    def __init__(self):
        self.shown = []

    def set_guest_qr(self, modules):
        self.shown.append(modules)


class GuestPresenterQrTest(unittest.TestCase):
    """🖥 The code on the presenter screen, for as long as guests can ask."""

    URL = GuestTunnelTest.URL
    # Set by GuestTunnelTest.setUp, borrowed for its patches.
    win: Any
    desk: GuestDesk
    tunnels: list
    saved: Any

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        GuestTunnelTest.setUp(cast(Any, self))
        self.screen = _FakePresenter()
        cast(Any, self.win)._presenter = self.screen

    def _code(self):
        srv = self.desk.server
        return srv.code if srv is not None else ""

    def test_closed_shows_no_code(self):
        self.assertEqual(self.desk.presenter_link(), "")

    def test_open_shows_the_page_with_its_event_code(self):
        self.desk.set_running(True)
        link = self.desk.presenter_link()
        self.assertEqual(link, guest_qr_url(self.desk.status()["urls"][0], self._code()))
        self.assertIsNotNone(self.screen.shown[-1])
        self.desk.new_code()
        self.assertTrue(self.desk.presenter_link().endswith(self._code()))
        self.desk.set_running(False)
        self.assertIsNone(self.screen.shown[-1])

    def test_no_code_on_the_screen_while_connecting(self):
        self.win._settings["guest_mode"] = "tunnel"
        self.desk.set_running(True)
        self.assertEqual(self.desk.presenter_link(), "")
        self.assertIsNone(self.screen.shown[-1])
        self.tunnels[0].on_url(self.URL)
        self.assertEqual(self.desk.presenter_link(), guest_qr_url(self.URL, self._code()))
        self.assertIsNotNone(self.screen.shown[-1])

    def test_the_public_address_takes_over_when_it_arrives(self):
        self.win._settings["guest_mode"] = "tunnel"
        self.desk.set_running(True)
        self.desk.pick_address(self.desk.status()["urls"][0])   # a LAN one, picked before
        self.tunnels[0].on_url(self.URL)
        self.assertEqual(self.desk.presenter_link(), guest_qr_url(self.URL, self._code()))

    def test_the_address_picked_in_the_window_is_the_one_shown(self):
        self.desk.set_running(True)
        dlg = GuestDialog(self.desk)
        self.addCleanup(dlg.deleteLater)
        dlg._addr.addItem("http://10.0.0.7:8766")
        dlg._addr.setCurrentIndex(dlg._addr.count() - 1)
        self.desk.status = lambda: {**GuestDesk.status(self.desk),
                                    "urls": ["http://192.168.1.20:8766", "http://10.0.0.7:8766"]}
        dlg._show_code()
        self.assertEqual(self.desk.presenter_link(),
                         guest_qr_url("http://10.0.0.7:8766", self._code()))

    def test_the_window_switches_it_off_and_on(self):
        self.desk.set_running(True)
        dlg = GuestDialog(self.desk)
        self.addCleanup(dlg.deleteLater)
        self.assertTrue(dlg._on_presenter.isChecked())
        dlg._on_presenter.click()
        self.assertFalse(self.win._settings["guest_qr_presenter"])
        self.assertEqual(self.desk.presenter_link(), "")
        self.assertIsNone(self.screen.shown[-1])
        self.saved.assert_called()
        dlg._on_presenter.click()
        self.assertIsNotNone(self.screen.shown[-1])

    def test_no_presenter_screen_is_no_trouble(self):
        cast(Any, self.win)._presenter = None
        self.desk.set_running(True)
        self.desk.sync_presenter()


if __name__ == "__main__":
    unittest.main()
