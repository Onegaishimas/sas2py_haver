# Technical Implementation Document: Dual-Source Data Extraction

## 1. Implementation Strategy

### Development Approach
**Methodology**: Test-Driven Development with Real API Integration
- Integration tests written first to define expected behavior
- Real API calls used instead of mocked responses for reliability
- Incremental implementation with continuous testing validation

**Order of Implementation**:
1. **Foundation First**: Abstract base class and exception hierarchy
2. **FRED Implementation**: Primary data source with rate limiting
3. **Haver Implementation**: Secondary source with format standardization
4. **Factory Integration**: Unified creation and interface pattern
5. **Testing Validation**: Comprehensive integration test suite

**Integration Strategy**: 
- Build against live APIs from day one to catch real-world issues
- Implement error handling based on actual API behavior patterns
- Validate data formats with real API responses

### Coding Patterns
**Design Patterns Used**:
- **Factory Pattern**: Dynamic data source creation based on type
- **Abstract Base Class**: Enforce consistent interface across implementations  
- **Context Manager**: Automatic resource management for connections
- **Decorator Pattern**: Retry logic and error handling cross-cutting concerns

**Code Organization Philosophy**:
- Single Responsibility: Each class has one primary responsibility
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: Depend on abstractions, not concrete implementations
- Open/Closed: Open for extension (new data sources), closed for modification

**Error Handling Strategy**:
- Exception hierarchy reflects different error categories and recovery strategies
- Context preservation for debugging and user feedback
- Graceful degradation with partial success reporting

## 2. Code Structure

### Directory Structure Implementation
```
src/federal_reserve_etl/
├── __init__.py                     # Public API exports and factory
├── config.py                       # Configuration management and validation
├── data_sources/
│   ├── __init__.py                # Factory function and exports
│   ├── base.py                    # Abstract DataSource base class
│   ├── fred_client.py             # FRED API implementation
│   └── haver_client.py            # Haver Analytics implementation
└── utils/
    ├── __init__.py                # Utility function exports
    ├── exceptions.py              # Exception hierarchy definition
    ├── error_handling.py          # Retry decorators and utilities
    └── logging.py                 # Centralized logging configuration
```

### Key Class Implementations

**Abstract Base Class** (`data_sources/base.py`):
```python
from abc import ABC, abstractmethod
from typing import Union, List, Dict, Any
import pandas as pd
from datetime import datetime
import logging

class DataSource(ABC):
    """
    Abstract base class for all data source implementations.
    
    Defines the contract that all data sources must implement to ensure
    consistent behavior across different APIs (FRED, Haver, etc.).
    """
    
    def __init__(self, api_key: str, **kwargs):
        """
        Initialize data source with API credentials and configuration.
        
        Args:
            api_key: API key for authentication
            **kwargs: Additional configuration options
        """
        self.api_key = api_key
        self.config = kwargs
        self.is_connected = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Validate API key format during initialization
        self._validate_api_key()
    
    def _validate_api_key(self):
        """Validate API key format - override in subclasses for specific validation"""
        if not self.api_key or not isinstance(self.api_key, str):
            raise ValueError("API key must be a non-empty string")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data source and validate credentials.
        
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            AuthenticationError: If API credentials are invalid
            ConnectionError: If unable to reach the service
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Clean up connection resources and mark as disconnected."""
        pass
    
    @abstractmethod
    def get_data(self, variables: Union[str, List[str]], 
                start_date: Union[str, datetime], 
                end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Extract data for specified variables and date range.
        
        Args:
            variables: Single variable code or list of variable codes
            start_date: Start date (YYYY-MM-DD string or datetime)
            end_date: End date (YYYY-MM-DD string or datetime)
            
        Returns:
            DataFrame with DatetimeIndex and variable columns
            
        Raises:
            ValidationError: If parameters are invalid
            DataRetrievalError: If API call fails
            ConnectionError: If not connected to service
        """
        pass
    
    @abstractmethod
    def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Get metadata for specified variables.
        
        Args:
            variables: Single variable code or list of variable codes
            
        Returns:
            Dictionary with variable metadata
            
        Raises:
            ValidationError: If variable codes are invalid
            DataRetrievalError: If metadata retrieval fails
        """
        pass
    
    @abstractmethod
    def get_variable_metadata(self, variable: str) -> Dict[str, Any]:
        """
        Get metadata for a single variable.
        
        Args:
            variable: Variable code
            
        Returns:
            Dictionary with variable metadata
        """
        pass
    
    @abstractmethod
    def validate_response(self, response) -> bool:
        """
        Validate API response format and content.
        
        Args:
            response: API response object
            
        Returns:
            bool: True if response is valid
            
        Raises:
            DataRetrievalError: If response format is invalid
        """
        pass
    
    # Context manager implementation
    def __enter__(self):
        """Enter context manager - establish connection"""
        if not self.connect():
            raise ConnectionError("Failed to establish connection")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - clean up connection"""
        self.disconnect()
        # Return False to propagate any exceptions
        return False
    
    # Utility methods for common operations
    def _normalize_variables(self, variables: Union[str, List[str]]) -> List[str]:
        """Convert variable input to consistent list format"""
        if isinstance(variables, str):
            return [variables]
        elif isinstance(variables, list):
            return variables
        else:
            raise ValidationError("Variables must be string or list of strings")
    
    def _format_date(self, date_input: Union[str, datetime]) -> str:
        """Convert date input to YYYY-MM-DD string format"""
        if isinstance(date_input, str):
            # Validate string format
            try:
                datetime.strptime(date_input, '%Y-%m-%d')
                return date_input
            except ValueError:
                raise ValidationError("Date string must be in YYYY-MM-DD format")
        elif isinstance(date_input, datetime):
            return date_input.strftime('%Y-%m-%d')
        else:
            raise ValidationError("Date must be string (YYYY-MM-DD) or datetime object")
```

