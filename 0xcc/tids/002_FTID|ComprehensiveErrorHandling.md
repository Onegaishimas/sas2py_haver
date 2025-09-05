# Technical Implementation Document: Comprehensive Error Handling Framework

## 1. Implementation Strategy

### Development Approach
**Methodology**: Exception-first design with comprehensive error context preservation
**Order of Implementation**: Exception hierarchy → Decorator framework → Context management → Integration
**Integration Strategy**: Decorator pattern applied to existing methods without breaking changes
**Risk Mitigation**: Fail-safe error handling that never causes secondary failures

### Coding Patterns
**Design Patterns**: Decorator Pattern, Context Manager Pattern, Factory Pattern for error creation
**Code Organization**: Centralized exception hierarchy with specialized error handling utilities
**Naming Conventions**: Error classes end with "Error", decorators prefixed with "handle_"
**Documentation Standards**: Google-style docstrings with comprehensive error scenario documentation

## 2. Code Structure

### Directory Structure
```
src/federal_reserve_etl/utils/
├── exceptions.py                 # Exception hierarchy and factory functions
├── error_handling.py            # Decorators and context managers
└── type_definitions.py          # Error context type definitions
```

### Key Class Definitions

#### Exception Hierarchy Implementation
```python
# utils/exceptions.py
import uuid
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

class FederalReserveETLError(Exception):
    """
    Base exception class with comprehensive context preservation.
    
    Features:
    - Automatic error ID generation for tracking
    - Structured context information
    - Serializable error data for logging
    - User-friendly error messages with suggestions
    """
    
    def __init__(self, 
                 message: str, 
                 context: Optional[Dict[str, Any]] = None,
                 suggestion: Optional[str] = None,
                 error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion
        self.error_code = error_code or self.__class__.__name__.upper()
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        
        # Add automatic context information
        self.context.update({
            'error_id': self.error_id,
            'timestamp': self.timestamp,
            'error_type': self.__class__.__name__
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and serialization"""
        return {
            'error_id': self.error_id,
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'suggestion': self.suggestion,
            'context': self.context,
            'timestamp': self.timestamp
        }
    
    def __str__(self) -> str:
        """User-friendly string representation"""
        base_msg = f"{self.message}"
        if self.suggestion:
            base_msg += f"\nSuggestion: {self.suggestion}"
        base_msg += f"\nError ID: {self.error_id}"
        return base_msg

class ConnectionError(FederalReserveETLError):
    """Network connectivity and API endpoint issues"""
    
    def __init__(self, message: str, endpoint: Optional[str] = None, 
                 status_code: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        if endpoint:
            self.context['endpoint'] = endpoint
        if status_code:
            self.context['status_code'] = status_code

class AuthenticationError(FederalReserveETLError):
    """API credential validation and authentication failures"""
    
    def __init__(self, message: str, api_source: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if api_source:
            self.context['api_source'] = api_source
            
    def get_setup_guidance(self) -> List[str]:
        """Return setup steps for resolving authentication issues"""
        api_source = self.context.get('api_source', 'API')
        if api_source.upper() == 'FRED':
            return [
                "1. Register at https://fred.stlouisfed.org/docs/api/api_key.html",
                "2. Set environment variable: export FRED_API_KEY='your_key_here'",
                "3. Restart the application to load the new configuration"
            ]
        elif api_source.upper() == 'HAVER':
            return [
                "1. Obtain Haver Analytics credentials from your subscription",
                "2. Set environment variables: HAVER_USERNAME and HAVER_PASSWORD",
                "3. Verify network access to Haver servers"
            ]
        return ["Contact your system administrator for API credentials"]

class DataRetrievalError(FederalReserveETLError):
    """Data source specific errors and malformed responses"""
    
    def __init__(self, message: str, variable_codes: Optional[List[str]] = None,
                 date_range: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if variable_codes:
            self.context['variable_codes'] = variable_codes
        if date_range:
            self.context['date_range'] = date_range

class ValidationError(FederalReserveETLError):
    """Input parameter validation and data format issues"""
    
    def __init__(self, message: str, invalid_params: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, **kwargs)
        if invalid_params:
            self.context['invalid_params'] = invalid_params

class RateLimitError(FederalReserveETLError):
    """API rate limiting with retry-after information"""
    
    def __init__(self, message: str, retry_after: Optional[float] = None,
                 requests_per_period: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        if retry_after:
            self.context['retry_after'] = retry_after
        if requests_per_period:
            self.context['requests_per_period'] = requests_per_period

class ConfigurationError(FederalReserveETLError):
    """System configuration issues and missing settings"""
    
    def __init__(self, message: str, missing_config: Optional[List[str]] = None, **kwargs):
        super().__init__(message, **kwargs)
        if missing_config:
            self.context['missing_config'] = missing_config

# Factory functions for common error scenarios
def create_connection_error(endpoint: str, status_code: int, response_text: str) -> ConnectionError:
    """Factory function for API connection errors"""
    return ConnectionError(
        message=f"Failed to connect to {endpoint} (HTTP {status_code})",
        endpoint=endpoint,
        status_code=status_code,
        context={'response_text': response_text[:500]},  # Truncate long responses
        suggestion="Check network connectivity and API endpoint availability"
    )

def create_auth_error(api_source: str, error_details: str) -> AuthenticationError:
    """Factory function for authentication errors"""
    return AuthenticationError(
        message=f"{api_source} authentication failed: {error_details}",
        api_source=api_source,
        suggestion="Verify API credentials are correctly configured"
    )
```

