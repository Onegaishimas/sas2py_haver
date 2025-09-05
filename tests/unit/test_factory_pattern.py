"""
Unit tests for data source factory pattern

Tests the create_data_source factory function with various configuration
scenarios, credential handling, and error conditions using real API validation.
"""

import pytest
import os
from unittest.mock import patch, Mock
from typing import Dict, Any

from src.federal_reserve_etl.data_sources import (
    create_data_source,
    get_available_sources,
    validate_source_config,
    DATA_SOURCE_REGISTRY,
    DataSource,
    FREDDataSource,
    HaverDataSource
)
from src.federal_reserve_etl.utils.exceptions import (
    ConfigurationError,
    ValidationError
)

# Test configuration
FRED_API_KEY = os.getenv('FRED_API_KEY')
HAVER_USERNAME = os.getenv('HAVER_USERNAME')
HAVER_PASSWORD = os.getenv('HAVER_PASSWORD')

SKIP_FRED_TESTS = FRED_API_KEY is None
SKIP_HAVER_TESTS = HAVER_USERNAME is None or HAVER_PASSWORD is None


class TestDataSourceRegistry:
    """Test cases for data source registry functionality"""
    
    def test_registry_contains_expected_sources(self):
        """Test that registry contains expected data sources"""
        assert 'fred' in DATA_SOURCE_REGISTRY
        assert 'haver' in DATA_SOURCE_REGISTRY
        assert 'FRED' in DATA_SOURCE_REGISTRY
        assert 'HAVER' in DATA_SOURCE_REGISTRY
        
        assert DATA_SOURCE_REGISTRY['fred'] == FREDDataSource
        assert DATA_SOURCE_REGISTRY['haver'] == HaverDataSource
        assert DATA_SOURCE_REGISTRY['FRED'] == FREDDataSource
        assert DATA_SOURCE_REGISTRY['HAVER'] == HaverDataSource
    
    def test_case_insensitive_aliases(self):
        """Test case-insensitive source type handling"""
        assert DATA_SOURCE_REGISTRY['fred'] == DATA_SOURCE_REGISTRY['FRED']
        assert DATA_SOURCE_REGISTRY['fred'] == DATA_SOURCE_REGISTRY['Fred']
        assert DATA_SOURCE_REGISTRY['haver'] == DATA_SOURCE_REGISTRY['HAVER']
        assert DATA_SOURCE_REGISTRY['haver'] == DATA_SOURCE_REGISTRY['Haver']
    
    def test_get_available_sources(self):
        """Test get_available_sources function"""
        sources = get_available_sources()
        
        assert isinstance(sources, dict)
        assert 'fred' in sources
        assert 'haver' in sources
        assert sources['fred'] == 'FREDDataSource'
        assert sources['haver'] == 'HaverDataSource'
        
        # Should not have duplicates due to case-insensitive handling
        assert len(sources) == 2


class TestFactoryBasicFunctionality:
    """Test cases for basic factory functionality"""
    
    def test_invalid_source_type_none(self):
        """Test factory with None source type"""
        with pytest.raises(ConfigurationError, match="source_type must be a non-empty string"):
            create_data_source(None)
    
    def test_invalid_source_type_empty_string(self):
        """Test factory with empty string source type"""
        with pytest.raises(ConfigurationError, match="source_type must be a non-empty string"):
            create_data_source("")
    
    def test_invalid_source_type_integer(self):
        """Test factory with integer source type"""
        with pytest.raises(ConfigurationError, match="source_type must be a non-empty string"):
            create_data_source(123)
    
    def test_unsupported_source_type(self):
        """Test factory with unsupported source type"""
        with pytest.raises(ConfigurationError, match="Unsupported data source: 'invalid'"):
            create_data_source("invalid")
        
        # Error message should include available sources
        try:
            create_data_source("invalid")
        except ConfigurationError as e:
            assert "Available sources:" in str(e)
            assert "fred" in str(e).lower()
            assert "haver" in str(e).lower()
    
    def test_source_type_with_whitespace(self):
        """Test factory handles source type with whitespace"""
        with pytest.raises(ConfigurationError, match="API key is required"):
            # Should normalize " fred " to "fred" but then fail on missing API key
            create_data_source(" fred ")


