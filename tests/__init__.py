"""The test suite, one package per side of the app.
"""
import atexit
import os
import shutil
import tempfile

# Test windows enter Playing mode; they must not mute the system sounds of the
# machine the suite runs on (see player.system_sounds.default_backend).
os.environ.setdefault("DANCEPLAYLIST_KEEP_SYSTEM_SOUNDS", "1")

# Everything the app writes — audio_features.db, backups/, caches — goes to a
# throwaway folder, never the real one (see planner.config._env_data_dir).
if not os.environ.get("DANCEPLAYLIST_DATA_DIR"):
    _data_dir = tempfile.mkdtemp(prefix="dp_suite_data_")
    os.environ["DANCEPLAYLIST_DATA_DIR"] = _data_dir
    atexit.register(shutil.rmtree, _data_dir, ignore_errors=True)
