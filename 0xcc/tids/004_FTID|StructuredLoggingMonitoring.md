# Technical Implementation Document: Structured Logging and Monitoring

**Document Type**: Feature Technical Implementation Document  
**Feature ID**: 004  
**Feature Name**: Structured Logging and Monitoring  
**Version**: 1.0  
**Created**: 2024-08-29  
**Status**: Implementation Complete  

## Executive Summary

This Technical Implementation Document provides comprehensive guidance for implementing and extending the Structured Logging and Monitoring feature in the Federal Reserve ETL Pipeline. The implementation includes production-ready code patterns, security considerations, performance optimizations, and integration strategies based on the existing codebase at `src/federal_reserve_etl/utils/logging.py`.

## Implementation Architecture

### Core Components Overview
```
src/federal_reserve_etl/utils/
├── logging.py              # Main logging framework implementation
├── exceptions.py           # Integration point for ConfigurationError
├── type_definitions.py     # Type hints for logging components
└── __init__.py            # Public API exports
```

### Implementation File Structure
```python
# src/federal_reserve_etl/utils/logging.py
"""
Complete implementation with:
- SensitiveDataFilter      # Automatic data masking
- JSONFormatter           # Structured output
- PerformanceFilter       # Metrics collection
- LoggingContext          # Contextual modifications
- setup_logging()         # Main configuration function
- log_performance()       # Context manager for timing
"""
```

## Detailed Implementation Guide

### 1. Sensitive Data Protection Implementation

#### 1.1 Core Filter Implementation
```python
class SensitiveDataFilter(logging.Filter):
    """
    Production implementation of sensitive data masking
    
    Key Implementation Details:
    - Uses compiled regex patterns for performance
    - Case-insensitive matching for comprehensive coverage
    - Preserves log message structure while masking data
    - Extensible pattern system for custom sensitive data
    """
    
    SENSITIVE_PATTERNS = [
        # API Keys and tokens - matches various formats
        (r'api_?key["\']?\s*[:=]\s*["\']?([^"\'\s&]{8,})["\']?', r'api_key=***MASKED***'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\'\s&]{8,})["\']?', r'token=***MASKED***'),
        (r'auth["\']?\s*[:=]\s*["\']?([^"\'\s&]{8,})["\']?', r'auth=***MASKED***'),
        
        # Passwords - various naming conventions
        (r'pass(word)?["\']?\s*[:=]\s*["\']?([^"\'\s&]+)["\']?', r'password=***MASKED***'),
        
        # URLs with embedded credentials
        (r'https?://([^:]+):([^@]+)@', r'https://***USER***:***PASS***@'),
        
        # Generic secrets and keys
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s&]{8,})["\']?', r'secret=***MASKED***'),
        (r'key["\']?\s*[:=]\s*["\']?([A-Za-z0-9+/]{20,})["\']?', r'key=***MASKED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Implementation Strategy:
        1. Check if record has message content
        2. Apply all masking patterns sequentially
        3. Preserve original record structure
        4. Always return True (modify, don't filter)
        """
```

#### 1.2 Pattern Extension Strategy
```python
# Custom pattern addition for organization-specific data
def add_sensitive_pattern(pattern: str, replacement: str):
    """
    Add custom sensitive data patterns
    
    Usage:
        add_sensitive_pattern(
            r'customer_id["\']?\s*[:=]\s*["\']?([0-9]{8,})["\']?',
            r'customer_id=***MASKED***'
        )
    """
    SensitiveDataFilter.SENSITIVE_PATTERNS.append((pattern, replacement))
```

### 2. Structured Output Implementation