class TestFREDFactoryCreation:
    """Test cases for FRED data source factory creation"""
    
    def test_fred_creation_with_explicit_api_key(self):
        """Test FRED creation with explicitly provided API key"""
        api_key = "12345678901234567890123456789012"  # Valid format
        
        fred = create_data_source("fred", api_key=api_key)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key
    
    def test_fred_creation_with_config_api_key(self):
        """Test FRED creation with API key in config"""
        api_key = "12345678901234567890123456789012"
        config = {"api_key": api_key}
        
        fred = create_data_source("fred", config=config)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key
    
    @pytest.mark.skipif(SKIP_FRED_TESTS, reason="FRED_API_KEY environment variable not set")
    def test_fred_creation_with_environment_variable(self):
        """Test FRED creation using environment variable"""
        fred = create_data_source("fred")
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == FRED_API_KEY
    
    def test_fred_creation_missing_api_key(self):
        """Test FRED creation without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="FRED API key is required"):
                create_data_source("fred")
    
    def test_fred_creation_invalid_api_key(self):
        """Test FRED creation with invalid API key format"""
        with pytest.raises((ConfigurationError, ValidationError)):
            create_data_source("fred", api_key="invalid")
    
    def test_fred_creation_with_custom_config(self):
        """Test FRED creation with custom configuration"""
        api_key = "12345678901234567890123456789012"
        config = {
            "rate_limit": 60,
            "timeout": 15,
            "base_url": "https://custom.fred.api.com"
        }
        
        fred = create_data_source("fred", api_key=api_key, config=config)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key
        assert fred.rate_limit == 60
        assert fred.timeout == 15
        assert fred.base_url == "https://custom.fred.api.com"
    
    def test_fred_kwargs_override_config(self):
        """Test that kwargs take precedence over config"""
        api_key = "12345678901234567890123456789012"
        config = {"api_key": "config_key"}
        
        fred = create_data_source("fred", config=config, api_key=api_key)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key  # kwargs should override config
    
    def test_fred_case_insensitive_creation(self):
        """Test FRED creation with various case formats"""
        api_key = "12345678901234567890123456789012"
        
        # Test different case formats
        for source_name in ["fred", "FRED", "Fred"]:
            fred = create_data_source(source_name, api_key=api_key)
            assert isinstance(fred, FREDDataSource)
            assert fred.api_key == api_key


class TestHaverFactoryCreation:
    """Test cases for Haver data source factory creation"""
    
    def test_haver_creation_with_explicit_credentials(self):
        """Test Haver creation with explicitly provided credentials"""
        username = "test_user"
        password = "test_password"
        
        haver = create_data_source("haver", username=username, password=password)
        
        assert isinstance(haver, HaverDataSource)
        assert haver.username == username
        assert haver.password == password
    
    def test_haver_creation_with_config_credentials(self):
        """Test Haver creation with credentials in config"""
        config = {
            "username": "test_user",
            "password": "test_password"
        }
        
        haver = create_data_source("haver", config=config)
        
        assert isinstance(haver, HaverDataSource)
        assert haver.username == "test_user"
        assert haver.password == "test_password"
    
    @pytest.mark.skipif(SKIP_HAVER_TESTS, reason="HAVER_USERNAME/PASSWORD environment variables not set")
    def test_haver_creation_with_environment_variables(self):
        """Test Haver creation using environment variables"""
        haver = create_data_source("haver")
        
        assert isinstance(haver, HaverDataSource)
        assert haver.username == HAVER_USERNAME
        assert haver.password == HAVER_PASSWORD
    
    def test_haver_creation_missing_username(self):
        """Test Haver creation without username"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="Haver username is required"):
                create_data_source("haver", password="password")
    
    def test_haver_creation_missing_password(self):
        """Test Haver creation without password"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="Haver password is required"):
                create_data_source("haver", username="username")
    
    def test_haver_creation_missing_both_credentials(self):
        """Test Haver creation without any credentials"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="Haver username is required"):
                create_data_source("haver")
    
    def test_haver_creation_with_custom_config(self):
        """Test Haver creation with custom configuration"""
        config = {
            "rate_limit": 5,
            "timeout": 30,
            "base_url": "https://custom.haver.com"
        }
        
        haver = create_data_source(
            "haver", 
            config=config,
            username="test_user",
            password="test_password"
        )
        
        assert isinstance(haver, HaverDataSource)
        assert haver.username == "test_user"
        assert haver.password == "test_password"
        assert haver.rate_limit == 5
        assert haver.timeout == 30
        assert haver.base_url == "https://custom.haver.com"
    
    def test_haver_kwargs_override_config(self):
        """Test that kwargs take precedence over config"""
        config = {
            "username": "config_user",
            "password": "config_password"
        }
        
        haver = create_data_source(
            "haver", 
            config=config,
            username="kwargs_user",
            password="kwargs_password"
        )
        
        assert isinstance(haver, HaverDataSource)
        assert haver.username == "kwargs_user"  # kwargs should override config
        assert haver.password == "kwargs_password"
    
    def test_haver_case_insensitive_creation(self):
        """Test Haver creation with various case formats"""
        username = "test_user"
        password = "test_password"
        
        # Test different case formats
        for source_name in ["haver", "HAVER", "Haver"]:
            haver = create_data_source(source_name, username=username, password=password)
            assert isinstance(haver, HaverDataSource)
            assert haver.username == username
            assert haver.password == password


