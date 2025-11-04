import logging
import os
from datetime import datetime

from rich.logging import RichHandler

logger = logging.getLogger("rich")


def setup_logging(repo_name: str, logs_dir: str) -> None:
    """
    Configure logging:
    - console output using RichHandler
    - file output to logs/<repo_name>_<timestamp>.log
    """
    logger.setLevel(logging.DEBUG)

    # Console handler (Rich)
    console_handler = RichHandler(rich_tracebacks=True)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(message)s", datefmt="[%X]")
    console_handler.setFormatter(console_formatter)

    # File handler
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = f"{repo_name}_{timestamp}.log"
    filename = os.path.join(logs_dir, log_file)
    file_handler = logging.FileHandler(filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Attach handlers
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {filename}")