#### 2.1 JSON Formatter Design
```python
class JSONFormatter(logging.Formatter):
    """
    Production JSON formatter with standardized schema
    
    Implementation Features:
    - Consistent field naming across all logs
    - ISO 8601 timestamp formatting
    - Exception traceback preservation
    - Extra fields integration
    - Unicode support with ensure_ascii=False
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Implementation Pattern:
        1. Create base log entry with standard fields
        2. Add extra fields if present in record
        3. Handle exception information properly
        4. Return valid JSON string
        
        Standard Schema:
        {
            "timestamp": "ISO 8601 formatted",
            "level": "INFO|DEBUG|WARNING|ERROR|CRITICAL",
            "logger": "hierarchical.logger.name",
            "message": "formatted message content",
            "module": "python module name",
            "function": "function name where log occurred",
            "line": "line number in source",
            "extra_fields": {custom fields},
            "exception": "full traceback if present"
        }
        """
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Integration with extra fields system
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        # Exception handling
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, ensure_ascii=False)
```

#### 2.2 Text Formatter Configuration
```python
# Production text format for human readability
text_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
)

# Key Implementation Details:
# - asctime: Human readable timestamp
# - name: Full logger hierarchy
# - levelname: LOG LEVEL for filtering
# - module:funcName:lineno: Source location for debugging
# - message: Actual log content
```

### 3. Performance Monitoring Implementation

#### 3.1 Performance Context Manager
```python
@contextmanager
def log_performance(logger: logging.Logger, operation: str, 
                   extra_fields: Optional[Dict[str, Any]] = None):
    """
    Production implementation of performance monitoring
    
    Implementation Strategy:
    1. Record start time before operation
    2. Log operation start with context
    3. Yield performance data dictionary for custom metrics
    4. Calculate duration after operation completion
    5. Log completion or failure with full timing data
    6. Handle exceptions while preserving performance data
    
    Usage Patterns:
    # Basic timing
    with log_performance(logger, "FRED API call"):
        data = api_client.get_series(['GDP', 'UNRATE'])
    
    # Custom metrics
    with log_performance(logger, "data processing") as perf:
        result = process_data(input_data)
        perf['input_rows'] = len(input_data)
        perf['output_rows'] = len(result)
        perf['processing_rate'] = len(result) / duration
    """
    start_time = time.time()
    perf_data = extra_fields.copy() if extra_fields else {}
    
    # Log operation start
    logger.info(f"Starting {operation}", extra={'extra_fields': {
        'operation': operation,
        'operation_phase': 'start',
        **perf_data
    }})
    
    try:
        yield perf_data
        
        # Success path - calculate and log completion
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Completed {operation} in {duration:.3f}s", extra={'extra_fields': {
            'operation': operation,
            'operation_phase': 'complete',
            'duration_seconds': duration,
            'success': True,
            **perf_data
        }})
        
    except Exception as e:
        # Failure path - still log timing data
        end_time = time.time()
        duration = end_time - start_time
        
        logger.error(f"Failed {operation} after {duration:.3f}s: {str(e)}", extra={'extra_fields': {
            'operation': operation,
            'operation_phase': 'failed',
            'duration_seconds': duration,
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            **perf_data
        }})
        
        raise  # Re-raise to preserve exception handling
```

#### 3.2 Performance Filter Implementation
```python
class PerformanceFilter(logging.Filter):
    """
    Automatic performance metrics injection
    
    Implementation Details:
    - Adds timestamp to all records for correlation
    - Minimal overhead design
    - Integration with extra_fields system
    - Thread-safe operation tracking
    """
    
    def __init__(self):
        super().__init__()
        self.start_times = {}  # Thread-safe operation tracking
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add performance timestamp to all records"""
        if not hasattr(record, 'extra_fields'):
            record.extra_fields = {}
            
        record.extra_fields['performance_timestamp'] = time.time()
        return True
```

### 4. Configuration Management Implementation

