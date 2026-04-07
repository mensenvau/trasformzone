import sys
import logging
from config.settings import get_settings

def setup_logging(level: str = None) -> None:
    s = get_settings()
    for noisy in ("azure.core", "azure.storage", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.basicConfig(
        level=getattr(logging, (level or s.LOG_LEVEL).upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def get_logger(name: str):
    return logging.getLogger(name)
