"""Coverage-guided fuzzing with HypoFuzz: the fuzz tests for hours, not dozens.

The fuzz tests (tests/**/test_*_fuzz.py, see tests/fuzz_support.py) try a few
dozen inputs per commit. HypoFuzz runs the same tests without an end, keeps
the inputs that reach new code and builds on those, on every core:

    .venv\\Scripts\\python.exe -m tools.dev.hypofuzz_run --minutes 60
    .venv\\Scripts\\python.exe -m tools.dev.hypofuzz_run tests/shared/remote --dashboard
    .venv\\Scripts\\python.exe -m tools.dev.hypofuzz_run -k venue_pack -n 2

Without paths it fuzzes every fuzz module; other arguments go to pytest to
pick tests. It runs until stopped (Ctrl+C), or for --minutes. --dashboard
serves HypoFuzz's live page on localhost.

What it finds lands in Hypothesis' example database (.hypothesis/ in the
checkout), which every ordinary run reads first: after a fuzz run,

    .venv\\Scripts\\python.exe -m pytest -n0 -k fuzz tests

replays each failing input and prints its traceback. By hand, not in CI or a
hook: it has no end of its own.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fuzz_modules(root: Path = ROOT) -> list[str]:
    """Every fuzz test module, as paths relative to `root`."""
    return sorted(p.relative_to(root).as_posix() for p in (root / "tests").rglob("test_*_fuzz.py"))


def command(pytest_args: list[str], workers: int, dashboard: bool) -> list[str]:
    """The HypoFuzz command line. Its pytest run is serial: HypoFuzz spreads
    the tests over its own processes, and the repo's addopts asks for xdist."""
    named = any((ROOT / a.split("::")[0]).exists() for a in pytest_args
                if not a.startswith("-"))     # not the value of -k
    picks = pytest_args if named else [*pytest_args, *fuzz_modules()]
    return [sys.executable, "-c", "from hypothesis.extra.cli import main; main()",
            "fuzz", "-n", str(workers), "--dashboard" if dashboard else "--no-dashboard",
            "--", "-n0", "-p", "no:cacheprovider", *picks]


def fuzz_env(temp: str) -> dict[str, str]:
    """`temp` as every worker's temp folder: a worker stopped at --minutes
    runs no atexit, so the suite's own temp root (tests/__init__.py) would
    stay behind in the user's; this one is removed after the run."""
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")   # the window start fuzz builds windows
    env["PYTHONUTF8"] = "1"                         # emoji in the log on a cp1252 console
    env["PYTHONUNBUFFERED"] = "1"                   # a stopped worker's last lines too
    env["DANCEPLAYLIST_HYPOFUZZ"] = "1"             # conftest: keep the suite's TEMP
    env["TMP"] = env["TEMP"] = env["TMPDIR"] = temp
    return env


def stop(proc: subprocess.Popen) -> None:
    """The fuzzer and every worker it started."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        os.killpg(proc.pid, 15)
    proc.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--minutes", type=float, help="stop after this long (default: never)")
    parser.add_argument("-n", "--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                        help="fuzzing processes (default: one per core but one)")
    parser.add_argument("--dashboard", action="store_true", help="serve the live page")
    args, pytest_args = parser.parse_known_args(argv)
    cmd = command(pytest_args, args.workers, args.dashboard)
    print(f"HypoFuzz on {args.workers} processes"
          + (f" for {args.minutes:g} min" if args.minutes else ", until Ctrl+C"), flush=True)
    temp = tempfile.mkdtemp(prefix="dp_hypofuzz_")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=fuzz_env(temp),
                            start_new_session=sys.platform != "win32")
    try:
        code = proc.wait(timeout=args.minutes * 60 if args.minutes else None)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        stop(proc)
        code = 0
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    print("Done. Replay what it found:\n"
          "    .venv\\Scripts\\python.exe -m pytest -n0 -k fuzz tests", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
