"""
Data Sources Module

Provides API clients and factory patterns for accessing Federal Reserve data
from multiple sources including FRED and Haver Analytics.

Public API:
    - DataSource: Abstract base class for all data source implementations
    - FREDDataSource: Federal Reserve Economic Data API client
    - HaverDataSource: Haver Analytics API client
    - create_data_source: Factory function for dynamic data source instantiation
"""

from typing import Dict, Any, Optional
from .base import DataSource
from .fred_client import FREDDataSource
from .haver_client import HaverDataSource
from ..utils import ConfigurationError, get_logger

# Registry of available data sources
DATA_SOURCE_REGISTRY = {
    'fred': FREDDataSource,
    'haver': HaverDataSource,
    'FRED': FREDDataSource,  # Case-insensitive aliases
    'HAVER': HaverDataSource,
    'Haver': HaverDataSource,
    'Fred': FREDDataSource
}


def create_data_source(
    source_type: str,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> DataSource:
    """
    Factory function for creating data source instances
    
    Dynamically creates appropriate data source client based on the
    specified source type. Supports both FRED and Haver Analytics
    with flexible configuration options.
    
    Args:
        source_type: Data source identifier ('fred', 'haver')
        config: Optional configuration dictionary
        **kwargs: Additional parameters passed to data source constructor
        
    Returns:
        Initialized data source instance
        
    Raises:
        ConfigurationError: If source_type is not supported or configuration is invalid
        ValidationError: If required credentials are missing
        
    Examples:
        >>> # Create FRED client
        >>> fred = create_data_source('fred', api_key='your-api-key')
        
        >>> # Create Haver client with configuration
        >>> haver_config = {'rate_limit': 5, 'timeout': 60}
        >>> haver = create_data_source('haver', 
        ...     config=haver_config,
        ...     username='user',
        ...     password='pass')
        
        >>> # Create from environment variables (requires config implementation)
        >>> client = create_data_source('fred')  # Uses FRED_API_KEY env var
    """
    logger = get_logger(__name__)
    
    if not source_type or not isinstance(source_type, str):
        raise ConfigurationError(
            "source_type must be a non-empty string",
            config_key="source_type"
        )
    
    # Normalize source type
    source_key = source_type.strip()
    
    if source_key not in DATA_SOURCE_REGISTRY:
        available_sources = sorted(set(key.lower() for key in DATA_SOURCE_REGISTRY.keys()))
        raise ConfigurationError(
            f"Unsupported data source: '{source_type}'. Available sources: {available_sources}",
            config_key="source_type"
        )
    
    source_class = DATA_SOURCE_REGISTRY[source_key]
    logger.info(f"Creating {source_class.__name__} instance")
    
    try:
        # Merge config with kwargs, with kwargs taking precedence
        final_config = config.copy() if config else {}
        
        # Handle source-specific instantiation
        if source_class == FREDDataSource:
            return _create_fred_source(final_config, **kwargs)
        elif source_class == HaverDataSource:
            return _create_haver_source(final_config, **kwargs)
        else:
            # Generic instantiation (for future extensibility)
            return source_class(config=final_config, **kwargs)
            
    except Exception as e:
        logger.error(f"Failed to create {source_class.__name__}: {str(e)}")
        raise ConfigurationError(
            f"Failed to create data source '{source_type}': {str(e)}",
            config_key="source_instantiation"
        ) from e


def _create_fred_source(config: Dict[str, Any], **kwargs) -> FREDDataSource:
    """
    Create FRED data source with appropriate parameter handling
    
    Args:
        config: Configuration dictionary
        **kwargs: Additional parameters
        
    Returns:
        Initialized FREDDataSource instance
        
    Raises:
        ConfigurationError: If API key is missing
    """
    import os
    
    # Get API key from kwargs, config, or environment
    api_key = kwargs.get('api_key') or config.get('api_key') or os.getenv('FRED_API_KEY')
    
    if not api_key:
        raise ConfigurationError(
            "FRED API key is required. Provide via api_key parameter or FRED_API_KEY environment variable",
            config_key="api_key"
        )
    
    # Remove api_key from kwargs to avoid duplicate parameter
    kwargs_clean = {k: v for k, v in kwargs.items() if k != 'api_key'}
    
    return FREDDataSource(api_key=api_key, config=config, **kwargs_clean)


def _create_haver_source(config: Dict[str, Any], **kwargs) -> HaverDataSource:
    """
    Create Haver Analytics data source with appropriate parameter handling
    
    Args:
        config: Configuration dictionary
        **kwargs: Additional parameters
        
    Returns:
        Initialized HaverDataSource instance
        
    Raises:
        ConfigurationError: If credentials are missing
    """
    import os
    
    # Get credentials from kwargs, config, or environment
    username = kwargs.get('username') or config.get('username') or os.getenv('HAVER_USERNAME')
    password = kwargs.get('password') or config.get('password') or os.getenv('HAVER_PASSWORD')
    
    if not username:
        raise ConfigurationError(
            "Haver username is required. Provide via username parameter or HAVER_USERNAME environment variable",
            config_key="username"
        )
    
    if not password:
        raise ConfigurationError(
            "Haver password is required. Provide via password parameter or HAVER_PASSWORD environment variable",
            config_key="password"
        )
    
    # Remove credentials from kwargs to avoid duplicate parameters
    kwargs_clean = {k: v for k, v in kwargs.items() if k not in ['username', 'password']}
    
    return HaverDataSource(username=username, password=password, config=config, **kwargs_clean)


def get_available_sources() -> Dict[str, str]:
    """
    Get list of available data sources
    
    Returns:
        Dictionary mapping source identifiers to class names
        
    Examples:
        >>> sources = get_available_sources()
        >>> print(sources)
        {'fred': 'FREDDataSource', 'haver': 'HaverDataSource'}
    """
    # Get unique sources (case-insensitive)
    unique_sources = {}
    for key, cls in DATA_SOURCE_REGISTRY.items():
        if key.lower() not in unique_sources:
            unique_sources[key.lower()] = cls.__name__
    
    return unique_sources


def validate_source_config(source_type: str, config: Dict[str, Any]) -> bool:
    """
    Validate configuration for a specific data source type
    
    Args:
        source_type: Data source identifier
        config: Configuration to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ConfigurationError: If configuration is invalid
        ValidationError: If specific fields are invalid
    """
    logger = get_logger(__name__)
    
    if source_type.lower() not in get_available_sources():
        raise ConfigurationError(f"Unknown source type: {source_type}")
    
    source_class = DATA_SOURCE_REGISTRY.get(source_type, DATA_SOURCE_REGISTRY.get(source_type.lower()))
    
    try:
        # Attempt to create instance with dry-run validation
        if source_class == FREDDataSource:
            api_key = config.get('api_key', 'test-key-32-characters-long-test')
            temp_instance = FREDDataSource.__new__(FREDDataSource)
            temp_instance._validate_api_key(api_key)
            
        elif source_class == HaverDataSource:
            username = config.get('username', 'testuser')
            password = config.get('password', 'testpass')
            temp_instance = HaverDataSource.__new__(HaverDataSource)
            temp_instance._validate_username(username)
            temp_instance._validate_password(password)
        
        logger.info(f"Configuration valid for {source_type}")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed for {source_type}: {str(e)}")
        raise


__all__ = [
    'DataSource',
    'FREDDataSource',
    'HaverDataSource',
    'create_data_source',
    'get_available_sources',
    'validate_source_config',
    'DATA_SOURCE_REGISTRY'
]