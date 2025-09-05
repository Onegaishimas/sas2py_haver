"""
Type Definitions for Federal Reserve ETL Pipeline

Centralized type definitions and type aliases for consistent
type hints across the entire codebase.
"""

from typing import Dict, List, Optional, Union, Any, Callable, Tuple
from datetime import datetime
import pandas as pd


# Basic type aliases
VariableCode = str
DateString = str  # YYYY-MM-DD format
DateRange = Tuple[datetime, datetime]
APIKey = str
URL = str

# Data structure types
VariableList = List[VariableCode]
VariableDict = Dict[VariableCode, Any]
MetadataDict = Dict[str, Any]
ConfigDict = Dict[str, Any]
ContextDict = Dict[str, Any]

# API response types
JSONResponse = Dict[str, Any]
APIResponse = Union[JSONResponse, str, bytes]

# DataFrame types
TimeSeriesData = pd.DataFrame  # DataFrame with DatetimeIndex
WideFormatData = pd.DataFrame  # Variables as columns
LongFormatData = pd.DataFrame  # Date, Variable, Value columns

# Function types
DataSourceFactory = Callable[[str], Any]
ValidationFunction = Callable[[Any], bool]
TransformFunction = Callable[[pd.DataFrame], pd.DataFrame]
ErrorHandler = Callable[[Exception], None]

# Configuration types
LoggingConfig = Dict[str, Union[str, int, bool]]
APIConfig = Dict[str, Union[str, int, Dict[str, str]]]
RateLimitConfig = Dict[str, Union[int, float]]

# Status and state types
ConnectionStatus = bool
ProcessingStatus = str  # "pending", "processing", "completed", "failed"
RateLimitStatus = Dict[str, Union[int, float, Optional[datetime]]]

# Error context types
ErrorContext = Dict[str, Any]
ValidationResult = Tuple[bool, Optional[str]]
RetryConfig = Dict[str, Union[int, float, Tuple[type, ...]]]


class TypedDict:
    """
    Base class for typed dictionary structures
    
    Provides a foundation for strongly-typed dictionary-like objects
    used throughout the ETL pipeline.
    """
    pass


class VariableMetadata(TypedDict):
    """
    Type definition for variable metadata structure
    
    Attributes:
        code: Variable code identifier
        name: Human-readable variable name
        description: Detailed description of the variable
        units: Units of measurement
        frequency: Data frequency (daily, weekly, monthly, etc.)
        source: Data source name (FRED, Haver, etc.)
        category: Variable category
        start_date: First available date (YYYY-MM-DD)
        end_date: Last available date (YYYY-MM-DD)
    """
    code: VariableCode
    name: str
    description: str
    units: str
    frequency: str
    source: str
    category: str
    start_date: DateString
    end_date: DateString


class DataSourceConfig(TypedDict):
    """
    Type definition for data source configuration
    
    Attributes:
        source_name: Name of the data source
        base_url: Base URL for API endpoints
        api_key: API authentication key
        rate_limit: Maximum requests per minute
        timeout: Request timeout in seconds
        retry_config: Retry configuration parameters
    """
    source_name: str
    base_url: URL
    api_key: Optional[APIKey]
    rate_limit: int
    timeout: int
    retry_config: RetryConfig


class CoverageSummary(TypedDict):
    """
    Type definition for data coverage summary
    
    Attributes:
        requested_start: Requested start date
        requested_end: Requested end date
        actual_start: Actual data start date
        actual_end: Actual data end date
        coverage_percentage: Coverage percentage (0-100)
        total_observations: Total number of observations
        business_days_count: Number of business days covered
        adjustment_message: Message about any adjustments made
    """
    requested_start: DateString
    requested_end: DateString
    actual_start: DateString
    actual_end: DateString
    coverage_percentage: float
    total_observations: int
    business_days_count: int
    adjustment_message: Optional[str]


# Type guards and validation functions
def is_valid_variable_code(value: Any) -> bool:
    """
    Type guard for variable codes
    
    Args:
        value: Value to check
        
    Returns:
        True if value is a valid variable code
    """
    return isinstance(value, str) and len(value.strip()) > 0 and len(value) <= 50


def is_valid_date_string(value: Any) -> bool:
    """
    Type guard for date strings
    
    Args:
        value: Value to check
        
    Returns:
        True if value is a valid date string (YYYY-MM-DD)
    """
    if not isinstance(value, str):
        return False
    
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def is_wide_format_dataframe(df: Any) -> bool:
    """
    Type guard for wide format DataFrames
    
    Args:
        df: Value to check
        
    Returns:
        True if df is a wide format DataFrame
    """
    if not isinstance(df, pd.DataFrame):
        return False
    
    # Wide format should have DatetimeIndex and numeric columns
    return (
        isinstance(df.index, pd.DatetimeIndex) and
        len(df.columns) > 0 and
        all(pd.api.types.is_numeric_dtype(df[col]) for col in df.columns)
    )


def is_long_format_dataframe(df: Any) -> bool:
    """
    Type guard for long format DataFrames
    
    Args:
        df: Value to check
        
    Returns:
        True if df is a long format DataFrame
    """
    if not isinstance(df, pd.DataFrame):
        return False
    
    # Long format should have specific required columns
    required_columns = {'Date', 'InstrumentName', 'InterestRatePct'}
    return required_columns.issubset(set(df.columns))


# Type validation decorators
def validate_types(**type_specs) -> Callable:
    """
    Decorator for runtime type validation
    
    Args:
        **type_specs: Mapping of parameter names to expected types
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            import inspect
            
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate specified types
            for param_name, expected_type in type_specs.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    
                    if value is not None and not isinstance(value, expected_type):
                        raise TypeError(
                            f"Parameter '{param_name}' expected {expected_type.__name__}, "
                            f"got {type(value).__name__}"
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Common type combinations
OptionalString = Optional[str]
OptionalInt = Optional[int]
OptionalFloat = Optional[float]
OptionalDict = Optional[Dict[str, Any]]
OptionalList = Optional[List[Any]]

StringOrList = Union[str, List[str]]
DateOrString = Union[datetime, str]
DataFrameOrNone = Optional[pd.DataFrame]
ErrorOrNone = Optional[Exception]

# Export commonly used types
__all__ = [
    # Basic types
    'VariableCode',
    'DateString',
    'DateRange',
    'APIKey',
    'URL',
    
    # Collection types
    'VariableList',
    'VariableDict',
    'MetadataDict',
    'ConfigDict',
    'ContextDict',
    
    # API types
    'JSONResponse',
    'APIResponse',
    
    # DataFrame types
    'TimeSeriesData',
    'WideFormatData',
    'LongFormatData',
    
    # Function types
    'DataSourceFactory',
    'ValidationFunction',
    'TransformFunction',
    'ErrorHandler',
    
    # Configuration types
    'LoggingConfig',
    'APIConfig',
    'RateLimitConfig',
    
    # Status types
    'ConnectionStatus',
    'ProcessingStatus',
    'RateLimitStatus',
    
    # Typed dictionaries
    'VariableMetadata',
    'DataSourceConfig',
    'CoverageSummary',
    
    # Type guards
    'is_valid_variable_code',
    'is_valid_date_string',
    'is_wide_format_dataframe',
    'is_long_format_dataframe',
    
    # Decorators
    'validate_types',
    
    # Common combinations
    'OptionalString',
    'OptionalInt',
    'OptionalFloat',
    'OptionalDict',
    'OptionalList',
    'StringOrList',
    'DateOrString',
    'DataFrameOrNone',
    'ErrorOrNone'
]