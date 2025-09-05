"""
Unit tests for Haver Analytics API client implementation

Tests the HaverDataSource class with real API calls to verify
authentication, data retrieval, rate limiting, and error handling.
Requires HAVER_USERNAME and HAVER_PASSWORD environment variables to be set.
"""

import pytest
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.federal_reserve_etl.data_sources.haver_client import HaverDataSource
from src.federal_reserve_etl.utils.exceptions import (
    ValidationError,
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    RateLimitError
)

# Test configuration
HAVER_USERNAME = os.getenv('HAVER_USERNAME')
HAVER_PASSWORD = os.getenv('HAVER_PASSWORD')
SKIP_REAL_API_TESTS = HAVER_USERNAME is None or HAVER_PASSWORD is None

def skip_if_no_haver_credentials():
    return pytest.mark.skipif(
        SKIP_REAL_API_TESTS, 
        reason="HAVER_USERNAME and HAVER_PASSWORD environment variables not set"
    )


class TestHaverDataSourceInitialization:
    """Test cases for Haver data source initialization"""
    
    def test_valid_credentials_initialization(self):
        """Test initialization with valid credentials"""
        username = "test_user"
        password = "test_password"
        
        haver = HaverDataSource(username=username, password=password)
        
        assert haver.username == username
        assert haver.password == password
        assert haver.base_url == "https://api.haver.com/v1"
        assert haver.rate_limit == 10
        assert haver.timeout == 45
        assert not haver.is_connected
    
    def test_initialization_with_config(self):
        """Test initialization with custom configuration"""
        username = "test_user"
        password = "test_password"
        config = {
            'base_url': 'https://custom.haver.com/api',
            'rate_limit': 5,
            'timeout': 30
        }
        
        haver = HaverDataSource(username=username, password=password, config=config)
        
        assert haver.base_url == "https://custom.haver.com/api"
        assert haver.rate_limit == 5
        assert haver.timeout == 30
    
    def test_invalid_username_none(self):
        """Test initialization with None username"""
        with pytest.raises(ValidationError, match="Username must be a non-empty string"):
            HaverDataSource(username=None, password="password")
    
    def test_invalid_username_empty_string(self):
        """Test initialization with empty string username"""
        with pytest.raises(ValidationError, match="Username must be a non-empty string"):
            HaverDataSource(username="", password="password")
    
    def test_invalid_password_none(self):
        """Test initialization with None password"""
        with pytest.raises(ValidationError, match="Password must be a non-empty string"):
            HaverDataSource(username="username", password=None)
    
    def test_invalid_password_empty_string(self):
        """Test initialization with empty string password"""
        with pytest.raises(ValidationError, match="Password must be a non-empty string"):
            HaverDataSource(username="username", password="")