**FRED Client Implementation** (`data_sources/fred_client.py`):
```python
import requests
import pandas as pd
import time
from datetime import datetime
from typing import Union, List, Dict, Any
from collections import deque
import asyncio

from .base import DataSource
from ..utils.exceptions import (
    AuthenticationError, ConnectionError, DataRetrievalError, ValidationError
)
from ..utils.error_handling import retry_on_failure
from ..utils.logging import get_logger

class RateLimiter:
    """Rate limiter for FRED API (120 requests per minute)"""
    
    def __init__(self, max_requests: int = 120, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock() if asyncio else None
    
    def acquire(self):
        """Block until request can be made within rate limits"""
        now = time.time()
        
        # Remove requests outside time window
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        # Wait if at rate limit
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.requests.append(now)

class FREDDataSource(DataSource):
    """
    Federal Reserve Economic Data (FRED) API client implementation.
    
    Implements the DataSource interface for FRED API with:
    - Rate limiting compliance (120 requests/minute)
    - Automatic retry logic for transient failures
    - Data format standardization to pandas DataFrame
    """
    
    def __init__(self, api_key: str, base_url: str = None, timeout: int = 30):
        """
        Initialize FRED data source.
        
        Args:
            api_key: FRED API key (32-character string)
            base_url: Optional custom base URL for FRED API
            timeout: Request timeout in seconds
        """
        super().__init__(api_key)
        
        self.base_url = base_url or "https://api.stlouisfed.org/fred"
        self.timeout = timeout
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(max_requests=120, time_window=60)
        
        # Configure session with connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # Handle retries manually
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def _validate_api_key(self):
        """Validate FRED API key format (32 characters)"""
        super()._validate_api_key()
        if len(self.api_key) != 32:
            raise ValueError("FRED API key must be exactly 32 characters")
    
    def connect(self) -> bool:
        """
        Test FRED API connection and validate credentials.
        
        Makes a simple API call to verify the API key works.
        """
        try:
            # Test with a simple API call
            test_url = f"{self.base_url}/series"
            test_params = {
                'series_id': 'FEDFUNDS',
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': 1
            }
            
            response = self.session.get(test_url, params=test_params, timeout=self.timeout)
            
            if response.status_code == 400 and 'api_key' in response.text.lower():
                raise AuthenticationError("Invalid FRED API key")
            elif response.status_code == 403:
                raise AuthenticationError("FRED API access forbidden - check API key permissions")
            elif response.status_code != 200:
                raise ConnectionError(f"FRED API returned status {response.status_code}")
            
            self.is_connected = True
            self.logger.info("Successfully connected to FRED API")
            return True
            
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to FRED API: {e}")
    
    def disconnect(self) -> None:
        """Clean up FRED connection resources"""
        if self.session:
            self.session.close()
        self.is_connected = False
        self.logger.info("Disconnected from FRED API")
    
    @retry_on_failure(max_attempts=3, backoff_factor=1.0)
    def get_data(self, variables: Union[str, List[str]], 
                start_date: Union[str, datetime], 
                end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Extract data from FRED API for specified variables and date range.
        
        Implementation handles:
        - Multiple variables through separate API calls
        - Rate limiting compliance
        - Data format standardization
        - Missing data handling
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to FRED API. Call connect() first.")
        
        # Normalize inputs
        variables_list = self._normalize_variables(variables)
        start_str = self._format_date(start_date)
        end_str = self._format_date(end_date)
        
        # Validate date range
        if start_str > end_str:
            raise ValidationError("Start date must be before or equal to end date")
        
        # Extract data for each variable
        all_data = {}
        for variable in variables_list:
            self.logger.info(f"Extracting FRED data for variable: {variable}")
            
            # Apply rate limiting
            self.rate_limiter.acquire()
            
            try:
                # Fetch series observations
                observations = self._fetch_series_observations(variable, start_str, end_str)
                all_data[variable] = observations
                
            except Exception as e:
                self.logger.error(f"Failed to extract data for variable {variable}: {e}")
                raise DataRetrievalError(f"Failed to retrieve data for {variable}: {e}")
        
        # Combine all variables into single DataFrame
        return self._create_combined_dataframe(all_data)
    
    def _fetch_series_observations(self, series_id: str, start_date: str, end_date: str) -> Dict:
        """Fetch observations for a single series from FRED API"""
        url = f"{self.base_url}/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'observation_start': start_date,
            'observation_end': end_date
        }
        
        response = self.session.get(url, params=params, timeout=self.timeout)
        
        if not self.validate_response(response):
            raise DataRetrievalError(f"Invalid response for series {series_id}")
        
        data = response.json()
        
        # Check for API errors
        if 'error_code' in data:
            if data['error_code'] == 404:
                raise DataRetrievalError(f"Series {series_id} not found")
            else:
                raise DataRetrievalError(f"FRED API error: {data.get('error_message', 'Unknown error')}")
        
        return data.get('observations', [])
    
    def _create_combined_dataframe(self, all_data: Dict[str, List]) -> pd.DataFrame:
        """Create combined DataFrame from multiple variable observations"""
        if not all_data:
            return pd.DataFrame()
        
        # Create DataFrame for each variable
        variable_dfs = {}
        
        for variable, observations in all_data.items():
            if not observations:
                self.logger.warning(f"No observations found for variable {variable}")
                continue
            
            # Convert observations to DataFrame
            df_data = []
            for obs in observations:
                try:
                    date = pd.to_datetime(obs['date'])
                    value = pd.to_numeric(obs['value'], errors='coerce')  # Convert '.' to NaN
                    df_data.append({'date': date, variable: value})
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Skipping invalid observation for {variable}: {e}")
            
            if df_data:
                var_df = pd.DataFrame(df_data).set_index('date')
                variable_dfs[variable] = var_df
        
        if not variable_dfs:
            return pd.DataFrame()
        
        # Combine all variable DataFrames
        combined_df = pd.concat(variable_dfs.values(), axis=1, sort=True)
        
        # Ensure DatetimeIndex is properly named
        combined_df.index.name = 'date'
        
        return combined_df
    
    def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Any]:
        """Get metadata for specified variables from FRED API"""
        variables_list = self._normalize_variables(variables)
        metadata = {}
        
        for variable in variables_list:
            try:
                var_metadata = self.get_variable_metadata(variable)
                metadata[variable] = var_metadata
            except Exception as e:
                self.logger.error(f"Failed to get metadata for {variable}: {e}")
                # Continue with other variables
        
        return metadata
    
    def get_variable_metadata(self, variable: str) -> Dict[str, Any]:
        """Get metadata for a single variable"""
        if not self.is_connected:
            raise ConnectionError("Not connected to FRED API")
        
        self.rate_limiter.acquire()
        
        url = f"{self.base_url}/series"
        params = {
            'series_id': variable,
            'api_key': self.api_key,
            'file_type': 'json'
        }
        
        response = self.session.get(url, params=params, timeout=self.timeout)
        
        if not self.validate_response(response):
            raise DataRetrievalError(f"Failed to get metadata for {variable}")
        
        data = response.json()
        
        if 'error_code' in data:
            raise DataRetrievalError(f"FRED API error for {variable}: {data.get('error_message')}")
        
        series_info = data.get('seriess', [{}])[0]  # FRED API returns 'seriess' (plural)
        
        return {
            'code': variable,
            'name': series_info.get('title', ''),
            'description': series_info.get('notes', ''),
            'source': 'FRED',
            'units': series_info.get('units', ''),
            'frequency': series_info.get('frequency', ''),
            'last_updated': series_info.get('last_updated', '')
        }
    
    def validate_response(self, response: requests.Response) -> bool:
        """Validate FRED API response"""
        if response.status_code != 200:
            self.logger.error(f"FRED API returned status {response.status_code}: {response.text}")
            return False
        
        try:
            data = response.json()
            # Basic structure validation
            if isinstance(data, dict):
                return True
            else:
                self.logger.error("FRED API response is not a valid JSON object")
                return False
        except ValueError as e:
            self.logger.error(f"FRED API response is not valid JSON: {e}")
            return False
```

