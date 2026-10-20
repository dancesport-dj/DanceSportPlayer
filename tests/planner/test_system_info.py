"""🖥 The machine and the app's own use of it, for session.log.

Run:  py -m unittest tests.planner.test_system_info -v

A tester's slow start could not be weighed: the log named neither his
computer nor how busy the app kept it. The macOS and Linux branches are fed
canned command output and /proc files here, so they are read on Windows too.
"""
import ctypes
import re
import sys
import threading
import unittest
from unittest import mock

from planner import system_info

_VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               10000.
Pages active:                            200000.
Pages inactive:                           20000.
Pages speculative:                         5000.
Pages wired down:                         90000.
Pages purgeable:                           1000.
"""
_MEMINFO = "MemTotal:       16303428 kB\nMemFree:  1000 kB\nMemAvailable:    8151714 kB\n"
_CPUINFO = "processor\t: 0\nmodel name\t: Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz\n"


class ThisMachineTest(unittest.TestCase):
    def test_the_start_block_names_system_cpu_and_memory(self):
        lines = system_info.machine_lines().splitlines()
        self.assertEqual([line.split(":")[0] for line in lines],
                         ["system", "cpu", "ram", "app ram"])
        self.assertRegex(lines[2], r"^ram: [\d.]+ GB total, [\d.]+ GB free$")
        self.assertRegex(lines[3], r"^app ram: \d+ MB$")

    def test_the_usage_lines_measure_since_the_last_reading(self):
        meter = system_info.UsageMeter()
        sum(range(2_000_000))
        out = meter.lines()
        self.assertRegex(out, r"app ram: \d+ MB\nfree ram: [\d.]+ GB\napp cpu: \d+ % of one core")
        share = int(re.search(r"app cpu: (\d+)", out).group(1))
        self.assertGreater(share, 0)

    def test_the_cpu_line_names_both_one_core_and_the_whole_machine(self):
        """Marcel read "155 % of a core" as a measuring bug: it is the sum over
        all the app's threads, so it says the whole machine's share too."""
        with mock.patch.object(system_info.time, "perf_counter", side_effect=[0.0, 10.0]), \
                mock.patch.object(system_info.time, "process_time", side_effect=[0.0, 15.5]), \
                mock.patch.object(system_info.os, "cpu_count", return_value=16):
            out = system_info.UsageMeter().lines()
        self.assertTrue(out.endswith("app cpu: 155 % of one core = 1.6 of 16 cores (10 %)"),
                        out)

    def test_without_a_core_count_the_cpu_line_keeps_one_core(self):
        with mock.patch.object(system_info.time, "perf_counter", side_effect=[0.0, 10.0]), \
                mock.patch.object(system_info.time, "process_time", side_effect=[0.0, 15.5]), \
                mock.patch.object(system_info.os, "cpu_count", return_value=None):
            out = system_info.UsageMeter().lines()
        self.assertTrue(out.endswith("app cpu: 155 % of one core"), out)


class MacTest(unittest.TestCase):
    def run_as_mac(self, fn):
        answers = {"hw.memsize": "17179869184\n", "machdep.cpu.brand_string": "Apple M2\n",
                   "vm_stat": _VM_STAT, "rss=": "524288\n"}

        def run(*cmd):
            return next(v for k, v in answers.items() if k in cmd)

        with mock.patch.object(system_info.sys, "platform", "darwin"), \
                mock.patch.object(system_info, "_run", side_effect=run):
            return fn()

    def test_memory_counts_what_macos_gives_back(self):
        total, avail = self.run_as_mac(system_info.ram)
        self.assertEqual(total, 16 * 1024 ** 3)
        self.assertEqual(avail, 16384 * (10000 + 20000 + 5000 + 1000))

    def test_cpu_and_app_memory(self):
        self.assertEqual(self.run_as_mac(system_info.cpu_name), "Apple M2")
        self.assertEqual(self.run_as_mac(system_info.app_ram), 512 * 1024 ** 2)


class LinuxTest(unittest.TestCase):
    def run_as_linux(self, fn, text):
        with mock.patch.object(system_info.sys, "platform", "linux"), \
                mock.patch("builtins.open", mock.mock_open(read_data=text)):
            return fn()

    def test_memory_from_proc(self):
        total, avail = self.run_as_linux(system_info.ram, _MEMINFO)
        self.assertEqual(total, 16303428 * 1024)
        self.assertEqual(avail, 8151714 * 1024)

    def test_cpu_and_app_memory_from_proc(self):
        self.assertEqual(self.run_as_linux(system_info.cpu_name, _CPUINFO),
                         "Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz")
        self.assertEqual(self.run_as_linux(system_info.app_ram, "VmRSS:\t  204800 kB\n"),
                         200 * 1024 ** 2)


class LowerThreadPriorityTest(unittest.TestCase):
    """🐢 The library scan's threads below the GUI and the audio player."""

    @unittest.skipUnless(sys.platform == "win32", "Windows thread priorities")
    def test_windows_puts_the_calling_thread_at_lowest(self):
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.GetCurrentThread.restype = ctypes.c_void_p
        kernel32.GetThreadPriority.argtypes = [ctypes.c_void_p]
        seen = {}

        def scan_thread():
            system_info.lower_thread_priority()
            seen["scan"] = kernel32.GetThreadPriority(kernel32.GetCurrentThread())

        t = threading.Thread(target=scan_thread)
        t.start()
        t.join()
        self.assertEqual(seen["scan"], -2)      # THREAD_PRIORITY_LOWEST
        self.assertEqual(kernel32.GetThreadPriority(kernel32.GetCurrentThread()), 0)

    def test_linux_niceness_of_the_thread_alone(self):
        with mock.patch.object(system_info.sys, "platform", "linux"), \
                mock.patch.object(system_info.os, "PRIO_PROCESS", 0, create=True), \
                mock.patch.object(system_info.os, "setpriority", create=True) as nice:
            system_info.lower_thread_priority()
        nice.assert_called_once_with(0, threading.get_native_id(), 15)

    def test_macos_utility_class(self):
        with mock.patch.object(system_info.sys, "platform", "darwin"), \
                mock.patch.object(system_info.ctypes, "CDLL") as libc:
            system_info.lower_thread_priority()
        libc.return_value.pthread_set_qos_class_self_np.assert_called_once_with(0x11, 0)

    def test_a_system_that_refuses_keeps_going(self):
        with mock.patch.object(system_info.sys, "platform", "linux"), \
                mock.patch.object(system_info.os, "PRIO_PROCESS", 0, create=True), \
                mock.patch.object(system_info.os, "setpriority", create=True,
                                  side_effect=PermissionError):
            system_info.lower_thread_priority()


if __name__ == "__main__":
    unittest.main()