class TestHaverConnection:
    """Test cases for Haver API connection management with real API"""
    
    @skip_if_no_haver_credentials()
    def test_successful_connection_real_api(self):
        """Test successful connection to real Haver API"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        result = haver.connect()
        
        assert result is True
        assert haver.is_connected is True
        assert haver.session is not None
        
        # Clean up
        haver.disconnect()
    
    def test_connection_with_invalid_credentials(self):
        """Test connection failure with invalid credentials"""
        haver = HaverDataSource(username="invalid_user", password="invalid_password")
        
        with pytest.raises(AuthenticationError):
            haver.connect()
        
        assert haver.is_connected is False
    
    @skip_if_no_haver_credentials()
    def test_disconnect_after_connection(self):
        """Test disconnection from Haver API after successful connection"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        haver.connect()
        
        assert haver.is_connected is True
        
        haver.disconnect()
        
        assert haver.is_connected is False
        assert haver.session is None
    
    def test_disconnect_when_not_connected(self):
        """Test disconnect when already disconnected"""
        haver = HaverDataSource(username="test_user", password="test_password")
        
        # Should not raise any exceptions
        haver.disconnect()
        
        assert haver.is_connected is False
        assert haver.session is None
    
    @skip_if_no_haver_credentials()
    def test_context_manager_real_api(self):
        """Test context manager functionality with real API"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver as h:
            assert h is haver
            assert h.is_connected is True
            assert h.session is not None
        
        assert haver.is_connected is False
        assert haver.session is None


class TestHaverRateLimiting:
    """Test cases for Haver API rate limiting"""
    
    def setup_method(self):
        """Set up for each test"""
        self.haver = HaverDataSource(username="test_user", password="test_password")
        
        # Set up connected state for rate limiting tests
        self.haver.is_connected = True
        self.haver.last_request_time = datetime.now() - timedelta(seconds=1)
        self.haver.requests_this_second = 0
        self.haver.second_window_start = datetime.now()
    
    def test_rate_limit_under_limit(self):
        """Test rate limiting when under the limit"""
        self.haver.requests_this_second = 5  # Under limit of 10
        
        # Should not raise any exceptions
        self.haver._enforce_rate_limit()
        
        assert self.haver.requests_this_second == 6
    
    def test_rate_limit_at_limit(self):
        """Test rate limiting when at the limit"""
        self.haver.requests_this_second = 10  # At limit
        
        with pytest.raises(RateLimitError, match="Haver API rate limit exceeded"):
            self.haver._enforce_rate_limit()
    
    def test_rate_limit_reset_after_second(self):
        """Test rate limit reset after second window"""
        # Set up rate limit state from previous second
        self.haver.requests_this_second = 10
        self.haver.second_window_start = datetime.now() - timedelta(seconds=2)
        
        # Should reset and allow request
        self.haver._enforce_rate_limit()
        
        assert self.haver.requests_this_second == 1


class TestHaverDataRetrieval:
    """Test cases for Haver data retrieval with real API"""
    
    def test_get_data_not_connected(self):
        """Test data retrieval when not connected"""
        haver = HaverDataSource(username="test_user", password="test_password")
        
        with pytest.raises(ConnectionError, match="Not connected to Haver API"):
            haver.get_data("GDP")
    
    @skip_if_no_haver_credentials()
    def test_get_data_single_variable_success(self):
        """Test successful data retrieval for single variable with real API"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            # Use common Haver variables - GDP growth, CPI, etc.
            # Note: Variable names may vary by Haver subscription
            try:
                result = haver.get_data("GDP", "2022-01-01", "2022-12-31")
                
                assert isinstance(result, pd.DataFrame)
                assert "GDP" in result.columns
                assert len(result) > 0
                assert isinstance(result.index, pd.DatetimeIndex)
                
            except DataRetrievalError:
                # Variable might not be available in test subscription
                # This is acceptable for unit tests
                pytest.skip("GDP variable not available in test Haver subscription")
    
    @skip_if_no_haver_credentials()
    def test_get_data_multiple_variables_success(self):
        """Test successful data retrieval for multiple variables with real API"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            try:
                # Try common economic indicators
                result = haver.get_data(["GDP", "CPI"], "2022-01-01", "2022-12-31")
                
                assert isinstance(result, pd.DataFrame)
                assert len(result) > 0
                assert isinstance(result.index, pd.DatetimeIndex)
                
                # At least one variable should have data
                assert any(result[col].notna().sum() > 0 for col in result.columns)
                
            except DataRetrievalError:
                # Variables might not be available in test subscription
                pytest.skip("Test variables not available in Haver subscription")
    
    @skip_if_no_haver_credentials()
    def test_get_data_with_date_range(self):
        """Test data retrieval with specific date range"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            try:
                result = haver.get_data("GDP", "2022-06-01", "2022-06-30")
                
                assert isinstance(result, pd.DataFrame)
                
                if len(result) > 0:
                    # Verify date range is respected (if data exists)
                    assert result.index.min() >= pd.Timestamp("2022-06-01")
                    assert result.index.max() <= pd.Timestamp("2022-06-30")
                    
            except DataRetrievalError:
                # Variable might not be available
                pytest.skip("Test variable not available in Haver subscription")
    
    @skip_if_no_haver_credentials()
    def test_get_data_invalid_variable(self):
        """Test data retrieval with invalid variable"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            # Should handle invalid variables gracefully
            try:
                result = haver.get_data("COMPLETELY_INVALID_VARIABLE_12345")
                
                # Result could be empty DataFrame or raise DataRetrievalError
                if isinstance(result, pd.DataFrame):
                    # If it returns empty DataFrame, that's acceptable
                    assert len(result) == 0 or "COMPLETELY_INVALID_VARIABLE_12345" not in result.columns
                    
            except DataRetrievalError:
                # This is expected for invalid variables
                pass


class TestHaverMetadataRetrieval:
    """Test cases for Haver metadata retrieval with real API"""
    
    @skip_if_no_haver_credentials()
    def test_get_variable_metadata_success(self):
        """Test successful metadata retrieval with real API"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            try:
                result = haver.get_variable_metadata("GDP")
                
                assert isinstance(result, dict)
                assert 'name' in result or 'description' in result
                
                # Should have basic metadata fields
                expected_fields = ['name', 'description', 'units', 'frequency', 'start_date', 'end_date']
                available_fields = sum(1 for field in expected_fields if field in result)
                assert available_fields >= 3  # Should have at least 3 of the expected fields
                
            except DataRetrievalError:
                # Variable might not be available in test subscription
                pytest.skip("GDP variable metadata not available in test Haver subscription")
    
    @skip_if_no_haver_credentials()
    def test_get_variable_metadata_invalid_series(self):
        """Test metadata retrieval for non-existent variable"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            with pytest.raises(DataRetrievalError):
                haver.get_variable_metadata("COMPLETELY_INVALID_VARIABLE_CODE_98765")


class TestHaverValidation:
    """Test cases for Haver input validation and error handling"""
    
    @skip_if_no_haver_credentials()
    def test_invalid_date_range(self):
        """Test handling of invalid date ranges"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            # End date before start date should raise ValidationError
            with pytest.raises((ValidationError, ValueError)):
                haver.get_data("GDP", "2022-12-31", "2022-01-01")
    
    @skip_if_no_haver_credentials()
    def test_future_date_range(self):
        """Test handling of future dates"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            try:
                # Future dates should either return empty data or handle gracefully
                future_date = "2030-01-01"
                result = haver.get_data("GDP", future_date, "2030-01-31")
                
                # Should not crash - might return empty data
                assert isinstance(result, pd.DataFrame)
                
            except DataRetrievalError:
                # This is acceptable - the variable might not support future dates
                pass


class TestHaverStringRepresentations:
    """Test cases for Haver string representation methods"""
    
    def test_str_representation_disconnected(self):
        """Test string representation when disconnected"""
        haver = HaverDataSource(username="test_user", password="test_password")
        str_repr = str(haver)
        assert "Haver" in str_repr or "HaverDataSource" in str_repr
    
    @skip_if_no_haver_credentials()
    def test_str_representation_connected(self):
        """Test string representation when connected"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            str_repr = str(haver)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
    
    def test_repr_representation(self):
        """Test detailed representation"""
        haver = HaverDataSource(username="test_user", password="test_password")
        repr_str = repr(haver)
        assert "HaverDataSource" in repr_str or "Haver" in repr_str


