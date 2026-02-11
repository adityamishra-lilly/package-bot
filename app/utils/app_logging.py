"""
This module sets up a custom logging configuration that formats log messages with timestamps in Eastern Daylight Time (EDT).
The log messages include the timestamp, log level, filename, function name, line number, and the actual log message. 
The logs are output to standard output (stdout) and are set to the DEBUG level, allowing for detailed logging during development and troubleshooting.
"""
import logging
import sys
from datetime import datetime, timedelta, timezone

EDT = timezone(timedelta(hours=-4))


def custom_time(*_):
    """Return the current time in EDT as a timetuple for logging."""
    return datetime.now(EDT).timetuple()


logging.Formatter.converter = custom_time
logging.basicConfig(
    format=(
        "%(asctime)s | %(levelname)s | %(filename)s | %(funcName)s() | "
        "line %(lineno)d | %(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)