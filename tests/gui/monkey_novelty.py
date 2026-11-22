"""🐒 Novelty for the monkey: prefer the controls it has worked least.

A uniform pick spends a walk where the controls are: the main window holds a
few hundred, a dialog a dozen, so the dialog's Apply path is hit about as
often as any single cell of the library table. Fastbot2 (ASE 2022) keys an
action by the screen it is on, the widget and the kind of action, and prefers
the ones not yet executed; this does the same with one weight per key,
1 / (1 + times worked), so a control never worked is picked first and a
worked one stays possible.

The counts live for one walk, and so a seed replays the same walk. With
DANCEPLAYLIST_MONKEY_VISITS=<file.json> they are read at the start and
written back after a walk that passed (the nightly keeps one per seed slot):
the next night's walk then leans to what the earlier ones missed, and a red
walk leaves the file as it found it, so the same seed and file replay it.

    python -m tests.gui.monkey_novelty visits.json    # what no walk has hit
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

VISITS_ENV = "DANCEPLAYLIST_MONKEY_VISITS"


def _text_of(w) -> str:
    for getter in ("objectName", "text", "toolTip", "accessibleName"):
        fn = getattr(w, getter, None)
        if callable(fn):
            try:
                text = fn()
            except TypeError:
                continue
            if text:
                return " ".join(str(text).split())[:40]
    return ""


def target_key(kind: str, w) -> str:
    """'<window> | <widget class>:<name or label> | <action kind>'.

    The window is its class and title (every QMessageBox is the same class);
    the widget its objectName, else its label — the same control on the next
    run gets the same key, two buttons of one dialog get two."""
    host = w if hasattr(w, "window") else w.parent()   # a QShortcut has no window of its own
    win = host.window() if host is not None else None
    where = f"{type(win).__name__}:{win.windowTitle()}" if win is not None else "?"
    return f"{where} | {type(w).__name__}:{_text_of(w)} | {kind}"


class Novelty:
    """How often each key was offered and worked, and the pick weights from that."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.worked: Counter[str] = Counter()
        self.offered: Counter[str] = Counter()
        if path is not None and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.worked.update(data.get("worked", {}))
            self.offered.update(data.get("offered", {}))

    @classmethod
    def from_env(cls) -> Novelty:
        name = os.environ.get(VISITS_ENV)
        return cls(Path(name) if name else None)

    def weights(self, keys: list[str]) -> list[float]:
        for k in keys:
            self.offered[k] += 1
        return [1.0 / (1 + self.worked[k]) for k in keys]

    def mark(self, key: str) -> None:
        self.worked[key] += 1

    def never_hit(self) -> list[str]:
        """Keys some walk offered and none worked, the most-offered first."""
        return sorted((k for k in self.offered if not self.worked[k]),
                      key=lambda k: (-self.offered[k], k))

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"worked": dict(sorted(self.worked.items())),
                                   "offered": dict(sorted(self.offered.items()))},
                                  ensure_ascii=False, indent=0), encoding="utf-8")
        os.replace(tmp, self.path)


def report(novelty: Novelty, top: int = 60) -> str:
    missed = novelty.never_hit()
    lines = [f"{len(novelty.worked)} controls worked, {len(missed)} offered and never worked"]
    lines += [f"  {novelty.offered[k]:5d}x offered  {k}" for k in missed[:top]]
    if len(missed) > top:
        lines.append(f"  ... {len(missed) - top} more")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m tests.gui.monkey_novelty <visits.json>")
    out = report(Novelty(Path(sys.argv[1])))
    print(out.encode("ascii", "backslashreplace").decode("ascii"))
