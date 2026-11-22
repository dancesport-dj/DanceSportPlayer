"""Mutation testing with cosmic-ray: which changes to a module its tests miss.

Coverage says a line ran; a mutant says whether a test noticed when the line
was wrong. cosmic-ray rewrites one operator at a time (`<` to `<=`, `and` to
`or`, a constant to another) and runs the module's tests; a mutant the tests
still pass on ("survived") marks code that is run but not checked.

    .venv\\Scripts\\python.exe -m tools.dev.mutation planner/music/parsing.py
    .venv\\Scripts\\python.exe -m tools.dev.mutation planner/x.py --diff main
    .venv\\Scripts\\python.exe -m tools.dev.mutation gui/y.py --tests tests/gui/test_y.py

The tests are the module's area folder (tests/planner for planner/..., the
same map as tools.dev.commit_scope), unless --tests names others. --diff BASE
keeps only the mutants on lines changed since BASE (cr-filter-git); a line
marked `# pragma: no mutate` is never mutated (cr-filter-pragma), and nor is
a type annotation: Python 3.14 does not evaluate one unless asked, so
`list[str] | None` turned into `list[str] + None` is a mutant no test can kill
(in the pilot on parsing.py, 363 of the 674 that survived).

cosmic-ray changes the module on disk for every mutant, so nothing runs in
this checkout: each worker gets its own copy of the tracked tree in a temp
folder. The session database stays in .mutation/ and a run that is stopped
picks up its pending mutants the next time; --fresh starts over. The tests
run once unmutated first: they must pass, and their time sets the per-mutant
timeout (a mutant that loops forever counts as killed).

    .venv\\Scripts\\cr-html .mutation\\planner.music.parsing.sqlite > report.html
"""
import argparse
import ast
import json
import os
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = ROOT / ".mutation"


def tests_for(module: str) -> str:
    """The test folder for a module path, by the commit-scope area map."""
    from tools.dev.commit_scope import area_of

    area = area_of(module)
    if area in (None, "full", "i18n"):
        return "tests"
    return f"tests/{area}"


def test_command(python: str, tests: list[str]) -> str:
    """One serial pytest run that stops on the first failure.

    Serial because each worker already is one process of the parallel run;
    cosmic-ray splits the command with shlex, so the paths go in POSIX form."""
    args = [Path(python).as_posix(), "-m", "pytest", "-x", "-q", "-n0", "-p", "no:cacheprovider",
            *(Path(t).as_posix() for t in tests)]
    return shlex.join(args)


def session_path(module: str) -> Path:
    return SESSIONS / (Path(module).with_suffix("").as_posix().replace("/", ".") + ".sqlite")


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root,
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def make_copy(root: Path, files: list[str]) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="mutation-"))
    for name in files:
        src = root / name
        if not src.is_file():
            continue  # a deleted file git still lists
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dest


def test_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    # cosmic-ray decodes the test output as UTF-8; a cp1252 console would make
    # every mutant with a non-ASCII line in its output "incompetent".
    env["PYTHONUTF8"] = "1"
    return env


def baseline(copy: Path, command: str) -> float:
    start = time.monotonic()
    done = subprocess.run(shlex.split(command), cwd=copy, env=test_env(), capture_output=True)
    if done.returncode != 0:
        sys.stdout.write(done.stdout.decode("utf-8", "replace")[-3000:])
        raise SystemExit("The tests fail without any mutant: fix them first.")
    return time.monotonic() - start


def worker() -> None:
    """Run the mutants named on stdin in the current folder, one JSON line each way."""
    from cosmic_ray.mutating import mutate_and_test
    from cosmic_ray.work_item import MutationSpec

    out = sys.stdout
    sys.stdout = sys.stderr  # nothing but results on the pipe
    for line in sys.stdin:
        job = json.loads(line)
        specs = [MutationSpec(Path(m["module"]), m["operator"], m["occurrence"], (0, 0), (0, 1))
                 for m in job["mutations"]]
        result = mutate_and_test(specs, job["command"], job["timeout"])
        out.write(json.dumps({
            "job_id": job["job_id"],
            "worker_outcome": result.worker_outcome.value,
            "test_outcome": result.test_outcome.value if result.test_outcome else None,
            "output": result.output,
            "diff": result.diff,
        }) + "\n")
        out.flush()


def run_mutants(db, copies: list[Path], command: str, timeout: float) -> None:
    from cosmic_ray.work_item import WorkResult

    jobs = queue.Queue()
    pending = list(db.pending_work_items)
    for item in pending:
        jobs.put(item)
    results = queue.Queue()

    def feed(copy: Path) -> None:
        proc = subprocess.Popen([sys.executable, "-m", "tools.dev.mutation", "--worker"], cwd=copy,
                                env=test_env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        stdin, stdout = proc.stdin, proc.stdout
        if stdin is None or stdout is None:   # both are PIPE above
            raise RuntimeError("mutation worker has no pipes")
        try:
            while True:
                try:
                    item = jobs.get_nowait()
                except queue.Empty:
                    break
                stdin.write(json.dumps({
                    "job_id": item.job_id, "command": command, "timeout": timeout,
                    "mutations": [{"module": m.module_path.as_posix(), "operator": m.operator_name,
                                   "occurrence": m.occurrence} for m in item.mutations],
                }) + "\n")
                stdin.flush()
                results.put(json.loads(stdout.readline()))
        finally:
            stdin.close()
            proc.wait()

    threads = [threading.Thread(target=feed, args=(c,), daemon=True) for c in copies]
    for t in threads:
        t.start()
    for n in range(1, len(pending) + 1):
        got = results.get()
        job_id = got.pop("job_id")
        db.set_result(job_id, WorkResult(**got))
        if n % 25 == 0 or n == len(pending):
            print(f"  {n}/{len(pending)} mutants", flush=True)
    for t in threads:
        t.join()


def annotation_spans(source: str) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """(start, end) as (line, column) of every annotation in the source."""
    spans = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.arg):
            found = [node.annotation]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found = [node.returns]
        elif isinstance(node, ast.AnnAssign):
            found = [node.annotation]
        else:
            continue
        spans += [((a.lineno, a.col_offset), (a.end_lineno, a.end_col_offset)) for a in found if a is not None]
    return spans


