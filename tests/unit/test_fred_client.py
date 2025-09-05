"""
Unit tests for FRED API client implementation

Tests the FREDDataSource class with real API calls to verify
authentication, data retrieval, rate limiting, and error handling.
Requires FRED_API_KEY environment variable to be set.
"""

import pytest
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import patch

from src.federal_reserve_etl.data_sources.fred_client import FREDDataSource
from src.federal_reserve_etl.utils.exceptions import (
    ValidationError,
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    RateLimitError
)

# Test configuration
FRED_API_KEY = os.getenv('FRED_API_KEY')
SKIP_REAL_API_TESTS = FRED_API_KEY is None

def skip_if_no_api_key():
    return pytest.mark.skipif(SKIP_REAL_API_TESTS, reason="FRED_API_KEY environment variable not set")


class TestFREDDataSourceInitialization:
    """Test cases for FRED data source initialization"""
    
    def test_valid_api_key_initialization(self):
        """Test initialization with valid API key format"""
        api_key = "12345678901234567890123456789012"  # 32 chars
        
        fred = FREDDataSource(api_key=api_key)
        
        assert fred.api_key == api_key
        assert fred.base_url == "https://api.stlouisfed.org/fred"
        assert fred.rate_limit == 120
        assert fred.timeout == 30
        assert not fred.is_connected
    
    def test_initialization_with_config(self):
        """Test initialization with custom configuration"""
        api_key = "12345678901234567890123456789012"
        config = {
            'base_url': 'https://custom.api.com/fred',
            'rate_limit': 60,
            'timeout': 15
        }
        
        fred = FREDDataSource(api_key=api_key, config=config)
        
        assert fred.base_url == "https://custom.api.com/fred"
        assert fred.rate_limit == 60
        assert fred.timeout == 15
    
    def test_invalid_api_key_none(self):
        """Test initialization with None API key"""
        with pytest.raises(ValidationError, match="FRED API key must be a non-empty string"):
            FREDDataSource(api_key=None)
    
    def test_invalid_api_key_empty_string(self):
        """Test initialization with empty string API key"""
        with pytest.raises(ValidationError, match="FRED API key must be a non-empty string"):
            FREDDataSource(api_key="")
    
    def test_invalid_api_key_wrong_length(self):
        """Test initialization with wrong length API key"""
        with pytest.raises(ValidationError, match="FRED API key must be 32 character alphanumeric"):
            FREDDataSource(api_key="short")
    
    def test_invalid_api_key_non_alphanumeric(self):
        """Test initialization with non-alphanumeric API key"""
        with pytest.raises(ValidationError, match="FRED API key must be 32 character alphanumeric"):
            FREDDataSource(api_key="123456789012345678901234567890!@")
    
    def test_api_key_with_hyphens_allowed(self):
        """Test that API keys with hyphens are allowed"""
        api_key = "1234567890-234567890123456789012"  # 32 chars with hyphen
        
        fred = FREDDataSource(api_key=api_key)
        
        assert fred.api_key == api_key