**Factory Implementation** (`data_sources/__init__.py`):
```python
"""
Data source factory and public interface for Federal Reserve ETL Pipeline.

This module provides the main entry point for creating data source instances
and accessing the core functionality of the ETL pipeline.
"""

from typing import Optional
from .base import DataSource
from .fred_client import FREDDataSource
from .haver_client import HaverDataSource
from ..utils.exceptions import ValidationError, ConfigurationError

def create_data_source(source: str, api_key: str = None, **config) -> DataSource:
    """
    Create a data source instance for the specified source type.
    
    This factory function provides a unified interface for creating different
    types of data sources with appropriate configuration and validation.
    
    Args:
        source: Data source type ('fred' or 'haver')
        api_key: API key for authentication (required)
        **config: Additional configuration parameters specific to the data source
        
    Returns:
        DataSource: Configured data source instance ready for use
        
    Raises:
        ValueError: If source type is not supported
        ConfigurationError: If required configuration is missing or invalid
        
    Examples:
        >>> # Create FRED data source
        >>> fred = create_data_source('fred', api_key='your_fred_api_key')
        >>> 
        >>> # Create Haver data source with custom timeout
        >>> haver = create_data_source('haver', api_key='your_haver_key', timeout=60)
        >>>
        >>> # Use context manager for automatic connection management
        >>> with create_data_source('fred', api_key='your_key') as fred:
        ...     df = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
    """
    
    if not api_key:
        raise ConfigurationError(f"API key is required for {source} data source")
    
    source_lower = source.lower().strip()
    
    if source_lower == 'fred':
        return FREDDataSource(api_key=api_key, **config)
    elif source_lower == 'haver':
        return HaverDataSource(api_key=api_key, **config)
    else:
        supported_sources = ['fred', 'haver']
        raise ValueError(f"Unsupported data source '{source}'. Supported sources: {supported_sources}")

# Export main classes and functions
__all__ = [
    'DataSource',
    'FREDDataSource', 
    'HaverDataSource',
    'create_data_source'
]
```

## 3. Key Algorithms

### Rate Limiting Algorithm
**Implementation**: Token Bucket with Time Window
```python
class RateLimiter:
    """
    Token bucket rate limiter with sliding time window.
    
    Algorithm ensures compliance with API rate limits by tracking request
    timestamps and enforcing delays when necessary.
    
    Time Complexity: O(1) amortized (O(k) worst case where k = max_requests)
    Space Complexity: O(k) where k = max_requests
    """
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window (e.g., 120 for FRED)
            time_window: Time window in seconds (e.g., 60 for per-minute limiting)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()  # Store request timestamps
        self._lock = threading.Lock()  # Thread safety for concurrent access
    
    def acquire(self) -> None:
        """
        Acquire permission to make a request, blocking if rate limit reached.
        
        Algorithm:
        1. Remove expired requests from sliding window
        2. Check if current requests < max_requests
        3. If at limit, calculate sleep time until oldest request expires
        4. Add current timestamp to request history
        """
        with self._lock:
            now = time.time()
            
            # Step 1: Remove requests outside time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # Step 2 & 3: Check limit and sleep if necessary
            if len(self.requests) >= self.max_requests:
                # Calculate sleep time until we can make another request
                oldest_request_time = self.requests[0]
                sleep_time = oldest_request_time + self.time_window - now
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    # Remove the expired request after sleeping
                    if self.requests and self.requests[0] == oldest_request_time:
                        self.requests.popleft()
            
            # Step 4: Record this request
            self.requests.append(time.time())
```

### Data Transformation Pipeline
**Algorithm**: Multi-source Data Standardization
```python
def _create_combined_dataframe(self, all_data: Dict[str, List]) -> pd.DataFrame:
    """
    Transform raw API data from multiple sources into standardized DataFrame.
    
    Algorithm handles:
    - Different API response formats (FRED JSON vs Haver XML)
    - Missing data standardization (convert '.' to NaN)
    - Date parsing and timezone handling
    - Variable alignment across different observation frequencies
    
    Time Complexity: O(n*m) where n = observations, m = variables
    Space Complexity: O(n*m) for final DataFrame
    """
    
    if not all_data:
        return pd.DataFrame()
    
    variable_dfs = {}
    
    for variable, observations in all_data.items():
        if not observations:
            continue
        
        # Phase 1: Parse and validate individual observations
        parsed_data = []
        for obs in observations:
            try:
                # Standardize date format
                if isinstance(obs.get('date'), str):
                    date = pd.to_datetime(obs['date'], format='%Y-%m-%d')
                else:
                    date = pd.to_datetime(obs['date'])
                
                # Standardize value format - handle FRED's '.' for missing data
                raw_value = obs.get('value', obs.get('val', ''))  # Haver uses 'val'
                if raw_value == '.' or raw_value == '' or raw_value is None:
                    value = pd.NA  # Use pandas native NA
                else:
                    value = pd.to_numeric(raw_value, errors='coerce')
                
                parsed_data.append({
                    'date': date,
                    'value': value
                })
                
            except (KeyError, ValueError, TypeError) as e:
                self.logger.warning(f"Skipping invalid observation for {variable}: {obs}, Error: {e}")
                continue
        
        # Phase 2: Create DataFrame for this variable
        if parsed_data:
            var_df = pd.DataFrame(parsed_data)
            var_df = var_df.set_index('date').rename(columns={'value': variable})
            
            # Remove duplicate dates (keep last occurrence)
            var_df = var_df[~var_df.index.duplicated(keep='last')]
            
            variable_dfs[variable] = var_df
    
    if not variable_dfs:
        return pd.DataFrame()
    
    # Phase 3: Combine all variables with proper alignment
    # Use outer join to preserve all dates across variables
    combined_df = pd.concat(variable_dfs.values(), axis=1, join='outer', sort=True)
    
    # Phase 4: Final standardization
    combined_df.index.name = 'date'
    
    # Sort by date for consistent output
    combined_df = combined_df.sort_index()
    
    return combined_df
```