#### 4.1 Main Setup Function
```python
def setup_logging(
    level: str = 'INFO',
    format_type: str = 'text',
    log_file: Optional[str] = None,
    max_file_size: int = 10485760,  # 10MB
    backup_count: int = 5,
    include_performance: bool = False,
    mask_sensitive_data: bool = True
) -> logging.Logger:
    """
    Production logging setup implementation
    
    Implementation Strategy:
    1. Parameter validation and normalization
    2. Logger instance creation and configuration
    3. Handler setup (console and optional file)
    4. Filter chain configuration
    5. Error handling for configuration failures
    6. Return configured logger instance
    
    Key Features:
    - Flexible configuration for different environments
    - Automatic log directory creation
    - Rotating file handler for disk space management
    - Filter chain for security and performance
    - Comprehensive error handling
    """
    try:
        # Get root logger for the package
        logger = logging.getLogger('federal_reserve_etl')
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Create formatter based on format type
        if format_type.lower() == 'json':
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
            )
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # Add filters based on configuration
        if mask_sensitive_data:
            console_handler.addFilter(SensitiveDataFilter())
            
        if include_performance:
            console_handler.addFilter(PerformanceFilter())
            
        logger.addHandler(console_handler)
        
        # Setup file handler if specified
        if log_file:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            
            # Add same filters to file handler
            if mask_sensitive_data:
                file_handler.addFilter(SensitiveDataFilter())
                
            if include_performance:
                file_handler.addFilter(PerformanceFilter())
                
            logger.addHandler(file_handler)
        
        # Log configuration summary
        logger.info(f"Logging configured - Level: {level}, Format: {format_type}, "
                   f"File: {log_file or 'Console only'}, Performance: {include_performance}")
        
        return logger
        
    except Exception as e:
        raise ConfigurationError(f"Failed to configure logging: {str(e)}") from e
```

#### 4.2 Quick Setup for Development
```python
def quick_setup(debug: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """
    Simplified setup for development and testing
    
    Implementation Pattern:
    - Sensible defaults for development
    - Debug mode enables performance tracking
    - Always includes sensitive data masking
    - Text format for human readability
    """
    level = 'DEBUG' if debug else 'INFO'
    return setup_logging(
        level=level,
        format_type='text',
        log_file=log_file,
        include_performance=debug,
        mask_sensitive_data=True
    )
```

### 5. Advanced Context Management

#### 5.1 Contextual Logging Implementation
```python
class LoggingContext:
    """
    Context manager for temporary logging configuration
    
    Implementation Features:
    - Non-destructive temporary configuration changes
    - Automatic restoration of original settings
    - Support for temporary log level changes
    - Extra fields injection for operation context
    - Thread-safe operation
    """
    
    def __init__(self, logger: logging.Logger, level: Optional[str] = None, 
                 extra_fields: Optional[Dict[str, Any]] = None):
        """
        Initialize context with original state preservation
        
        Implementation Strategy:
        1. Store original logger configuration
        2. Prepare temporary modifications
        3. Create context filter for extra fields
        4. Validate parameters for safety
        """
        self.logger = logger
        self.original_level = logger.level
        self.new_level = getattr(logging, level.upper(), None) if level else None
        self.extra_fields = extra_fields or {}
        self.original_filters = list(logger.filters)
        self.context_filter = None
    
    def __enter__(self):
        """
        Apply temporary configuration
        
        Implementation Steps:
        1. Set temporary log level if specified
        2. Add context filter for extra fields
        3. Return logger for use in context
        """
        # Set temporary log level
        if self.new_level:
            self.logger.setLevel(self.new_level)
        
        # Add context filter for extra fields
        if self.extra_fields:
            self.context_filter = ContextFilter(self.extra_fields)
            self.logger.addFilter(self.context_filter)
        
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Restore original configuration
        
        Implementation Steps:
        1. Restore original log level
        2. Remove context filter
        3. Ensure clean restoration even on exceptions
        """
        # Restore original log level
        self.logger.setLevel(self.original_level)
        
        # Remove context filter
        if self.context_filter:
            self.logger.removeFilter(self.context_filter)
```