#### Error Handling Decorator Implementation
```python
# utils/error_handling.py
import asyncio
import functools
import random
import time
import logging
from typing import Type, Tuple, Callable, Any, Optional
from .exceptions import FederalReserveETLError, RateLimitError, ConnectionError

class ErrorContext:
    """
    Context manager for operation tracking and resource cleanup.
    
    Features:
    - Automatic operation timing
    - Error context preservation
    - Resource cleanup guarantees
    - Integration with logging system
    """
    
    def __init__(self, operation_name: str, logger: Optional[logging.Logger] = None, **context_data):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger(__name__)
        self.context_data = context_data
        self.start_time = None
        self.error_occurred = False
        self.operation_id = str(uuid.uuid4())
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting operation: {self.operation_name}", 
                        extra={'operation_id': self.operation_id, **self.context_data})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0
        
        if exc_type is None:
            self.logger.info(f"Operation completed: {self.operation_name}", 
                           extra={'operation_id': self.operation_id, 
                                'duration': duration, **self.context_data})
        else:
            self.error_occurred = True
            self.logger.error(f"Operation failed: {self.operation_name}",
                            extra={'operation_id': self.operation_id,
                                 'duration': duration,
                                 'error_type': exc_type.__name__,
                                 'error_message': str(exc_val),
                                 **self.context_data})
        
        # Return False to propagate exceptions
        return False

def handle_api_errors(max_retries: int = 3,
                     backoff_base: float = 1.0,
                     backoff_max: float = 60.0,
                     retry_exceptions: Tuple[Type[Exception], ...] = (ConnectionError, RateLimitError),
                     logger: Optional[logging.Logger] = None):
    """
    Decorator for comprehensive API error handling with exponential backoff.
    
    Features:
    - Configurable retry logic with exponential backoff
    - Rate limit specific handling with retry-after respect
    - Jitter to prevent thundering herd problems
    - Comprehensive error logging with context
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_base: Base delay for exponential backoff (seconds)
        backoff_max: Maximum delay between retries (seconds)
        retry_exceptions: Exception types that should trigger retries
        logger: Logger instance for error reporting
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if logger is None:
                func_logger = logging.getLogger(func.__module__)
            else:
                func_logger = logger
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        func_logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        func_logger.error(f"Function {func.__name__} failed after {max_retries + 1} attempts")
                        raise
                    
                    # Calculate backoff delay
                    if isinstance(e, RateLimitError) and hasattr(e, 'context') and 'retry_after' in e.context:
                        # Respect API-provided retry-after header
                        delay = float(e.context['retry_after'])
                    else:
                        # Exponential backoff with jitter
                        delay = min(backoff_base * (2 ** attempt), backoff_max)
                        jitter = delay * 0.1 * random.random()  # Up to 10% jitter
                        delay += jitter
                    
                    func_logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt + 1}, retrying in {delay:.2f} seconds",
                        extra={
                            'attempt': attempt + 1,
                            'max_attempts': max_retries + 1,
                            'delay': delay,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    )
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    # Non-retryable exception
                    func_logger.error(f"Function {func.__name__} failed with non-retryable error: {e}")
                    raise
            
            # This should never be reached due to the raise in the loop
            raise last_exception
        
        # Preserve original function metadata
        wrapper.__wrapped__ = func
        return wrapper
    
    return decorator

# Async version of the decorator
def handle_async_api_errors(max_retries: int = 3,
                           backoff_base: float = 1.0,
                           backoff_max: float = 60.0,
                           retry_exceptions: Tuple[Type[Exception], ...] = (ConnectionError, RateLimitError),
                           logger: Optional[logging.Logger] = None):
    """Async version of handle_api_errors decorator"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if logger is None:
                func_logger = logging.getLogger(func.__module__)
            else:
                func_logger = logger
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        func_logger.info(f"Async function {func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        func_logger.error(f"Async function {func.__name__} failed after {max_retries + 1} attempts")
                        raise
                    
                    # Calculate backoff delay (same logic as sync version)
                    if isinstance(e, RateLimitError) and hasattr(e, 'context') and 'retry_after' in e.context:
                        delay = float(e.context['retry_after'])
                    else:
                        delay = min(backoff_base * (2 ** attempt), backoff_max)
                        jitter = delay * 0.1 * random.random()
                        delay += jitter
                    
                    func_logger.warning(
                        f"Async function {func.__name__} failed on attempt {attempt + 1}, retrying in {delay:.2f} seconds",
                        extra={
                            'attempt': attempt + 1,
                            'max_attempts': max_retries + 1,
                            'delay': delay,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    )
                    
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    func_logger.error(f"Async function {func.__name__} failed with non-retryable error: {e}")
                    raise
            
            raise last_exception
        
        wrapper.__wrapped__ = func
        return wrapper
    
    return decorator
```

## 3. Key Algorithms

### Exponential Backoff with Jitter
```python
def calculate_backoff_delay(attempt: int, base_delay: float, max_delay: float, jitter_factor: float = 0.1) -> float:
    """
    Calculate exponential backoff delay with jitter to prevent thundering herd.
    
    Algorithm: delay = min(base * 2^attempt, max) + random_jitter
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    # Basic exponential backoff
    exponential_delay = base_delay * (2 ** attempt)
    
    # Cap at maximum delay
    capped_delay = min(exponential_delay, max_delay)
    
    # Add jitter to prevent synchronized retries
    jitter = capped_delay * jitter_factor * random.random()
    
    return capped_delay + jitter

def should_retry_error(exception: Exception, retry_exceptions: Tuple[Type[Exception], ...]) -> bool:
    """
    Determine if an exception should trigger a retry attempt.
    
    Logic:
    1. Check if exception type matches retry_exceptions
    2. For HTTP errors, check if status code is retryable (5xx, 429)
    3. For rate limit errors, always retry with proper delay
    """
    if isinstance(exception, retry_exceptions):
        return True
    
    # Special handling for HTTP errors
    if hasattr(exception, 'context') and 'status_code' in exception.context:
        status_code = exception.context['status_code']
        # Retry on server errors (5xx) and rate limit (429)
        return status_code >= 500 or status_code == 429
    
    return False
```