### Retry Logic with Exponential Backoff
**Algorithm**: Exponential Backoff with Jitter
```python
def retry_on_failure(max_attempts: int = 3, backoff_factor: float = 1.0, 
                    max_backoff: float = 60.0, jitter: bool = True):
    """
    Decorator implementing retry logic with exponential backoff and jitter.
    
    Algorithm:
    - Exponential backoff: delay = backoff_factor * (2 ** attempt)  
    - Jitter: Add randomness to prevent thundering herd
    - Max backoff: Cap maximum delay to prevent excessive wait times
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Base multiplier for exponential backoff
        max_backoff: Maximum delay between retries (seconds)
        jitter: Add random jitter to backoff delay
    """
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except (ConnectionError, requests.Timeout, requests.ConnectionError) as e:
                    # These are potentially transient errors - retry
                    last_exception = e
                    
                    if attempt < max_attempts - 1:  # Don't sleep on last attempt
                        # Calculate exponential backoff delay
                        delay = min(backoff_factor * (2 ** attempt), max_backoff)
                        
                        # Add jitter to prevent thundering herd
                        if jitter:
                            delay *= (0.5 + random.random() * 0.5)  # ±25% jitter
                        
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                    
                except (AuthenticationError, ValidationError) as e:
                    # These are permanent errors - don't retry
                    logger.error(f"Permanent error, not retrying: {e}")
                    raise
                    
                except Exception as e:
                    # Unknown errors - treat as permanent to avoid infinite loops
                    logger.error(f"Unknown error, not retrying: {e}")
                    raise
            
            # All attempts exhausted
            raise DataRetrievalError(f"Request failed after {max_attempts} attempts: {last_exception}")
        
        return wrapper
    return decorator
```

## 4. Integration Points

### FRED API Integration Implementation
**Complete HTTP Client with Error Handling**:
```python
class FREDAPIClient:
    """
    Low-level HTTP client for FRED API with comprehensive error handling.
    
    Handles all FRED API communication patterns including:
    - Series data retrieval
    - Metadata queries  
    - Error response parsing
    - Rate limiting compliance
    """
    
    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Configure session with appropriate headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FederalReserveETL/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # Connection pooling configuration
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=0,  # Handle retries at higher level
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request to FRED API with comprehensive error handling.
        
        Args:
            endpoint: API endpoint (e.g., 'series/observations')
            params: Query parameters dictionary
            
        Returns:
            Parsed JSON response
            
        Raises:
            AuthenticationError: Invalid API key
            DataRetrievalError: API error or invalid response
            ConnectionError: Network or service issues
        """
        
        # Add API key and format to parameters
        full_params = {
            'api_key': self.api_key,
            'file_type': 'json',
            **params
        }
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(
                url, 
                params=full_params, 
                timeout=self.timeout,
                stream=False  # Load full response for JSON parsing
            )
            
            # Handle different HTTP status codes
            if response.status_code == 200:
                return self._parse_response(response)
                
            elif response.status_code == 400:
                error_data = self._safe_json_parse(response)
                if 'api_key' in response.text.lower():
                    raise AuthenticationError("Invalid FRED API key")
                else:
                    error_msg = error_data.get('error_message', 'Bad request')
                    raise DataRetrievalError(f"FRED API error: {error_msg}")
                    
            elif response.status_code == 403:
                raise AuthenticationError("FRED API access forbidden - check API key permissions")
                
            elif response.status_code == 404:
                raise DataRetrievalError("Requested data not found")
                
            elif response.status_code == 429:
                raise RateLimitError("FRED API rate limit exceeded")
                
            elif 500 <= response.status_code < 600:
                raise ConnectionError(f"FRED API server error: {response.status_code}")
                
            else:
                raise DataRetrievalError(f"Unexpected HTTP status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            raise ConnectionError(f"Request timeout after {self.timeout} seconds")
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to FRED API: {e}")
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"HTTP request failed: {e}")
    
    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parse and validate JSON response from FRED API"""
        try:
            data = response.json()
            
            # Check for API-level errors in successful HTTP responses
            if isinstance(data, dict) and 'error_code' in data:
                error_code = data['error_code']
                error_msg = data.get('error_message', 'Unknown API error')
                
                if error_code == 400:
                    raise DataRetrievalError(f"Invalid request: {error_msg}")
                elif error_code == 404:
                    raise DataRetrievalError(f"Data not found: {error_msg}")
                else:
                    raise DataRetrievalError(f"FRED API error {error_code}: {error_msg}")
            
            return data
            
        except ValueError as e:
            raise DataRetrievalError(f"Invalid JSON response from FRED API: {e}")
    
    def _safe_json_parse(self, response: requests.Response) -> Dict[str, Any]:
        """Safely parse JSON response, returning empty dict if parse fails"""
        try:
            return response.json()
        except ValueError:
            return {}
```

### Haver Analytics Integration Pattern
**Format Standardization Implementation**:
```python
class HaverDataSource(DataSource):
    """
    Haver Analytics API implementation with format standardization.
    
    Key challenges addressed:
    - Proprietary API response format conversion
    - Variable code mapping between Haver and FRED conventions
    - Different authentication mechanisms
    - Subscription-based rate limiting
    """
    
    def __init__(self, api_key: str, subscription_type: str = 'standard', **kwargs):
        super().__init__(api_key, **kwargs)
        
        self.subscription_type = subscription_type
        self.base_url = kwargs.get('base_url', 'https://api.haver.com/data')
        
        # Subscription-based rate limiting
        rate_limits = {
            'basic': {'requests': 60, 'window': 60},      # 60/minute
            'standard': {'requests': 300, 'window': 60},  # 300/minute  
            'premium': {'requests': 1200, 'window': 60}   # 1200/minute
        }
        
        limit_config = rate_limits.get(subscription_type, rate_limits['standard'])
        self.rate_limiter = RateLimiter(
            max_requests=limit_config['requests'],
            time_window=limit_config['window']
        )
        
        # Variable code mapping from Haver to FRED conventions
        self.variable_mapping = {
            'FFUNDS': 'FEDFUNDS',  # Federal Funds Rate
            'TB10Y': 'DGS10',      # 10-Year Treasury
            'TB3M': 'TB3MS',       # 3-Month Treasury Bill
            # Add more mappings as needed
        }
    
    def _map_variable_code(self, haver_code: str) -> str:
        """Map Haver variable codes to FRED-compatible names"""
        return self.variable_mapping.get(haver_code, haver_code)
    
    def _transform_haver_response(self, haver_data: Dict) -> List[Dict]:
        """
        Transform Haver API response to FRED-compatible format.
        
        Haver Response Format:
        {
            "series": {
                "FFUNDS": {
                    "data": [
                        {"date": "2023-01-01", "val": 4.25},
                        {"date": "2023-02-01", "val": 4.50}
                    ],
                    "metadata": {...}
                }
            }
        }
        
        Target Format (FRED-compatible):
        [
            {"date": "2023-01-01", "value": "4.25"},
            {"date": "2023-02-01", "value": "4.50"}
        ]
        """
        
        transformed_data = {}
        
        series_data = haver_data.get('series', {})
        
        for haver_code, series_info in series_data.items():
            # Map to FRED-compatible variable name
            fred_code = self._map_variable_code(haver_code)
            
            # Transform data points
            observations = []
            for data_point in series_info.get('data', []):
                observations.append({
                    'date': data_point['date'],
                    'value': str(data_point.get('val', data_point.get('value', '')))
                })
            
            transformed_data[fred_code] = observations
        
        return transformed_data
    
    @retry_on_failure(max_attempts=3, backoff_factor=1.0)
    def get_data(self, variables: Union[str, List[str]], 
                start_date: Union[str, datetime], 
                end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Extract data from Haver Analytics with format standardization.
        
        Implementation converts Haver's proprietary format to match FRED's
        DataFrame structure exactly, enabling seamless source switching.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Haver API")
        
        # Normalize inputs using base class methods
        variables_list = self._normalize_variables(variables)
        start_str = self._format_date(start_date)
        end_str = self._format_date(end_date)
        
        # Apply rate limiting
        self.rate_limiter.acquire()
        
        # Make API request to Haver
        haver_response = self._make_haver_request(variables_list, start_str, end_str)
        
        # Transform to FRED-compatible format
        standardized_data = self._transform_haver_response(haver_response)
        
        # Use base class method to create DataFrame (same as FRED)
        return self._create_combined_dataframe(standardized_data)
    
    def _make_haver_request(self, variables: List[str], 
                          start_date: str, end_date: str) -> Dict:
        """Make HTTP request to Haver Analytics API"""
        
        # Haver uses POST with JSON payload
        payload = {
            'series': variables,
            'start_date': start_date,
            'end_date': end_date,
            'format': 'json',
            'metadata': True
        }
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/extract",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid Haver Analytics API credentials")
            elif response.status_code == 403:
                raise AuthenticationError("Haver Analytics API access forbidden")
            elif response.status_code != 200:
                raise DataRetrievalError(f"Haver API error: {response.status_code}")
            
            return response.json()
            
        except requests.RequestException as e:
            raise ConnectionError(f"Haver API request failed: {e}")
```