class TestHaverCredentialValidation:
    """Test cases for Haver credential validation"""
    
    def test_validate_username_types(self):
        """Test username validation with various types"""
        # Integer username should be converted to string
        haver = HaverDataSource(username=12345, password="password")
        assert haver.username == "12345"
        
        # Boolean should be converted to string
        haver = HaverDataSource(username=True, password="password")
        assert haver.username == "True"
    
    def test_validate_password_types(self):
        """Test password validation with various types"""
        # Integer password should be converted to string
        haver = HaverDataSource(username="username", password=12345)
        assert haver.password == "12345"
    
    def test_username_with_special_characters(self):
        """Test that usernames with special characters are allowed"""
        special_username = "user@company.com"
        haver = HaverDataSource(username=special_username, password="password")
        assert haver.username == special_username
    
    def test_password_security_not_logged(self):
        """Test that passwords are not exposed in string representations"""
        haver = HaverDataSource(username="test_user", password="secret_password")
        
        str_repr = str(haver)
        repr_str = repr(haver)
        
        # Password should not appear in string representations
        assert "secret_password" not in str_repr
        assert "secret_password" not in repr_str
        
        # Username might appear, but password should not
        assert "test_user" in str_repr or "test_user" in repr_str


@pytest.mark.integration
class TestHaverIntegrationScenarios:
    """Integration test scenarios for Haver API client"""
    
    @skip_if_no_haver_credentials()
    def test_typical_workflow_scenario(self):
        """Test typical data extraction workflow"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        # Test complete workflow
        with haver:
            # Test connection is established
            assert haver.is_connected
            
            try:
                # Get metadata first
                metadata = haver.get_variable_metadata("GDP")
                assert isinstance(metadata, dict)
                
                # Then get data
                data = haver.get_data("GDP", "2022-01-01", "2022-03-31")
                assert isinstance(data, pd.DataFrame)
                
                if len(data) > 0:
                    assert "GDP" in data.columns
                    assert isinstance(data.index, pd.DatetimeIndex)
                    
            except DataRetrievalError:
                # Variables might not be available in test subscription
                pytest.skip("Test variables not available in Haver subscription")
    
    @skip_if_no_haver_credentials()
    def test_rate_limiting_under_load(self):
        """Test rate limiting behavior under load"""
        haver = HaverDataSource(username=HAVER_USERNAME, password=HAVER_PASSWORD)
        
        with haver:
            # Make several rapid requests to test rate limiting
            request_count = 0
            max_requests = 5  # Conservative test
            
            for i in range(max_requests):
                try:
                    # Make metadata requests which are typically lighter
                    result = haver.get_variable_metadata("GDP")
                    request_count += 1
                    
                except (DataRetrievalError, RateLimitError):
                    # Either the variable doesn't exist or rate limit hit
                    # Both are acceptable outcomes for this test
                    break
            
            # Should have made at least one successful request
            assert request_count >= 1