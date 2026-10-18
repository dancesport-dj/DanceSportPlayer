"""🌐 The Cloudflare quick tunnel: finding cloudflared, fetching it, reading its address."""
import io
import shutil
import sys
import tarfile
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from shared.remote import tunnel

# What cloudflared prints on the way up, shortened from a real run.
_FAKE = r'''
import sys, time
print("2026-10-17T10:00:00Z INF Requesting new quick Tunnel on trycloudflare.com...", flush=True)
print("2026-10-17T10:00:01Z INF |  https://moon-river-tango-waltz.trycloudflare.com  |", flush=True)
print("2026-10-17T10:00:02Z INF Registered tunnel connection", flush=True)
if sys.argv[1:] == ["exit"]:
    sys.exit(3)
time.sleep(30)
'''


class _Response(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}


class AssetTest(unittest.TestCase):
    def test_each_system_gets_its_release_file(self):
        cases = {("win32", "AMD64"): "cloudflared-windows-amd64.exe",
                 ("win32", "ARM64"): "cloudflared-windows-amd64.exe",
                 ("darwin", "arm64"): "cloudflared-darwin-arm64.tgz",
                 ("darwin", "x86_64"): "cloudflared-darwin-amd64.tgz",
                 ("linux", "x86_64"): "cloudflared-linux-amd64",
                 ("linux", "aarch64"): "cloudflared-linux-arm64",
                 ("linux", "riscv64"): None,
                 ("freebsd14", "amd64"): None}
        for (plat, machine), want in cases.items():
            self.assertEqual(tunnel.asset_name(plat, machine), want, (plat, machine))

    def test_the_binary_name(self):
        self.assertEqual(tunnel.binary_name("win32"), "cloudflared.exe")
        self.assertEqual(tunnel.binary_name("darwin"), "cloudflared")


