"""A scratch audio database for one test.

Not named test_*.py on purpose — unittest discovery would import it as a
test module.
"""
import threading

import planner.music.db as pdb
from planner import config as planner_config


def use_scratch_db(test, path):
    """Point planner.music.db at `path` until `test` ends, then back where it was.

    A fresh thread-local makes this thread open `path` instead of reusing its
    connection to the old file; the reset flag makes that open run the
    migrations. The cleanup closes the connection this thread made, so
    Windows can delete the test's temp folder.
    """
    saved = (planner_config.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
    planner_config.AUDIO_DB_FILE = path
    pdb._DB_LOCAL = threading.local()
    pdb._DB_INITIALIZED = False

    def restore():
        conn = getattr(pdb._DB_LOCAL, "conn", None)
        if conn is not None:
            conn.close()
        planner_config.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved
    test.addCleanup(restore)
    return path
