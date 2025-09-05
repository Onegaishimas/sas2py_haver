"""
Custom Exception Classes for Federal Reserve ETL Pipeline

Provides specific exception types for different categories of errors
that can occur during data source operations, enabling targeted
error handling and user feedback.
"""

from typing import Optional, Dict, Any


class FederalReserveETLError(Exception):
    """
    Base exception class for all Federal Reserve ETL operations
    
    All custom exceptions in the pipeline inherit from this base class,
    providing a common interface for error handling and categorization.
    
    Attributes:
        message: Human-readable error message
        error_code: Optional error code for programmatic handling
        context: Additional context information about the error
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base exception
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            context: Additional context information about the error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        """String representation of the error"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"{self.__class__.__name__}("
                f"message='{self.message}', "
                f"error_code='{self.error_code}', "
                f"context={self.context})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization"""
        return {
            "exception_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context
        }


class ConnectionError(FederalReserveETLError):
    """
    Raised when unable to establish connection to data source API
    
    This exception indicates network connectivity issues, API endpoint
    unavailability, or other connection-related problems.
    
    Common scenarios:
    - Network connectivity issues
    - API endpoints unreachable
    - Timeout during connection establishment
    - SSL/TLS certificate problems
    """
    
    def __init__(
        self, 
        message: str, 
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize connection error
        
        Args:
            message: Human-readable error message
            endpoint: API endpoint that failed to connect
            status_code: HTTP status code (if applicable)
            **kwargs: Additional context passed to base class
        """
        context = kwargs.get('context', {})
        if endpoint:
            context['endpoint'] = endpoint
        if status_code:
            context['status_code'] = status_code
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class AuthenticationError(FederalReserveETLError):
    """
    Raised when API authentication fails
    
    This exception indicates problems with API credentials, including
    invalid API keys, expired tokens, or insufficient permissions.
    
    Common scenarios:
    - Invalid or missing API key
    - API key expired or revoked
    - Insufficient permissions for requested operation
    - Authentication server unavailable
    """
    
    def __init__(
        self, 
        message: str, 
        api_key_hint: Optional[str] = None,
        source: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize authentication error
        
        Args:
            message: Human-readable error message
            api_key_hint: Partial API key for debugging (first/last 4 chars)
            source: Data source name where authentication failed
            **kwargs: Additional context passed to base class
        """
        context = kwargs.get('context', {})
        if api_key_hint:
            context['api_key_hint'] = api_key_hint
        if source:
            context['source'] = source
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class DataRetrievalError(FederalReserveETLError):
    """
    Raised when data retrieval from API fails
    
    This exception indicates problems during the data fetching process,
    including API errors, invalid parameters, or data processing issues.
    
    Common scenarios:
    - Invalid variable codes requested
    - Date ranges outside available data
    - API rate limit exceeded
    - Malformed API responses
    - Data processing errors
    """
    
    def __init__(
        self, 
        message: str, 
        variables: Optional[list] = None,
        date_range: Optional[tuple] = None,
        response_status: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize data retrieval error
        
        Args:
            message: Human-readable error message
            variables: List of variable codes that failed
            date_range: Date range tuple (start_date, end_date) that failed
            response_status: HTTP response status code
            **kwargs: Additional context passed to base class
        """
        context = kwargs.get('context', {})
        if variables:
            context['variables'] = variables
        if date_range:
            context['date_range'] = date_range
        if response_status:
            context['response_status'] = response_status
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class ValidationError(FederalReserveETLError):
    """
    Raised when data validation fails
    
    This exception indicates problems with input validation, data format
    validation, or response validation during pipeline operations.
    
    Common scenarios:
    - Invalid date formats
    - Invalid variable codes
    - Malformed API responses
    - Data type mismatches
    - Schema validation failures
    """
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize validation error
        
        Args:
            message: Human-readable error message
            field: Field name that failed validation
            expected: Expected value or format
            actual: Actual value that failed validation
            **kwargs: Additional context passed to base class
        """
        context = kwargs.get('context', {})
        if field:
            context['field'] = field
        if expected is not None:
            context['expected'] = expected
        if actual is not None:
            context['actual'] = actual
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class ConfigurationError(FederalReserveETLError):
    """
    Raised when configuration is invalid or missing
    
    This exception indicates problems with pipeline configuration,
    including missing required settings, invalid configuration values,
    or configuration file issues.
    
    Common scenarios:
    - Missing required configuration parameters
    - Invalid configuration file format
    - Environment variable not set
    - Configuration value out of valid range
    """
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize configuration error
        
        Args:
            message: Human-readable error message
            config_key: Configuration key that caused the error
            config_file: Configuration file path (if applicable)
            **kwargs: Additional context passed to base class
        """
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        if config_file:
            context['config_file'] = config_file
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class RateLimitError(DataRetrievalError):
    """
    Raised when API rate limit is exceeded
    
    This is a specialized data retrieval error that specifically handles
    rate limiting scenarios with additional context about limits and timing.
    
    Common scenarios:
    - API request rate exceeded
    - Daily/monthly quota exceeded
    - Temporary throttling by API provider
    """
    
    def __init__(
        self, 
        message: str, 
        limit: Optional[int] = None,
        reset_time: Optional[int] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize rate limit error
        
        Args:
            message: Human-readable error message
            limit: Rate limit threshold that was exceeded
            reset_time: Unix timestamp when limit resets
            retry_after: Seconds to wait before retrying
            **kwargs: Additional context passed to base class
        """
        context = kwargs.get('context', {})
        if limit:
            context['limit'] = limit
        if reset_time:
            context['reset_time'] = reset_time
        if retry_after:
            context['retry_after'] = retry_after
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


# Convenience functions for common error scenarios

def create_connection_error(endpoint: str, status_code: Optional[int] = None) -> ConnectionError:
    """
    Create a standardized connection error
    
    Args:
        endpoint: API endpoint that failed
        status_code: HTTP status code if available
        
    Returns:
        ConnectionError with standardized message
    """
    if status_code:
        message = f"Failed to connect to {endpoint} (HTTP {status_code})"
        error_code = f"CONN_{status_code}"
    else:
        message = f"Failed to connect to {endpoint}"
        error_code = "CONN_FAILED"
    
    return ConnectionError(
        message=message,
        error_code=error_code,
        endpoint=endpoint,
        status_code=status_code
    )


def create_auth_error(source: str, api_key_hint: Optional[str] = None) -> AuthenticationError:
    """
    Create a standardized authentication error
    
    Args:
        source: Data source name
        api_key_hint: Partial API key for debugging
        
    Returns:
        AuthenticationError with standardized message
    """
    if api_key_hint:
        message = f"Authentication failed for {source} (API key: {api_key_hint})"
    else:
        message = f"Authentication failed for {source}"
    
    return AuthenticationError(
        message=message,
        error_code="AUTH_FAILED",
        source=source,
        api_key_hint=api_key_hint
    )


def create_data_error(variables: list, message: Optional[str] = None) -> DataRetrievalError:
    """
    Create a standardized data retrieval error
    
    Args:
        variables: List of variables that failed
        message: Optional custom message
        
    Returns:
        DataRetrievalError with standardized message
    """
    if not message:
        var_list = ", ".join(variables[:3])  # Show first 3 variables
        if len(variables) > 3:
            var_list += f" (and {len(variables) - 3} more)"
        message = f"Failed to retrieve data for variables: {var_list}"
    
    return DataRetrievalError(
        message=message,
        error_code="DATA_FAILED",
        variables=variables
    )