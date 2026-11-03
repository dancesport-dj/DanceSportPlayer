"""Work the window has started or wants started, kept on one object so the
window itself does not grow a new attribute for each (see
tests.app.test_mainwindow_budget)."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PendingWork:
    # One Paso Doble detection per track path, so a replay finds its own (#11).
    pd_workers: dict = field(default_factory=dict)
    # The title whose loudness wait ran out: play on, the level follows (#1).
    lufs_expired: Path | None = None
    # A true peak waiting for the free worker slot (#12).
    peak_wanted: Path | None = None
