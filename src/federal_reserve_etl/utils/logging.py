"""
Centralized logging configuration for Federal Reserve ETL Pipeline

Provides consistent logging setup across all modules with both console
and file output, following ADR logging standards.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that forces immediate flushing for proper output ordering"""
    
    def emit(self, record):
        try:
            super().emit(record)
            self.flush()  # Force immediate flush
        except Exception:
            self.handleError(record)


# Global flag to prevent multiple logging initialization
_logging_initialized = False

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    max_log_size_mb: int = 10,
    backup_count: int = 5,
    force_reinit: bool = False
) -> logging.Logger:
    """
    Set up centralized logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, creates timestamped file
        enable_console: Whether to enable console output
        max_log_size_mb: Maximum log file size in MB before rotation
        backup_count: Number of backup log files to keep
        force_reinit: Force re-initialization even if already initialized
        
    Returns:
        Configured logger instance
    """
    global _logging_initialized
    
    # Prevent multiple initialization unless forced
    if _logging_initialized and not force_reinit:
        return logging.getLogger("federal_reserve_etl")
    
    # Clear existing handlers to prevent duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create main logger
    logger = logging.getLogger("federal_reserve_etl")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter for structured logging
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler - use custom flushing handler for proper ordering
    if enable_console:
        console_handler = FlushingStreamHandler(stream=sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)  # Console shows INFO and above
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file is None:
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"federal_reserve_etl_{timestamp}.log")
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_log_size_mb * 1024 * 1024,  # Convert MB to bytes
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # File logs everything
    logger.addHandler(file_handler)
    
    # Log initial setup message (only on first initialization)
    logger.info(f"🚀 Federal Reserve ETL Pipeline logging initialized")
    logger.info(f"   • Log Level: {log_level.upper()}")
    logger.info(f"   • Console Output: {'Enabled' if enable_console else 'Disabled'}")
    logger.info(f"   • Log File: {log_file}")
    logger.debug(f"   • Max Log Size: {max_log_size_mb}MB")
    logger.debug(f"   • Backup Count: {backup_count}")
    
    # Mark logging as initialized
    _logging_initialized = True
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for specific module
    
    Args:
        name: Module or component name
        
    Returns:
        Child logger instance
    """
    return logging.getLogger(f"federal_reserve_etl.{name}")


def log_api_request(logger: logging.Logger, method: str, url: str, params: dict = None):
    """
    Log API request details for debugging and monitoring
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        params: Request parameters dictionary
    """
    logger.debug(f"🌐 API Request: {method} {url}")
    if params:
        # Log parameters but mask sensitive data
        safe_params = {k: "***" if "key" in k.lower() or "password" in k.lower() else v 
                      for k, v in params.items()}
        logger.debug(f"   Parameters: {safe_params}")


def log_api_response(logger: logging.Logger, status_code: int, response_size: int = None):
    """
    Log API response details
    
    Args:
        logger: Logger instance
        status_code: HTTP status code
        response_size: Response size in bytes (optional)
    """
    if 200 <= status_code < 300:
        level = logging.INFO
        emoji = "✅"
    elif 400 <= status_code < 500:
        level = logging.WARNING
        emoji = "⚠️"
    else:
        level = logging.ERROR
        emoji = "❌"
    
    msg = f"{emoji} API Response: {status_code}"
    if response_size:
        msg += f" ({response_size:,} bytes)"
    
    logger.log(level, msg)


def log_data_processing(logger: logging.Logger, operation: str, input_count: int, output_count: int):
    """
    Log data processing operation results
    
    Args:
        logger: Logger instance
        operation: Description of operation
        input_count: Number of input records/observations
        output_count: Number of output records/observations
    """
    percentage = (output_count / input_count * 100) if input_count > 0 else 0
    logger.info(f"🔄 {operation}: {input_count:,} → {output_count:,} ({percentage:.1f}%)")


def log_error_with_context(logger: logging.Logger, error: Exception, context: str):
    """
    Log error with contextual information
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Context description where error occurred
    """
    logger.error(f"❌ Error in {context}: {type(error).__name__}: {str(error)}")
    logger.debug(f"   Full error details:", exc_info=True)


# Create module-level logger for this utils module
_logger = get_logger("utils.logging")