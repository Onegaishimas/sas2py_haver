"""
Unit tests for custom exception classes

Tests the exception hierarchy, error context handling, and
utility functions for creating standardized exceptions.
"""

import pytest
from typing import Dict, Any, Optional

from src.federal_reserve_etl.utils.exceptions import (
    FederalReserveETLError,
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    ValidationError,
    ConfigurationError,
    RateLimitError,
    create_connection_error,
    create_auth_error,
    create_data_error
)


class TestFederalReserveETLError:
    """Test cases for base FederalReserveETLError class"""
    
    def test_basic_initialization(self):
        """Test basic exception initialization"""
        error = FederalReserveETLError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code is None
        assert error.context == {}
    
    def test_initialization_with_error_code(self):
        """Test exception initialization with error code"""
        error = FederalReserveETLError("Test error", error_code="TEST_001")
        
        assert str(error) == "[TEST_001] Test error"
        assert error.message == "Test error"
        assert error.error_code == "TEST_001"
        assert error.context == {}
    
    def test_initialization_with_context(self):
        """Test exception initialization with context"""
        context = {"variable": "FEDFUNDS", "operation": "data_retrieval"}
        error = FederalReserveETLError("Test error", context=context)
        
        assert error.message == "Test error"
        assert error.context == context
    
    def test_initialization_with_all_parameters(self):
        """Test exception initialization with all parameters"""
        context = {"endpoint": "/api/data", "status": 404}
        error = FederalReserveETLError(
            "Test error",
            error_code="TEST_404",
            context=context
        )
        
        assert str(error) == "[TEST_404] Test error"
        assert error.message == "Test error"
        assert error.error_code == "TEST_404"
        assert error.context == context
    
    def test_repr_method(self):
        """Test detailed string representation"""
        context = {"key": "value"}
        error = FederalReserveETLError(
            "Test error",
            error_code="TEST_001",
            context=context
        )
        
        repr_str = repr(error)
        
        assert "FederalReserveETLError" in repr_str
        assert "message='Test error'" in repr_str
        assert "error_code='TEST_001'" in repr_str
        assert "context={'key': 'value'}" in repr_str
    
    def test_to_dict_method(self):
        """Test conversion to dictionary"""
        context = {"variable": "FEDFUNDS"}
        error = FederalReserveETLError(
            "Test error",
            error_code="TEST_001",
            context=context
        )
        
        error_dict = error.to_dict()
        
        expected = {
            "exception_type": "FederalReserveETLError",
            "message": "Test error",
            "error_code": "TEST_001",
            "context": {"variable": "FEDFUNDS"}
        }
        
        assert error_dict == expected
    
    def test_inheritance_from_exception(self):
        """Test that base error inherits from Exception"""
        error = FederalReserveETLError("Test error")
        
        assert isinstance(error, Exception)
        assert isinstance(error, FederalReserveETLError)


class TestConnectionError:
    """Test cases for ConnectionError class"""
    
    def test_basic_initialization(self):
        """Test basic ConnectionError initialization"""
        error = ConnectionError("Connection failed")
        
        assert isinstance(error, FederalReserveETLError)
        assert str(error) == "Connection failed"
        assert error.message == "Connection failed"
    
    def test_initialization_with_endpoint(self):
        """Test initialization with endpoint parameter"""
        error = ConnectionError(
            "Failed to connect",
            endpoint="https://api.test.com/data"
        )
        
        assert error.message == "Failed to connect"
        assert error.context["endpoint"] == "https://api.test.com/data"
    
    def test_initialization_with_status_code(self):
        """Test initialization with status code parameter"""
        error = ConnectionError(
            "Connection failed",
            status_code=503
        )
        
        assert error.message == "Connection failed"
        assert error.context["status_code"] == 503
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters"""
        error = ConnectionError(
            "Connection failed",
            endpoint="https://api.test.com",
            status_code=503,
            error_code="CONN_503",
            context={"retry_count": 3}
        )
        
        assert str(error) == "[CONN_503] Connection failed"
        assert error.context["endpoint"] == "https://api.test.com"
        assert error.context["status_code"] == 503
        assert error.context["retry_count"] == 3


class TestAuthenticationError:
    """Test cases for AuthenticationError class"""
    
    def test_basic_initialization(self):
        """Test basic AuthenticationError initialization"""
        error = AuthenticationError("Authentication failed")
        
        assert isinstance(error, FederalReserveETLError)
        assert str(error) == "Authentication failed"
        assert error.message == "Authentication failed"
    
    def test_initialization_with_api_key_hint(self):
        """Test initialization with API key hint"""
        error = AuthenticationError(
            "Invalid API key",
            api_key_hint="abc***xyz"
        )
        
        assert error.message == "Invalid API key"
        assert error.context["api_key_hint"] == "abc***xyz"
    
    def test_initialization_with_source(self):
        """Test initialization with data source"""
        error = AuthenticationError(
            "Authentication failed",
            source="FRED"
        )
        
        assert error.message == "Authentication failed"
        assert error.context["source"] == "FRED"
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters"""
        error = AuthenticationError(
            "Authentication failed",
            api_key_hint="abc***xyz",
            source="FRED",
            error_code="AUTH_INVALID"
        )
        
        assert str(error) == "[AUTH_INVALID] Authentication failed"
        assert error.context["api_key_hint"] == "abc***xyz"
        assert error.context["source"] == "FRED"


