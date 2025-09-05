"""
Unit tests for the abstract DataSource base class

Tests the base class functionality, abstract method enforcement,
and common behaviors shared across all data source implementations.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, Any, Union, List, Optional

from src.federal_reserve_etl.data_sources.base import DataSource
from src.federal_reserve_etl.utils.exceptions import (
    AuthenticationError, ConnectionError, DataRetrievalError, ValidationError
)


class ConcreteDataSource(DataSource):
    """Concrete implementation of DataSource for testing"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.source_name = "Test Source"
        self.base_url = "https://api.test.com"
        self.rate_limit = 60
        self._connect_called = False
        self._disconnect_called = False
    
    def connect(self) -> bool:
        self._connect_called = True
        if self.api_key is None:
            raise AuthenticationError("API key required")
        if self.api_key == "invalid":
            raise AuthenticationError("Invalid API key")
        if self.api_key == "connection_error":
            raise ConnectionError("Failed to connect")
        
        self.is_connected = True
        return True
    
    def get_data(
        self,
        variables: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        **kwargs
    ) -> pd.DataFrame:
        if not self.is_connected:
            raise ConnectionError("Not connected")
        
        if isinstance(variables, str):
            variables = [variables]
        
        if "invalid" in variables:
            raise DataRetrievalError("Invalid variable")
        
        # Create mock data
        dates = pd.date_range("2023-01-01", periods=10, freq='D')
        data = {}
        for var in variables:
            data[var] = range(len(dates))
        
        return pd.DataFrame(data, index=dates)
    
    def validate_response(self, response: Any) -> bool:
        if response is None:
            raise ValidationError("Response cannot be None")
        return True
    
    def disconnect(self) -> None:
        self._disconnect_called = True
        self.is_connected = False
    
    def get_variable_metadata(self, variable: str) -> Dict[str, Any]:
        if variable == "invalid":
            raise DataRetrievalError("Variable not found")
        
        return {
            "name": f"Test Variable {variable}",
            "description": f"Description for {variable}",
            "units": "Units",
            "frequency": "daily",
            "start_date": "2020-01-01",
            "end_date": "2023-12-31"
        }


class TestDataSourceBase:
    """Test cases for DataSource base class functionality"""
    
    def test_abstract_class_cannot_be_instantiated(self):
        """Test that DataSource abstract class cannot be instantiated directly"""
        with pytest.raises(TypeError):
            DataSource()
    
    def test_concrete_implementation_initialization(self):
        """Test successful initialization of concrete implementation"""
        source = ConcreteDataSource(api_key="test_key")
        
        assert source.api_key == "test_key"
        assert source.source_name == "Test Source"
        assert source.base_url == "https://api.test.com"
        assert source.rate_limit == 60
        assert not source.is_connected
        assert source._session is None
        assert source._last_request_time is None
        assert source._request_count == 0
    
    def test_initialization_with_kwargs(self):
        """Test initialization with additional keyword arguments"""
        source = ConcreteDataSource(
            api_key="test_key",
            custom_param="custom_value"
        )
        
        assert source.api_key == "test_key"
        assert source.source_name == "Test Source"
    
    def test_initialization_without_api_key(self):
        """Test initialization without API key"""
        source = ConcreteDataSource()
        
        assert source.api_key is None
        assert source.source_name == "Test Source"


class TestConnectionManagement:
    """Test cases for connection management functionality"""
    
    def test_successful_connection(self):
        """Test successful connection establishment"""
        source = ConcreteDataSource(api_key="valid_key")
        
        result = source.connect()
        
        assert result is True
        assert source.is_connected is True
        assert source._connect_called is True
    
    def test_connection_without_api_key(self):
        """Test connection failure without API key"""
        source = ConcreteDataSource()
        
        with pytest.raises(AuthenticationError, match="API key required"):
            source.connect()
        
        assert source.is_connected is False
    
    def test_connection_with_invalid_api_key(self):
        """Test connection failure with invalid API key"""
        source = ConcreteDataSource(api_key="invalid")
        
        with pytest.raises(AuthenticationError, match="Invalid API key"):
            source.connect()
        
        assert source.is_connected is False
    
    def test_connection_error(self):
        """Test connection failure due to network issues"""
        source = ConcreteDataSource(api_key="connection_error")
        
        with pytest.raises(ConnectionError, match="Failed to connect"):
            source.connect()
        
        assert source.is_connected is False
    
    def test_disconnect(self):
        """Test proper disconnection"""
        source = ConcreteDataSource(api_key="valid_key")
        source.connect()
        
        assert source.is_connected is True
        
        source.disconnect()
        
        assert source.is_connected is False
        assert source._disconnect_called is True
    
    def test_test_connection_success(self):
        """Test successful connection test"""
        source = ConcreteDataSource(api_key="valid_key")
        
        result = source.test_connection()
        
        assert result is True
        assert source.is_connected is False  # Should disconnect after test
        assert source._connect_called is True
        assert source._disconnect_called is True
    
    def test_test_connection_failure(self):
        """Test failed connection test"""
        source = ConcreteDataSource(api_key="invalid")
        
        result = source.test_connection()
        
        assert result is False
        assert source.is_connected is False