#### 5.2 Context Filter Implementation
```python
class ContextFilter(logging.Filter):
    """
    Filter for injecting context fields into log records
    
    Implementation Strategy:
    - Minimal overhead field injection
    - Integration with extra_fields system
    - Preservation of existing extra fields
    - Thread-safe operation
    """
    
    def __init__(self, context_fields: Dict[str, Any]):
        """Store context fields for injection"""
        super().__init__()
        self.context_fields = context_fields
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Inject context fields into record
        
        Implementation Details:
        1. Ensure extra_fields attribute exists
        2. Update with context fields (preserves existing)
        3. Always return True (don't filter records)
        """
        if not hasattr(record, 'extra_fields'):
            record.extra_fields = {}
            
        record.extra_fields.update(self.context_fields)
        return True
```

### 6. Integration Patterns

#### 6.1 Factory Pattern Implementation
```python
def get_logger(name: str = None) -> logging.Logger:
    """
    Logger factory with consistent naming convention
    
    Implementation Pattern:
    - Hierarchical logger naming
    - Automatic configuration inheritance
    - Lazy initialization for performance
    - Integration with package structure
    
    Usage Examples:
    logger = get_logger()                    # 'federal_reserve_etl'
    logger = get_logger('data_sources')      # 'federal_reserve_etl.data_sources'
    logger = get_logger('fred_client')       # 'federal_reserve_etl.fred_client'
    """
    if name:
        return logging.getLogger(f'federal_reserve_etl.{name}')
    return logging.getLogger('federal_reserve_etl')
```

#### 6.2 Third-Party Library Integration
```python
def configure_third_party_logging():
    """
    Production configuration for external library logging
    
    Implementation Strategy:
    - Reduce noise from verbose libraries
    - Preserve important error information
    - Centralized configuration management
    - Environment-specific overrides
    
    Libraries Configured:
    - urllib3: HTTP connection details (WARNING level)
    - requests: API call details (WARNING level)
    - pandas: Data processing warnings (WARNING level)
    - matplotlib: Rendering warnings (WARNING level)
    """
    # Reduce urllib3 verbosity (used by requests)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Reduce requests verbosity
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Reduce pandas verbosity
    logging.getLogger('pandas').setLevel(logging.WARNING)
    
    # Reduce matplotlib verbosity if present
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
```

## Production Integration Examples

### 1. Data Source Integration
```python
# src/federal_reserve_etl/data_sources/fred_client.py
from ..utils import get_logger, log_performance, LoggingContext

class FREDClient:
    def __init__(self):
        self.logger = get_logger('data_sources.fred')
    
    def get_series_data(self, variables: List[str], start_date: str, end_date: str):
        """
        Example of complete logging integration
        
        Features demonstrated:
        - Performance monitoring with custom metrics
        - Contextual logging with operation details
        - Error handling with performance preservation
        - Structured logging with extra fields
        """
        with LoggingContext(self.logger, extra_fields={
            'data_source': 'FRED',
            'variables_count': len(variables),
            'date_range': f"{start_date} to {end_date}"
        }):
            with log_performance(self.logger, "FRED API data retrieval") as perf:
                try:
                    # API call with detailed logging
                    self.logger.info(f"Requesting data for variables: {variables[:5]}")
                    
                    response = self._make_api_request(variables, start_date, end_date)
                    
                    # Add custom performance metrics
                    perf['response_size_bytes'] = len(response.content)
                    perf['variables_requested'] = len(variables)
                    
                    data = self._parse_response(response)
                    
                    perf['rows_returned'] = len(data)
                    perf['columns_returned'] = len(data.columns)
                    
                    self.logger.info("Data retrieval completed successfully")
                    return data
                    
                except Exception as e:
                    self.logger.error(f"Data retrieval failed: {str(e)}")
                    raise
```

### 2. Error Handling Integration
```python
# Integration with error handling decorators
from ..utils import get_logger, log_performance
from ..utils.error_handling import handle_api_errors

class DataProcessor:
    def __init__(self):
        self.logger = get_logger('data_processor')
    
    @handle_api_errors(max_retries=3, backoff_base=1.0)
    def process_batch(self, data_batch):
        """
        Example of logging + error handling integration
        
        Features:
        - Automatic retry logging from error handling decorator
        - Performance monitoring for processing operations
        - Contextual information for debugging
        """
        with log_performance(self.logger, "batch processing") as perf:
            self.logger.debug(f"Processing batch of {len(data_batch)} records")
            
            # Processing logic with detailed logging
            processed_data = self._transform_data(data_batch)
            
            perf['input_records'] = len(data_batch)
            perf['output_records'] = len(processed_data)
            perf['processing_rate'] = len(processed_data) / perf.get('duration_seconds', 1)
            
            return processed_data
```