### Error Context Aggregation
```python
class ErrorContextAggregator:
    """
    Aggregates error context across multiple retry attempts for debugging.
    """
    
    def __init__(self):
        self.attempts = []
        self.total_duration = 0.0
        self.final_error = None
    
    def add_attempt(self, attempt_number: int, error: Exception, duration: float):
        """Record an error attempt with timing information"""
        attempt_data = {
            'attempt': attempt_number,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if hasattr(error, 'context'):
            attempt_data['error_context'] = error.context
        
        self.attempts.append(attempt_data)
        self.total_duration += duration
    
    def set_final_error(self, error: Exception):
        """Set the final error after all retries exhausted"""
        self.final_error = error
        
        # Enhance final error with retry history
        if hasattr(error, 'context'):
            error.context['retry_history'] = {
                'total_attempts': len(self.attempts),
                'total_duration': self.total_duration,
                'attempts': self.attempts
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all retry attempts"""
        return {
            'total_attempts': len(self.attempts),
            'total_duration': self.total_duration,
            'error_types': [attempt['error_type'] for attempt in self.attempts],
            'attempts': self.attempts,
            'final_error': str(self.final_error) if self.final_error else None
        }
```

## 4. Integration Points

### Data Source Integration
```python
# Integration with FRED API client
# data_sources/fred_client.py
from ..utils.error_handling import handle_api_errors, ErrorContext
from ..utils.exceptions import create_connection_error, create_auth_error

class FREDDataSource(DataSource):
    
    @handle_api_errors(max_retries=3, 
                      backoff_base=1.0,
                      retry_exceptions=(ConnectionError, RateLimitError))
    def connect(self) -> None:
        """Connect to FRED API with comprehensive error handling"""
        with ErrorContext("fred_connection", self.logger, api_source="FRED"):
            try:
                # Test API connection with a simple request
                test_response = self.session.get(
                    f"{self.base_url}/series/categories",
                    params={'api_key': self.api_key, 'file_type': 'json', 'limit': 1},
                    timeout=self.timeout
                )
                
                if test_response.status_code == 400:
                    raise create_auth_error("FRED", "Invalid API key format")
                elif test_response.status_code == 403:
                    raise create_auth_error("FRED", "API key denied access")
                elif test_response.status_code != 200:
                    raise create_connection_error(
                        self.base_url, 
                        test_response.status_code, 
                        test_response.text
                    )
                
                self.connected = True
                self.logger.info("Successfully connected to FRED API")
                
            except requests.RequestException as e:
                raise ConnectionError(
                    f"Network error connecting to FRED API: {str(e)}",
                    context={'base_url': self.base_url},
                    suggestion="Check internet connectivity and FRED API status"
                )
    
    @handle_api_errors(max_retries=3, backoff_base=2.0)
    def get_data(self, variables: Union[str, List[str]], 
                 start_date: Union[str, datetime], 
                 end_date: Union[str, datetime]) -> pd.DataFrame:
        """Get data with comprehensive error handling and validation"""
        
        with ErrorContext("fred_data_extraction", self.logger, 
                         variables=variables, 
                         date_range=f"{start_date} to {end_date}"):
            
            # Input validation with detailed error messages
            validated_vars = self._validate_variables(variables)
            validated_dates = self._validate_dates(start_date, end_date)
            
            # Rate limiting check
            self._enforce_rate_limit()
            
            try:
                # API request implementation with error handling
                return self._fetch_series_data(validated_vars, validated_dates)
                
            except requests.Timeout:
                raise ConnectionError(
                    "FRED API request timed out",
                    context={'timeout_seconds': self.timeout},
                    suggestion="Try reducing the date range or check FRED API status"
                )
```

### Configuration Integration
```python
# Integration with configuration management
# config.py
from .utils.exceptions import ConfigurationError

def validate_fred_configuration(config: FREDConfig) -> None:
    """Validate FRED configuration with detailed error reporting"""
    missing_configs = []
    
    if not config.api_key:
        missing_configs.append("FRED_API_KEY")
    elif len(config.api_key) != 32:
        raise ConfigurationError(
            "FRED API key must be exactly 32 characters",
            context={'provided_length': len(config.api_key)},
            suggestion="Verify your FRED API key from https://fred.stlouisfed.org"
        )
    
    if not config.base_url:
        missing_configs.append("FRED_BASE_URL")
    
    if missing_configs:
        raise ConfigurationError(
            f"Missing required FRED configuration: {', '.join(missing_configs)}",
            missing_config=missing_configs,
            suggestion="Set the missing environment variables and restart the application"
        )
```

## 5. Configuration