class TestFREDConnection:
    """Test cases for FRED API connection management with real API"""
    
    @skip_if_no_api_key()
    def test_successful_connection_real_api(self):
        """Test successful connection to real FRED API"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        result = fred.connect()
        
        assert result is True
        assert fred.is_connected is True
        assert fred.session is not None
        
        # Clean up
        fred.disconnect()
    
    def test_connection_with_invalid_api_key(self):
        """Test connection failure with invalid API key"""
        invalid_key = "12345678901234567890123456789012"  # Valid format but invalid key
        fred = FREDDataSource(api_key=invalid_key)
        
        with pytest.raises(AuthenticationError, match="Invalid FRED API key"):
            fred.connect()
        
        assert fred.is_connected is False
    
    @skip_if_no_api_key()
    def test_disconnect_after_connection(self):
        """Test disconnection from FRED API after successful connection"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        fred.connect()
        
        assert fred.is_connected is True
        
        fred.disconnect()
        
        assert fred.is_connected is False
        assert fred.session is None
    
    def test_disconnect_when_not_connected(self):
        """Test disconnect when already disconnected"""
        fred = FREDDataSource(api_key="12345678901234567890123456789012")
        
        # Should not raise any exceptions
        fred.disconnect()
        
        assert fred.is_connected is False
        assert fred.session is None
    
    @skip_if_no_api_key()
    def test_context_manager_real_api(self):
        """Test context manager functionality with real API"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred as f:
            assert f is fred
            assert f.is_connected is True
            assert f.session is not None
        
        assert fred.is_connected is False
        assert fred.session is None


class TestFREDRateLimiting:
    """Test cases for FRED API rate limiting"""
    
    def setup_method(self):
        """Set up for each test"""
        self.api_key = "12345678901234567890123456789012"
        with patch('src.federal_reserve_etl.utils.logging.get_logger'):
            self.fred = FREDDataSource(api_key=self.api_key)
        
        # Set up connected state
        self.fred.is_connected = True
        self.fred.minute_window_start = datetime.now()
        self.fred.requests_this_minute = 0
        self.fred.last_request_time = datetime.now() - timedelta(seconds=1)
    
    def test_rate_limit_under_limit(self):
        """Test rate limiting when under the limit"""
        self.fred.requests_this_minute = 50  # Under limit of 120
        
        # Should not raise any exceptions
        self.fred._enforce_rate_limit()
        
        assert self.fred.requests_this_minute == 51
    
    def test_rate_limit_at_limit(self):
        """Test rate limiting when at the limit"""
        self.fred.requests_this_minute = 120  # At limit
        
        with pytest.raises(RateLimitError, match="FRED API rate limit exceeded"):
            self.fred._enforce_rate_limit()
    
    def test_rate_limit_reset_after_minute(self):
        """Test rate limit reset after minute window"""
        # Set up rate limit state from previous minute
        self.fred.requests_this_minute = 120
        self.fred.minute_window_start = datetime.now() - timedelta(seconds=65)
        
        # Should reset and allow request
        self.fred._enforce_rate_limit()
        
        assert self.fred.requests_this_minute == 1
    
    @patch('time.sleep')
    def test_minimum_time_between_requests(self, mock_sleep):
        """Test minimum time enforcement between requests"""
        self.fred.last_request_time = datetime.now() - timedelta(seconds=0.1)  # 0.1 seconds ago
        
        self.fred._enforce_rate_limit()
        
        # Should sleep for remaining time (0.4 seconds)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.3 <= sleep_time <= 0.5  # Allow for some timing variance
    
    @patch('time.sleep')
    def test_no_sleep_when_enough_time_passed(self, mock_sleep):
        """Test no sleep when enough time has passed"""
        self.fred.last_request_time = datetime.now() - timedelta(seconds=1.0)
        
        self.fred._enforce_rate_limit()
        
        # Should not sleep
        mock_sleep.assert_not_called()


class TestFREDDataRetrieval:
    """Test cases for FRED data retrieval with real API"""
    
    def test_get_data_not_connected(self):
        """Test data retrieval when not connected"""
        fred = FREDDataSource(api_key="12345678901234567890123456789012")
        
        with pytest.raises(ConnectionError, match="Not connected to FRED API"):
            fred.get_data("FEDFUNDS")
    
    @skip_if_no_api_key()
    def test_get_data_single_variable_success(self):
        """Test successful data retrieval for single variable with real API"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            result = fred.get_data("FEDFUNDS", "2023-01-01", "2023-01-31")
        
        assert isinstance(result, pd.DataFrame)
        assert "FEDFUNDS" in result.columns
        assert len(result) > 0
        assert isinstance(result.index, pd.DatetimeIndex)
        
        # Verify data types and values are reasonable
        assert result["FEDFUNDS"].dtype in ['float64', 'object']  # Some may be missing
        # Federal funds rate should be between 0 and 20% typically
        numeric_values = pd.to_numeric(result["FEDFUNDS"], errors='coerce').dropna()
        if len(numeric_values) > 0:
            assert (numeric_values >= 0).all()
            assert (numeric_values <= 20).all()
    
    @skip_if_no_api_key()
    def test_get_data_multiple_variables_success(self):
        """Test successful data retrieval for multiple variables with real API"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            result = fred.get_data(["FEDFUNDS", "DGS10"], "2023-01-01", "2023-01-31")
        
        assert isinstance(result, pd.DataFrame)
        assert "FEDFUNDS" in result.columns
        assert "DGS10" in result.columns
        assert len(result) > 0
        assert isinstance(result.index, pd.DatetimeIndex)
        
        # Both series should have data
        assert result["FEDFUNDS"].notna().sum() > 0
        assert result["DGS10"].notna().sum() > 0
    
    @skip_if_no_api_key()
    def test_get_data_with_date_range(self):
        """Test data retrieval with specific date range"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            result = fred.get_data("FEDFUNDS", "2023-06-01", "2023-06-30")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        
        # Verify date range is respected
        assert result.index.min() >= pd.Timestamp("2023-06-01")
        assert result.index.max() <= pd.Timestamp("2023-06-30")
    
    @skip_if_no_api_key()
    def test_get_data_invalid_variable(self):
        """Test data retrieval with invalid variable"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            # Should handle invalid variables gracefully
            # FRED API typically returns empty data for invalid series
            result = fred.get_data("INVALID_SERIES_CODE")
            
            # Result could be empty DataFrame or raise DataRetrievalError
            if isinstance(result, pd.DataFrame):
                # If it returns empty DataFrame, that's acceptable
                assert len(result) == 0 or "INVALID_SERIES_CODE" not in result.columns
    
    @skip_if_no_api_key()
    def test_get_data_mixed_valid_invalid(self):
        """Test data retrieval with mix of valid and invalid variables"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            # Mix valid and invalid variables
            result = fred.get_data(["FEDFUNDS", "INVALID_VAR", "DGS10"], "2023-01-01", "2023-01-31")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        
        # Should have valid variables
        assert "FEDFUNDS" in result.columns
        assert "DGS10" in result.columns
        
        # Invalid variable should not be present or be empty
        if "INVALID_VAR" in result.columns:
            assert result["INVALID_VAR"].isna().all()
    
    @skip_if_no_api_key()
    def test_get_data_historical_range(self):
        """Test data retrieval for historical date range"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            # Get historical data
            result = fred.get_data("FEDFUNDS", "2020-01-01", "2020-12-31")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "FEDFUNDS" in result.columns
        
        # Should have a full year of data (roughly 250+ business days)
        assert len(result) > 200  # Account for weekends and holidays




class TestFREDMetadataRetrieval:
    """Test cases for FRED metadata retrieval with real API"""
    
    @skip_if_no_api_key()
    def test_get_variable_metadata_success(self):
        """Test successful metadata retrieval with real API"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            result = fred.get_variable_metadata("FEDFUNDS")
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'description' in result or 'title' in result
        assert 'units' in result
        assert 'frequency' in result
        assert 'start_date' in result
        assert 'end_date' in result
        
        # Verify reasonable values
        assert "Federal" in result['name']
        assert result['units'] in ['Percent', 'Rate']
        assert result['frequency'].lower() in ['daily', 'weekly', 'monthly', 'quarterly', 'annual']
    
    @skip_if_no_api_key()
    def test_get_variable_metadata_treasury_rate(self):
        """Test metadata retrieval for 10-year Treasury"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            result = fred.get_variable_metadata("DGS10")
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'Treasury' in result['name'] or '10' in result['name']
        assert result['units'] in ['Percent', 'Rate']
    
    @skip_if_no_api_key()
    def test_get_variable_metadata_invalid_series(self):
        """Test metadata retrieval for non-existent variable"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            with pytest.raises(DataRetrievalError):
                fred.get_variable_metadata("COMPLETELY_INVALID_SERIES_CODE_12345")


