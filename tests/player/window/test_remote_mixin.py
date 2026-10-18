"""📱 Phone remote, desk side: what the phone sees, and what its buttons do."""
import http.client
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from player.window import main_remote
from player.window.main_remote import RemoteMixin
from shared.remote import remote_server as rs


def _host(pads=None, page=0, live=()):
    host = mock.Mock()
    host._presenter_state.return_value = (
        "Slow Waltz", "Moon", ("▶  01:39", "−  00:38", False, 0.7),
        [("Tango", "Tango One")], ("", ""))
    host._is_player_stopped.return_value = False
    wall = mock.Mock()
    wall.current_page.return_value = page
    wall.pages.return_value = [pc.Page(name="Main", pads=pads or {})]
    host._cartwall = wall
    host._cart_voices.is_playing.side_effect = lambda key: key in live
    host._remote_pad_keys = []
    return host


class StateTest(unittest.TestCase):
    def test_state_carries_the_now_the_next_and_the_pads_in_wall_order(self):
        pads = {(1, 0): pc.CartPad(path=r"C:\s\Horn.mp3", colour="#aa0000"),
                (0, 1): pc.CartPad(path=r"C:\s\Applause.mp3", label="Clap")}
        host = _host(pads, live={(0, 1, 0)})
        s = RemoteMixin._remote_state(host)
        self.assertEqual(s["dance"], "Slow Waltz")
        self.assertEqual(s["title"], "Moon")
        self.assertEqual(s["played"], "▶  01:39")
        self.assertEqual(s["left"], "−  00:38")
        self.assertAlmostEqual(s["fraction"], 0.7)
        self.assertEqual(s["next"], [["Tango", "Tango One"]])
        self.assertTrue(s["playing"])
        self.assertEqual([p["label"] for p in s["pads"]], ["Clap", "Horn"])
        self.assertEqual([p["live"] for p in s["pads"]], [False, True])
        self.assertEqual(s["pads"][1]["colour"], "#aa0000")
        self.assertEqual(host._remote_pad_keys, [(0, 0, 1), (0, 1, 0)])

    def test_state_says_whether_the_next_dance_is_announced(self):
        host = _host()
        host._play_panel.announce_next.return_value = True
        self.assertTrue(RemoteMixin._remote_state(host)["announce"])
        host._play_panel.announce_next.return_value = False
        self.assertFalse(RemoteMixin._remote_state(host)["announce"])

    def test_no_wall_no_pads(self):
        host = _host()
        host._cartwall = None
        self.assertEqual(RemoteMixin._remote_state(host)["pads"], [])


class CommandTest(unittest.TestCase):
    def test_each_button_reaches_its_desk_action(self):
        host = _host()
        host._remote_pad_keys = [(0, 0, 0), (0, 0, 1)]
        for cmd, arg in (("toggle", None), ("next", None), ("prev", None),
                         ("fade", None), ("hold", None), ("stop_pads", None),
                         ("pad", 1), ("pad", 9)):
            RemoteMixin._on_remote_command(host, cmd, arg)
        host._presenter_play_pause.assert_called_once()
        host._on_player_next.assert_called_once()
        host._preview_skip.assert_called_once_with(-1)
        host._fade_out_now.assert_called_once()
        host._fade_and_hold.assert_called_once()
        host._on_cart_stop_all.assert_called_once()
        # A pad number from a stale page is ignored, not mapped elsewhere.
        host._cartwall.play_pad.assert_called_once_with((0, 0, 1))

    def test_a_tapped_next_title_is_played(self):
        host = _host()
        RemoteMixin._on_remote_command(host, "jump", (1, "Tango One"))
        host._play_upcoming.assert_called_once_with(1, "Tango One")

    def test_seek_moves_the_playhead_to_that_point_of_the_bar(self):
        host = _host()
        RemoteMixin._on_remote_command(host, "seek", 0.25)
        host._seek_fraction.assert_called_once_with(0.25)

    def test_announce_flips_the_play_panels_toggle(self):
        """🔈 The same switch as the desk's, so it is remembered the same way."""
        host = _host()
        chk = host._play_panel.announce_check
        chk.isChecked.return_value = False
        RemoteMixin._on_remote_command(host, "announce", None)
        chk.setChecked.assert_called_once_with(True)
        chk.isChecked.return_value = True
        RemoteMixin._on_remote_command(host, "announce", None)
        chk.setChecked.assert_called_with(False)


