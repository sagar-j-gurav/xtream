"""
Logging Configuration for TESS
Structured logging with correlation IDs
"""
import logging
import sys
from typing import Optional
from contextvars import ContextVar
import structlog
from pythonjsonlogger import jsonlogger

from src.config.settings import get_settings
from src.config.constants import LOG_FORMAT, LOG_DATE_FORMAT

# Context variable for correlation ID
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context"""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context"""
    correlation_id_ctx.set(correlation_id)


def setup_logging() -> None:
    """
    Setup application logging with structured logs

    Configures both standard logging and structlog for
    consistent structured logging across the application
    """
    settings = get_settings()

    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_correlation_id,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log event"""
    corr_id = get_correlation_id()
    if corr_id:
        event_dict["correlation_id"] = corr_id
    return event_dict


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        structlog.BoundLogger: Configured logger
    """
    return structlog.get_logger(name)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for production logging"""

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

        # Add correlation ID if available
        corr_id = get_correlation_id()
        if corr_id:
            log_record['correlation_id'] = corr_id


def setup_json_logging() -> None:
    """
    Setup JSON logging for production environments

    Uses JSON format for easier log aggregation and analysis
    """
    settings = get_settings()

    # Create JSON formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(logger)s %(message)s'
    )

    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, settings.log_level))


# Initialize logging based on environment
def init_logging() -> None:
    """Initialize logging based on environment"""
    settings = get_settings()

    if settings.is_production:
        setup_json_logging()
    else:
        setup_logging()
