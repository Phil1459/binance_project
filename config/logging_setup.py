import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Adding the UTC note to the logging template
class UTCFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, UTC)

        if datefmt:
            return dt.strftime(datefmt)

        return dt.strftime("%Y-%m-%d %H:%M:%S.%f UTC")


def setup_logger(name: str, log_file: str) -> logging.Logger:
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