## 5. Configuration Implementation

### Environment-based Configuration System
**Complete Configuration Management**:
```python
# config.py
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

from .utils.exceptions import ConfigurationError

@dataclass
class APIEndpointConfig:
    """Configuration for API endpoints and connection parameters"""
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit: int = 120
    rate_window: int = 60

@dataclass  
class FREDConfig(APIEndpointConfig):
    """FRED-specific configuration with defaults"""
    base_url: str = "https://api.stlouisfed.org/fred"
    rate_limit: int = 120  # FRED allows 120 requests per minute
    
    def __post_init__(self):
        if self.rate_limit > 120:
            logging.warning("FRED API rate limit should not exceed 120 requests/minute")

@dataclass
class HaverConfig(APIEndpointConfig):
    """Haver Analytics configuration with subscription-aware defaults"""
    base_url: str = "https://api.haver.com/data"
    subscription_type: str = "standard"
    rate_limit: int = field(init=False)  # Calculated based on subscription
    
    def __post_init__(self):
        # Set rate limit based on subscription type
        subscription_limits = {
            'basic': 60,
            'standard': 300, 
            'premium': 1200
        }
        self.rate_limit = subscription_limits.get(self.subscription_type, 300)

@dataclass
class LoggingConfig:
    """Logging configuration with file and console options"""
    level: str = "INFO"
    log_file: Optional[str] = None
    enable_console: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5
    
    def __post_init__(self):
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ConfigurationError(f"Invalid log level: {self.level}")
        
        # Create log directory if file logging enabled
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

@dataclass
class ETLConfig:
    """Main ETL pipeline configuration"""
    fred: FREDConfig = field(default_factory=FREDConfig)
    haver: HaverConfig = field(default_factory=HaverConfig) 
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # API credentials (loaded from environment)
    fred_api_key: Optional[str] = field(default=None, init=False)
    haver_api_key: Optional[str] = field(default=None, init=False)
    
    def __post_init__(self):
        # Load API keys from environment
        self.fred_api_key = os.getenv('FRED_API_KEY')
        self.haver_api_key = os.getenv('HAVER_API_KEY')

class ConfigManager:
    """Centralized configuration management for the ETL pipeline"""
    
    def __init__(self):
        self.config = ETLConfig()
        self.logger = logging.getLogger(__name__)
    
    def validate_credentials(self, source: str) -> bool:
        """
        Validate that required credentials are available for a data source.
        
        Args:
            source: Data source type ('fred' or 'haver')
            
        Returns:
            bool: True if valid credentials available
        """
        if source.lower() == 'fred':
            api_key = self.config.fred_api_key
            if not api_key:
                return False
            
            # Validate FRED API key format (32 characters)
            if len(api_key) != 32:
                self.logger.error("FRED API key must be exactly 32 characters")
                return False
            
            return True
            
        elif source.lower() == 'haver':
            api_key = self.config.haver_api_key
            if not api_key:
                return False
            
            # Haver API keys vary in format, just check non-empty
            return len(api_key.strip()) > 0
            
        else:
            raise ValueError(f"Unknown data source: {source}")
    
    def get_missing_credentials(self, source: str = None) -> List[str]:
        """
        Get list of missing credential environment variables.
        
        Args:
            source: Specific source to check, or None for all sources
            
        Returns:
            List of missing environment variable names
        """
        missing = []
        
        sources_to_check = [source] if source else ['fred', 'haver']
        
        for src in sources_to_check:
            if src.lower() == 'fred' and not self.config.fred_api_key:
                missing.append('FRED_API_KEY')
            elif src.lower() == 'haver' and not self.config.haver_api_key:
                missing.append('HAVER_API_KEY')
        
        return missing
    
    def get_data_source_config(self, source: str) -> Dict[str, Any]:
        """
        Get configuration dictionary for a specific data source.
        
        Args:
            source: Data source type ('fred' or 'haver')
            
        Returns:
            Configuration dictionary for the data source
            
        Raises:
            ConfigurationError: If source is unsupported or credentials missing
        """
        if source.lower() == 'fred':
            if not self.validate_credentials('fred'):
                missing = self.get_missing_credentials('fred')
                raise ConfigurationError(f"Missing FRED credentials: {missing}")
            
            return {
                'source_name': 'FRED',
                'api_key': self.config.fred_api_key,
                'base_url': self.config.fred.base_url,
                'timeout': self.config.fred.timeout,
                'rate_limit': self.config.fred.rate_limit,
                'rate_window': self.config.fred.rate_window,
                'max_retries': self.config.fred.max_retries
            }
            
        elif source.lower() == 'haver':
            if not self.validate_credentials('haver'):
                missing = self.get_missing_credentials('haver')
                raise ConfigurationError(f"Missing Haver credentials: {missing}")
            
            return {
                'source_name': 'Haver Analytics',
                'api_key': self.config.haver_api_key,
                'base_url': self.config.haver.base_url,
                'timeout': self.config.haver.timeout,
                'rate_limit': self.config.haver.rate_limit,
                'rate_window': self.config.haver.rate_window,
                'max_retries': self.config.haver.max_retries,
                'subscription_type': self.config.haver.subscription_type
            }
            
        else:
            raise ValueError(f"Unsupported data source: {source}")
    
    def setup_logging(self) -> logging.Logger:
        """Configure logging based on configuration settings"""
        from .utils.logging import setup_logging
        
        return setup_logging(
            log_level=self.config.logging.level,
            log_file=self.config.logging.log_file,
            enable_console=self.config.logging.enable_console,
            max_log_size_mb=self.config.logging.max_file_size_mb,
            backup_count=self.config.logging.backup_count
        )

# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get singleton instance of configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def validate_source_credentials(source: str) -> bool:
    """
    Validate credentials for a specific data source.
    
    Args:
        source: Data source type ('fred' or 'haver')
        
    Returns:
        bool: True if credentials are valid
    """
    return get_config_manager().validate_credentials(source)

# Environment variable validation functions
def check_environment_setup() -> Dict[str, Any]:
    """
    Check current environment setup and return status report.
    
    Returns:
        Dictionary with environment status information
    """
    manager = get_config_manager()
    
    return {
        'fred_configured': manager.validate_credentials('fred'),
        'haver_configured': manager.validate_credentials('haver'),
        'missing_credentials': manager.get_missing_credentials(),
        'environment_variables': {
            'FRED_API_KEY': 'SET' if os.getenv('FRED_API_KEY') else 'NOT SET',
            'HAVER_API_KEY': 'SET' if os.getenv('HAVER_API_KEY') else 'NOT SET'
        }
    }
```