### Error Handling Configuration
```python
# config/error_handling_config.py
from dataclasses import dataclass
from typing import Tuple, Type
import os

@dataclass
class ErrorHandlingConfig:
    # Retry configuration
    default_max_retries: int = int(os.getenv('ETL_MAX_RETRIES', '3'))
    default_backoff_base: float = float(os.getenv('ETL_BACKOFF_BASE', '1.0'))
    default_backoff_max: float = float(os.getenv('ETL_BACKOFF_MAX', '60.0'))
    
    # Rate limiting configuration
    fred_rate_limit_per_minute: int = int(os.getenv('FRED_RATE_LIMIT', '120'))
    haver_rate_limit_per_second: int = int(os.getenv('HAVER_RATE_LIMIT', '10'))
    
    # Error reporting configuration
    enable_error_details: bool = os.getenv('ETL_ERROR_DETAILS', 'true').lower() == 'true'
    max_error_context_size: int = int(os.getenv('ETL_MAX_ERROR_CONTEXT', '10000'))
    
    # Logging integration
    error_log_level: str = os.getenv('ETL_ERROR_LOG_LEVEL', 'ERROR')
    include_stack_trace: bool = os.getenv('ETL_INCLUDE_STACK_TRACE', 'true').lower() == 'true'

# Global configuration instance
error_config = ErrorHandlingConfig()
```

### Environment Variables
```bash
# Error handling configuration
export ETL_MAX_RETRIES=3
export ETL_BACKOFF_BASE=1.0
export ETL_BACKOFF_MAX=60.0

# API specific configuration
export FRED_RATE_LIMIT=120
export HAVER_RATE_LIMIT=10

# Error reporting configuration
export ETL_ERROR_DETAILS=true
export ETL_MAX_ERROR_CONTEXT=10000
export ETL_ERROR_LOG_LEVEL=ERROR
export ETL_INCLUDE_STACK_TRACE=true
```

## 6. Testing Implementation

### Unit Test Structure
```python
# tests/unit/test_error_handling.py
import pytest
import time
from unittest.mock import Mock, patch
from src.federal_reserve_etl.utils.exceptions import *
from src.federal_reserve_etl.utils.error_handling import handle_api_errors, ErrorContext

class TestExceptionHierarchy:
    
    def test_base_exception_context_preservation(self):
        """Test that base exception preserves context information"""
        context = {'operation': 'test', 'params': {'key': 'value'}}
        error = FederalReserveETLError("Test error", context=context, suggestion="Fix it")
        
        assert error.message == "Test error"
        assert error.context['operation'] == 'test'
        assert error.suggestion == "Fix it"
        assert 'error_id' in error.context
        assert 'timestamp' in error.context
    
    def test_exception_serialization(self):
        """Test exception to_dict method"""
        error = ConnectionError("Connection failed", endpoint="https://api.test.com", status_code=500)
        error_dict = error.to_dict()
        
        assert error_dict['error_type'] == 'ConnectionError'
        assert error_dict['message'] == 'Connection failed'
        assert error_dict['context']['endpoint'] == 'https://api.test.com'
        assert error_dict['context']['status_code'] == 500
    
    def test_authentication_error_setup_guidance(self):
        """Test authentication error provides setup guidance"""
        error = AuthenticationError("Auth failed", api_source="FRED")
        guidance = error.get_setup_guidance()
        
        assert len(guidance) == 3
        assert "FRED_API_KEY" in guidance[1]
        assert "fred.stlouisfed.org" in guidance[0]

class TestErrorHandlingDecorator:
    
    @pytest.fixture
    def mock_function(self):
        """Create a mock function for testing decorators"""
        mock_func = Mock()
        mock_func.__name__ = 'test_function'
        mock_func.__module__ = 'test_module'
        return mock_func
    
    def test_successful_execution_no_retry(self, mock_function):
        """Test successful function execution without retries"""
        mock_function.return_value = "success"
        decorated_func = handle_api_errors()(mock_function)
        
        result = decorated_func("arg1", kwarg1="value1")
        
        assert result == "success"
        mock_function.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_retry_on_connection_error(self, mock_function):
        """Test retry behavior on connection errors"""
        # Fail twice, then succeed
        mock_function.side_effect = [
            ConnectionError("Connection failed"),
            ConnectionError("Connection failed"),
            "success"
        ]
        
        decorated_func = handle_api_errors(max_retries=3)(mock_function)
        
        start_time = time.time()
        result = decorated_func()
        duration = time.time() - start_time
        
        assert result == "success"
        assert mock_function.call_count == 3
        assert duration >= 3.0  # Should have backoff delays
    
    def test_max_retries_exhausted(self, mock_function):
        """Test behavior when max retries are exhausted"""
        mock_function.side_effect = ConnectionError("Persistent failure")
        decorated_func = handle_api_errors(max_retries=2)(mock_function)
        
        with pytest.raises(ConnectionError, match="Persistent failure"):
            decorated_func()
        
        assert mock_function.call_count == 3  # Initial + 2 retries
    
    def test_non_retryable_exception(self, mock_function):
        """Test that non-retryable exceptions are not retried"""
        mock_function.side_effect = ValidationError("Invalid input")
        decorated_func = handle_api_errors()(mock_function)
        
        with pytest.raises(ValidationError, match="Invalid input"):
            decorated_func()
        
        assert mock_function.call_count == 1  # No retries

class TestErrorContext:
    
    def test_context_manager_success(self):
        """Test error context manager with successful operation"""
        with patch('logging.getLogger') as mock_logger_factory:
            mock_logger = Mock()
            mock_logger_factory.return_value = mock_logger
            
            with ErrorContext("test_operation", mock_logger, param1="value1"):
                # Simulate work
                time.sleep(0.1)
            
            # Verify logging calls
            assert mock_logger.info.call_count == 2  # Start and completion
            start_call = mock_logger.info.call_args_list[0]
            assert "Starting operation: test_operation" in start_call[0][0]
            
            completion_call = mock_logger.info.call_args_list[1]
            assert "Operation completed: test_operation" in completion_call[0][0]
    
    def test_context_manager_with_exception(self):
        """Test error context manager with exception"""
        with patch('logging.getLogger') as mock_logger_factory:
            mock_logger = Mock()
            mock_logger_factory.return_value = mock_logger
            
            with pytest.raises(ValueError, match="Test error"):
                with ErrorContext("test_operation", mock_logger):
                    raise ValueError("Test error")
            
            # Verify error logging
            assert mock_logger.error.called
            error_call = mock_logger.error.call_args_list[0]
            assert "Operation failed: test_operation" in error_call[0][0]
```