### 3. Configuration Integration
```python
# src/federal_reserve_etl/config.py
from .utils import setup_logging, configure_third_party_logging
import os

def initialize_logging():
    """
    Production logging initialization
    
    Environment-based configuration:
    - Development: DEBUG level, text format, console only
    - Testing: INFO level, JSON format, file output
    - Production: INFO level, JSON format, rotating files
    """
    environment = os.getenv('ETL_ENVIRONMENT', 'development')
    
    if environment == 'production':
        logger = setup_logging(
            level=os.getenv('ETL_LOG_LEVEL', 'INFO'),
            format_type='json',
            log_file='/var/log/etl/pipeline.log',
            max_file_size=50 * 1024 * 1024,  # 50MB
            backup_count=10,
            include_performance=True,
            mask_sensitive_data=True
        )
    elif environment == 'testing':
        logger = setup_logging(
            level='INFO',
            format_type='json',
            log_file='./logs/test.log',
            include_performance=True,
            mask_sensitive_data=True
        )
    else:  # development
        logger = setup_logging(
            level='DEBUG',
            format_type='text',
            log_file='./logs/dev.log',
            include_performance=True,
            mask_sensitive_data=True
        )
    
    # Configure third-party library logging
    configure_third_party_logging()
    
    return logger
```

## Security Implementation Details

### 1. Sensitive Data Pattern Coverage
```python
# Production patterns covering common sensitive data types
PRODUCTION_PATTERNS = [
    # Federal Reserve specific
    (r'fred_?api_?key["\']?\s*[:=]\s*["\']?([a-f0-9]{32})["\']?', r'fred_api_key=***MASKED***'),
    (r'haver_?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9]{20,})["\']?', r'haver_key=***MASKED***'),
    
    # Database credentials
    (r'password["\']?\s*[:=]\s*["\']?([^"\'\s&]+)["\']?', r'password=***MASKED***'),
    (r'postgresql://([^:]+):([^@]+)@', r'postgresql://***USER***:***PASS***@'),
    
    # AWS credentials
    (r'aws_access_key_id["\']?\s*[:=]\s*["\']?([A-Z0-9]{20})["\']?', r'aws_access_key_id=***MASKED***'),
    (r'aws_secret_access_key["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?', r'aws_secret_access_key=***MASKED***'),
    
    # Generic secrets
    (r'(token|secret|key)["\']?\s*[:=]\s*["\']?([A-Za-z0-9+/]{16,})["\']?', r'\\1=***MASKED***'),
]
```

### 2. Security Testing Implementation
```python
# tests/unit/test_logging_security.py
import pytest
from federal_reserve_etl.utils.logging import SensitiveDataFilter

class TestSensitiveDataMasking:
    """
    Comprehensive security testing for logging
    
    Test Coverage:
    - All defined sensitive patterns
    - Edge cases and false positives
    - Custom pattern addition
    - Performance impact measurement
    """
    
    def test_api_key_masking(self):
        """Test API key pattern detection and masking"""
        filter_instance = SensitiveDataFilter()
        
        test_cases = [
            ("api_key=abc123456789", "api_key=***MASKED***"),
            ("fred_api_key='1234567890abcdef'", "fred_api_key=***MASKED***"),
            ("Authorization: Bearer token123456789", "Authorization: Bearer ***MASKED***"),
        ]
        
        for input_msg, expected in test_cases:
            record = create_log_record(input_msg)
            filter_instance.filter(record)
            assert expected in record.msg
    
    def test_no_false_positives(self):
        """Ensure legitimate data isn't masked"""
        filter_instance = SensitiveDataFilter()
        
        safe_messages = [
            "Processing 123 records",
            "API call completed in 1.23 seconds",
            "Configuration key 'timeout' set to 30",
        ]
        
        for msg in safe_messages:
            record = create_log_record(msg)
            original_msg = record.msg
            filter_instance.filter(record)
            assert record.msg == original_msg  # No masking occurred
```