def skip_annotations(db, root: Path) -> int:
    """Mark the mutants inside an annotation skipped (also ones already run,
    so an older session is counted the same way); returns how many."""
    from cosmic_ray.work_item import WorkerOutcome, WorkResult

    spans: dict[str, list] = {}
    skipped = 0
    for item in db.work_items:
        m = item.mutations[0]
        path = str(m.module_path)
        if path not in spans:
            spans[path] = annotation_spans((root / path).read_text(encoding="utf-8"))
        if any(start <= tuple(m.start_pos) < end for start, end in spans[path]):
            db.set_result(item.job_id, WorkResult(worker_outcome=WorkerOutcome.SKIPPED))
            skipped += 1
    return skipped


def summarize(db) -> dict[str, int]:
    """Counts by outcome. Only a mutant the tests ran against counts for the rate."""
    counts = {"killed": 0, "survived": 0, "incompetent": 0, "skipped": 0, "other": 0}
    for _item, result in db.completed_work_items:
        if result.worker_outcome.value == "skipped":
            counts["skipped"] += 1
        elif result.worker_outcome.value != "normal":
            counts["other"] += 1
        else:
            counts[result.test_outcome.value] += 1
    return counts


def kill_rate(counts: dict[str, int]) -> float | None:
    tested = counts["killed"] + counts["survived"]
    return counts["killed"] / tested if tested else None


def survivors(db) -> list[tuple[int, str, str]]:
    """(line, operator, diff) of each survived mutant, by line."""
    out = []
    for item, result in db.completed_work_items:
        if result.worker_outcome.value == "normal" and result.test_outcome.value == "survived":
            m = item.mutations[0]
            out.append((m.start_pos[0], m.operator_name.split("/")[-1], result.diff or ""))
    return sorted(out)


def cosmic_ray(*args: str, cwd: Path) -> None:
    scripts = Path(sys.executable).parent
    # The filters read the module with the default encoding (cp1252 here).
    subprocess.run([str(scripts / args[0]), *args[1:]], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, env=test_env())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("module", nargs="?", help="the module to mutate, e.g. planner/music/parsing.py")
    ap.add_argument("--tests", nargs="+", help="test files or folders (default: the module's area)")
    ap.add_argument("--diff", metavar="BASE", help="only mutate lines changed since this git ref")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2), help="parallel workers")
    ap.add_argument("--fresh", action="store_true", help="discard an earlier session of this module")
    ap.add_argument("--show", type=int, default=30, help="survivors to print")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.worker:
        worker()
        return 0
    if not args.module:
        ap.error("name the module to mutate")

    from cosmic_ray.work_db import WorkDB, use_db

    module = Path(args.module).as_posix()
    tests = args.tests or [tests_for(module)]
    command = test_command(sys.executable, tests)
    session = session_path(module)
    SESSIONS.mkdir(exist_ok=True)
    if args.fresh:
        session.unlink(missing_ok=True)

    files = tracked_files(ROOT)
    copies = [make_copy(ROOT, files)]
    try:
        took = baseline(copies[0], command)
        timeout = round(took * 3 + 10)
        print(f"Unmutated: {' '.join(tests)} passes in {took:.0f} s, per-mutant timeout {timeout} s")
        config = session.with_suffix(".toml")
        config.write_text(
            "[cosmic-ray]\n"
            f"module-path = {json.dumps(module)}\n"
            f"timeout = {timeout}.0\n"
            "excluded-modules = []\n"
            f"test-command = {json.dumps(command)}\n"
            "\n[cosmic-ray.distributor]\nname = \"local\"\n"
            f"\n[cosmic-ray.filters.git-filter]\nbranch = {json.dumps(args.diff or 'HEAD')}\n",
            encoding="utf-8", newline="\n")
        if not session.exists():
            cosmic_ray("cosmic-ray", "init", str(config), str(session), cwd=copies[0])
            cosmic_ray("cr-filter-pragma", str(session), cwd=copies[0])
            if args.diff:
                cosmic_ray("cr-filter-git", "--config", str(config), str(session), cwd=ROOT)
        with use_db(str(session), WorkDB.Mode.open) as db:
            print(f"{skip_annotations(db, copies[0])} mutants in annotations skipped")
            todo = db.num_work_items - db.num_results
            jobs = min(args.jobs, todo)
            print(f"{db.num_work_items} mutants, {todo} to run on {jobs} workers")
            copies += [make_copy(ROOT, files) for _ in range(jobs - 1)]
            if todo:
                run_mutants(db, copies[:jobs], command, timeout)
            counts = summarize(db)
            rate = kill_rate(counts)
            print(f"\n{module}: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v))
            print("kill rate: " + (f"{rate:.1%}" if rate is not None else "nothing tested"))
            left = survivors(db)
            for line, operator, diff in left[: args.show]:
                change = [d for d in diff.splitlines() if d.startswith(("-", "+"))
                          and not d.startswith(("---", "+++"))]
                print(f"\n  line {line}  {operator}")
                for d in change:
                    print(f"    {d.strip()}")
            if len(left) > args.show:
                print(f"\n  ... {len(left) - args.show} more; cr-html {session.relative_to(ROOT)} for all")
    finally:
        for copy in copies:
            shutil.rmtree(copy, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