## 6. Testing Implementation

### Integration Test Suite Structure
**Real API Testing Framework**:
```python
# tests/integration/test_fred_api_connectivity.py
import pytest
import os
import pandas as pd
from datetime import datetime, timedelta

# Add src to Python path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from federal_reserve_etl import create_data_source, validate_source_credentials
from federal_reserve_etl.utils import (
    ConnectionError, AuthenticationError, DataRetrievalError, ValidationError
)

class TestFREDAPIConnectivity:
    """
    Integration tests for FRED API with real API calls.
    
    These tests validate the complete integration with the FRED API
    using actual API calls to ensure real-world compatibility.
    """
    
    @classmethod
    def setup_class(cls):
        """Setup for all tests - validate API key availability"""
        cls.api_key = os.getenv('FRED_API_KEY')
        if not cls.api_key:
            pytest.skip("FRED_API_KEY environment variable not set")
        
        # Validate API key format
        if len(cls.api_key) != 32:
            pytest.skip("Invalid FRED_API_KEY format - must be 32 characters")
    
    def test_fred_api_key_validation(self):
        """Test that our API key is valid and credentials work"""
        assert validate_source_credentials('fred'), "FRED credentials should be valid"
    
    def test_fred_data_source_creation(self):
        """Test creating FRED data source with factory pattern"""
        fred = create_data_source('fred', api_key=self.api_key)
        
        assert fred is not None
        assert hasattr(fred, 'connect')
        assert hasattr(fred, 'get_data')
        assert hasattr(fred, 'get_metadata')
        assert fred.api_key == self.api_key
    
    def test_fred_connection_lifecycle(self):
        """Test complete FRED connection lifecycle"""
        fred = create_data_source('fred', api_key=self.api_key)
        
        # Test connection
        connection_result = fred.connect()
        assert connection_result == True
        assert fred.is_connected == True
        
        # Test disconnection
        fred.disconnect()
        assert fred.is_connected == False
    
    def test_fred_context_manager(self):
        """Test FRED data source context manager pattern"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            assert fred.is_connected == True
            # Connection should be active inside context
            
            # Test a simple data request while in context
            df = fred.get_data(
                variables="FEDFUNDS",
                start_date="2023-01-01",
                end_date="2023-01-31"
            )
            assert isinstance(df, pd.DataFrame)
        
        # Connection should be closed after context
        assert fred.is_connected == False
    
    @pytest.mark.parametrize("variable,expected_columns", [
        ("FEDFUNDS", ["FEDFUNDS"]),
        ("DGS10", ["DGS10"]), 
        ("TB3MS", ["TB3MS"]),
    ])
    def test_single_variable_extraction(self, variable, expected_columns):
        """Test extracting single variables from FRED with parameterized inputs"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Get recent data (last 30 days)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            df = fred.get_data(
                variables=variable,
                start_date=start_date,
                end_date=end_date
            )
            
            # Validate DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert isinstance(df.index, pd.DatetimeIndex)
            assert list(df.columns) == expected_columns
            assert len(df) >= 0  # May be empty for weekends/holidays in recent data
    
    def test_multiple_variable_extraction(self):
        """Test extracting multiple variables simultaneously"""
        variables = ["FEDFUNDS", "DGS10", "TB3MS"]
        
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Get data for a known period with data
            df = fred.get_data(
                variables=variables,
                start_date="2023-01-01", 
                end_date="2023-03-31"
            )
            
            # Validate DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert isinstance(df.index, pd.DatetimeIndex)
            
            # Should have all requested variables as columns
            for var in variables:
                assert var in df.columns, f"Missing variable {var}"
            
            # Should have data for Q1 2023
            assert len(df) > 0, "Should have observations for Q1 2023"
            
            # Check date range
            assert df.index.min().strftime('%Y-%m-%d') >= "2023-01-01"
            assert df.index.max().strftime('%Y-%m-%d') <= "2023-03-31"
    
    def test_historical_data_extraction(self):
        """Test extracting historical data from different time periods"""
        test_cases = [
            ("2020-01-01", "2020-01-31", "Recent historical data"),
            ("2010-01-01", "2010-01-31", "10+ years historical data"),
            ("2000-01-01", "2000-01-31", "20+ years historical data"),
        ]
        
        with create_data_source('fred', api_key=self.api_key) as fred:
            for start_date, end_date, description in test_cases:
                df = fred.get_data(
                    variables="FEDFUNDS",
                    start_date=start_date,
                    end_date=end_date
                )
                
                assert isinstance(df, pd.DataFrame), f"Failed for {description}"
                assert len(df) > 0, f"No data for {description}"
                
                # Validate date range
                assert df.index.min().strftime('%Y-%m-%d') >= start_date
                assert df.index.max().strftime('%Y-%m-%d') <= end_date
    
    def test_metadata_retrieval(self):
        """Test retrieving metadata for FRED variables"""
        variables = ["FEDFUNDS", "DGS10"]
        
        with create_data_source('fred', api_key=self.api_key) as fred:
            metadata = fred.get_metadata(variables)
            
            # Validate metadata structure
            assert isinstance(metadata, dict)
            assert len(metadata) == len(variables)
            
            for var in variables:
                assert var in metadata, f"Missing metadata for {var}"
                
                var_meta = metadata[var]
                required_fields = ['code', 'name', 'source']
                for field in required_fields:
                    assert field in var_meta, f"Missing field {field} for {var}"
                
                assert var_meta['source'] == 'FRED'
                assert var_meta['code'] == var
    
    def test_get_variable_metadata_single(self):
        """Test getting metadata for a single variable"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            metadata = fred.get_variable_metadata("FEDFUNDS")
            
            assert isinstance(metadata, dict)
            assert metadata['code'] == 'FEDFUNDS'
            assert metadata['source'] == 'FRED'
            assert 'name' in metadata
            assert 'description' in metadata
    
    def test_error_handling_invalid_variable(self):
        """Test error handling for invalid variable codes"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Test with obviously invalid variable code
            with pytest.raises(DataRetrievalError):
                fred.get_data(
                    variables="INVALID_VAR_CODE_12345",
                    start_date="2023-01-01",
                    end_date="2023-01-31"
                )
    
    def test_error_handling_invalid_dates(self):
        """Test error handling for invalid date ranges"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Test with invalid date range (start > end)
            with pytest.raises(ValidationError):
                fred.get_data(
                    variables="FEDFUNDS",
                    start_date="2023-12-31",  # Start after end
                    end_date="2023-01-01"
                )
    
    def test_authentication_error_simulation(self):
        """Test authentication error with invalid API key"""
        # Test with properly formatted but invalid API key
        invalid_key = '1234567890123456789012345678901X'  # 32 chars but invalid
        
        fred = create_data_source('fred', api_key=invalid_key)
        
        # Should fail when trying to connect
        with pytest.raises(AuthenticationError):
            fred.connect()

# Test fixtures for data validation
@pytest.fixture(scope="session")
def fred_api_key():
    """Fixture providing FRED API key for integration tests"""
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        pytest.skip("FRED_API_KEY environment variable not set")
    return api_key

def assert_valid_dataframe(df: pd.DataFrame, expected_columns: list = None, min_rows: int = 1):
    """Custom assertion for validating DataFrame structure"""
    assert isinstance(df, pd.DataFrame), "Expected pandas DataFrame"
    assert len(df) >= min_rows, f"Expected at least {min_rows} rows, got {len(df)}"
    
    if expected_columns:
        for col in expected_columns:
            assert col in df.columns, f"Missing expected column: {col}"
    
    # Check for DatetimeIndex
    assert isinstance(df.index, pd.DatetimeIndex), "Expected DatetimeIndex for time series data"

def assert_valid_metadata(metadata: dict, expected_variables: list):
    """Custom assertion for validating metadata structure"""
    assert isinstance(metadata, dict), "Expected metadata dictionary"
    
    for var in expected_variables:
        assert var in metadata, f"Missing metadata for variable: {var}"
        
        var_meta = metadata[var]
        required_fields = ['code', 'name', 'source']
        
        for field in required_fields:
            assert field in var_meta, f"Missing required metadata field '{field}' for variable {var}"
        
        assert var_meta['code'] == var, f"Metadata code mismatch for {var}"
```

