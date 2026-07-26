# Logging setup with UTC timestamps and rotating file output.
"""
Provide reusable project logging setup.

This module contains a UTC formatter and a logger factory with console and file
handlers.
"""

import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Adding the UTC note to the logging template
class UTCFormatter(logging.Formatter):
    """
    A formatter that renders log timestamps in UTC.

    Attributes:
        converter (callable): Inherited timestamp conversion hook from logging.
    """

    def formatTime(self, record, datefmt=None):
        """
        Format a log record timestamp as UTC.

        Parameters:
            record (logging.LogRecord): Log record containing the creation time.
            datefmt (str | None): Optional datetime format string.

        Returns:
            str: Formatted UTC timestamp.
        """
        dt = datetime.fromtimestamp(record.created, UTC)

        if datefmt:
            return dt.strftime(datefmt)

        return dt.strftime("%Y-%m-%d %H:%M:%S.%f UTC")


def setup_logger(name: str, log_file: str) -> logging.Logger:
    """
    Create or return a configured project logger.

    Parameters:
        name (str): Logger name.
        log_file (str): Log file path.

    Returns:
        logging.Logger: Configured logger instance.
    """
    Path("logs").mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = UTCFormatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5_000_000,
        backupCount=20,
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
