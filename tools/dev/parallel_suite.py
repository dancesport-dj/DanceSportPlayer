"""Run the whole suite across several processes at once.

Serially the suite takes about 7 minutes, and tests/gui alone takes over 5 of
them, so one process per package would barely help. Instead the test modules
are cut into small batches, and a pool of processes works through them. Each
process gets its own throwaway data folder (tests/__init__.py makes one when
DANCEPLAYLIST_DATA_DIR is unset), so no two share a database or a settings file.

The suite has an intermittent native crash of unknown cause (it ends a run
with no "Ran N tests" line). A batch that dies that way is run once more on its
own and reported as "native crash, retried", not as a red suite. A real
failure fails twice, so the retry hides nothing but the crash.

    .venv\\Scripts\\python.exe -m tools.dev.parallel_suite
"""
import contextlib
import io
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKERS = min(8, os.cpu_count() or 1)
BATCH = 4

# How a native crash ends the process: SIGSEGV as a POSIX shell reports it
# (139) or as subprocess does (-11), and an access violation on Windows, which
# arrives unsigned or signed depending on who reads it.
NATIVE_CRASH = {139, -11, 0xC0000005, -1073741819}

# A batch normally takes well under a minute. One that runs this long is wedged
# (a Qt deadlock offscreen is the plausible cause): it is killed, and treated like
# a crash - run once more on its own, red if it hangs again. 124 is the exit code
# `timeout` uses.
BATCH_TIMEOUT = 900
HUNG = 124


def batches() -> list[list[str]]:
    names = sorted(".".join(p.relative_to(ROOT).with_suffix("").parts)
                   for p in ROOT.glob("tests/**/test_*.py"))
    return [names[i:i + BATCH] for i in range(0, len(names), BATCH)]


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    # One shared value would put every process in the same data folder.
    env.pop("DANCEPLAYLIST_DATA_DIR", None)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_batch(batch: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run([sys.executable, "-m", "unittest", "-q", *batch],
                              cwd=ROOT, env=child_env(),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              encoding="utf-8", errors="replace",
                              timeout=BATCH_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        partial = exc.output
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        return HUNG, f"{partial or ''}\n⏱ timed out after {BATCH_TIMEOUT} s: {' '.join(batch)}\n"
    return proc.returncode, proc.stdout or ""


def tests_ran(output: str) -> int:
    match = re.search(r"^Ran (\d+) tests?", output, re.MULTILINE)
    return int(match.group(1)) if match else 0


def run_all(work: list[list[str]]) -> int:
    started = time.monotonic()
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(run_batch, work))
    ran = 0
    failed = []
    for batch, (code, output) in zip(work, results, strict=True):
        if code in NATIVE_CRASH or code == HUNG:
            cause = "timed out" if code == HUNG else "native crash"
            # On its own, so a second crash cannot be blamed on the others.
            code, output = run_batch(batch)
            print(f"⚠️ {cause}, retried: {' '.join(batch)}", flush=True)
        ran += tests_ran(output)
        if code:
            failed.append(batch)
            print(output, flush=True)
    seconds = time.monotonic() - started
    icon = "🛑" if failed else "✅"
    print(f"{icon} Ran {ran} tests in {seconds:.0f} s\n"
          f"processes: {WORKERS}\n"
          f"batches: {len(work)}", flush=True)
    for batch in failed:
        print(f"🛑 red: {' '.join(batch)}", flush=True)
    return 1 if failed else 0


def main() -> int:
    # The console is cp1252; the result lines lead with an emoji.
    if isinstance(sys.stdout, io.TextIOWrapper):
        with contextlib.suppress(OSError):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return run_all(batches())


if __name__ == "__main__":
    sys.exit(main())