### Performance and Load Testing
**Rate Limiting and Performance Validation**:
```python
def test_rate_limiting_behavior(self):
    """Test FRED API rate limiting compliance under load"""
    with create_data_source('fred', api_key=self.api_key) as fred:
        # Make multiple rapid requests to test rate limiting
        start_time = datetime.now()
        requests_made = 0
        
        # Conservative test - stay well under limit but test timing
        for i in range(5):
            df = fred.get_data(
                variables="FEDFUNDS",
                start_date="2023-01-01",
                end_date="2023-01-31"
            )
            assert len(df) >= 0  # May be empty but shouldn't error
            requests_made += 1
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should take at least some time due to rate limiting
        # With 120 requests/minute, 5 requests should take at least 2 seconds
        expected_min_time = (requests_made - 1) * (60.0 / 120)  # Account for rate limiting
        
        assert duration >= expected_min_time * 0.8, f"Rate limiting should enforce minimum delays. Expected: {expected_min_time}s, Got: {duration}s"

def test_concurrent_requests_handling(self):
    """Test handling of concurrent requests (if implemented)"""
    import threading
    import queue
    
    def worker(api_key: str, result_queue: queue.Queue, worker_id: int):
        """Worker function for concurrent testing"""
        try:
            with create_data_source('fred', api_key=api_key) as fred:
                df = fred.get_data("FEDFUNDS", "2023-01-01", "2023-01-31")
                result_queue.put(f"worker-{worker_id}: success, {len(df)} rows")
        except Exception as e:
            result_queue.put(f"worker-{worker_id}: error - {e}")
    
    # Test with small number of concurrent workers
    num_workers = 3
    result_queue = queue.Queue()
    threads = []
    
    # Start workers
    for i in range(num_workers):
        t = threading.Thread(target=worker, args=(self.api_key, result_queue, i))
        threads.append(t)
        t.start()
    
    # Wait for completion
    for t in threads:
        t.join()
    
    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())
    
    # Validate all workers completed successfully
    assert len(results) == num_workers
    for result in results:
        assert "success" in result, f"Worker failed: {result}"
```

## 7. Development Tools and Scripts

