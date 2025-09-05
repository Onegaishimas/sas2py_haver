"""
FRED API Client Implementation

Federal Reserve Economic Data (FRED) API client for retrieving economic
time series data with authentication, rate limiting, and error handling.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import requests
from urllib.parse import urlencode

from .base import DataSource
from ..utils import (
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    ValidationError,
    RateLimitError,
    handle_api_errors,
    log_and_handle_error,
    validate_and_convert_dates,
    validate_variable_codes,
    get_logger,
    VariableCode,
    DateString,
    TimeSeriesData,
    APIKey,
    DataSourceConfig
)


class FREDDataSource(DataSource):
    """
    Federal Reserve Economic Data (FRED) API client implementation
    
    Provides access to FRED economic time series data with proper authentication,
    rate limiting, and standardized error handling. Inherits from DataSource
    abstract base class and implements all required methods.
    
    Attributes:
        api_key: FRED API key for authentication
        base_url: Base URL for FRED API endpoints
        session: HTTP session for connection pooling
        rate_limiter: Rate limiting state tracking
        is_connected: Connection status flag
        last_request_time: Timestamp of last API request
        requests_this_minute: Counter for rate limiting
    
    Examples:
        >>> fred = FREDDataSource(api_key='your-api-key')
        >>> fred.connect()
        >>> data = fred.get_data(['FEDFUNDS', 'DGS10'], '2020-01-01', '2020-12-31')
        >>> fred.disconnect()
    """
    
    def __init__(self, api_key: APIKey, config: Optional[DataSourceConfig] = None):
        """
        Initialize FRED API client
        
        Args:
            api_key: Valid FRED API key for authentication
            config: Optional configuration override dictionary
            
        Raises:
            ValidationError: If API key is invalid format
            ConfigurationError: If configuration parameters are invalid
        """
        super().__init__()
        
        self.logger = get_logger(__name__)
        self.api_key = self._validate_api_key(api_key)
        
        # Default configuration
        default_config = {
            'base_url': 'https://api.stlouisfed.org/fred',
            'rate_limit': 120,  # requests per minute
            'timeout': 30,      # seconds
            'retry_config': {
                'retry_count': 3,
                'retry_delay': 1.0,
                'backoff_factor': 2.0,
                'retry_exceptions': (ConnectionError, requests.RequestException)
            }
        }
        
        # Merge with provided config
        self.config = {**default_config, **(config or {})}
        self.base_url = self.config['base_url']
        self.rate_limit = self.config['rate_limit']
        self.timeout = self.config['timeout']
        
        # Connection state
        self.session: Optional[requests.Session] = None
        self.is_connected = False
        
        # Rate limiting state
        self.last_request_time = datetime.min
        self.requests_this_minute = 0
        self.minute_window_start = datetime.min
        
        self.logger.info(f"Initialized FREDDataSource with rate limit {self.rate_limit}/min")
    
    def _validate_api_key(self, api_key: str) -> str:
        """
        Validate FRED API key format
        
        Args:
            api_key: API key to validate
            
        Returns:
            Validated API key
            
        Raises:
            ValidationError: If API key format is invalid
        """
        if not api_key or not isinstance(api_key, str):
            raise ValidationError(
                "FRED API key must be a non-empty string",
                field="api_key",
                expected="non-empty string",
                actual=type(api_key).__name__
            )
        
        # FRED API keys are typically 32 character alphanumeric strings
        if len(api_key) != 32 or not api_key.replace('-', '').isalnum():
            raise ValidationError(
                "FRED API key must be 32 character alphanumeric string",
                field="api_key",
                expected="32 character alphanumeric",
                actual=f"length {len(api_key)}"
            )
        
        return api_key
    
    @handle_api_errors(retry_count=3, retry_delay=1.0, backoff_factor=2.0)
    def connect(self) -> bool:
        """
        Establish connection to FRED API
        
        Creates HTTP session, validates API key by making test request,
        and initializes rate limiting state.
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If unable to connect to API
            AuthenticationError: If API key is invalid
        """
        try:
            self.logger.info("Connecting to FRED API...")
            
            # Create HTTP session with connection pooling
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'federal-reserve-etl/1.0',
                'Accept': 'application/json'
            })
            
            # Test connection with API key validation
            test_url = f"{self.base_url}/series"
            test_params = {
                'api_key': self.api_key,
                'series_id': 'FEDFUNDS',  # Always available test series
                'limit': 1,
                'file_type': 'json'
            }
            
            response = self.session.get(
                test_url,
                params=test_params,
                timeout=self.timeout
            )
            
            if response.status_code == 400:
                # Check if it's an API key issue
                error_data = response.json()
                if 'error_message' in error_data and 'api_key' in error_data['error_message'].lower():
                    raise AuthenticationError(
                        f"Invalid FRED API key: {error_data.get('error_message', 'Unknown error')}",
                        api_key_hint=f"{self.api_key[:4]}...{self.api_key[-4:]}",
                        source="FRED"
                    )
            
            response.raise_for_status()
            
            # Initialize rate limiting
            self.minute_window_start = datetime.now()
            self.requests_this_minute = 1  # Count the test request
            self.last_request_time = datetime.now()
            
            self.is_connected = True
            self.logger.info("Successfully connected to FRED API")
            return True
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to FRED API: {str(e)}",
                endpoint=self.base_url
            )
        except requests.exceptions.Timeout as e:
            raise ConnectionError(
                f"Connection timeout to FRED API: {str(e)}",
                endpoint=self.base_url
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "FRED API authentication failed - check API key",
                    api_key_hint=f"{self.api_key[:4]}...{self.api_key[-4:]}",
                    source="FRED"
                )
            else:
                raise ConnectionError(
                    f"HTTP error connecting to FRED API: {str(e)}",
                    endpoint=self.base_url,
                    status_code=e.response.status_code
                )
    
    def disconnect(self) -> None:
        """
        Close connection to FRED API
        
        Closes HTTP session and resets connection state.
        Safe to call multiple times.
        """
        if self.session:
            self.session.close()
            self.session = None
        
        self.is_connected = False
        self.logger.info("Disconnected from FRED API")
    
    def _enforce_rate_limit(self) -> None:
        """
        Enforce FRED API rate limits (120 requests per minute)
        
        Tracks requests in sliding window and enforces delays when necessary.
        
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        now = datetime.now()
        
        # Reset counter if we're in a new minute window
        if (now - self.minute_window_start).total_seconds() >= 60:
            self.minute_window_start = now
            self.requests_this_minute = 0
        
        # Check if we're at the rate limit
        if self.requests_this_minute >= self.rate_limit:
            seconds_to_wait = 60 - (now - self.minute_window_start).total_seconds()
            if seconds_to_wait > 0:
                raise RateLimitError(
                    f"FRED API rate limit exceeded. Wait {seconds_to_wait:.1f} seconds",
                    limit=self.rate_limit,
                    retry_after=int(seconds_to_wait) + 1
                )
        
        # Ensure minimum time between requests (0.5 seconds)
        time_since_last = (now - self.last_request_time).total_seconds()
        if time_since_last < 0.5:
            time.sleep(0.5 - time_since_last)
        
        self.requests_this_minute += 1
        self.last_request_time = datetime.now()
    
    def get_data(
        self,
        variables: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        **kwargs
    ) -> TimeSeriesData:
        """
        Retrieve time series data from FRED API
        
        Fetches economic time series data for specified variables within
        the given date range. Handles rate limiting, authentication, and
        data format standardization.
        
        Args:
            variables: Variable code(s) to retrieve (e.g., 'FEDFUNDS', ['FEDFUNDS', 'DGS10'])
            start_date: Start date in YYYY-MM-DD format or datetime object
            end_date: End date in YYYY-MM-DD format or datetime object
            **kwargs: Additional parameters:
                - frequency: Data frequency ('d', 'w', 'm', 'q', 'a')
                - aggregation_method: How to aggregate ('avg', 'sum', 'eop')
                - transformation: Data transformation ('lin', 'chg', 'ch1', 'pch', 'pc1', 'pca', 'cch', 'cca', 'log')
        
        Returns:
            DataFrame with DatetimeIndex and variable columns
            
        Raises:
            ValidationError: If variables or dates are invalid
            DataRetrievalError: If data retrieval fails
            RateLimitError: If rate limit is exceeded
            ConnectionError: If not connected to API
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to FRED API. Call connect() first.")
        
        # Validate and normalize inputs
        variable_list = validate_variable_codes(variables)
        start_dt, end_dt = validate_and_convert_dates(start_date, end_date)
        
        # Convert datetime objects to YYYY-MM-DD format for FRED API
        start_str = start_dt.strftime('%Y-%m-%d')
        end_str = end_dt.strftime('%Y-%m-%d')
        
        self.logger.info(f"Retrieving FRED data for {len(variable_list)} variables from {start_str} to {end_str}")
        
        # Collect data for all variables
        all_data = {}
        failed_variables = []
        
        for variable in variable_list:
            try:
                self._enforce_rate_limit()
                
                # Get series observations
                series_data = self._fetch_series_observations(
                    variable, start_str, end_str, **kwargs
                )
                
                if not series_data.empty:
                    all_data[variable] = series_data
                else:
                    self.logger.warning(f"No data returned for variable {variable}")
                    failed_variables.append(variable)
                    
            except Exception as e:
                self.logger.error(f"Failed to retrieve data for variable {variable}: {str(e)}")
                failed_variables.append(variable)
        
        if not all_data:
            raise DataRetrievalError(
                "No data retrieved for any requested variables",
                variables=variable_list,
                date_range=(start_str, end_str)
            )
        
        # Combine all series into single DataFrame
        combined_df = pd.DataFrame()
        for variable, series in all_data.items():
            combined_df[variable] = series
        
        # Log summary
        if failed_variables:
            self.logger.warning(f"Failed to retrieve {len(failed_variables)} variables: {failed_variables}")
        
        self.logger.info(f"Successfully retrieved data: {combined_df.shape[0]} observations, {combined_df.shape[1]} variables")
        
        return combined_df
    
    def _fetch_series_observations(
        self,
        series_id: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> pd.Series:
        """
        Fetch observations for a single FRED series
        
        Args:
            series_id: FRED series identifier
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional FRED API parameters
            
        Returns:
            Pandas Series with DatetimeIndex
            
        Raises:
            DataRetrievalError: If API request fails
        """
        url = f"{self.base_url}/series/observations"
        
        params = {
            'api_key': self.api_key,
            'series_id': series_id,
            'observation_start': start_date,
            'observation_end': end_date,
            'file_type': 'json',
            'sort_order': 'asc'
        }
        
        # Add optional parameters
        if 'frequency' in kwargs:
            params['frequency'] = kwargs['frequency']
        if 'aggregation_method' in kwargs:
            params['aggregation_method'] = kwargs['aggregation_method']
        if 'transformation' in kwargs:
            params['units'] = kwargs['transformation']
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Validate response format
            if 'observations' not in data:
                raise DataRetrievalError(
                    f"Invalid FRED API response format for series {series_id}",
                    variables=[series_id],
                    response_status=response.status_code
                )
            
            observations = data['observations']
            if not observations:
                return pd.Series(dtype=float)
            
            # Convert to pandas Series
            dates = []
            values = []
            
            for obs in observations:
                try:
                    date_str = obs['date']
                    value_str = obs['value']
                    
                    # Skip missing values (represented as '.')
                    if value_str == '.':
                        continue
                    
                    dates.append(pd.to_datetime(date_str))
                    values.append(float(value_str))
                    
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Skipping invalid observation for {series_id}: {obs}")
                    continue
            
            if not dates:
                return pd.Series(dtype=float)
            
            series = pd.Series(values, index=dates, name=series_id)
            series.index.name = 'Date'
            
            return series
            
        except requests.exceptions.RequestException as e:
            raise DataRetrievalError(
                f"Failed to fetch FRED series {series_id}: {str(e)}",
                variables=[series_id],
                response_status=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            )
    
    def validate_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Validate FRED API response format and content
        
        Args:
            response_data: Raw response data from FRED API
            
        Returns:
            True if response is valid
            
        Raises:
            ValidationError: If response format is invalid
        """
        if not isinstance(response_data, dict):
            raise ValidationError(
                "FRED API response must be a dictionary",
                field="response_data",
                expected="dict",
                actual=type(response_data).__name__
            )
        
        # Check for error indicators
        if 'error_message' in response_data:
            raise ValidationError(
                f"FRED API error: {response_data['error_message']}",
                field="api_response",
                actual=response_data['error_message']
            )
        
        # For series observations, validate structure
        if 'observations' in response_data:
            observations = response_data['observations']
            if not isinstance(observations, list):
                raise ValidationError(
                    "FRED observations must be a list",
                    field="observations",
                    expected="list",
                    actual=type(observations).__name__
                )
            
            # Validate observation structure
            if observations:
                first_obs = observations[0]
                required_fields = ['date', 'value']
                for field in required_fields:
                    if field not in first_obs:
                        raise ValidationError(
                            f"FRED observation missing required field: {field}",
                            field="observation_structure",
                            expected=required_fields,
                            actual=list(first_obs.keys())
                        )
        
        return True
    
    def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve metadata for FRED series
        
        Args:
            variables: Variable code(s) to get metadata for
            
        Returns:
            Dictionary mapping variable codes to metadata dictionaries
            
        Raises:
            DataRetrievalError: If metadata retrieval fails
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to FRED API. Call connect() first.")
        
        variable_list = validate_variable_codes(variables)
        metadata = {}
        
        for variable in variable_list:
            try:
                self._enforce_rate_limit()
                
                url = f"{self.base_url}/series"
                params = {
                    'api_key': self.api_key,
                    'series_id': variable,
                    'file_type': 'json'
                }
                
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                self.validate_response(data)
                
                if 'seriess' in data and data['seriess']:
                    series_info = data['seriess'][0]
                    metadata[variable] = {
                        'code': variable,
                        'name': series_info.get('title', ''),
                        'description': series_info.get('notes', ''),
                        'units': series_info.get('units', ''),
                        'frequency': series_info.get('frequency', ''),
                        'source': 'FRED',
                        'category': series_info.get('group', ''),
                        'start_date': series_info.get('observation_start', ''),
                        'end_date': series_info.get('observation_end', '')
                    }
                else:
                    self.logger.warning(f"No metadata found for variable {variable}")
                    
            except Exception as e:
                self.logger.error(f"Failed to retrieve metadata for {variable}: {str(e)}")
        
        return metadata
    
    def get_variable_metadata(self, variable: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific FRED variable (implements abstract method)
        
        Args:
            variable: Variable code to get metadata for
            
        Returns:
            Dictionary containing variable metadata
            
        Raises:
            DataRetrievalError: If metadata retrieval fails
        """
        metadata_dict = self.get_metadata([variable])
        if variable in metadata_dict:
            return metadata_dict[variable]
        else:
            raise DataRetrievalError(
                f"No metadata found for variable {variable}",
                variables=[variable]
            )
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    def __repr__(self) -> str:
        """String representation"""
        status = "connected" if self.is_connected else "disconnected"
        return f"FREDDataSource(api_key='{self.api_key[:4]}...{self.api_key[-4:]}', status='{status}')"