class TestFactoryErrorHandling:
    """Test cases for factory error handling and logging"""
    
    def test_factory_error_propagation(self):
        """Test that underlying errors are properly wrapped"""
        # Invalid API key format should be caught and wrapped
        with pytest.raises(ConfigurationError) as exc_info:
            create_data_source("fred", api_key="invalid")
        
        # Should contain information about the failure
        assert "Failed to create data source 'fred'" in str(exc_info.value)
        assert exc_info.value.context["config_key"] == "source_instantiation"
    
    def test_factory_logging_integration(self):
        """Test factory logging integration"""
        api_key = "12345678901234567890123456789012"
        
        with patch('src.federal_reserve_etl.data_sources.get_logger') as mock_logger:
            mock_log_instance = Mock()
            mock_logger.return_value = mock_log_instance
            
            fred = create_data_source("fred", api_key=api_key)
            
            # Should log successful creation
            mock_log_instance.info.assert_called_with("Creating FREDDataSource instance")
            assert isinstance(fred, FREDDataSource)
    
    def test_factory_error_logging(self):
        """Test factory error logging"""
        with patch('src.federal_reserve_etl.data_sources.get_logger') as mock_logger:
            mock_log_instance = Mock()
            mock_logger.return_value = mock_log_instance
            
            with pytest.raises(ConfigurationError):
                create_data_source("fred", api_key="invalid")
            
            # Should log the error
            mock_log_instance.error.assert_called()
            error_call = mock_log_instance.error.call_args[0][0]
            assert "Failed to create FREDDataSource" in error_call


class TestConfigurationValidation:
    """Test cases for configuration validation"""
    
    def test_validate_fred_config_success(self):
        """Test successful FRED configuration validation"""
        config = {"api_key": "12345678901234567890123456789012"}
        
        result = validate_source_config("fred", config)
        
        assert result is True
    
    def test_validate_fred_config_invalid_api_key(self):
        """Test FRED configuration validation with invalid API key"""
        config = {"api_key": "invalid"}
        
        with pytest.raises(ValidationError):
            validate_source_config("fred", config)
    
    def test_validate_haver_config_success(self):
        """Test successful Haver configuration validation"""
        config = {
            "username": "test_user",
            "password": "test_password"
        }
        
        result = validate_source_config("haver", config)
        
        assert result is True
    
    def test_validate_haver_config_invalid_username(self):
        """Test Haver configuration validation with invalid username"""
        config = {
            "username": "",
            "password": "test_password"
        }
        
        with pytest.raises(ValidationError):
            validate_source_config("haver", config)
    
    def test_validate_unknown_source_type(self):
        """Test configuration validation with unknown source type"""
        config = {"api_key": "test"}
        
        with pytest.raises(ConfigurationError, match="Unknown source type: invalid"):
            validate_source_config("invalid", config)
    
    def test_validate_config_logging(self):
        """Test configuration validation logging"""
        config = {"api_key": "12345678901234567890123456789012"}
        
        with patch('src.federal_reserve_etl.data_sources.get_logger') as mock_logger:
            mock_log_instance = Mock()
            mock_logger.return_value = mock_log_instance
            
            result = validate_source_config("fred", config)
            
            assert result is True
            mock_log_instance.info.assert_called_with("Configuration valid for fred")