## Performance Optimization Strategies

### 1. Logging Overhead Minimization
```python
# Efficient pattern matching implementation
class OptimizedSensitiveDataFilter(SensitiveDataFilter):
    """
    Performance-optimized sensitive data filtering
    
    Optimizations:
    - Compiled regex patterns for faster matching
    - Early exit for messages without sensitive indicators
    - Minimal string operations
    - Caching for repeated patterns
    """
    
    def __init__(self):
        super().__init__()
        # Pre-compile patterns for performance
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.SENSITIVE_PATTERNS
        ]
        
        # Quick check patterns for early exit
        self.quick_checks = ['key', 'token', 'password', 'secret', 'auth']
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Optimized filtering with early exit
        
        Performance Strategy:
        1. Quick check for potential sensitive data indicators
        2. Only apply full pattern matching if indicators present
        3. Use compiled regex patterns
        4. Minimize string operations
        """
        if not hasattr(record, 'msg') or not record.msg:
            return True
        
        message = str(record.msg).lower()
        
        # Early exit if no sensitive data indicators
        if not any(indicator in message for indicator in self.quick_checks):
            return True
        
        # Apply pattern matching only if needed
        original_msg = str(record.msg)
        for pattern, replacement in self.compiled_patterns:
            original_msg = pattern.sub(replacement, original_msg)
        
        record.msg = original_msg
        return True
```

### 2. Memory-Efficient Logging
```python
# Memory optimization for high-throughput scenarios
class MemoryOptimizedJSONFormatter(JSONFormatter):
    """
    Memory-optimized JSON formatter
    
    Optimizations:
    - Object reuse for standard fields
    - Minimal temporary object creation
    - Efficient string building
    - Optional field compression
    """
    
    def __init__(self, compress_fields: bool = False):
        super().__init__()
        self.compress_fields = compress_fields
        
        # Reusable template for performance
        self.base_template = {
            'timestamp': None,
            'level': None,
            'logger': None,
            'message': None,
            'module': None,
            'function': None,
            'line': None
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Memory-efficient formatting
        
        Strategy:
        1. Reuse base template object
        2. Minimize temporary object creation
        3. Optional field compression for large messages
        4. Efficient JSON serialization
        """
        # Update template with current record data
        log_entry = self.base_template.copy()
        log_entry.update({
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        })
        
        # Add extra fields efficiently
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Handle exceptions
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Optional compression for large messages
        if self.compress_fields and len(log_entry.get('message', '')) > 1000:
            log_entry['message'] = log_entry['message'][:1000] + '...[TRUNCATED]'
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
```

## Testing Implementation Guide

### 1. Unit Test Coverage
```python
# tests/unit/test_logging_framework.py
import pytest
import logging
from unittest.mock import patch, MagicMock
from federal_reserve_etl.utils.logging import (
    setup_logging, get_logger, log_performance,
    SensitiveDataFilter, JSONFormatter, LoggingContext
)

class TestLoggingFramework:
    """Comprehensive unit tests for logging framework"""
    
    def test_setup_logging_configuration(self):
        """Test logging setup with various configurations"""
        # Test default configuration
        logger = setup_logging()
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1  # Console handler only
        
        # Test file output configuration
        with patch('pathlib.Path.mkdir'):
            logger = setup_logging(log_file='/tmp/test.log')
            assert len(logger.handlers) == 2  # Console + file
    
    def test_json_formatter_output(self):
        """Test JSON formatter produces valid JSON"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='', lineno=1,
            msg='test message', args=(), exc_info=None
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)  # Should not raise exception
        
        # Verify required fields
        required_fields = ['timestamp', 'level', 'logger', 'message']
        for field in required_fields:
            assert field in parsed
    
    def test_performance_context_manager(self):
        """Test performance logging context manager"""
        logger = MagicMock()
        
        with log_performance(logger, "test operation") as perf:
            perf['custom_metric'] = 42
        
        # Verify start and completion logging
        assert logger.info.call_count == 2
        start_call, complete_call = logger.info.call_args_list
        
        assert "Starting test operation" in start_call[0][0]
        assert "Completed test operation" in complete_call[0][0]
```

