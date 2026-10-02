import logging

from pathlib import Path

from datetime import datetime


class Logger:

    def __init__(self):

        log_dir = Path.home() / ".robocap_decryptor" / "logs"

        log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        logfile = log_dir / f"{datetime.now():%Y-%m-%d}.log"

        self.logger = logging.getLogger("RobocapDecryptor")

        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:

            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s"
            )

            file_handler = logging.FileHandler(logfile)

            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def info(self, message):

        self.logger.info(message)

    def warning(self, message):

        self.logger.warning(message)

    def error(self, message):

        self.logger.error(message)

    def exception(self, message):

        self.logger.exception(message)