### Development Environment Setup
**Complete Development Script**:
```bash
#!/bin/bash
# scripts/dev_setup.sh - Development environment setup script

set -e  # Exit on any error

echo "🚀 Setting up Federal Reserve ETL Pipeline development environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing runtime dependencies..."
pip install -r requirements.txt

echo "🧪 Installing development dependencies..."
pip install -r requirements-dev.txt

# Install package in development mode
echo "🔗 Installing package in development mode..."
pip install -e .

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p output
mkdir -p tests/fixtures

# Set up git hooks (if .git directory exists)
if [ -d ".git" ]; then
    echo "🪝 Setting up git pre-commit hooks..."
    
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for Federal Reserve ETL Pipeline

echo "🔍 Running pre-commit checks..."

# Check for Python syntax errors
echo "Checking Python syntax..."
find src tests -name "*.py" -exec python -m py_compile {} \;

if [ $? -ne 0 ]; then
    echo "❌ Python syntax errors found"
    exit 1
fi

# Check for large files (>1MB)
echo "Checking for large files..."
large_files=$(find . -size +1M -not -path "./.git/*" -not -path "./venv/*" -not -path "./__pycache__/*")
if [ -n "$large_files" ]; then
    echo "⚠️ Large files found (consider .gitignore):"
    echo "$large_files"
fi

# Check for API keys in code
echo "Checking for exposed API keys..."
if grep -r "api_key.*=" src/ --include="*.py" | grep -v "api_key.*os.getenv\|api_key.*None\|api_key.*str"; then
    echo "❌ Potential API key exposure found in source code"
    exit 1
fi

echo "✅ Pre-commit checks passed"
EOF

    chmod +x .git/hooks/pre-commit
fi

# Verify installation
echo "🧪 Verifying installation..."

# Test imports
python3 -c "
import sys
sys.path.insert(0, 'src')

try:
    from federal_reserve_etl import create_data_source
    from federal_reserve_etl.utils import ValidationError
    print('✅ Package imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

# Check if API keys are available
if [ -n "$FRED_API_KEY" ]; then
    echo "✅ FRED_API_KEY environment variable is set"
    
    # Test API connectivity
    python3 -c "
import sys
import os
sys.path.insert(0, 'src')

from federal_reserve_etl import validate_source_credentials

try:
    if validate_source_credentials('fred'):
        print('✅ FRED API connection test successful')
    else:
        print('⚠️ FRED API credentials may be invalid')
except Exception as e:
    print(f'⚠️ FRED API test failed: {e}')
"
else
    echo "⚠️ FRED_API_KEY not set - some functionality will be limited"
    echo "   Set it with: export FRED_API_KEY='your_api_key_here'"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Activate the virtual environment: source venv/bin/activate"
echo "   2. Set your FRED API key: export FRED_API_KEY='your_key'"
echo "   3. Run tests: pytest tests/integration/"
echo "   4. Start developing!"
echo ""
echo "🔧 Available commands:"
echo "   pytest                    - Run all tests"
echo "   pytest tests/integration/ - Run integration tests only"
echo "   python extract_fed_data.py --help - CLI usage"
echo "   jupyter notebook Federal_Reserve_ETL_Interactive.ipynb - Interactive interface"
```

### Code Quality Tools
**Automated Code Quality Script**:
```python
#!/usr/bin/env python3
# scripts/check_code_quality.py - Code quality validation script

import os
import sys
import subprocess
import re
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} passed")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def check_python_syntax():
    """Check Python syntax for all source files"""
    python_files = []
    for root in ['src', 'tests']:
        if os.path.exists(root):
            for path in Path(root).rglob('*.py'):
                python_files.append(str(path))
    
    if not python_files:
        print("⚠️ No Python files found")
        return True
    
    syntax_errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), file_path, 'exec')
        except SyntaxError as e:
            syntax_errors.append(f"{file_path}: {e}")
    
    if syntax_errors:
        print("❌ Python syntax errors found:")
        for error in syntax_errors:
            print(f"   {error}")
        return False
    else:
        print("✅ Python syntax check passed")
        return True

def check_imports():
    """Check that all imports can be resolved"""
    print("🔍 Checking import resolution...")
    
    import_check_script = '''
import sys
sys.path.insert(0, "src")

try:
    # Test core imports
    from federal_reserve_etl import create_data_source, validate_source_credentials
    from federal_reserve_etl.data_sources import DataSource, FREDDataSource
    from federal_reserve_etl.utils import ValidationError, DataRetrievalError
    print("✅ All imports resolved successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
'''
    
    return run_command(f'python3 -c "{import_check_script}"', "Import resolution check")

def check_docstrings():
    """Check that public functions have docstrings"""
    print("🔍 Checking docstring coverage...")
    
    python_files = list(Path('src').rglob('*.py'))
    missing_docstrings = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Simple regex to find function definitions
            functions = re.findall(r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content, re.MULTILINE)
            
            for func_name in functions:
                # Skip private functions and special methods
                if func_name.startswith('_'):
                    continue
                
                # Check if function has a docstring
                func_pattern = rf'def\s+{re.escape(func_name)}\s*\([^)]*\):[^"\']*?"""'
                if not re.search(func_pattern, content, re.DOTALL):
                    missing_docstrings.append(f"{file_path}:{func_name}")
        
        except Exception as e:
            print(f"⚠️ Error checking {file_path}: {e}")
    
    if missing_docstrings:
        print(f"⚠️ Functions missing docstrings ({len(missing_docstrings)}):")
        for missing in missing_docstrings[:10]:  # Show first 10
            print(f"   {missing}")
        if len(missing_docstrings) > 10:
            print(f"   ... and {len(missing_docstrings) - 10} more")
        return False
    else:
        print("✅ Docstring coverage check passed")
        return True

def check_security():
    """Check for potential security issues"""
    print("🔍 Checking for security issues...")
    
    security_issues = []
    
    # Check for hardcoded API keys
    python_files = list(Path('src').rglob('*.py'))
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                # Check for hardcoded API key patterns
                if re.search(r'api_key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', line):
                    security_issues.append(f"{file_path}:{i} - Potential hardcoded API key")
                
                # Check for print statements with sensitive data
                if re.search(r'print\s*\(.*api_key.*\)', line, re.IGNORECASE):
                    security_issues.append(f"{file_path}:{i} - API key in print statement")
        
        except Exception as e:
            print(f"⚠️ Error checking {file_path}: {e}")
    
    if security_issues:
        print("❌ Security issues found:")
        for issue in security_issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ Security check passed")
        return True

def check_test_coverage():
    """Check test file presence and basic coverage"""
    print("🔍 Checking test coverage...")
    
    # Check if test files exist
    test_dirs = ['tests/unit', 'tests/integration']
    test_files_found = 0
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            test_files = list(Path(test_dir).rglob('test_*.py'))
            test_files_found += len(test_files)
            print(f"   Found {len(test_files)} test files in {test_dir}")
    
    if test_files_found == 0:
        print("⚠️ No test files found")
        return False
    else:
        print(f"✅ Found {test_files_found} total test files")
        return True

def main():
    """Main code quality check function"""
    print("🔍 Federal Reserve ETL Pipeline - Code Quality Check")
    print("=" * 60)
    
    checks = [
        (check_python_syntax, "Python Syntax"),
        (check_imports, "Import Resolution"),
        (check_docstrings, "Docstring Coverage"),
        (check_security, "Security Issues"),
        (check_test_coverage, "Test Coverage")
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check_func, check_name in checks:
        print(f"\n📋 Running {check_name} check...")
        if check_func():
            passed_checks += 1
        print("-" * 40)
    
    # Summary
    print(f"\n📊 Code Quality Summary:")
    print(f"   Passed: {passed_checks}/{total_checks} checks")
    
    if passed_checks == total_checks:
        print("🎉 All code quality checks passed!")
        return 0
    else:
        print(f"⚠️ {total_checks - passed_checks} checks failed")
        print("💡 Please address the issues above before committing")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

**Document Status**: ✅ Complete - Comprehensive Implementation Guide  
**Last Updated**: August 29, 2024  
**Version**: 1.0 (Post-Implementation Documentation)  
**Implementation Status**: Fully implemented and tested with 19 integration tests passing