class TestFactoryIntegrationScenarios:
    """Integration test scenarios for factory pattern"""
    
    @pytest.mark.skipif(SKIP_FRED_TESTS, reason="FRED_API_KEY environment variable not set")
    def test_fred_factory_with_real_connection(self):
        """Test FRED factory creates working client"""
        fred = create_data_source("fred")
        
        assert isinstance(fred, FREDDataSource)
        
        # Test that it can actually connect
        try:
            result = fred.connect()
            assert result is True
            assert fred.is_connected is True
            
            # Test basic functionality
            fred.disconnect()
            assert fred.is_connected is False
            
        except Exception as e:
            pytest.fail(f"FRED client created by factory failed to connect: {str(e)}")
    
    @pytest.mark.skipif(SKIP_HAVER_TESTS, reason="HAVER credentials not available")
    def test_haver_factory_with_real_connection(self):
        """Test Haver factory creates working client"""
        haver = create_data_source("haver")
        
        assert isinstance(haver, HaverDataSource)
        
        # Test that it can actually connect
        try:
            result = haver.connect()
            assert result is True
            assert haver.is_connected is True
            
            # Test basic functionality
            haver.disconnect()
            assert haver.is_connected is False
            
        except Exception as e:
            pytest.fail(f"Haver client created by factory failed to connect: {str(e)}")
    
    def test_factory_creates_independent_instances(self):
        """Test that factory creates independent instances"""
        api_key = "12345678901234567890123456789012"
        
        fred1 = create_data_source("fred", api_key=api_key)
        fred2 = create_data_source("fred", api_key=api_key)
        
        # Should be different instances
        assert fred1 is not fred2
        assert isinstance(fred1, FREDDataSource)
        assert isinstance(fred2, FREDDataSource)
        assert fred1.api_key == fred2.api_key
    
    def test_factory_with_mixed_configurations(self):
        """Test factory with complex configuration scenarios"""
        # FRED with partial environment + partial explicit
        with patch.dict(os.environ, {'FRED_API_KEY': '12345678901234567890123456789012'}):
            fred = create_data_source(
                "fred",
                config={"rate_limit": 60, "timeout": 20}
            )
            
            assert isinstance(fred, FREDDataSource)
            assert fred.api_key == "12345678901234567890123456789012"
            assert fred.rate_limit == 60
            assert fred.timeout == 20
    
    def test_factory_parameter_precedence(self):
        """Test parameter precedence: kwargs > config > environment"""
        with patch.dict(os.environ, {'FRED_API_KEY': 'env_key_12345678901234567890'}):
            config = {"api_key": "config_key_123456789012345678"}
            
            fred = create_data_source(
                "fred",
                config=config,
                api_key="kwargs_key_1234567890123456789"  # Should take precedence
            )
            
            assert isinstance(fred, FREDDataSource)
            assert fred.api_key == "kwargs_key_1234567890123456789"


class TestFactoryEdgeCases:
    """Test cases for factory edge cases and corner scenarios"""
    
    def test_empty_config_dictionary(self):
        """Test factory with empty config dictionary"""
        api_key = "12345678901234567890123456789012"
        
        fred = create_data_source("fred", config={}, api_key=api_key)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key
    
    def test_none_config_dictionary(self):
        """Test factory with None config"""
        api_key = "12345678901234567890123456789012"
        
        fred = create_data_source("fred", config=None, api_key=api_key)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key
    
    def test_config_with_unexpected_keys(self):
        """Test factory with config containing unexpected keys"""
        api_key = "12345678901234567890123456789012"
        config = {
            "api_key": api_key,
            "unexpected_key": "unexpected_value",
            "another_unexpected": 123
        }
        
        # Should handle unexpected keys gracefully
        fred = create_data_source("fred", config=config)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key
    
    def test_very_large_config(self):
        """Test factory with large configuration dictionary"""
        api_key = "12345678901234567890123456789012"
        config = {f"key_{i}": f"value_{i}" for i in range(100)}
        config["api_key"] = api_key
        
        fred = create_data_source("fred", config=config)
        
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == api_key