class TestFREDValidation:
    """Test cases for FRED input validation and error handling"""
    
    @skip_if_no_api_key()
    def test_invalid_date_range(self):
        """Test handling of invalid date ranges"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            # End date before start date should raise ValidationError
            with pytest.raises((ValidationError, ValueError)):
                fred.get_data("FEDFUNDS", "2023-12-31", "2023-01-01")
    
    @skip_if_no_api_key()  
    def test_future_date_range(self):
        """Test handling of future dates"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            # Future dates should either return empty data or handle gracefully
            future_date = "2030-01-01"
            result = fred.get_data("FEDFUNDS", future_date, "2030-01-31")
            
            # Should not crash - might return empty data
            assert isinstance(result, pd.DataFrame)


class TestFREDStringRepresentations:
    """Test cases for FRED string representation methods"""
    
    def test_str_representation_disconnected(self):
        """Test string representation when disconnected"""
        fred = FREDDataSource(api_key="12345678901234567890123456789012")
        str_repr = str(fred)
        assert "FRED" in str_repr or "FREDDataSource" in str_repr
    
    @skip_if_no_api_key()
    def test_str_representation_connected(self):
        """Test string representation when connected"""
        fred = FREDDataSource(api_key=FRED_API_KEY)
        
        with fred:
            str_repr = str(fred)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
    
    def test_repr_representation(self):
        """Test detailed representation"""
        fred = FREDDataSource(api_key="12345678901234567890123456789012")
        repr_str = repr(fred)
        assert "FREDDataSource" in repr_str or "FRED" in repr_str