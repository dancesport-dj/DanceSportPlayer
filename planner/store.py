#!/usr/bin/env python3
"""What the app remembers between starts, and where it keeps it.

Eight JSON files hold everything that survives closing the app: the settings,
the working playlist autosave, the cartwall pads, the tournament tree, the user
themes, the OpenRouter credentials. Each of them had its own pair of
read/write functions, and each pair restated the same contract in its own
words — read it if it is there, warn naming the file and carry on with a
default if it is not readable, write it through a temp file so a crash can
never leave half a file behind, and never raise at the caller either way.
Seven copies of one paragraph, differing only in which of them remembered
`encoding="utf-8"` and which logged a warning where its neighbour logged an
error.

They also each named their file the same wrong way: as a module-level Path
built while the module was importing. That made the folder those files live in
a property of import order rather than of the machine, and it is why
DANCEPLAYLIST_STATE_DIR only worked when it was set before the first `import
gui.dialogs` anywhere in the process — a headless test that got the order
wrong wrote over the operator's real settings. A store resolves its path when
it is asked, so there is no moment to be too late for.

`JsonStore` is the module: give it a file name and the root it lives under and
it answers read / write / remove. What each store means is still the caller's
— `load_settings` fills in per-machine defaults, `load_autosave` checks the
envelope version — but where the file is, how it is encoded, how it survives a
crash and what happens when it cannot be read are asked once here.
"""
import json
import logging
import os
import shutil
import time
from pathlib import Path

from planner import config

log = logging.getLogger("dancesport.store")


def state_dir() -> Path:
    """Folder holding the per-machine GUI state: settings, autosave, cartwall,
    tournament tree.

    Defaults to the app's data dir; DANCEPLAYLIST_STATE_DIR redirects it so a
    headless test can build a MainWindow without overwriting the real
    gui_settings.json / autosave_playlist.json. Read on every call, not once at
    import: a test that sets the variable after importing a gui module is still
    redirected.
    """
    env = os.environ.get("DANCEPLAYLIST_STATE_DIR")
    if env:
        d = Path(env)
        d.mkdir(parents=True, exist_ok=True)
        return d
    return config.APP_DIR


def data_dir() -> Path:
    """Folder holding the app's own files — caches, DB, themes, credentials.

    Not the same root as state_dir(): a test redirects the state it might
    clobber, and keeps reading the themes and caches it shares with the app.
    """
    return config.APP_DIR


class JsonStore:
    """One JSON file the app remembers something in.

    The path is resolved per call from the root, so redirecting a root moves
    every store under it — including the ones a module already holds.
    """

    def __init__(self, name: str, *, root=None, note: str = "using defaults"):
        self.name = name
        self._root = root or state_dir
        # What happens instead when the file cannot be read — the tail of the
        # warning, so the log says what the operator will actually see.
        self.note = note

    @classmethod
    def at(cls, path, *, note: str = "using defaults") -> "JsonStore":
        """A store over one named file — for the callers that are handed a path
        (a test's temp file) rather than living under one of the roots."""
        p = Path(path)
        return cls(p.name, root=lambda: p.parent, note=note)

    @property
    def path(self) -> Path:
        return self._root() / self.name

    def exists(self) -> bool:
        return self.path.exists()

    def read(self, default=None):
        """The parsed file, or `default` when it is absent or unreadable.

        A missing file is the normal first start and says nothing; anything
        else is worth a warning naming the file, because the app is about to
        carry on without what was in it.
        """
        path = self.path
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default
        except Exception as exc:
            log.warning("⚠️ Could not read stored state\n"
                        "file: %s\n"
                        "error: %s\n"
                        "instead: %s\n"
                        "kept as: %s", path.name, exc, self.note,
                        self._keep_unreadable(path) or "—")
            return default

    @staticmethod
    def _keep_unreadable(path: Path) -> str | None:
        """Copy a file that could not be read aside, under a name nothing
        writes to — the defaults the app carries on with are saved over it on
        the next click, and a hand edit with one comma wrong would otherwise
        take everything in the file with it. The copy's name, or None."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        n = 1
        while True:
            tail = "" if n == 1 else f"-{n}"
            kept = path.with_name(f"{path.stem}.unreadable-{stamp}{tail}{path.suffix}")
            if not kept.exists():
                break
            n += 1
        try:
            shutil.copy2(path, kept)
        except OSError:
            return None
        return kept.name

    def write(self, obj) -> bool:
        """Write the file atomically. Never raises: nothing the app persists is
        worth losing the user's next click over. False when it did not land."""
        try:
            config.write_json_atomic(self.path, obj)
            return True
        except Exception as exc:
            log.error("⚠️ Could not save stored state\n"
                      "file: %s\n"
                      "error: %s", self.path.name, exc)
            return False

    def remove(self) -> None:
        """Forget it. A file that is already gone is the wanted outcome."""
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            log.debug("🧹 Could not remove %s: %s", self.path.name, exc)


# ── The app's own files (data dir) ───────────────────────────────────────────
USER_THEMES = JsonStore("themes.json", root=data_dir,
                        note="using built-in themes only")
OPENROUTER = JsonStore("openrouter_config.json", root=data_dir,
                       note="asking for the API key again")