class TestDataRetrievalError:
    """Test cases for DataRetrievalError class"""
    
    def test_basic_initialization(self):
        """Test basic DataRetrievalError initialization"""
        error = DataRetrievalError("Data retrieval failed")
        
        assert isinstance(error, FederalReserveETLError)
        assert str(error) == "Data retrieval failed"
        assert error.message == "Data retrieval failed"
    
    def test_initialization_with_variables(self):
        """Test initialization with variables parameter"""
        error = DataRetrievalError(
            "Variables not found",
            variables=["FEDFUNDS", "DGS10"]
        )
        
        assert error.message == "Variables not found"
        assert error.context["variables"] == ["FEDFUNDS", "DGS10"]
    
    def test_initialization_with_date_range(self):
        """Test initialization with date range parameter"""
        error = DataRetrievalError(
            "Invalid date range",
            date_range=("2023-01-01", "2023-12-31")
        )
        
        assert error.message == "Invalid date range"
        assert error.context["date_range"] == ("2023-01-01", "2023-12-31")
    
    def test_initialization_with_response_status(self):
        """Test initialization with response status parameter"""
        error = DataRetrievalError(
            "API returned error",
            response_status=404
        )
        
        assert error.message == "API returned error"
        assert error.context["response_status"] == 404
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters"""
        error = DataRetrievalError(
            "Data retrieval failed",
            variables=["FEDFUNDS"],
            date_range=("2023-01-01", "2023-12-31"),
            response_status=404,
            error_code="DATA_404"
        )
        
        assert str(error) == "[DATA_404] Data retrieval failed"
        assert error.context["variables"] == ["FEDFUNDS"]
        assert error.context["date_range"] == ("2023-01-01", "2023-12-31")
        assert error.context["response_status"] == 404


class TestValidationError:
    """Test cases for ValidationError class"""
    
    def test_basic_initialization(self):
        """Test basic ValidationError initialization"""
        error = ValidationError("Validation failed")
        
        assert isinstance(error, FederalReserveETLError)
        assert str(error) == "Validation failed"
        assert error.message == "Validation failed"
    
    def test_initialization_with_field(self):
        """Test initialization with field parameter"""
        error = ValidationError(
            "Invalid field value",
            field="start_date"
        )
        
        assert error.message == "Invalid field value"
        assert error.context["field"] == "start_date"
    
    def test_initialization_with_expected_actual(self):
        """Test initialization with expected and actual values"""
        error = ValidationError(
            "Type mismatch",
            expected="string",
            actual="integer"
        )
        
        assert error.message == "Type mismatch"
        assert error.context["expected"] == "string"
        assert error.context["actual"] == "integer"
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters"""
        error = ValidationError(
            "Validation failed",
            field="api_key",
            expected="32 characters",
            actual="16 characters",
            error_code="VALID_001"
        )
        
        assert str(error) == "[VALID_001] Validation failed"
        assert error.context["field"] == "api_key"
        assert error.context["expected"] == "32 characters"
        assert error.context["actual"] == "16 characters"


