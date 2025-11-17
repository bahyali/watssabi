import logging
import sys

import structlog


def setup_logging():
    """
    Configures structured logging for the application.

    This setup ensures that all logs are processed by structlog and
    rendered as JSON, which is ideal for production environments and log analysis.
    """
    # Configure the standard logging library to be a target for structlog.
    # This allows logs from other libraries (like uvicorn, sqlalchemy) to be
    # processed by structlog as well.
    structlog.configure(
        processors=[
            # Add context variables to the log record.
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            # Format exceptions if they are present.
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Render the final log record as JSON.
            structlog.processors.JSONRenderer(),
        ],
        # Use a wrapper class that is compatible with the standard library's logger.
        wrapper_class=structlog.stdlib.BoundLogger,
        # Use a logger factory that is compatible with the standard library.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache the logger factory for performance.
        cache_logger_on_first_use=True,
    )

    # Get the root logger and configure it.
    root_logger = logging.getLogger()
    # Set the default log level.
    root_logger.setLevel(logging.INFO)
    # Clear any existing handlers.
    root_logger.handlers.clear()
    # Add a stream handler to output logs to stdout.
    handler = logging.StreamHandler(sys.stdout)
    root_logger.addHandler(handler)