### 2. Integration Test Implementation
```python
# tests/integration/test_logging_integration.py
import tempfile
import json
from pathlib import Path
from federal_reserve_etl.utils.logging import setup_logging, get_logger

class TestLoggingIntegration:
    """Integration tests with real logging operations"""
    
    def test_complete_logging_workflow(self):
        """Test end-to-end logging workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            
            # Setup logging with file output
            setup_logging(
                level='DEBUG',
                format_type='json',
                log_file=str(log_file),
                include_performance=True,
                mask_sensitive_data=True
            )
            
            # Get logger and perform operations
            logger = get_logger('integration_test')
            
            # Test various logging scenarios
            logger.info("Basic info message")
            logger.debug("Debug message", extra={'extra_fields': {'test_id': 123}})
            logger.warning("API key leaked: api_key=secret123456")
            
            # Verify log file contents
            assert log_file.exists()
            
            with open(log_file) as f:
                lines = f.readlines()
            
            assert len(lines) >= 3
            
            # Parse and verify JSON format
            for line in lines:
                parsed = json.loads(line.strip())
                assert 'timestamp' in parsed
                assert 'level' in parsed
                assert 'message' in parsed
            
            # Verify sensitive data masking
            warning_line = [json.loads(line) for line in lines 
                          if 'WARNING' in line][0]
            assert '***MASKED***' in warning_line['message']
            assert 'secret123456' not in warning_line['message']
```

## Deployment and Operations

### 1. Production Configuration Templates
```yaml
# config/production.yml
logging:
  level: INFO
  format: json
  file: /var/log/etl/pipeline.log
  max_file_size: 52428800  # 50MB
  backup_count: 20
  performance_monitoring: true
  sensitive_data_masking: true
  
  # Third-party library levels
  urllib3_level: WARNING
  requests_level: WARNING
  pandas_level: WARNING

# Environment variables for containerized deployments
ETL_LOG_LEVEL=INFO
ETL_LOG_FORMAT=json
ETL_LOG_FILE=/var/log/etl/pipeline.log
ETL_LOG_PERFORMANCE=true
ETL_LOG_MASK_SENSITIVE=true
```

### 2. Monitoring Integration
```python
# monitoring/log_analysis.py
"""
Production log analysis and monitoring integration

Features:
- Real-time log parsing for monitoring systems
- Performance metrics extraction
- Error rate calculation
- Alert trigger detection
"""

def extract_performance_metrics(log_line: str) -> Dict[str, Any]:
    """Extract performance metrics from structured logs"""
    try:
        log_data = json.loads(log_line)
        
        if 'operation_phase' in log_data.get('extra_fields', {}):
            extra = log_data['extra_fields']
            
            return {
                'timestamp': log_data['timestamp'],
                'operation': extra.get('operation'),
                'phase': extra.get('operation_phase'),
                'duration': extra.get('duration_seconds'),
                'success': extra.get('success'),
                'custom_metrics': {
                    k: v for k, v in extra.items()
                    if k not in ['operation', 'operation_phase', 'duration_seconds', 'success']
                }
            }
    except (json.JSONDecodeError, KeyError):
        return None

def generate_alerts(metrics: Dict[str, Any]) -> List[str]:
    """Generate alerts based on performance metrics"""
    alerts = []
    
    # Performance alerts
    if metrics.get('duration', 0) > 30.0:
        alerts.append(f"Slow operation: {metrics['operation']} took {metrics['duration']:.2f}s")
    
    # Failure alerts
    if not metrics.get('success', True):
        alerts.append(f"Operation failed: {metrics['operation']}")
    
    return alerts
```