class TestConfigurationError:
    """Test cases for ConfigurationError class"""
    
    def test_basic_initialization(self):
        """Test basic ConfigurationError initialization"""
        error = ConfigurationError("Configuration error")
        
        assert isinstance(error, FederalReserveETLError)
        assert str(error) == "Configuration error"
        assert error.message == "Configuration error"
    
    def test_initialization_with_config_key(self):
        """Test initialization with config key parameter"""
        error = ConfigurationError(
            "Missing configuration",
            config_key="api_key"
        )
        
        assert error.message == "Missing configuration"
        assert error.context["config_key"] == "api_key"
    
    def test_initialization_with_config_file(self):
        """Test initialization with config file parameter"""
        error = ConfigurationError(
            "Invalid config file",
            config_file="/path/to/config.yml"
        )
        
        assert error.message == "Invalid config file"
        assert error.context["config_file"] == "/path/to/config.yml"
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters"""
        error = ConfigurationError(
            "Configuration error",
            config_key="database_url",
            config_file="/etc/app/config.yml",
            error_code="CONFIG_001"
        )
        
        assert str(error) == "[CONFIG_001] Configuration error"
        assert error.context["config_key"] == "database_url"
        assert error.context["config_file"] == "/etc/app/config.yml"


class TestRateLimitError:
    """Test cases for RateLimitError class"""
    
    def test_basic_initialization(self):
        """Test basic RateLimitError initialization"""
        error = RateLimitError("Rate limit exceeded")
        
        assert isinstance(error, DataRetrievalError)
        assert isinstance(error, FederalReserveETLError)
        assert str(error) == "Rate limit exceeded"
        assert error.message == "Rate limit exceeded"
    
    def test_initialization_with_limit(self):
        """Test initialization with limit parameter"""
        error = RateLimitError(
            "Rate limit exceeded",
            limit=120
        )
        
        assert error.message == "Rate limit exceeded"
        assert error.context["limit"] == 120
    
    def test_initialization_with_timing_parameters(self):
        """Test initialization with timing parameters"""
        error = RateLimitError(
            "Rate limit exceeded",
            reset_time=1640995200,  # Unix timestamp
            retry_after=60
        )
        
        assert error.message == "Rate limit exceeded"
        assert error.context["reset_time"] == 1640995200
        assert error.context["retry_after"] == 60
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters"""
        error = RateLimitError(
            "Rate limit exceeded",
            limit=120,
            reset_time=1640995200,
            retry_after=60,
            error_code="RATE_LIMIT",
            variables=["FEDFUNDS"]
        )
        
        assert str(error) == "[RATE_LIMIT] Rate limit exceeded"
        assert error.context["limit"] == 120
        assert error.context["reset_time"] == 1640995200
        assert error.context["retry_after"] == 60
        assert error.context["variables"] == ["FEDFUNDS"]


class TestUtilityFunctions:
    """Test cases for utility functions"""
    
    def test_create_connection_error_basic(self):
        """Test basic connection error creation"""
        error = create_connection_error("https://api.test.com")
        
        assert isinstance(error, ConnectionError)
        assert "Failed to connect to https://api.test.com" in str(error)
        assert error.error_code == "CONN_FAILED"
        assert error.context["endpoint"] == "https://api.test.com"
    
    def test_create_connection_error_with_status(self):
        """Test connection error creation with status code"""
        error = create_connection_error("https://api.test.com", status_code=503)
        
        assert isinstance(error, ConnectionError)
        assert "Failed to connect to https://api.test.com (HTTP 503)" in str(error)
        assert error.error_code == "CONN_503"
        assert error.context["endpoint"] == "https://api.test.com"
        assert error.context["status_code"] == 503
    
    def test_create_auth_error_basic(self):
        """Test basic authentication error creation"""
        error = create_auth_error("FRED")
        
        assert isinstance(error, AuthenticationError)
        assert "Authentication failed for FRED" in str(error)
        assert error.error_code == "AUTH_FAILED"
        assert error.context["source"] == "FRED"
    
    def test_create_auth_error_with_key_hint(self):
        """Test authentication error creation with API key hint"""
        error = create_auth_error("FRED", api_key_hint="abc***xyz")
        
        assert isinstance(error, AuthenticationError)
        assert "Authentication failed for FRED (API key: abc***xyz)" in str(error)
        assert error.error_code == "AUTH_FAILED"
        assert error.context["source"] == "FRED"
        assert error.context["api_key_hint"] == "abc***xyz"
    
    def test_create_data_error_basic(self):
        """Test basic data retrieval error creation"""
        variables = ["FEDFUNDS", "DGS10"]
        error = create_data_error(variables)
        
        assert isinstance(error, DataRetrievalError)
        assert "Failed to retrieve data for variables: FEDFUNDS, DGS10" in str(error)
        assert error.error_code == "DATA_FAILED"
        assert error.context["variables"] == variables
    
    def test_create_data_error_many_variables(self):
        """Test data error creation with many variables"""
        variables = ["VAR1", "VAR2", "VAR3", "VAR4", "VAR5"]
        error = create_data_error(variables)
        
        assert isinstance(error, DataRetrievalError)
        message = str(error)
        assert "Failed to retrieve data for variables: VAR1, VAR2, VAR3 (and 2 more)" in message
        assert error.context["variables"] == variables
    
    def test_create_data_error_custom_message(self):
        """Test data error creation with custom message"""
        variables = ["FEDFUNDS"]
        custom_message = "Custom error message"
        error = create_data_error(variables, message=custom_message)
        
        assert isinstance(error, DataRetrievalError)
        assert str(error) == "[DATA_FAILED] Custom error message"
        assert error.context["variables"] == variables


