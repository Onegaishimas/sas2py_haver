"""
Utilities Module

Common utilities for logging, configuration, and error handling across
the Federal Reserve ETL pipeline.

Public API:
    - Custom exception classes for data source operations
    - Logging configuration and setup utilities
    - Standardized error handling patterns and decorators
    - Common utility functions for data processing
"""

from .exceptions import (
    FederalReserveETLError,
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    ValidationError,
    ConfigurationError,
    RateLimitError
)

from .error_handling import (
    handle_api_errors,
    log_and_handle_error,
    safe_execute,
    validate_and_convert_dates,
    validate_variable_codes,
    ErrorContext
)

from .logging import (
    setup_logging,
    get_logger
)

from .type_definitions import (
    # Basic types
    VariableCode,
    DateString,
    DateRange,
    APIKey,
    # Collection types
    VariableList,
    VariableDict,
    MetadataDict,
    # DataFrame types
    TimeSeriesData,
    WideFormatData,
    LongFormatData,
    # Typed dictionaries
    VariableMetadata,
    DataSourceConfig,
    CoverageSummary,
    # Configuration types
    LoggingConfig,
    APIConfig,
    RateLimitConfig,
    # Common combinations
    StringOrList,
    DateOrString,
    DataFrameOrNone
)

from .docstring_standards import (
    validate_docstring,
    get_docstring_template,
    generate_docstring_report
)

__all__ = [
    # Exception classes
    'FederalReserveETLError',
    'ConnectionError',
    'AuthenticationError', 
    'DataRetrievalError',
    'ValidationError',
    'ConfigurationError',
    'RateLimitError',
    
    # Error handling utilities
    'handle_api_errors',
    'log_and_handle_error',
    'safe_execute',
    'validate_and_convert_dates',
    'validate_variable_codes',
    'ErrorContext',
    
    # Logging utilities
    'setup_logging',
    'get_logger',
    
    # Type definitions
    'VariableCode',
    'DateString', 
    'DateRange',
    'APIKey',
    'VariableList',
    'VariableDict',
    'MetadataDict',
    'TimeSeriesData',
    'WideFormatData',
    'LongFormatData',
    'VariableMetadata',
    'DataSourceConfig',
    'CoverageSummary',
    'StringOrList',
    'DateOrString',
    'DataFrameOrNone',
    # Configuration types
    'LoggingConfig',
    'APIConfig',
    'RateLimitConfig',
    
    # Docstring utilities
    'validate_docstring',
    'get_docstring_template',
    'generate_docstring_report'
]