class TestContextManager:
    """Test cases for context manager functionality"""
    
    def test_context_manager_success(self):
        """Test successful context manager usage"""
        source = ConcreteDataSource(api_key="valid_key")
        
        with source as s:
            assert s is source
            assert s.is_connected is True
            assert s._connect_called is True
        
        assert source.is_connected is False
        assert source._disconnect_called is True
    
    def test_context_manager_connection_failure(self):
        """Test context manager with connection failure"""
        source = ConcreteDataSource(api_key="invalid")
        
        with pytest.raises(AuthenticationError):
            with source:
                pass
        
        assert source.is_connected is False
    
    def test_context_manager_exception_handling(self):
        """Test context manager properly closes on exceptions"""
        source = ConcreteDataSource(api_key="valid_key")
        
        with pytest.raises(ValueError):
            with source:
                assert source.is_connected is True
                raise ValueError("Test exception")
        
        assert source.is_connected is False
        assert source._disconnect_called is True


class TestDataRetrieval:
    """Test cases for data retrieval functionality"""
    
    def setup_method(self):
        """Set up connected data source for each test"""
        self.source = ConcreteDataSource(api_key="valid_key")
        self.source.connect()
    
    def test_get_data_single_variable(self):
        """Test data retrieval for single variable"""
        df = self.source.get_data("TEST_VAR")
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "TEST_VAR" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)
    
    def test_get_data_multiple_variables(self):
        """Test data retrieval for multiple variables"""
        df = self.source.get_data(["VAR1", "VAR2", "VAR3"])
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "VAR1" in df.columns
        assert "VAR2" in df.columns
        assert "VAR3" in df.columns
    
    def test_get_data_not_connected(self):
        """Test data retrieval when not connected"""
        source = ConcreteDataSource(api_key="valid_key")
        
        with pytest.raises(ConnectionError, match="Not connected"):
            source.get_data("TEST_VAR")
    
    def test_get_data_invalid_variable(self):
        """Test data retrieval with invalid variable"""
        with pytest.raises(DataRetrievalError, match="Invalid variable"):
            self.source.get_data("invalid")
    
    def test_get_data_with_dates(self):
        """Test data retrieval with date parameters"""
        df = self.source.get_data(
            "TEST_VAR",
            start_date="2023-01-01",
            end_date="2023-01-31"
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10


class TestMetadataRetrieval:
    """Test cases for metadata retrieval functionality"""
    
    def setup_method(self):
        """Set up connected data source for each test"""
        self.source = ConcreteDataSource(api_key="valid_key")
        self.source.connect()
    
    def test_get_variable_metadata_success(self):
        """Test successful metadata retrieval"""
        metadata = self.source.get_variable_metadata("TEST_VAR")
        
        assert isinstance(metadata, dict)
        assert metadata["name"] == "Test Variable TEST_VAR"
        assert metadata["description"] == "Description for TEST_VAR"
        assert metadata["units"] == "Units"
        assert metadata["frequency"] == "daily"
        assert "start_date" in metadata
        assert "end_date" in metadata
    
    def test_get_variable_metadata_invalid(self):
        """Test metadata retrieval for invalid variable"""
        with pytest.raises(DataRetrievalError, match="Variable not found"):
            self.source.get_variable_metadata("invalid")
    
    def test_get_available_variables_default(self):
        """Test default implementation of get_available_variables"""
        variables = self.source.get_available_variables()
        
        assert isinstance(variables, list)
        assert len(variables) == 0  # Default implementation returns empty list


class TestRateLimiting:
    """Test cases for rate limiting functionality"""
    
    def test_get_rate_limit_status(self):
        """Test rate limit status reporting"""
        source = ConcreteDataSource(api_key="valid_key")
        
        status = source.get_rate_limit_status()
        
        assert isinstance(status, dict)
        assert status["limit"] == 60
        assert status["used"] == 0
        assert status["remaining"] == 60
        assert "reset_time" in status
    
    @patch('time.sleep')
    def test_enforce_rate_limit_under_limit(self, mock_sleep):
        """Test rate limiting when under the limit"""
        source = ConcreteDataSource(api_key="valid_key")
        source._request_count = 30
        source._last_request_time = datetime.now() - timedelta(seconds=10)  # Recent request
        
        source._enforce_rate_limit()
        
        assert source._request_count == 31
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    @patch('src.federal_reserve_etl.data_sources.base.datetime')
    def test_enforce_rate_limit_at_limit(self, mock_datetime, mock_sleep):
        """Test rate limiting when at the limit"""
        source = ConcreteDataSource(api_key="valid_key")
        source._request_count = 60
        
        # Mock datetime to control timing
        now = datetime(2023, 1, 1, 12, 0, 30)  # Current time
        last_request = datetime(2023, 1, 1, 12, 0, 0)  # 30 seconds ago
        
        mock_datetime.now.side_effect = [now, now, datetime(2023, 1, 1, 12, 1, 0)]  # Multiple calls
        source._last_request_time = last_request
        
        source._enforce_rate_limit()
        
        mock_sleep.assert_called_once_with(30)  # Should wait 30 seconds
    
    def test_enforce_rate_limit_reset_counter(self):
        """Test rate limit counter reset after time window"""
        source = ConcreteDataSource(api_key="valid_key")
        source._request_count = 60
        source._last_request_time = datetime.now() - timedelta(minutes=2)  # 2 minutes ago
        
        source._enforce_rate_limit()
        
        assert source._request_count == 1  # Should reset and increment


class TestValidation:
    """Test cases for validation functionality"""
    
    def test_validate_response_success(self):
        """Test successful response validation"""
        source = ConcreteDataSource(api_key="valid_key")
        
        result = source.validate_response({"data": "test"})
        
        assert result is True
    
    def test_validate_response_failure(self):
        """Test failed response validation"""
        source = ConcreteDataSource(api_key="valid_key")
        
        with pytest.raises(ValidationError, match="Response cannot be None"):
            source.validate_response(None)


class TestStringRepresentations:
    """Test cases for string representation methods"""
    
    def test_str_representation_connected(self):
        """Test string representation when connected"""
        source = ConcreteDataSource(api_key="valid_key")
        source.connect()
        
        str_repr = str(source)
        
        assert "Test Source (Connected)" in str_repr
    
    def test_str_representation_disconnected(self):
        """Test string representation when disconnected"""
        source = ConcreteDataSource(api_key="valid_key")
        
        str_repr = str(source)
        
        assert "Test Source (Disconnected)" in str_repr
    
    def test_repr_representation(self):
        """Test detailed representation"""
        source = ConcreteDataSource(api_key="valid_key")
        
        repr_str = repr(source)
        
        assert "ConcreteDataSource" in repr_str
        assert "source_name='Test Source'" in repr_str
        assert "is_connected=False" in repr_str
        assert "rate_limit=60" in repr_str


class TestLoggingIntegration:
    """Test cases for logging integration"""
    
    @patch('src.federal_reserve_etl.utils.logging.get_logger')
    def test_logger_initialization(self, mock_get_logger):
        """Test logger is properly initialized"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        source = ConcreteDataSource(api_key="valid_key")
        
        mock_get_logger.assert_called_once_with("data_sources.concretedatasource")
        assert source.logger == mock_logger
    
    @patch('src.federal_reserve_etl.utils.logging.get_logger')
    def test_test_connection_logging_on_failure(self, mock_get_logger):
        """Test logging during failed connection test"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        source = ConcreteDataSource(api_key="invalid")
        result = source.test_connection()
        
        assert result is False
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Connection test failed" in error_call
    
    @patch('src.federal_reserve_etl.utils.logging.get_logger')
    def test_get_available_variables_warning(self, mock_get_logger):
        """Test warning logged for default get_available_variables implementation"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        source = ConcreteDataSource(api_key="valid_key")
        result = source.get_available_variables()
        
        assert result == []
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "does not implement get_available_variables()" in warning_call