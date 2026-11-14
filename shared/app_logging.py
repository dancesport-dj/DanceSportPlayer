"""📝 The app's log: loguru is the sink, stdlib `logging` stays the front door.

Hundreds of modules call `logging.getLogger(...)` (and so do the libraries the app
uses), and `assertLogs` in the tests hooks into that. They stay as they are; one
handler on the root logger forwards every record to loguru, which writes the
console and session.log with one format.
"""
import logging
import sys

from loguru import logger

# "2026-11-11 00:25:41 I message": date, time, the level's first letter, the text.
# loguru ends a string format with a newline and "{exception}" itself, so a
# traceback lands under its message.
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} {level.name[0]} {message}"


class InterceptHandler(logging.Handler):
    """Every stdlib record into loguru, reported at the line that logged it."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Walk out of the logging module's own frames, so loguru names the caller.
        frame, depth = sys._getframe(0), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setupLogging(level: int = logging.INFO) -> None:
    """The console sink and the stdlib bridge. Under pythonw there is no console
    (sys.stdout is None), so then only the bridge and the file sink exist."""
    logger.remove()
    if sys.stdout is not None:
        logger.add(sys.stdout, format=LOG_FORMAT, level=level, colorize=False)
    logging.basicConfig(handlers=[InterceptHandler()], level=level, force=True)


def addFileSink(path) -> int:
    """session.log: rewritten from scratch on every start, one line at a time so a
    crash leaves its last entries in the file. Returns the sink's id."""
    return logger.add(path, format=LOG_FORMAT, level=logging.INFO, mode="w",
                      encoding="utf-8", colorize=False)
