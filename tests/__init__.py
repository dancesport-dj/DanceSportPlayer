"""The test suite, one package per side of the app.
"""
import os

# Test windows enter Playing mode; they must not mute the system sounds of the
# machine the suite runs on (see player.system_sounds.default_backend).
os.environ.setdefault("DANCEPLAYLIST_KEEP_SYSTEM_SOUNDS", "1")