class JumpTest(unittest.TestCase):
    """📱 The phone asked "play it now?" and got a yes: the tapped place in
    the "next" list is found on the desk again, by name."""

    def host(self):
        host = _host()
        self.table = mock.Mock()
        host._upcoming_rows.return_value = [
            (self.table, 4, Path("C:/m/Tango One.mp3")),
            (self.table, 5, Path("C:/m/Tango Two.mp3"))]
        return host

    def test_it_fades_into_the_tapped_title(self):
        host = self.host()
        host._crossfade_jump.return_value = True
        RemoteMixin._play_upcoming(host, 1, "Tango Two")
        host._upcoming_rows.assert_called_once_with(2)
        host._crossfade_jump.assert_called_once_with(
            self.table, 5, Path("C:/m/Tango Two.mp3"))
        self.table._on_play_click.assert_not_called()

    def test_where_nothing_fades_it_starts_like_a_click_on_its_play(self):
        """Stopped, or in the pause between dances."""
        host = self.host()
        host._crossfade_jump.return_value = False
        RemoteMixin._play_upcoming(host, 0, "Tango One")
        self.table._on_play_click.assert_called_once_with(
            4, Path("C:/m/Tango One.mp3"))
        self.table.scroll_row_into_play_view.assert_called_once_with(4)
        host._announcer.stop.assert_called_once()

    def test_a_list_that_moved_on_starts_nothing(self):
        host = self.host()
        for idx, title in ((1, "Tango One"), (2, "Tango Three"), (-1, "Tango One")):
            RemoteMixin._play_upcoming(host, idx, title)
        host._crossfade_jump.assert_not_called()
        self.table._on_play_click.assert_not_called()


class SwitchTest(unittest.TestCase):
    """🔀 Crossfade and ⏭ Auto / ✋ Manual from the phone: the play panel's
    own switches, flipped as a click on the desk flips them."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def host(self, **settings):
        from player.widgets.play_mode_panel import PlayModePanel
        from tests.qt_test_support import reap_widget
        host = _host()
        host._play_panel = PlayModePanel(settings)
        self.addCleanup(reap_widget, host._play_panel)
        return host

    def test_state_says_crossfade_and_auto(self):
        s = RemoteMixin._remote_state(self.host(auto_advance=True, xfade_on=True))
        self.assertIs(s["advance"], True)
        self.assertIs(s["xfade"], True)
        s = RemoteMixin._remote_state(self.host(auto_advance=True, xfade_on=False))
        self.assertIs(s["xfade"], False)

    def test_no_crossfade_where_titles_cannot_cross(self):
        """✋ Manual or a pause between songs: the desk takes the row off
        the panel, so the phone shows no button for it either."""
        manual = self.host(auto_advance=False, xfade_on=True)
        self.assertIs(RemoteMixin._remote_state(manual)["advance"], False)
        self.assertIsNone(RemoteMixin._remote_state(manual)["xfade"])
        pausing = self.host(auto_advance=True, pause_enabled=True, xfade_on=True)
        self.assertIsNone(RemoteMixin._remote_state(pausing)["xfade"])

    def test_the_phone_flips_the_crossfade(self):
        host = self.host(auto_advance=True, xfade_on=False)
        RemoteMixin._on_remote_command(host, "xfade", None)
        self.assertTrue(host._play_panel.xfade_on())
        RemoteMixin._on_remote_command(host, "xfade", None)
        self.assertFalse(host._play_panel.xfade_on())

    def test_manual_from_the_phone_is_manual_from_the_desk(self):
        """✋ silences the announcement as the desk's click does, and ⏭
        brings it back."""
        host = self.host(auto_advance=True, announce_next=True)
        panel = host._play_panel
        RemoteMixin._on_remote_command(host, "advance", None)
        self.assertFalse(panel.auto_advance())
        self.assertFalse(panel.announce_check.isChecked())
        RemoteMixin._on_remote_command(host, "advance", None)
        self.assertTrue(panel.auto_advance())
        self.assertTrue(panel.announce_check.isChecked())


class LiveServerTest(unittest.TestCase):
    """The whole way: the phone's POST lands on the GUI thread."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_remote_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        env = mock.patch.dict(os.environ, {"DANCEPLAYLIST_STATE_DIR": str(self.dir)})
        env.start()
        self.addCleanup(env.stop)

    def test_start_publish_command_stop(self):
        host = _host()
        host._remote = None
        host._remote_timer = None
        host._settings = {"remote_port": 0}
        host._remote_wanted = True
        host._on_remote_command = mock.Mock()
        host._remote_bridge = None
        for name in ("_start_remote", "_stop_remote", "_publish_remote", "_remote_state",
                     "remote_hub", "remote_log", "_on_remote_event", "remote_mode",
                     "_remote_pin_digits"):
            setattr(host, name, getattr(RemoteMixin, name).__get__(host))
        real = rs.RemoteServer
        # Loopback only: binding every interface from a test run would raise
        # the Windows firewall prompt.
        local = lambda *a, **k: real(*a, **{**k, "host": "127.0.0.1"})  # noqa: E731
        with mock.patch.object(main_remote, "save_settings") as saved, \
                mock.patch.object(main_remote.rs, "RemoteServer", side_effect=local):
            RemoteMixin._apply_remote(host)
        self.addCleanup(lambda: host._remote and host._remote.stop())
        srv = host._remote
        self.assertIsNotNone(srv)
        port = srv.port
        pin = host._settings["remote_pin"]
        self.assertEqual(len(pin), 4)
        saved.assert_called()
        srv.publish({"title": "Moon"})

        conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
        conn.request("POST", "/api/cmd", body=json.dumps({"cmd": "next"}),
                     headers={rs.PIN_HEADER: pin, "Content-Type": "application/json"})
        self.assertEqual(conn.getresponse().status, 204)
        conn.close()
        loop = QEventLoop()
        QTimer.singleShot(2000, loop.quit)
        host._on_remote_command.side_effect = lambda *a: loop.quit()
        if not host._on_remote_command.called:
            loop.exec()
        host._on_remote_command.assert_called_once_with("next", None)

        host._remote_wanted = False
        RemoteMixin._apply_remote(host)
        self.assertIsNone(host._remote)
        self.assertFalse(srv.running)
        # The 📱 window's log: started, the command, stopped — in that order.
        self.app.processEvents()
        log = host.remote_log()
        self.assertIn(f"Server started on port {port}", log[0])
        self.assertTrue(any("127.0.0.1 → next" in x for x in log), log)
        self.assertIn("Server stopped", log[-1])


