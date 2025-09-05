"""
Haver Analytics API Client Implementation

Haver Analytics API client for retrieving economic time series data with
authentication, rate limiting, and standardized error handling.
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


class HaverDataSource(DataSource):
    """
    Haver Analytics API client implementation
    
    Provides access to Haver Analytics economic time series data with proper
    authentication, rate limiting, and standardized error handling. Inherits
    from DataSource abstract base class and implements all required methods.
    
    Attributes:
        username: Haver Analytics username for authentication
        password: Haver Analytics password for authentication
        base_url: Base URL for Haver API endpoints
        session: HTTP session for connection pooling
        rate_limiter: Rate limiting state tracking
        is_connected: Connection status flag
        last_request_time: Timestamp of last API request
        requests_per_second: Rate limiting threshold
    
    Examples:
        >>> haver = HaverDataSource(username='user', password='pass')
        >>> haver.connect()
        >>> data = haver.get_data(['GDP', 'CPI'], '2020-01-01', '2020-12-31')
        >>> haver.disconnect()
    """
    
    def __init__(
        self, 
        username: str, 
        password: str, 
        config: Optional[DataSourceConfig] = None
    ):
        """
        Initialize Haver Analytics API client
        
        Args:
            username: Haver Analytics username for authentication
            password: Haver Analytics password for authentication
            config: Optional configuration override dictionary
            
        Raises:
            ValidationError: If credentials are invalid format
            ConfigurationError: If configuration parameters are invalid
        """
        super().__init__()
        
        self.logger = get_logger(__name__)
        self.username = self._validate_username(username)
        self.password = self._validate_password(password)
        
        # Default configuration
        default_config = {
            'base_url': 'https://api.haver.com/v1',
            'rate_limit': 10,   # requests per second (conservative estimate)
            'timeout': 45,      # seconds (longer for potentially large datasets)
            'retry_config': {
                'retry_count': 3,
                'retry_delay': 2.0,
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
        
        # Rate limiting state (per-second basis for Haver)
        self.last_request_time = datetime.min
        self.min_request_interval = 1.0 / self.rate_limit
        
        self.logger.info(f"Initialized HaverDataSource with rate limit {self.rate_limit}/sec")
    
    def _validate_username(self, username: str) -> str:
        """
        Validate Haver Analytics username
        
        Args:
            username: Username to validate
            
        Returns:
            Validated username
            
        Raises:
            ValidationError: If username format is invalid
        """
        if not username or not isinstance(username, str):
            raise ValidationError(
                "Haver username must be a non-empty string",
                field="username",
                expected="non-empty string",
                actual=type(username).__name__
            )
        
        if len(username.strip()) < 3:
            raise ValidationError(
                "Haver username must be at least 3 characters long",
                field="username",
                expected="minimum 3 characters",
                actual=f"length {len(username.strip())}"
            )
        
        return username.strip()
    
    def _validate_password(self, password: str) -> str:
        """
        Validate Haver Analytics password
        
        Args:
            password: Password to validate
            
        Returns:
            Validated password
            
        Raises:
            ValidationError: If password format is invalid
        """
        if not password or not isinstance(password, str):
            raise ValidationError(
                "Haver password must be a non-empty string",
                field="password",
                expected="non-empty string",
                actual=type(password).__name__
            )
        
        if len(password) < 6:
            raise ValidationError(
                "Haver password must be at least 6 characters long",
                field="password",
                expected="minimum 6 characters",
                actual=f"length {len(password)}"
            )
        
        return password
    
    @handle_api_errors(retry_count=3, retry_delay=2.0, backoff_factor=2.0)
    def connect(self) -> bool:
        """
        Establish connection to Haver Analytics API
        
        Creates HTTP session, validates credentials by making test request,
        and initializes rate limiting state.
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If unable to connect to API
            AuthenticationError: If credentials are invalid
        """
        try:
            self.logger.info("Connecting to Haver Analytics API...")
            
            # Create HTTP session with authentication
            self.session = requests.Session()
            self.session.auth = (self.username, self.password)
            self.session.headers.update({
                'User-Agent': 'federal-reserve-etl/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            
            # Test connection with credentials validation
            # Use a simple metadata endpoint for testing
            test_url = f"{self.base_url}/databases"
            
            response = self.session.get(test_url, timeout=self.timeout)
            
            if response.status_code == 401:
                raise AuthenticationError(
                    "Invalid Haver Analytics credentials",
                    api_key_hint=f"{self.username}:***",
                    source="Haver"
                )
            elif response.status_code == 403:
                raise AuthenticationError(
                    "Haver Analytics access denied - check subscription status",
                    api_key_hint=f"{self.username}:***",
                    source="Haver"
                )
            
            response.raise_for_status()
            
            # Initialize rate limiting
            self.last_request_time = datetime.now()
            
            self.is_connected = True
            self.logger.info("Successfully connected to Haver Analytics API")
            return True
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to Haver Analytics API: {str(e)}",
                endpoint=self.base_url
            )
        except requests.exceptions.Timeout as e:
            raise ConnectionError(
                f"Connection timeout to Haver Analytics API: {str(e)}",
                endpoint=self.base_url
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 403):
                raise AuthenticationError(
                    f"Haver Analytics authentication failed: {str(e)}",
                    api_key_hint=f"{self.username}:***",
                    source="Haver"
                )
            else:
                raise ConnectionError(
                    f"HTTP error connecting to Haver Analytics API: {str(e)}",
                    endpoint=self.base_url,
                    status_code=e.response.status_code
                )
    
    def disconnect(self) -> None:
        """
        Close connection to Haver Analytics API
        
        Closes HTTP session and resets connection state.
        Safe to call multiple times.
        """
        if self.session:
            self.session.close()
            self.session = None
        
        self.is_connected = False
        self.logger.info("Disconnected from Haver Analytics API")
    
    def _enforce_rate_limit(self) -> None:
        """
        Enforce Haver Analytics API rate limits
        
        Ensures minimum interval between requests to avoid overwhelming
        the API server.
        
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        now = datetime.now()
        time_since_last = (now - self.last_request_time).total_seconds()
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = datetime.now()
    
    def get_data(
        self,
        variables: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        **kwargs
    ) -> TimeSeriesData:
        """
        Retrieve time series data from Haver Analytics API
        
        Fetches economic time series data for specified variables within
        the given date range. Handles rate limiting, authentication, and
        data format standardization to match FRED output format.
        
        Args:
            variables: Variable code(s) to retrieve (e.g., 'GDP', ['GDP', 'CPI'])
            start_date: Start date in YYYY-MM-DD format or datetime object
            end_date: End date in YYYY-MM-DD format or datetime object
            **kwargs: Additional parameters:
                - database: Haver database name (default: 'USECON')
                - frequency: Data frequency override
                - transformation: Data transformation method
        
        Returns:
            DataFrame with DatetimeIndex and variable columns (standardized format)
            
        Raises:
            ValidationError: If variables or dates are invalid
            DataRetrievalError: If data retrieval fails
            RateLimitError: If rate limit is exceeded
            ConnectionError: If not connected to API
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Haver Analytics API. Call connect() first.")
        
        # Validate and normalize inputs
        variable_list = validate_variable_codes(variables)
        start_dt, end_dt = validate_and_convert_dates(start_date, end_date)
        
        # Convert datetime objects to YYYY-MM-DD format for Haver API
        start_str = start_dt.strftime('%Y-%m-%d')
        end_str = end_dt.strftime('%Y-%m-%d')
        
        # Default database
        database = kwargs.get('database', 'USECON')
        
        self.logger.info(f"Retrieving Haver data for {len(variable_list)} variables from {start_str} to {end_str}")
        
        # Collect data for all variables
        all_data = {}
        failed_variables = []
        
        for variable in variable_list:
            try:
                self._enforce_rate_limit()
                
                # Get series data
                series_data = self._fetch_series_data(
                    variable, database, start_str, end_str, **kwargs
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
        
        # Combine all series into single DataFrame (standardized format)
        combined_df = pd.DataFrame()
        for variable, series in all_data.items():
            combined_df[variable] = series
        
        # Ensure consistent datetime index
        combined_df.index.name = 'Date'
        
        # Log summary
        if failed_variables:
            self.logger.warning(f"Failed to retrieve {len(failed_variables)} variables: {failed_variables}")
        
        self.logger.info(f"Successfully retrieved data: {combined_df.shape[0]} observations, {combined_df.shape[1]} variables")
        
        return combined_df
    
    def _fetch_series_data(
        self,
        series_code: str,
        database: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> pd.Series:
        """
        Fetch data for a single Haver series
        
        Args:
            series_code: Haver series identifier
            database: Haver database name
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional Haver API parameters
            
        Returns:
            Pandas Series with DatetimeIndex
            
        Raises:
            DataRetrievalError: If API request fails
        """
        url = f"{self.base_url}/data/{database}/{series_code}"
        
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'format': 'json'
        }
        
        # Add optional parameters
        if 'frequency' in kwargs:
            params['frequency'] = kwargs['frequency']
        if 'transformation' in kwargs:
            params['transformation'] = kwargs['transformation']
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Validate response format
            if not isinstance(data, dict) or 'data' not in data:
                raise DataRetrievalError(
                    f"Invalid Haver API response format for series {series_code}",
                    variables=[series_code],
                    response_status=response.status_code
                )
            
            series_data = data['data']
            if not series_data:
                return pd.Series(dtype=float)
            
            # Convert to pandas Series (standardized format)
            dates = []
            values = []
            
            for entry in series_data:
                try:
                    # Haver API returns different date formats, handle common ones
                    date_str = entry.get('date') or entry.get('period')
                    value = entry.get('value')
                    
                    if date_str is None or value is None:
                        continue
                    
                    # Handle different date formats
                    try:
                        date_obj = pd.to_datetime(date_str)
                    except:
                        # Try alternative parsing for quarterly/monthly data
                        date_obj = pd.to_datetime(date_str, format='%Y-%m')
                    
                    dates.append(date_obj)
                    values.append(float(value))
                    
                except (KeyError, ValueError, TypeError) as e:
                    self.logger.warning(f"Skipping invalid entry for {series_code}: {entry}")
                    continue
            
            if not dates:
                return pd.Series(dtype=float)
            
            series = pd.Series(values, index=dates, name=series_code)
            series.index.name = 'Date'
            
            return series
            
        except requests.exceptions.RequestException as e:
            raise DataRetrievalError(
                f"Failed to fetch Haver series {series_code}: {str(e)}",
                variables=[series_code],
                response_status=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            )
    
    def validate_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Validate Haver Analytics API response format and content
        
        Args:
            response_data: Raw response data from Haver API
            
        Returns:
            True if response is valid
            
        Raises:
            ValidationError: If response format is invalid
        """
        if not isinstance(response_data, dict):
            raise ValidationError(
                "Haver API response must be a dictionary",
                field="response_data",
                expected="dict",
                actual=type(response_data).__name__
            )
        
        # Check for error indicators
        if 'error' in response_data:
            error_msg = response_data.get('error', 'Unknown error')
            raise ValidationError(
                f"Haver API error: {error_msg}",
                field="api_response",
                actual=error_msg
            )
        
        # For data responses, validate structure
        if 'data' in response_data:
            data = response_data['data']
            if not isinstance(data, list):
                raise ValidationError(
                    "Haver data must be a list",
                    field="data",
                    expected="list",
                    actual=type(data).__name__
                )
            
            # Validate data entry structure
            if data:
                first_entry = data[0]
                if not isinstance(first_entry, dict):
                    raise ValidationError(
                        "Haver data entries must be dictionaries",
                        field="data_entry",
                        expected="dict",
                        actual=type(first_entry).__name__
                    )
                
                # Check for required fields (flexible for different response formats)
                has_date = any(key in first_entry for key in ['date', 'period', 'time'])
                has_value = 'value' in first_entry
                
                if not (has_date and has_value):
                    raise ValidationError(
                        "Haver data entry missing date/value fields",
                        field="data_structure",
                        expected="date and value fields",
                        actual=list(first_entry.keys())
                    )
        
        return True
    
    def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve metadata for Haver series
        
        Args:
            variables: Variable code(s) to get metadata for
            
        Returns:
            Dictionary mapping variable codes to metadata dictionaries
            
        Raises:
            DataRetrievalError: If metadata retrieval fails
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Haver Analytics API. Call connect() first.")
        
        variable_list = validate_variable_codes(variables)
        metadata = {}
        
        for variable in variable_list:
            try:
                self._enforce_rate_limit()
                
                url = f"{self.base_url}/metadata/{variable}"
                
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                self.validate_response(data)
                
                if 'metadata' in data:
                    meta_info = data['metadata']
                    metadata[variable] = {
                        'code': variable,
                        'name': meta_info.get('name', ''),
                        'description': meta_info.get('description', ''),
                        'units': meta_info.get('units', ''),
                        'frequency': meta_info.get('frequency', ''),
                        'source': 'Haver',
                        'category': meta_info.get('category', ''),
                        'start_date': meta_info.get('start_date', ''),
                        'end_date': meta_info.get('end_date', '')
                    }
                else:
                    self.logger.warning(f"No metadata found for variable {variable}")
                    
            except Exception as e:
                self.logger.error(f"Failed to retrieve metadata for {variable}: {str(e)}")
        
        return metadata
    
    def get_variable_metadata(self, variable: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific Haver variable (implements abstract method)
        
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
        return f"HaverDataSource(username='{self.username}', status='{status}')"