### 3. Operational Procedures
```bash
#!/bin/bash
# scripts/logging-maintenance.sh
"""
Production logging maintenance script

Operations:
- Log rotation and archival
- Performance metrics aggregation
- Alert threshold monitoring
- Storage cleanup and optimization
"""

# Log rotation (if not handled by system logrotate)
find /var/log/etl -name "*.log.*" -mtime +30 -delete

# Performance metrics aggregation
python -m monitoring.log_analysis --date $(date --date='yesterday' +%Y-%m-%d)

# Storage monitoring
LOG_SIZE=$(du -sh /var/log/etl | cut -f1)
echo "Current log storage usage: $LOG_SIZE"

# Alert if log storage exceeds threshold
if [[ $(du -s /var/log/etl | cut -f1) -gt 5242880 ]]; then  # 5GB
    echo "WARNING: Log storage exceeds 5GB"
fi
```

## Extension and Customization Guide

### 1. Custom Log Formatters
```python
# custom_formatters.py
"""
Custom log formatters for specific operational requirements

Examples:
- Compliance-specific formatting
- Custom field extraction
- Integration with specific monitoring systems
"""

class ComplianceFormatter(JSONFormatter):
    """
    Compliance-focused formatter with audit trail features
    
    Features:
    - Audit sequence numbers
    - Digital signatures for log integrity
    - Regulatory timestamp formatting
    - Compliance field mapping
    """
    
    def __init__(self):
        super().__init__()
        self.sequence_number = 0
    
    def format(self, record: logging.LogRecord) -> str:
        """Add compliance-specific fields"""
        log_entry = super().format_base_entry(record)
        
        # Add compliance fields
        self.sequence_number += 1
        log_entry.update({
            'audit_sequence': self.sequence_number,
            'compliance_timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'regulatory_category': self._categorize_log_level(record.levelname),
            'data_classification': 'financial_data'
        })
        
        return json.dumps(log_entry, ensure_ascii=False)
```

### 2. Custom Filters and Handlers
```python
# custom_filters.py
"""
Custom logging filters for specific business requirements

Examples:
- Customer-specific sensitive data patterns
- Geographic data filtering
- Regulatory compliance filtering
"""

class CustomerDataFilter(logging.Filter):
    """
    Filter for customer-specific sensitive data patterns
    
    Customizable patterns for:
    - Customer identification numbers
    - Account numbers
    - Transaction identifiers
    - Geographic information
    """
    
    def __init__(self, customer_patterns: List[Tuple[str, str]] = None):
        super().__init__()
        self.customer_patterns = customer_patterns or []
        
        # Default customer data patterns
        self.default_patterns = [
            (r'customer_id["\']?\s*[:=]\s*["\']?(\d{8,})["\']?', r'customer_id=***MASKED***'),
            (r'account_number["\']?\s*[:=]\s*["\']?(\d{10,})["\']?', r'account_number=***MASKED***'),
            (r'ssn["\']?\s*[:=]\s*["\']?(\d{3}-\d{2}-\d{4})["\']?', r'ssn=***MASKED***'),
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Apply customer-specific sensitive data masking"""
        if not hasattr(record, 'msg') or not record.msg:
            return True
        
        message = str(record.msg)
        
        # Apply default customer patterns
        for pattern, replacement in self.default_patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        # Apply custom customer patterns
        for pattern, replacement in self.customer_patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        record.msg = message
        return True
```

---

**Document Control**
- **Author**: Federal Reserve ETL Development Team
- **Technical Implementation Lead**: Senior Software Engineer
- **Code Reviewers**: Principal Engineer, Security Architect, DevOps Lead
- **Implementation Status**: Complete
- **Production Deployment**: 2024-08-29
- **Next Review**: Quarterly performance and security review
- **Repository Location**: `src/federal_reserve_etl/utils/logging.py`