### Integration Test Examples
```python
# tests/integration/test_error_handling_integration.py
import pytest
import requests_mock
from src.federal_reserve_etl.data_sources.fred_client import FREDDataSource
from src.federal_reserve_etl.utils.exceptions import ConnectionError, AuthenticationError

class TestFREDErrorHandlingIntegration:
    
    @pytest.fixture
    def fred_client(self):
        """Create FRED client for testing"""
        from src.federal_reserve_etl.config import get_config_manager
        config = get_config_manager()
        return FREDDataSource(config.get_fred_config())
    
    def test_authentication_error_handling(self, fred_client):
        """Test authentication error handling with real API patterns"""
        with requests_mock.Mocker() as m:
            # Mock invalid API key response
            m.get(requests_mock.ANY, status_code=400, 
                  json={'error_code': 1, 'error_message': 'Bad Request'})
            
            with pytest.raises(AuthenticationError) as exc_info:
                fred_client.connect()
            
            error = exc_info.value
            assert error.context['api_source'] == 'FRED'
            assert len(error.get_setup_guidance()) > 0
            assert 'FRED_API_KEY' in str(error)
    
    def test_rate_limit_error_with_retry_after(self, fred_client):
        """Test rate limiting with retry-after header handling"""
        with requests_mock.Mocker() as m:
            # Mock rate limit response with retry-after header
            m.get(requests_mock.ANY, 
                  status_code=429,
                  headers={'Retry-After': '60'},
                  json={'error_code': 429, 'error_message': 'Rate limit exceeded'})
            
            start_time = time.time()
            
            with pytest.raises(RateLimitError) as exc_info:
                fred_client.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
            
            # Should have attempted retries with backoff
            duration = time.time() - start_time
            assert duration >= 3.0  # Should include backoff delays
            
            error = exc_info.value
            assert error.context.get('retry_after') == 60.0
    
    def test_connection_error_retry_behavior(self, fred_client):
        """Test connection error retry behavior"""
        with requests_mock.Mocker() as m:
            # First two calls fail, third succeeds
            responses = [
                {'status_code': 500, 'json': {'error': 'Internal server error'}},
                {'status_code': 500, 'json': {'error': 'Internal server error'}},
                {'status_code': 200, 'json': {'series': []}}
            ]
            
            for i, response in enumerate(responses):
                m.get(requests_mock.ANY, **response)
            
            # Should eventually succeed after retries
            fred_client.connect()
            assert fred_client.connected
            
            # Verify multiple requests were made
            assert len(m.request_history) == 3
```

## 7. Development Tools

### Required Dependencies
```python
# requirements.txt additions for error handling
typing-extensions>=4.0.0  # Enhanced type hints
structlog>=22.0.0        # Structured logging integration
tenacity>=8.0.0          # Alternative retry library for complex scenarios
```

### Error Analysis Tools
```python
# tools/error_analysis.py
import json
import re
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

class ErrorAnalyzer:
    """Tool for analyzing error patterns and generating reports"""
    
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.errors = []
        self.load_errors()
    
    def load_errors(self):
        """Load errors from structured log files"""
        with open(self.log_file_path, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    if log_entry.get('level') == 'ERROR' and 'error_id' in log_entry:
                        self.errors.append(log_entry)
                except json.JSONDecodeError:
                    continue
    
    def analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns and generate summary report"""
        error_types = defaultdict(int)
        error_sources = defaultdict(int)
        hourly_distribution = defaultdict(int)
        retry_patterns = defaultdict(list)
        
        for error in self.errors:
            # Count error types
            error_type = error.get('error_type', 'Unknown')
            error_types[error_type] += 1
            
            # Count error sources
            api_source = error.get('context', {}).get('api_source', 'Unknown')
            error_sources[api_source] += 1
            
            # Hourly distribution
            timestamp = datetime.fromisoformat(error.get('timestamp', ''))
            hour = timestamp.hour
            hourly_distribution[hour] += 1
            
            # Retry patterns
            retry_history = error.get('context', {}).get('retry_history', {})
            if retry_history:
                total_attempts = retry_history.get('total_attempts', 1)
                retry_patterns[error_type].append(total_attempts)
        
        return {
            'total_errors': len(self.errors),
            'error_types': dict(error_types),
            'error_sources': dict(error_sources),
            'hourly_distribution': dict(hourly_distribution),
            'average_retry_attempts': {
                error_type: sum(attempts) / len(attempts) if attempts else 0
                for error_type, attempts in retry_patterns.items()
            }
        }
    
    def generate_report(self) -> str:
        """Generate human-readable error analysis report"""
        analysis = self.analyze_error_patterns()
        
        report = f"""
# Error Analysis Report
Generated: {datetime.now().isoformat()}
Log File: {self.log_file_path}

## Summary
- Total Errors: {analysis['total_errors']}
- Time Period: Last 24 hours

## Error Types
"""
        
        for error_type, count in sorted(analysis['error_types'].items(), 
                                      key=lambda x: x[1], reverse=True):
            percentage = (count / analysis['total_errors']) * 100
            report += f"- {error_type}: {count} ({percentage:.1f}%)\n"
        
        report += "\n## API Sources\n"
        for source, count in analysis['error_sources'].items():
            percentage = (count / analysis['total_errors']) * 100
            report += f"- {source}: {count} ({percentage:.1f}%)\n"
        
        report += "\n## Retry Patterns\n"
        for error_type, avg_attempts in analysis['average_retry_attempts'].items():
            report += f"- {error_type}: {avg_attempts:.1f} average attempts\n"
        
        return report

# Usage script
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python error_analysis.py <log_file_path>")
        sys.exit(1)
    
    analyzer = ErrorAnalyzer(sys.argv[1])
    print(analyzer.generate_report())
```

