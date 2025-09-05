"""
Standardized Error Handling Patterns and Logging Integration

Provides consistent error handling patterns, logging integration,
and utilities for graceful error recovery across the Federal Reserve ETL pipeline.
"""

import functools
import traceback
from typing import Callable, Any, Optional, Type, Union, Dict, List
from datetime import datetime

from .exceptions import (
    FederalReserveETLError,
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    ValidationError,
    ConfigurationError,
    RateLimitError
)
from .logging import get_logger, log_error_with_context


def handle_api_errors(
    retry_count: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retriable_exceptions: tuple = (ConnectionError, RateLimitError)
):
    """
    Decorator for standardized API error handling with retry logic
    
    Provides automatic retry with exponential backoff for transient failures,
    comprehensive error logging, and consistent exception handling.
    
    Args:
        retry_count: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Exponential backoff multiplier
        retriable_exceptions: Exception types that should trigger retries
        
    Returns:
        Decorated function with error handling and retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(f"error_handling.{func.__name__}")
            last_exception = None
            
            for attempt in range(retry_count + 1):
                try:
                    # Log attempt for debugging
                    if attempt > 0:
                        logger.info(f"🔄 Retry attempt {attempt}/{retry_count} for {func.__name__}")
                    
                    result = func(*args, **kwargs)
                    
                    # Log successful retry
                    if attempt > 0:
                        logger.info(f"✅ {func.__name__} succeeded after {attempt} retries")
                    
                    return result
                    
                except retriable_exceptions as e:
                    last_exception = e
                    
                    if attempt < retry_count:
                        # Calculate delay with exponential backoff
                        delay = retry_delay * (backoff_factor ** attempt)
                        logger.warning(f"⚠️  {func.__name__} failed (attempt {attempt + 1}), retrying in {delay:.1f}s: {str(e)}")
                        
                        # Handle rate limit specific delays
                        if isinstance(e, RateLimitError) and hasattr(e, 'retry_after'):
                            delay = max(delay, e.context.get('retry_after', delay))
                        
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(f"❌ {func.__name__} failed after {retry_count} retries: {str(e)}")
                        log_error_with_context(logger, e, f"{func.__name__} (all retries exhausted)")
                        raise
                        
                except FederalReserveETLError as e:
                    # Non-retriable ETL errors - log and re-raise immediately
                    log_error_with_context(logger, e, func.__name__)
                    raise
                    
                except Exception as e:
                    # Unexpected errors - wrap and re-raise
                    logger.error(f"❌ Unexpected error in {func.__name__}: {type(e).__name__}: {str(e)}")
                    logger.debug("Full traceback:", exc_info=True)
                    
                    # Wrap unexpected exceptions in our hierarchy
                    wrapped_error = FederalReserveETLError(
                        message=f"Unexpected error in {func.__name__}: {str(e)}",
                        error_code="UNEXPECTED_ERROR",
                        context={
                            "original_exception": type(e).__name__,
                            "function_name": func.__name__,
                            "args": str(args)[:200],  # Truncate for logging
                            "kwargs": str(kwargs)[:200]
                        }
                    )
                    raise wrapped_error from e
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def log_and_handle_error(
    logger_name: str,
    error_message: str,
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True
) -> None:
    """
    Standardized error logging and handling utility
    
    Args:
        logger_name: Name of the logger to use
        error_message: Human-readable error message
        exception: Exception instance (if available)
        context: Additional context information
        reraise: Whether to re-raise the exception after logging
    """
    logger = get_logger(logger_name)
    
    # Create context dictionary
    error_context = context or {}
    if exception:
        error_context.update({
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "timestamp": datetime.now().isoformat()
        })
    
    # Log error with appropriate level
    if isinstance(exception, (ValidationError, ConfigurationError)):
        logger.error(f"❌ {error_message}")
    elif isinstance(exception, (ConnectionError, AuthenticationError)):
        logger.error(f"🔌 {error_message}")
    elif isinstance(exception, DataRetrievalError):
        logger.error(f"📊 {error_message}")
    elif isinstance(exception, RateLimitError):
        logger.warning(f"⏸️  {error_message}")
    else:
        logger.error(f"❌ {error_message}")
    
    # Log context if available
    if error_context:
        logger.debug(f"Error context: {error_context}")
    
    # Log full traceback for debugging
    if exception:
        logger.debug("Full error traceback:", exc_info=True)
    
    # Re-raise if requested
    if reraise and exception:
        raise exception


def safe_execute(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
    default_return: Any = None,
    logger_name: Optional[str] = None,
    error_message: Optional[str] = None
) -> Any:
    """
    Safely execute a function with comprehensive error handling
    
    Args:
        func: Function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        default_return: Value to return if function fails
        logger_name: Logger name for error reporting
        error_message: Custom error message
        
    Returns:
        Function result or default_return if function fails
    """
    kwargs = kwargs or {}
    logger = get_logger(logger_name or "error_handling.safe_execute")
    
    try:
        result = func(*args, **kwargs)
        return result
        
    except FederalReserveETLError as e:
        message = error_message or f"ETL error in {func.__name__}"
        log_and_handle_error(
            logger_name or "error_handling.safe_execute",
            message,
            e,
            reraise=False
        )
        return default_return
        
    except Exception as e:
        message = error_message or f"Unexpected error in {func.__name__}"
        logger.error(f"❌ {message}: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        return default_return


def validate_and_convert_dates(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    date_format: str = "%Y-%m-%d"
) -> tuple:
    """
    Validate and convert date parameters with standardized error handling
    
    Args:
        start_date: Start date string or datetime object
        end_date: End date string or datetime object
        date_format: Expected date format for string inputs
        
    Returns:
        Tuple of (start_datetime, end_datetime)
        
    Raises:
        ValidationError: If date validation fails
    """
    logger = get_logger("error_handling.date_validation")
    
    try:
        # Convert strings to datetime objects
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, date_format)
        else:
            start_dt = start_date
            
        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, date_format)
        else:
            end_dt = end_date
        
        # Validate date logic
        if start_dt >= end_dt:
            raise ValidationError(
                message="Start date must be before end date",
                error_code="INVALID_DATE_RANGE",
                field="date_range",
                expected="start_date < end_date",
                actual=f"start_date={start_dt.date()}, end_date={end_dt.date()}"
            )
        
        # Validate reasonable date bounds
        min_date = datetime(1900, 1, 1)
        max_date = datetime(2030, 12, 31)
        
        if start_dt < min_date or end_dt > max_date:
            raise ValidationError(
                message=f"Dates must be between {min_date.date()} and {max_date.date()}",
                error_code="DATE_OUT_OF_BOUNDS",
                field="date_range",
                expected=f"{min_date.date()} to {max_date.date()}",
                actual=f"{start_dt.date()} to {end_dt.date()}"
            )
        
        logger.debug(f"✅ Date validation passed: {start_dt.date()} to {end_dt.date()}")
        return start_dt, end_dt
        
    except ValueError as e:
        logger.error(f"❌ Date parsing failed: {str(e)}")
        raise ValidationError(
            message=f"Invalid date format: {str(e)}",
            error_code="INVALID_DATE_FORMAT",
            field="date",
            expected=date_format,
            actual=str(e)
        )


def validate_variable_codes(variables: Union[str, List[str]]) -> List[str]:
    """
    Validate and normalize variable codes with standardized error handling
    
    Args:
        variables: Single variable code string or list of variable codes
        
    Returns:
        List of validated variable codes
        
    Raises:
        ValidationError: If variable validation fails
    """
    logger = get_logger("error_handling.variable_validation")
    
    # Convert single string to list
    if isinstance(variables, str):
        var_list = [variables]
    else:
        var_list = list(variables)
    
    # Validate each variable code
    validated_vars = []
    invalid_vars = []
    
    for var in var_list:
        if not isinstance(var, str):
            invalid_vars.append(f"{var} (not string)")
            continue
            
        # Basic variable code validation
        var_clean = var.strip().upper()
        if not var_clean:
            invalid_vars.append(f"'{var}' (empty)")
            continue
            
        if len(var_clean) > 50:  # Reasonable length limit
            invalid_vars.append(f"'{var}' (too long)")
            continue
            
        validated_vars.append(var_clean)
    
    # Report validation results
    if invalid_vars:
        error_msg = f"Invalid variable codes: {', '.join(invalid_vars)}"
        logger.error(f"❌ {error_msg}")
        raise ValidationError(
            message=error_msg,
            error_code="INVALID_VARIABLES",
            field="variables",
            context={
                "valid_variables": validated_vars,
                "invalid_variables": invalid_vars
            }
        )
    
    logger.debug(f"✅ Variable validation passed: {len(validated_vars)} variables")
    return validated_vars


class ErrorContext:
    """
    Context manager for error handling with automatic logging and cleanup
    """
    
    def __init__(
        self,
        operation_name: str,
        logger_name: Optional[str] = None,
        cleanup_func: Optional[Callable] = None
    ):
        """
        Initialize error context manager
        
        Args:
            operation_name: Name of the operation for logging
            logger_name: Logger name to use
            cleanup_func: Optional cleanup function to call on error
        """
        self.operation_name = operation_name
        self.logger = get_logger(logger_name or "error_handling.context")
        self.cleanup_func = cleanup_func
        self.start_time = None
    
    def __enter__(self):
        """Enter context manager"""
        self.start_time = datetime.now()
        self.logger.info(f"🚀 Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager with error handling"""
        duration = datetime.now() - self.start_time if self.start_time else None
        
        if exc_type is None:
            # Success case
            duration_str = f" ({duration.total_seconds():.2f}s)" if duration else ""
            self.logger.info(f"✅ Completed {self.operation_name}{duration_str}")
            return False
        
        # Error case
        duration_str = f" after {duration.total_seconds():.2f}s" if duration else ""
        
        if issubclass(exc_type, FederalReserveETLError):
            self.logger.error(f"❌ {self.operation_name} failed{duration_str}: {str(exc_val)}")
            log_error_with_context(self.logger, exc_val, self.operation_name)
        else:
            self.logger.error(f"❌ {self.operation_name} failed{duration_str}: {exc_type.__name__}: {str(exc_val)}")
            self.logger.debug("Full traceback:", exc_info=True)
        
        # Run cleanup if provided
        if self.cleanup_func:
            try:
                self.logger.debug(f"🧹 Running cleanup for {self.operation_name}")
                self.cleanup_func()
            except Exception as cleanup_error:
                self.logger.error(f"❌ Cleanup failed: {str(cleanup_error)}")
        
        return False  # Don't suppress the exception