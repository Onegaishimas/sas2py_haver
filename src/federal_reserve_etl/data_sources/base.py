"""
Abstract Base Class for Federal Reserve Data Sources

Defines the interface contract that all data source implementations
must follow, enabling the factory pattern and consistent API access
across FRED and Haver Analytics sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import pandas as pd


class DataSource(ABC):
    """
    Abstract base class for all Federal Reserve data source implementations
    
    This class defines the interface contract that concrete implementations
    (FREDDataSource, HaverDataSource) must follow to ensure consistency
    and enable polymorphic usage through the factory pattern.
    
    Attributes:
        source_name: Human-readable name of the data source
        api_key: API authentication key (if required)
        base_url: Base URL for API endpoints
        rate_limit: Maximum requests per minute
        is_connected: Connection status flag
    """
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize data source with common attributes
        
        Args:
            api_key: API authentication key (optional for some sources)
            **kwargs: Additional source-specific configuration
        """
        self.api_key = api_key
        self.source_name = "Unknown Source"
        self.base_url = ""
        self.rate_limit = 60  # Default: 60 requests per minute
        self.is_connected = False
        self._session = None
        self._last_request_time = None
        self._request_count = 0
        
        # Initialize logging
        from ..utils.logging import get_logger
        self.logger = get_logger(f"data_sources.{self.__class__.__name__.lower()}")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data source API
        
        Performs authentication, validates credentials, and sets up
        any necessary session state for subsequent API calls.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            AuthenticationError: If API credentials are invalid
            ConnectionError: If unable to reach API endpoints
        """
        pass
    
    @abstractmethod
    def get_data(
        self,
        variables: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Retrieve time series data for specified variables
        
        Args:
            variables: Single variable code or list of variable codes
            start_date: Start date for data retrieval (YYYY-MM-DD or datetime)
            end_date: End date for data retrieval (YYYY-MM-DD or datetime)
            **kwargs: Additional source-specific parameters
            
        Returns:
            DataFrame with time series data in wide format
            - Index: DatetimeIndex with observation dates
            - Columns: Variable codes with numeric values
            
        Raises:
            DataRetrievalError: If data retrieval fails
            ValidationError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    def validate_response(self, response: Any) -> bool:
        """
        Validate API response format and content
        
        Args:
            response: Raw API response object
            
        Returns:
            True if response is valid, False otherwise
            
        Raises:
            ValidationError: If response format is invalid
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection and clean up resources
        
        Properly closes any open sessions, clears authentication state,
        and performs cleanup to prevent resource leaks.
        """
        pass
    
    @abstractmethod
    def get_variable_metadata(self, variable: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific variable
        
        Args:
            variable: Variable code to get metadata for
            
        Returns:
            Dictionary containing variable metadata:
            - name: Human-readable variable name
            - description: Detailed description
            - units: Units of measurement
            - frequency: Data frequency (daily, weekly, monthly, etc.)
            - start_date: First available date
            - end_date: Last available date
            
        Raises:
            DataRetrievalError: If metadata retrieval fails
        """
        pass
    
    def get_available_variables(self) -> List[Dict[str, Any]]:
        """
        Get list of all available variables from this source
        
        Default implementation returns empty list. Concrete classes
        should override this method to provide actual variable lists.
        
        Returns:
            List of dictionaries with variable information
        """
        self.logger.warning(f"{self.source_name} does not implement get_available_variables()")
        return []
    
    def test_connection(self) -> bool:
        """
        Test connection to data source without full authentication
        
        Performs a lightweight connectivity check to verify that
        the data source API is reachable.
        
        Returns:
            True if connection test passes, False otherwise
        """
        try:
            # Default implementation tries to connect and disconnect
            connected = self.connect()
            if connected:
                self.disconnect()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limiting status
        
        Returns:
            Dictionary with rate limiting information:
            - limit: Maximum requests per minute
            - used: Requests used in current minute
            - remaining: Requests remaining in current minute
            - reset_time: When the rate limit resets
        """
        return {
            "limit": self.rate_limit,
            "used": self._request_count,
            "remaining": max(0, self.rate_limit - self._request_count),
            "reset_time": None  # Concrete classes should implement this
        }
    
    def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limiting by pausing execution if necessary
        
        This method should be called before making API requests
        to ensure compliance with rate limits.
        """
        import time
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Reset counter if more than a minute has passed
        if (self._last_request_time is None or 
            (now - self._last_request_time) > timedelta(minutes=1)):
            self._request_count = 0
            self._last_request_time = now
        
        # If we're at the rate limit, wait until next minute
        if self._request_count >= self.rate_limit:
            wait_time = 60 - (now - self._last_request_time).seconds
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                self._request_count = 0
                self._last_request_time = datetime.now()
        
        self._request_count += 1
    
    def __str__(self) -> str:
        """String representation of data source"""
        status = "Connected" if self.is_connected else "Disconnected"
        return f"{self.source_name} ({status})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"{self.__class__.__name__}("
                f"source_name='{self.source_name}', "
                f"is_connected={self.is_connected}, "
                f"rate_limit={self.rate_limit})")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False