### Error Testing Utilities
```python
# tests/utils/error_test_helpers.py
from contextlib import contextmanager
from typing import Type, Any, Dict
from src.federal_reserve_etl.utils.exceptions import FederalReserveETLError

@contextmanager
def assert_raises_with_context(exception_type: Type[Exception], 
                             expected_context: Dict[str, Any] = None):
    """
    Context manager for testing exceptions with specific context.
    
    Usage:
        with assert_raises_with_context(ConnectionError, {'status_code': 500}):
            # Code that should raise ConnectionError with status_code 500
            pass
    """
    try:
        yield
    except exception_type as e:
        if expected_context:
            if hasattr(e, 'context'):
                for key, expected_value in expected_context.items():
                    assert key in e.context, f"Expected context key '{key}' not found"
                    assert e.context[key] == expected_value, \
                        f"Expected {key}={expected_value}, got {e.context[key]}"
            else:
                raise AssertionError(f"Exception {e} has no context attribute")
        return
    
    raise AssertionError(f"Expected {exception_type.__name__} was not raised")

def create_test_error(error_type: str = "ConnectionError", **context) -> FederalReserveETLError:
    """Factory function for creating test errors"""
    error_classes = {
        "ConnectionError": ConnectionError,
        "AuthenticationError": AuthenticationError,
        "DataRetrievalError": DataRetrievalError,
        "ValidationError": ValidationError,
        "RateLimitError": RateLimitError,
        "ConfigurationError": ConfigurationError
    }
    
    error_class = error_classes.get(error_type, FederalReserveETLError)
    return error_class("Test error", context=context)
```

## 8. Code Examples

