"""Logging module for the route listener."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import LOG_BACKUP_COUNT, LOG_FILE_MAX_BYTES


class Logger:
    """Custom logger for the route listener application."""

    def __init__(self, verbose: bool = False, log_file: str = "route_listener.log") -> None:
        """Initialize the logger.

        Args:
            verbose: Whether to enable verbose logging output
            log_file: Path to the log file (default: route_listener.log)
        """
        self.verbose = verbose
        self.log_file = log_file
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up the logging configuration."""
        # Create a formatter
        formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # Create a console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Create a file handler with size limit
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        # Create a logger
        self._logger = logging.getLogger("route_listener")
        self._logger.setLevel(logging.DEBUG)  # Set to DEBUG by default

        # Remove any existing handlers
        self._logger.handlers = []

        # Add handlers
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

        # Log startup message
        self._logger.info(
            f"Logging initialized. Console output enabled. "
            f"File logging to {self.log_file} (100KB limit)"
        )

    # Method names match stdlib logging.Logger so callers can use this drop-in.
    def setLevel(self, level: int) -> None:  # noqa: N802
        """Set the logging level.

        Args:
            level: The logging level to set
        """
        self._logger.setLevel(level)

    def info(self, message: str) -> None:
        """Log an info message.

        Args:
            message: The message to log
        """
        self._logger.info(message)

    def error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: The message to log
        """
        self._logger.error(message)

    def debug(self, message: str) -> None:
        """Log a debug message.

        Args:
            message: The message to log
        """
        self._logger.debug(message)

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802
        """Check if the logger is enabled for the given level.

        Args:
            level: The logging level to check

        Returns:
            True if the logger is enabled for the given level, False otherwise
        """
        return self._logger.isEnabledFor(level)

    def banner(self, message: str) -> None:
        """Log a banner message."""
        self._logger.info(message)

    def packet_info(
        self, src_addr: str, prefix: str, prefix_len: int, router: str | None = None
    ) -> None:
        """Log basic packet information in a single line.

        Args:
            src_addr: Source address of the Router Advertisement
            prefix: The prefix or route
            prefix_len: The prefix length
            router: The router address (if different from source)
        """
        router_str = f" via {router}" if router and router != src_addr else ""
        self._logger.debug(f"🔔 RA from {src_addr}: {prefix}/{prefix_len}{router_str}")

    def ignored_route(self, prefix: str, prefix_len: int, reason: str) -> None:
        """Log ignored route information in a single line.

        Args:
            prefix: The prefix that was ignored
            prefix_len: The prefix length
            reason: The reason for ignoring the route
        """
        self._logger.debug(f"⏭️  Ignored {prefix}/{prefix_len}: {reason}")