class TestExceptionHierarchy:
    """Test cases for exception inheritance hierarchy"""
    
    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from base"""
        exceptions = [
            ConnectionError("test"),
            AuthenticationError("test"),
            DataRetrievalError("test"),
            ValidationError("test"),
            ConfigurationError("test"),
            RateLimitError("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, FederalReserveETLError)
            assert isinstance(exc, Exception)
    
    def test_rate_limit_error_hierarchy(self):
        """Test that RateLimitError inherits from DataRetrievalError"""
        error = RateLimitError("Rate limit exceeded")
        
        assert isinstance(error, RateLimitError)
        assert isinstance(error, DataRetrievalError)
        assert isinstance(error, FederalReserveETLError)
        assert isinstance(error, Exception)
    
    def test_exception_catching_by_base_class(self):
        """Test that exceptions can be caught by base class"""
        with pytest.raises(FederalReserveETLError):
            raise ConnectionError("Connection failed")
        
        with pytest.raises(FederalReserveETLError):
            raise AuthenticationError("Auth failed")
        
        with pytest.raises(FederalReserveETLError):
            raise DataRetrievalError("Data failed")
    
    def test_exception_catching_by_specific_class(self):
        """Test that exceptions can be caught by specific class"""
        with pytest.raises(DataRetrievalError):
            raise RateLimitError("Rate limit exceeded")
        
        # But not by sibling classes
        with pytest.raises(RateLimitError):
            with pytest.raises(AuthenticationError):
                raise RateLimitError("Rate limit exceeded")


class TestErrorContextPreservation:
    """Test cases for error context preservation and serialization"""
    
    def test_context_preservation_through_inheritance(self):
        """Test that context is preserved through exception hierarchy"""
        original_context = {"operation": "get_data", "variables": ["FEDFUNDS"]}
        
        # Create base error with context
        base_error = FederalReserveETLError("Base error", context=original_context.copy())
        
        # Create derived error - context should be preserved
        data_error = DataRetrievalError(
            "Data error",
            variables=["DGS10"],
            context=base_error.context.copy()
        )
        
        # Original context should be preserved, new context added
        assert "operation" in data_error.context
        assert "variables" in data_error.context
        assert data_error.context["variables"] == ["DGS10"]  # New value should override
    
    def test_serialization_roundtrip(self):
        """Test that exceptions can be serialized and information preserved"""
        original_error = DataRetrievalError(
            "Test error",
            variables=["FEDFUNDS", "DGS10"],
            date_range=("2023-01-01", "2023-12-31"),
            error_code="TEST_001"
        )
        
        # Serialize to dict
        error_dict = original_error.to_dict()
        
        # Verify all information is present
        assert error_dict["exception_type"] == "DataRetrievalError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_001"
        assert error_dict["context"]["variables"] == ["FEDFUNDS", "DGS10"]
        assert error_dict["context"]["date_range"] == ("2023-01-01", "2023-12-31")
    
    def test_nested_context_handling(self):
        """Test handling of nested context dictionaries"""
        nested_context = {
            "request": {
                "variables": ["FEDFUNDS"],
                "dates": {"start": "2023-01-01", "end": "2023-12-31"}
            },
            "response": {
                "status_code": 404,
                "headers": {"content-type": "application/json"}
            }
        }
        
        error = FederalReserveETLError("Complex error", context=nested_context)
        
        assert error.context["request"]["variables"] == ["FEDFUNDS"]
        assert error.context["response"]["status_code"] == 404
        
        # Test serialization preserves nested structure
        error_dict = error.to_dict()
        assert error_dict["context"]["request"]["dates"]["start"] == "2023-01-01"