### Complete Error Handling Integration Example
```python
# Complete example of error handling in FRED client
# data_sources/fred_client.py

import logging
import time
from typing import Union, List, Dict, Any
from datetime import datetime
import pandas as pd
import requests

from .base import DataSource
from ..utils.exceptions import *
from ..utils.error_handling import handle_api_errors, ErrorContext
from ..config import FREDConfig

class FREDDataSource(DataSource):
    """
    FRED API client with comprehensive error handling.
    
    Features:
    - Automatic retry logic with exponential backoff
    - Rate limiting compliance and enforcement
    - Comprehensive error reporting with context
    - Connection health monitoring
    """
    
    def __init__(self, config: FREDConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.rate_limit = config.rate_limit_per_minute
        self.timeout = config.timeout_seconds
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting state
        self._request_times = []
        self._last_request_time = None
        
        # Connection state
        self.connected = False
        self.session = requests.Session()
    
    @handle_api_errors(max_retries=3, backoff_base=1.0)
    def connect(self) -> None:
        """
        Connect to FRED API with comprehensive error handling.
        
        Raises:
            AuthenticationError: Invalid or missing API key
            ConnectionError: Network or API connectivity issues
            ConfigurationError: Invalid configuration parameters
        """
        with ErrorContext("fred_api_connection", self.logger, api_source="FRED"):
            
            # Validate configuration
            self._validate_connection_config()
            
            try:
                # Test API connection with minimal request
                test_response = self.session.get(
                    f"{self.base_url}/series/categories",
                    params={
                        'api_key': self.api_key,
                        'file_type': 'json',
                        'limit': 1
                    },
                    timeout=self.timeout
                )
                
                # Handle different response scenarios
                if test_response.status_code == 400:
                    error_data = test_response.json()
                    if 'api_key' in error_data.get('error_message', '').lower():
                        raise AuthenticationError(
                            "FRED API key is invalid or malformed",
                            api_source="FRED",
                            context={'api_key_length': len(self.api_key)},
                            suggestion="Verify your FRED API key from https://fred.stlouisfed.org"
                        )
                    else:
                        raise ValidationError(
                            f"FRED API request validation failed: {error_data.get('error_message')}",
                            context={'request_params': {'limit': 1}}
                        )
                
                elif test_response.status_code == 403:
                    raise AuthenticationError(
                        "FRED API key access denied",
                        api_source="FRED",
                        suggestion="Check that your FRED API key has proper permissions"
                    )
                
                elif test_response.status_code == 429:
                    retry_after = test_response.headers.get('Retry-After', '60')
                    raise RateLimitError(
                        "FRED API rate limit exceeded during connection test",
                        retry_after=float(retry_after),
                        requests_per_period=self.rate_limit,
                        suggestion=f"Wait {retry_after} seconds before retrying"
                    )
                
                elif test_response.status_code != 200:
                    raise create_connection_error(
                        f"{self.base_url}/series/categories",
                        test_response.status_code,
                        test_response.text[:500]
                    )
                
                # Verify response format
                try:
                    response_data = test_response.json()
                    if 'categories' not in response_data:
                        raise DataRetrievalError(
                            "FRED API returned unexpected response format",
                            context={'response_keys': list(response_data.keys())},
                            suggestion="FRED API may be experiencing issues"
                        )
                except json.JSONDecodeError:
                    raise DataRetrievalError(
                        "FRED API returned non-JSON response",
                        context={'content_type': test_response.headers.get('Content-Type')},
                        suggestion="FRED API may be experiencing issues"
                    )
                
                self.connected = True
                self.logger.info("Successfully connected to FRED API",
                               extra={'api_version': response_data.get('api_version', 'unknown')})
                
            except requests.exceptions.Timeout:
                raise ConnectionError(
                    f"FRED API connection timed out after {self.timeout} seconds",
                    context={'timeout_seconds': self.timeout, 'base_url': self.base_url},
                    suggestion="Check internet connectivity or increase timeout setting"
                )
            
            except requests.exceptions.ConnectionError as e:
                raise ConnectionError(
                    f"Failed to establish connection to FRED API: {str(e)}",
                    context={'base_url': self.base_url},
                    suggestion="Check internet connectivity and FRED API status"
                )
            
            except requests.exceptions.RequestException as e:
                raise ConnectionError(
                    f"Unexpected network error connecting to FRED API: {str(e)}",
                    context={'error_type': type(e).__name__},
                    suggestion="Check network configuration and try again"
                )
    
    def _validate_connection_config(self) -> None:
        """Validate connection configuration parameters"""
        if not self.api_key:
            raise ConfigurationError(
                "FRED API key is required",
                missing_config=['FRED_API_KEY'],
                suggestion="Set FRED_API_KEY environment variable"
            )
        
        if len(self.api_key) != 32:
            raise ConfigurationError(
                f"FRED API key must be exactly 32 characters, got {len(self.api_key)}",
                context={'api_key_length': len(self.api_key)},
                suggestion="Verify your FRED API key format"
            )
        
        if not self.base_url:
            raise ConfigurationError(
                "FRED base URL is required",
                missing_config=['FRED_BASE_URL'],
                suggestion="Set FRED_BASE_URL environment variable"
            )
    
    @handle_api_errors(max_retries=3, backoff_base=2.0)
    def get_data(self, variables: Union[str, List[str]], 
                 start_date: Union[str, datetime], 
                 end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Retrieve data from FRED API with comprehensive error handling.
        
        Args:
            variables: Variable code(s) to retrieve
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            
        Returns:
            DataFrame with retrieved data
            
        Raises:
            ValidationError: Invalid input parameters
            DataRetrievalError: Data retrieval or processing errors
            RateLimitError: API rate limit exceeded
            ConnectionError: Network or API connectivity issues
        """
        # Ensure connection
        if not self.connected:
            raise ConnectionError(
                "Not connected to FRED API",
                suggestion="Call connect() method first"
            )
        
        # Input validation
        validated_variables = self._validate_variables(variables)
        validated_start_date, validated_end_date = self._validate_dates(start_date, end_date)
        
        with ErrorContext("fred_data_extraction", self.logger,
                         variables=validated_variables,
                         date_range=f"{validated_start_date} to {validated_end_date}"):
            
            all_data = {}
            
            for variable in validated_variables:
                # Rate limiting enforcement
                self._enforce_rate_limit()
                
                try:
                    series_data = self._fetch_single_series(
                        variable, validated_start_date, validated_end_date
                    )
                    all_data[variable] = series_data
                    
                    self.logger.debug(f"Successfully retrieved data for {variable}",
                                    extra={'data_points': len(series_data)})
                
                except Exception as e:
                    # Add context to any errors that occur during individual series fetch
                    if hasattr(e, 'context'):
                        e.context['current_variable'] = variable
                        e.context['completed_variables'] = list(all_data.keys())
                    raise
            
            # Convert to DataFrame with proper formatting
            return self._format_dataframe(all_data, validated_start_date, validated_end_date)
    
    def _enforce_rate_limit(self) -> None:
        """Enforce FRED API rate limiting with proper delays"""
        current_time = time.time()
        
        # Clean old request times (outside the 1-minute window)
        cutoff_time = current_time - 60.0
        self._request_times = [t for t in self._request_times if t > cutoff_time]
        
        # Check if we're at the rate limit
        if len(self._request_times) >= self.rate_limit:
            oldest_request = min(self._request_times)
            delay_needed = 60.0 - (current_time - oldest_request)
            
            if delay_needed > 0:
                self.logger.warning(f"Rate limit reached, waiting {delay_needed:.2f} seconds",
                                  extra={'current_requests': len(self._request_times),
                                        'rate_limit': self.rate_limit})
                
                raise RateLimitError(
                    f"FRED API rate limit of {self.rate_limit} requests per minute exceeded",
                    retry_after=delay_needed,
                    requests_per_period=self.rate_limit,
                    context={'current_requests': len(self._request_times)},
                    suggestion=f"Wait {delay_needed:.2f} seconds before making more requests"
                )
        
        # Record this request
        self._request_times.append(current_time)
        self._last_request_time = current_time
```

## 9. Performance Implementation

