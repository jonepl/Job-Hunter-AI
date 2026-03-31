"""Logging configuration for the Job Hunter AI Agent.

Sets up console and file handlers with a consistent formatter.
Called once at application startup before any other logging occurs.
"""

import logging
import os
import sys
from datetime import datetime


def configure_logging() -> None:
    """Configure console and file logging.

    Writes INFO+ to stdout and to logs/agent_<timestamp>.log.
    Creates the logs/ directory if it does not exist.
    """
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join("logs", f"agent_{timestamp}.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