class WindowSwitchTest(unittest.TestCase):
    """The 📱 window's Start / Stop and New PIN, without a server."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _host(self, settings):
        host = mock.Mock()
        host._settings = settings
        host._remote = None
        host._remote_bridge = None
        for name in ("remote_hub", "remote_log", "_on_remote_event", "set_remote_running",
                     "new_remote_pin", "remote_status", "remote_mode", "_remote_pin_digits"):
            setattr(host, name, getattr(RemoteMixin, name).__get__(host))
        return host

    def test_start_stop_lives_only_as_long_as_the_app(self):
        # Marcel: "it is nothing we remember in session state persisted to json".
        host = self._host({})
        with mock.patch.object(main_remote, "save_settings") as saved:
            host.set_remote_running(True)
        self.assertTrue(host._remote_wanted)
        self.assertNotIn("phone_remote", host._settings)
        saved.assert_not_called()
        host._apply_remote.assert_called_once_with()

    def test_a_new_pin_reaches_the_running_server_and_the_window(self):
        host = self._host({"remote_pin": "1111"})
        host._remote = mock.Mock(port=8765)
        changed = mock.Mock()
        host.remote_hub().changed.connect(changed)
        with mock.patch.object(main_remote, "save_settings"):
            host.new_remote_pin()
        pin = host._settings["remote_pin"]
        host._remote.set_pin.assert_called_once_with(pin)
        changed.assert_called_once()
        with mock.patch.object(main_remote.rs, "lan_addresses", return_value=["10.0.0.5"]):
            st = host.remote_status()
        self.assertEqual(st, {"running": True, "port": 8765, "pin": pin,
                              "mode": "wifi", "public": "", "waiting": False,
                              "urls": ["http://10.0.0.5:8765"]})

    def test_the_qr_address_carries_the_pin_after_the_hash(self):
        self.assertEqual(main_remote.qr_url("http://10.0.0.5:8765", "0420"),
                         "http://10.0.0.5:8765/#pin=0420")


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


class TunnelTest(unittest.TestCase):
    """🌐 The remote away from the Wi-Fi: the tunnel's address first, an
    8-digit PIN, and the tunnel goes with the server."""

    URL = "https://moon-river-tango-waltz.trycloudflare.com"

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        host = _host()
        host._remote = None
        host._remote_timer = None
        host._remote_bridge = None
        host._remote_wanted = True
        host._settings = {"remote_port": 0, "remote_pin": "4711", "remote_mode": "tunnel"}
        for name in ("_start_remote", "_stop_remote", "_publish_remote", "_remote_state",
                     "remote_hub", "remote_log", "_on_remote_event", "remote_mode",
                     "_remote_pin_digits", "_start_remote_tunnel", "_on_remote_tunnel_url",
                     "_on_remote_tunnel_ended", "remote_status", "set_remote_mode",
                     "_apply_remote", "new_remote_pin"):
            setattr(host, name, getattr(RemoteMixin, name).__get__(host))
        self.host = host
        self.tunnels = []

        def make(*a, **k):
            t = _FakeTunnel(*a, **k)
            self.tunnels.append(t)
            return t
        real = rs.RemoteServer
        local = lambda *a, **k: real(*a, **{**k, "host": "127.0.0.1"})  # noqa: E731
        for patch in (mock.patch.object(main_remote.rs, "RemoteServer", side_effect=local),
                      mock.patch.object(main_remote.tn, "Tunnel", side_effect=make),
                      mock.patch.object(main_remote.tn, "find_cloudflared",
                                        return_value=Path("cloudflared.exe")),
                      mock.patch.object(main_remote.rs, "lan_addresses",
                                        return_value=["10.0.0.5"])):
            patch.start()
            self.addCleanup(patch.stop)
        saving = mock.patch.object(main_remote, "save_settings")
        self.saved = saving.start()
        self.addCleanup(saving.stop)
        self.addCleanup(lambda: host._remote and host._stop_remote())

    def test_the_tunnel_leads_to_the_server_and_its_address_comes_first(self):
        self.host._apply_remote()
        self.assertEqual(len(self.tunnels), 1)
        tunnel = self.tunnels[0]
        self.assertEqual(tunnel.port, self.host._remote.port)
        st = self.host.remote_status()
        self.assertTrue(st["waiting"])
        tunnel.on_url(self.URL)
        self.app.processEvents()
        st = self.host.remote_status()
        self.assertFalse(st["waiting"])
        self.assertEqual(st["urls"][0], self.URL)
        self.assertIn(f"Public address: {self.URL}", self.host.remote_log()[-1])

    def test_a_four_digit_pin_grows_to_eight_on_the_internet(self):
        self.host._apply_remote()
        pin = self.host._settings["remote_pin"]
        self.assertEqual(len(pin), rs.TUNNEL_PIN_DIGITS)
        self.assertTrue(pin.isdigit())
        self.host.new_remote_pin()
        self.assertEqual(len(self.host._settings["remote_pin"]), rs.TUNNEL_PIN_DIGITS)

    def test_stopping_closes_the_tunnel(self):
        self.host._apply_remote()
        tunnel = self.tunnels[0]
        self.host._remote_wanted = False
        self.host._apply_remote()
        self.assertTrue(tunnel.stopped)
        self.assertEqual(self.host.remote_status()["public"], "")

    def test_a_tunnel_that_ends_leaves_the_wifi(self):
        self.host._apply_remote()
        tunnel = self.tunnels[0]
        tunnel.on_url(self.URL)
        tunnel.on_exit(1)
        self.app.processEvents()
        st = self.host.remote_status()
        self.assertEqual(st["urls"], ["http://10.0.0.5:" + str(self.host._remote.port)])
        self.assertIn("Wi-Fi only", self.host.remote_log()[-1])

    def test_a_new_mode_is_saved_and_restarts_the_server(self):
        self.host._settings["remote_mode"] = "wifi"
        self.host._settings["remote_pin"] = "4711"
        self.host._apply_remote()
        self.assertEqual(self.tunnels, [])
        old = self.host._remote
        self.host.set_remote_mode("tunnel")
        self.assertEqual(self.host._settings["remote_mode"], "tunnel")
        self.saved.assert_called()
        self.assertIsNot(self.host._remote, old)
        self.assertFalse(old.running)
        self.assertEqual(len(self.tunnels), 1)

    def test_a_tunnel_requested_through_cloudflare_logs_in_by_its_phone(self):
        self.host._apply_remote()
        pin = self.host._settings["remote_pin"]
        conn = http.client.HTTPConnection("127.0.0.1", self.host._remote.port, timeout=5)
        conn.request("GET", "/api/state", headers={rs.PIN_HEADER: pin,
                                                   "CF-Connecting-IP": "203.0.113.7"})
        self.assertEqual(conn.getresponse().status, 200)
        conn.close()
        loop = QEventLoop()
        QTimer.singleShot(300, loop.quit)
        loop.exec()
        self.assertTrue(any("203.0.113.7 logged in" in x for x in self.host.remote_log()),
                        self.host.remote_log())


if __name__ == "__main__":
    unittest.main()