class FindTest(unittest.TestCase):
    def setUp(self):
        self.dirs = (Path(tempfile.mkdtemp(prefix="dp_cf_a_")),
                     Path(tempfile.mkdtemp(prefix="dp_cf_b_")))
        for d in self.dirs:
            self.addCleanup(shutil.rmtree, d, ignore_errors=True)

    def test_next_to_the_app_first_then_the_data_folder_then_the_path(self):
        with mock.patch.object(tunnel.shutil, "which", return_value=r"C:\bin\cloudflared.exe"):
            self.assertEqual(tunnel.find_cloudflared(self.dirs), Path(r"C:\bin\cloudflared.exe"))
            (self.dirs[1] / tunnel.binary_name()).write_bytes(b"x")
            self.assertEqual(tunnel.find_cloudflared(self.dirs),
                             self.dirs[1] / tunnel.binary_name())
            (self.dirs[0] / tunnel.binary_name()).write_bytes(b"x")
            self.assertEqual(tunnel.find_cloudflared(self.dirs),
                             self.dirs[0] / tunnel.binary_name())

    def test_nowhere_is_none(self):
        with mock.patch.object(tunnel.shutil, "which", return_value=None), \
                mock.patch.object(tunnel, "_INSTALL_CANDIDATES", ()):
            self.assertIsNone(tunnel.find_cloudflared(self.dirs))

    def test_an_installed_copy_off_the_path_is_found(self):
        # An app started from Finder, or before the installer touched PATH,
        # misses an installed cloudflared on the PATH: the install places count.
        installed = Path(tempfile.mkdtemp(prefix="dp_cf_inst_"))
        self.addCleanup(shutil.rmtree, installed, ignore_errors=True)
        binary = installed / tunnel.binary_name()
        binary.write_bytes(b"x")
        with mock.patch.object(tunnel.shutil, "which", return_value=None), \
                mock.patch.object(tunnel, "_INSTALL_CANDIDATES",
                                  (installed / "missing" / tunnel.binary_name(), binary)):
            self.assertEqual(tunnel.find_cloudflared(self.dirs), binary)

    def test_the_install_places_cover_each_system(self):
        places = {p.as_posix() for p in tunnel._INSTALL_CANDIDATES}
        self.assertIn("/opt/homebrew/bin/cloudflared", places)
        self.assertIn("/usr/local/bin/cloudflared", places)
        self.assertTrue(any(p.endswith("cloudflared/cloudflared.exe") for p in places))


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_cf_dl_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_the_binary_lands_whole_with_progress(self):
        data = b"MZ" + b"\0" * 200_000
        seen, urls = [], []

        def opener(url, timeout):
            urls.append(url)
            return _Response(data)
        with mock.patch.object(tunnel, "asset_name", return_value="cloudflared-windows-amd64.exe"):
            path = tunnel.download(self.dir, lambda d, t: seen.append((d, t)), opener=opener)
        self.assertEqual(urls, [tunnel.DOWNLOAD_BASE + "cloudflared-windows-amd64.exe"])
        self.assertEqual(path, self.dir / tunnel.binary_name())
        self.assertEqual(path.read_bytes(), data)
        self.assertEqual(seen[-1], (len(data), len(data)))
        self.assertGreater(len(seen), 1)
        self.assertEqual([p.name for p in self.dir.iterdir()], [tunnel.binary_name()])

    def test_the_mac_archive_gives_up_its_binary(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tgz:
            info = tarfile.TarInfo("cloudflared")
            info.size = 5
            tgz.addfile(info, io.BytesIO(b"macho"))
        with mock.patch.object(tunnel, "asset_name", return_value="cloudflared-darwin-arm64.tgz"):
            path = tunnel.download(self.dir, opener=lambda url, timeout: _Response(buf.getvalue()))
        self.assertEqual(path.read_bytes(), b"macho")

    def test_no_build_for_this_system(self):
        with mock.patch.object(tunnel, "asset_name", return_value=None):
            with self.assertRaises(ValueError):
                tunnel.download(self.dir, opener=mock.Mock())

    def test_a_broken_download_leaves_no_binary(self):
        def opener(url, timeout):
            raise OSError("connection reset")
        with self.assertRaises(OSError):
            tunnel.download(self.dir, opener=opener)
        self.assertFalse((self.dir / tunnel.binary_name()).exists())


class TunnelTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_cf_run_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.script = self.dir / "fake_cloudflared.py"
        self.script.write_text(_FAKE, encoding="utf-8")

    def _tunnel(self, *args, resolves=lambda host: True):
        got = {"url": threading.Event(), "exit": threading.Event()}
        self.lines, self.codes, self.urls = [], [], []

        def on_url(url):
            self.urls.append(url)
            got["url"].set()

        def on_exit(code):
            self.codes.append(code)
            got["exit"].set()
        t = tunnel.Tunnel(Path("cloudflared"), 8766, on_url, self.lines.append, on_exit,
                          resolves=resolves)
        self.assertEqual(t.argv, ["cloudflared", "tunnel", "--no-autoupdate",
                                  "--url", "http://127.0.0.1:8766"])
        t.argv = [sys.executable, str(self.script), *args]
        self.addCleanup(t.stop)
        return t, got

    def test_the_public_address_is_read_off_its_output(self):
        t, got = self._tunnel()
        t.start()
        self.assertTrue(got["url"].wait(10))
        self.assertEqual(t.url, "https://moon-river-tango-waltz.trycloudflare.com")
        self.assertEqual(self.urls, [t.url])
        self.assertTrue(t.running)
        t.stop()
        self.assertTrue(got["exit"].wait(10))
        self.assertFalse(t.running)

    def test_an_early_end_is_heard(self):
        t, got = self._tunnel("exit")
        t.start()
        self.assertTrue(got["exit"].wait(10))
        self.assertEqual(self.codes, [3])
        self.assertIn("Registered tunnel connection", self.lines[-1])

    def test_the_address_waits_until_its_name_is_published(self):
        # cloudflared prints the address before Cloudflare's DNS has the name;
        # a phone asking then hears "name not resolved" and keeps hearing it.
        published, asked = threading.Event(), []

        def resolves(host):
            asked.append(host)
            return published.is_set()
        t, got = self._tunnel(resolves=resolves)
        with mock.patch.object(tunnel, "_DNS_POLL_SECS", 0.05):
            t.start()
            self.assertFalse(got["url"].wait(1))
            self.assertEqual(self.urls, [])
            self.assertIn("moon-river-tango-waltz.trycloudflare.com", asked)
            self.assertIn("Registered tunnel connection", self.lines[-1])  # still read
            published.set()
            self.assertTrue(got["url"].wait(10))
        self.assertEqual(self.urls, ["https://moon-river-tango-waltz.trycloudflare.com"])

    def test_a_name_never_seen_is_handed_out_after_the_wait(self):
        t, got = self._tunnel(resolves=lambda host: False)
        with mock.patch.object(tunnel, "_DNS_POLL_SECS", 0.05), \
                mock.patch.object(tunnel, "_DNS_WAIT_SECS", 0.3):
            t.start()
            self.assertTrue(got["url"].wait(10))
        self.assertEqual(len(self.urls), 1)

    def test_a_dns_that_cannot_be_asked_does_not_hold_it_back(self):
        t, got = self._tunnel(resolves=lambda host: None)
        t.start()
        self.assertTrue(got["url"].wait(10))

    def test_no_address_from_a_tunnel_that_ended_while_waiting(self):
        t, got = self._tunnel("exit", resolves=lambda host: False)
        with mock.patch.object(tunnel, "_DNS_POLL_SECS", 0.05), \
                mock.patch.object(tunnel, "_DNS_WAIT_SECS", 0.3):
            t.start()
            self.assertTrue(got["exit"].wait(10))
            self.assertFalse(got["url"].wait(1))

    def test_a_missing_program_raises(self):
        t = tunnel.Tunnel(self.dir / "nothere.exe", 8766, on_url=print)
        with self.assertRaises(OSError):
            t.start()


class DnsTest(unittest.TestCase):
    """The question put to Cloudflare's own nameservers, and its answer."""

    def test_the_question_names_the_host(self):
        q = tunnel.dns_query("moon.trycloudflare.com", 0x1234)
        self.assertEqual(q[:12], bytes.fromhex("123400000001000000000000"))
        self.assertEqual(q[12:], b"\x04moon\x0dtrycloudflare\x03com\x00\x00\x01\x00\x01")

    def test_an_answer_with_a_record_is_published(self):
        head = bytes.fromhex("1234" "8400" "0001" "0001" "0000" "0000")
        self.assertTrue(tunnel.dns_answered(head, 0x1234))

    def test_no_such_name_or_a_stranger_is_not(self):
        nx = bytes.fromhex("1234" "8403" "0001" "0000" "0000" "0000")
        empty = bytes.fromhex("1234" "8400" "0001" "0000" "0000" "0000")
        other = bytes.fromhex("9999" "8400" "0001" "0001" "0000" "0000")
        for reply in (nx, empty, other, b"\x12"):
            self.assertFalse(tunnel.dns_answered(reply, 0x1234), reply)

    def test_nameservers_out_of_reach_tell_nothing(self):
        with mock.patch.object(tunnel.socket, "socket", side_effect=OSError("blocked")):
            self.assertIsNone(tunnel.name_published("moon.trycloudflare.com"))


if __name__ == "__main__":
    unittest.main()
