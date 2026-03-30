import sys
import logging
import structlog
from config.settings import get_settings

def setup_logging(level: str = None) -> None:
    settings = get_settings()
    log_level = level or settings.LOG_LEVEL
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=getattr(logging, log_level.upper()))
    for noisy in ("azure.core", "azure.storage", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
