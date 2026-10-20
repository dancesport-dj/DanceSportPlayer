"""🖥 The machine the app runs on, and what the app uses of it — for session.log.

A tester's slow start could not be weighed: his log said neither what kind of
computer it ran on nor how busy the app kept it. Standard library only, one
branch per system; whatever a system won't tell comes back as None and is
logged as "?".
"""
import ctypes
import os
import platform
import re
import subprocess
import sys
import threading
import time

_GB = 1024 ** 3
_MB = 1024 ** 2


def os_name() -> str:
    """e.g. 'Windows 11 (10.0.26300) AMD64', 'macOS 14.5 arm64', 'Linux 6.8.0 x86_64'."""
    machine = platform.machine()
    if sys.platform == "darwin":
        return f"macOS {platform.mac_ver()[0]} {machine}"
    if sys.platform == "win32":
        return f"Windows {platform.release()} ({platform.version()}) {machine}"
    return f"{platform.system()} {platform.release()} {machine}"


def _run(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def cpu_name() -> str | None:
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            return platform.processor() or None
    if sys.platform == "darwin":
        return _run("sysctl", "-n", "machdep.cpu.brand_string").strip() or None
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


class _MemoryStatus(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def ram() -> tuple[int | None, int | None]:
    """(total, available) bytes of physical memory."""
    if sys.platform == "win32":
        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(_MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys, status.ullAvailPhys
        return None, None
    if sys.platform == "darwin":
        total = _run("sysctl", "-n", "hw.memsize").strip()
        # Free plus what macOS gives back on demand (inactive, purgeable,
        # speculative): roughly what Activity Monitor leaves out of "used".
        stat = _run("vm_stat")
        size = re.search(r"page size of (\d+) bytes", stat)
        pages = {k: int(v) for k, v in re.findall(r"Pages (\w+):\s+(\d+)", stat)}
        avail = None
        if size and pages:
            avail = int(size.group(1)) * sum(
                pages.get(k, 0) for k in ("free", "inactive", "purgeable", "speculative"))
        return (int(total) if total.isdigit() else None), avail
    info = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                key, _, rest = line.partition(":")
                info[key] = int(rest.split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return info.get("MemTotal"), info.get("MemAvailable")


class _ProcessMemory(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def app_ram() -> int | None:
    """Bytes of physical memory this process holds right now."""
    if sys.platform == "win32":
        counters = _ProcessMemory()
        counters.cb = ctypes.sizeof(_ProcessMemory)
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        if ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.c_void_p(kernel32.GetCurrentProcess()),
                ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize
        return None
    if sys.platform == "darwin":
        rss = _run("ps", "-o", "rss=", "-p", str(os.getpid())).strip()
        return int(rss) * 1024 if rss.isdigit() else None
    try:
        with open("/proc/self/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def _gb(n: int | None) -> str:
    return "?" if n is None else f"{n / _GB:.1f} GB"


def _mb(n: int | None) -> str:
    return "?" if n is None else f"{n / _MB:.0f} MB"


def machine_lines() -> str:
    """The session-start block: system, CPU and memory, one per line."""
    total, avail = ram()
    return (f"system: {os_name()}\n"
            f"cpu: {cpu_name() or '?'} ({os.cpu_count() or '?'} threads)\n"
            f"ram: {_gb(total)} total, {_gb(avail)} free\n"
            f"app ram: {_mb(app_ram())}")


# Lowest, but not idle or background mode: the scan's Python code shares a lock
# with the GUI's, and a thread starved of CPU while holding it would stall the GUI.
_LOWEST = -2               # Windows THREAD_PRIORITY_LOWEST
_NICE = 15                 # Linux: a thread's own niceness
_QOS_CLASS_UTILITY = 0x11   # macOS: long work the user follows by a progress bar


def lower_thread_priority() -> None:
    """🐢 The calling thread below the GUI and the audio player, for the
    library scan and its read-ahead: when the CPU is short, they wait, not the
    music. It changes no Python lock — the scan's Python code still takes
    turns with the GUI's. A system that refuses leaves the thread as it was."""
    try:
        if sys.platform == "win32":
            kernel32 = ctypes.WinDLL("kernel32")
            kernel32.GetCurrentThread.restype = ctypes.c_void_p
            kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
            kernel32.SetThreadPriority(kernel32.GetCurrentThread(), _LOWEST)
        elif sys.platform == "darwin":
            ctypes.CDLL(None).pthread_set_qos_class_self_np(_QOS_CLASS_UTILITY, 0)
        else:
            # On Linux the niceness is per thread, under the thread's own id.
            os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), _NICE)
    except (OSError, AttributeError):
        pass


class UsageMeter:
    """What the app uses right now: its memory, the machine's free memory, and
    its CPU time since the last reading as a share of one core (above 100 %
    means more than one core was busy) and of the whole machine."""

    def __init__(self):
        self._wall = time.perf_counter()
        self._cpu = time.process_time()

    def lines(self) -> str:
        wall, cpu = time.perf_counter(), time.process_time()
        share = (cpu - self._cpu) / (wall - self._wall) * 100 if wall > self._wall else 0.0
        self._wall, self._cpu = wall, cpu
        cpu_line = f"app cpu: {share:.0f} % of one core"
        cores = os.cpu_count()
        if cores:
            cpu_line += f" = {share / 100:.1f} of {cores} cores ({share / cores:.0f} %)"
        return (f"app ram: {_mb(app_ram())}\n"
                f"free ram: {_gb(ram()[1])}\n"
                f"{cpu_line}")
