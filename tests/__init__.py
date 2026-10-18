"""The test suite, one package per side of the app.
"""
import atexit
import gc
import os
import shutil
import sys
import tempfile

# Test windows enter Playing mode; they must not mute the system sounds of the
# machine the suite runs on (see player.audio.system_sounds.default_backend).
os.environ.setdefault("DANCEPLAYLIST_KEEP_SYSTEM_SOUNDS", "1")

# Every temp folder of this test process — the modules' mkdtemp scratch, Qt's
# temp files, those of the processes it starts — lands in one root, removed when
# the run ends. The modules never remove their own.
_temp_root = tempfile.mkdtemp(prefix="dp_suite_")
tempfile.tempdir = _temp_root
os.environ["TMP"] = os.environ["TEMP"] = os.environ["TMPDIR"] = _temp_root

# Everything the app writes — audio_features.db, backups/, caches — goes to a
# throwaway folder, never the real one (see planner.config._env_data_dir).
if not os.environ.get("DANCEPLAYLIST_DATA_DIR"):
    os.environ["DANCEPLAYLIST_DATA_DIR"] = tempfile.mkdtemp(prefix="dp_suite_data_")


def remove_temp_root():
    """Remove this process's temp root. At exit under unittest; pytest-xdist
    workers end without running atexit, so the root conftest.py calls it too.

    Windows deletes no file that is still open: the main thread's database
    connection is closed first; a thread's own is closed as the thread ends."""
    db = sys.modules.get("planner.music.db")
    conn = getattr(db._DB_LOCAL, "conn", None) if db else None
    if conn is not None:
        db._DB_LOCAL.conn = None
        conn.close()
    gc.collect()
    shutil.rmtree(_temp_root, ignore_errors=True)


atexit.register(remove_temp_root)