### Efficient Error Context Management
```python
# Performance-optimized error context handling
class LightweightErrorContext:
    """Lightweight error context for high-frequency operations"""
    
    __slots__ = ['operation_name', 'start_time', 'context_data', '_logger_name']
    
    def __init__(self, operation_name: str, logger_name: str = None):
        self.operation_name = operation_name
        self.start_time = None
        self.context_data = {}
        self._logger_name = logger_name
    
    def add_context(self, **context):
        """Add context data efficiently"""
        self.context_data.update(context)
        return self
    
    def __enter__(self):
        self.start_time = time.perf_counter()  # Higher precision timer
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and self._logger_name:
            duration = time.perf_counter() - self.start_time
            logger = logging.getLogger(self._logger_name)
            logger.error(f"Operation {self.operation_name} failed",
                        extra={'duration': duration, **self.context_data})
        return False

# Memory-efficient exception caching
class ErrorCacheManager:
    """Manage error caching to prevent memory leaks"""
    
    def __init__(self, max_errors: int = 1000, cleanup_interval: float = 3600):
        self.max_errors = max_errors
        self.cleanup_interval = cleanup_interval
        self._error_cache = {}
        self._last_cleanup = time.time()
    
    def cache_error(self, error: FederalReserveETLError):
        """Cache error with automatic cleanup"""
        current_time = time.time()
        
        # Periodic cleanup
        if current_time - self._last_cleanup > self.cleanup_interval:
            self._cleanup_cache()
            self._last_cleanup = current_time
        
        # Add to cache with timestamp
        self._error_cache[error.error_id] = {
            'error': error,
            'timestamp': current_time
        }
        
        # Enforce size limit
        if len(self._error_cache) > self.max_errors:
            self._evict_oldest()
    
    def _cleanup_cache(self):
        """Remove old errors from cache"""
        current_time = time.time()
        cutoff_time = current_time - self.cleanup_interval
        
        to_remove = [
            error_id for error_id, data in self._error_cache.items()
            if data['timestamp'] < cutoff_time
        ]
        
        for error_id in to_remove:
            del self._error_cache[error_id]
    
    def _evict_oldest(self):
        """Evict oldest 10% of cached errors"""
        if not self._error_cache:
            return
        
        sorted_errors = sorted(
            self._error_cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        
        evict_count = max(1, len(sorted_errors) // 10)
        for i in range(evict_count):
            del self._error_cache[sorted_errors[i][0]]
```

## 10. Deployment Considerations

### Production Error Handling Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  federal-reserve-etl:
    build: .
    environment:
      # Error handling configuration
      - ETL_MAX_RETRIES=5
      - ETL_BACKOFF_BASE=2.0
      - ETL_BACKOFF_MAX=120.0
      - ETL_ERROR_DETAILS=true
      - ETL_INCLUDE_STACK_TRACE=false  # Disable in production
      
      # API configuration
      - FRED_RATE_LIMIT=120
      - HAVER_RATE_LIMIT=10
      
      # Logging configuration
      - ETL_ERROR_LOG_LEVEL=ERROR
      - LOG_FORMAT=json
    
    # Health check with error monitoring
    healthcheck:
      test: ["CMD", "python", "-c", "from src.federal_reserve_etl.utils.exceptions import FederalReserveETLError; print('Error handling OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
    
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

### Monitoring Integration
```python
# monitoring/error_metrics.py
import time
from collections import defaultdict, deque
from typing import Dict, Any
import threading

class ErrorMetricsCollector:
    """Collect and expose error metrics for monitoring systems"""
    
    def __init__(self, window_size: int = 3600):  # 1 hour window
        self.window_size = window_size
        self._error_counts = defaultdict(lambda: deque())
        self._error_rates = {}
        self._lock = threading.RLock()
    
    def record_error(self, error_type: str, timestamp: float = None):
        """Record an error occurrence"""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            self._error_counts[error_type].append(timestamp)
            self._cleanup_old_errors(error_type, timestamp)
    
    def _cleanup_old_errors(self, error_type: str, current_time: float):
        """Remove errors outside the time window"""
        cutoff_time = current_time - self.window_size
        error_queue = self._error_counts[error_type]
        
        while error_queue and error_queue[0] < cutoff_time:
            error_queue.popleft()
    
    def get_error_rate(self, error_type: str) -> float:
        """Get current error rate (errors per minute)"""
        with self._lock:
            current_time = time.time()
            self._cleanup_old_errors(error_type, current_time)
            
            error_count = len(self._error_counts[error_type])
            return (error_count / self.window_size) * 60  # Convert to per minute
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all error metrics for monitoring export"""
        with self._lock:
            current_time = time.time()
            metrics = {}
            
            for error_type in self._error_counts:
                self._cleanup_old_errors(error_type, current_time)
                error_count = len(self._error_counts[error_type])
                
                metrics[f"error_rate_{error_type.lower()}"] = (error_count / self.window_size) * 60
                metrics[f"error_count_{error_type.lower()}"] = error_count
            
            return metrics

# Global metrics collector instance
error_metrics = ErrorMetricsCollector()

# Integration with exception handling
def record_error_metric(error: FederalReserveETLError):
    """Record error in metrics system"""
    error_metrics.record_error(error.__class__.__name__)
```

---

**Document Status**: ✅ Complete - Production Implementation Guide  
**Last Updated**: September 1, 2025  
**Version**: 1.0 (Post-Implementation Documentation)  
**Implementation Files**: 
- `src/federal_reserve_etl/utils/exceptions.py` (Exception hierarchy and factories)
- `src/federal_reserve_etl/utils/error_handling.py` (Decorators and context managers)
- Integration across all data source clients and system components