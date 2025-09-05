"""
Configuration Management for Federal Reserve ETL Pipeline

Centralized configuration management with environment variable support,
credential handling, and secure storage patterns for all data sources.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import json
from datetime import datetime

from .utils import (
    ConfigurationError,
    ValidationError,
    get_logger,
    DataSourceConfig,
    APIConfig,
    RateLimitConfig,
    LoggingConfig
)


@dataclass
class FREDConfig:
    """
    Configuration container for FRED API settings
    
    Attributes:
        api_key: FRED API key (from env var FRED_API_KEY)
        base_url: FRED API base URL
        rate_limit: Maximum requests per minute
        timeout: Request timeout in seconds
        retry_config: Retry configuration dictionary
    """
    api_key: Optional[str] = None
    base_url: str = 'https://api.stlouisfed.org/fred'
    rate_limit: int = 120
    timeout: int = 30
    retry_config: Dict[str, Any] = field(default_factory=lambda: {
        'retry_count': 3,
        'retry_delay': 1.0,
        'backoff_factor': 2.0
    })
    
    def __post_init__(self):
        """Load API key from environment if not provided"""
        if not self.api_key:
            self.api_key = os.getenv('FRED_API_KEY')


@dataclass
class HaverConfig:
    """
    Configuration container for Haver Analytics API settings
    
    Attributes:
        username: Haver username (from env var HAVER_USERNAME)
        password: Haver password (from env var HAVER_PASSWORD)
        base_url: Haver API base URL
        rate_limit: Maximum requests per second
        timeout: Request timeout in seconds
        retry_config: Retry configuration dictionary
        default_database: Default database for queries
    """
    username: Optional[str] = None
    password: Optional[str] = None
    base_url: str = 'https://api.haver.com/v1'
    rate_limit: int = 10
    timeout: int = 45
    retry_config: Dict[str, Any] = field(default_factory=lambda: {
        'retry_count': 3,
        'retry_delay': 2.0,
        'backoff_factor': 2.0
    })
    default_database: str = 'USECON'
    
    def __post_init__(self):
        """Load credentials from environment if not provided"""
        if not self.username:
            self.username = os.getenv('HAVER_USERNAME')
        if not self.password:
            self.password = os.getenv('HAVER_PASSWORD')


@dataclass
class PipelineConfig:
    """
    Main pipeline configuration container
    
    Attributes:
        fred: FRED API configuration
        haver: Haver Analytics API configuration
        logging: Logging configuration
        cache_dir: Directory for caching data
        temp_dir: Directory for temporary files
        max_workers: Maximum number of concurrent workers
        default_start_date: Default start date for data retrieval
        output_format: Default output format ('wide' or 'long')
    """
    fred: FREDConfig = field(default_factory=FREDConfig)
    haver: HaverConfig = field(default_factory=HaverConfig)
    logging: LoggingConfig = field(default_factory=lambda: {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_path': None
    })
    cache_dir: str = '.cache/federal_reserve_etl'
    temp_dir: str = '.tmp/federal_reserve_etl'
    max_workers: int = 4
    default_start_date: str = '2000-01-01'
    output_format: str = 'wide'


class ConfigurationManager:
    """
    Central configuration manager for the Federal Reserve ETL pipeline
    
    Handles loading configuration from environment variables, config files,
    and providing validated configuration objects to components.
    
    Attributes:
        config: Main pipeline configuration
        logger: Logger instance
        config_file_paths: List of configuration file paths to check
    
    Examples:
        >>> config_mgr = ConfigurationManager()
        >>> config_mgr.load_config()
        >>> fred_config = config_mgr.get_fred_config()
        >>> if config_mgr.validate_credentials('fred'):
        ...     # Use FRED API
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Optional path to configuration file
        """
        self.logger = get_logger(__name__)
        self.config = PipelineConfig()
        self.config_loaded = False
        
        # Define configuration file search paths
        self.config_file_paths = []
        if config_file:
            self.config_file_paths.append(config_file)
        
        # Add standard configuration file locations
        self.config_file_paths.extend([
            'federal_reserve_etl_config.json',
            os.path.expanduser('~/.federal_reserve_etl/config.json'),
            '/etc/federal_reserve_etl/config.json'
        ])
        
        self.logger.info("Configuration manager initialized")
    
    def load_config(self, force_reload: bool = False) -> None:
        """
        Load configuration from environment variables and config files
        
        Args:
            force_reload: Force reloading even if already loaded
            
        Raises:
            ConfigurationError: If configuration loading fails
        """
        if self.config_loaded and not force_reload:
            return
        
        self.logger.info("Loading configuration...")
        
        try:
            # Load from config files (if available)
            config_data = self._load_from_files()
            
            # Merge with environment variables (env vars take precedence)
            self._load_from_environment(config_data)
            
            # Create directories if needed
            self._ensure_directories()
            
            self.config_loaded = True
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise ConfigurationError(
                f"Configuration loading failed: {str(e)}"
            ) from e
    
    def _load_from_files(self) -> Dict[str, Any]:
        """
        Load configuration from JSON files
        
        Returns:
            Configuration dictionary from files
        """
        config_data = {}
        
        for config_path in self.config_file_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        file_data = json.load(f)
                    
                    # Merge configuration data
                    self._merge_config_data(config_data, file_data)
                    self.logger.info(f"Loaded configuration from {config_path}")
                    break
                    
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.warning(f"Failed to load config from {config_path}: {str(e)}")
                    continue
        
        return config_data
    
    def _load_from_environment(self, base_config: Dict[str, Any]) -> None:
        """
        Load configuration from environment variables
        
        Args:
            base_config: Base configuration to merge with
        """
        # FRED configuration
        fred_config = base_config.get('fred', {})
        if os.getenv('FRED_API_KEY'):
            fred_config['api_key'] = os.getenv('FRED_API_KEY')
        if os.getenv('FRED_BASE_URL'):
            fred_config['base_url'] = os.getenv('FRED_BASE_URL')
        if os.getenv('FRED_RATE_LIMIT'):
            try:
                fred_config['rate_limit'] = int(os.getenv('FRED_RATE_LIMIT'))
            except ValueError:
                self.logger.warning("Invalid FRED_RATE_LIMIT value, using default")
        
        # Haver configuration
        haver_config = base_config.get('haver', {})
        if os.getenv('HAVER_USERNAME'):
            haver_config['username'] = os.getenv('HAVER_USERNAME')
        if os.getenv('HAVER_PASSWORD'):
            haver_config['password'] = os.getenv('HAVER_PASSWORD')
        if os.getenv('HAVER_BASE_URL'):
            haver_config['base_url'] = os.getenv('HAVER_BASE_URL')
        if os.getenv('HAVER_RATE_LIMIT'):
            try:
                haver_config['rate_limit'] = int(os.getenv('HAVER_RATE_LIMIT'))
            except ValueError:
                self.logger.warning("Invalid HAVER_RATE_LIMIT value, using default")
        
        # Pipeline configuration
        if os.getenv('FED_ETL_CACHE_DIR'):
            base_config['cache_dir'] = os.getenv('FED_ETL_CACHE_DIR')
        if os.getenv('FED_ETL_TEMP_DIR'):
            base_config['temp_dir'] = os.getenv('FED_ETL_TEMP_DIR')
        if os.getenv('FED_ETL_MAX_WORKERS'):
            try:
                base_config['max_workers'] = int(os.getenv('FED_ETL_MAX_WORKERS'))
            except ValueError:
                self.logger.warning("Invalid FED_ETL_MAX_WORKERS value, using default")
        
        # Update configuration objects
        if fred_config:
            for key, value in fred_config.items():
                if hasattr(self.config.fred, key):
                    setattr(self.config.fred, key, value)
        
        if haver_config:
            for key, value in haver_config.items():
                if hasattr(self.config.haver, key):
                    setattr(self.config.haver, key, value)
        
        # Update other configuration fields
        for key, value in base_config.items():
            if key not in ['fred', 'haver'] and hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def _merge_config_data(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merge configuration dictionaries
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config_data(target[key], value)
            else:
                target[key] = value
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        dirs_to_create = [self.config.cache_dir, self.config.temp_dir]
        
        for dir_path in dirs_to_create:
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Ensured directory exists: {dir_path}")
            except Exception as e:
                self.logger.warning(f"Failed to create directory {dir_path}: {str(e)}")
    
    def get_fred_config(self) -> FREDConfig:
        """
        Get FRED API configuration
        
        Returns:
            FRED configuration object
            
        Raises:
            ConfigurationError: If configuration not loaded
        """
        if not self.config_loaded:
            self.load_config()
        
        return self.config.fred
    
    def get_haver_config(self) -> HaverConfig:
        """
        Get Haver Analytics API configuration
        
        Returns:
            Haver configuration object
            
        Raises:
            ConfigurationError: If configuration not loaded
        """
        if not self.config_loaded:
            self.load_config()
        
        return self.config.haver
    
    def get_data_source_config(self, source: str) -> DataSourceConfig:
        """
        Get standardized data source configuration
        
        Args:
            source: Data source name ('fred' or 'haver')
            
        Returns:
            Standardized data source configuration
            
        Raises:
            ConfigurationError: If source is not supported
        """
        if not self.config_loaded:
            self.load_config()
        
        source_lower = source.lower()
        
        if source_lower == 'fred':
            fred_config = self.config.fred
            return {
                'source_name': 'FRED',
                'base_url': fred_config.base_url,
                'api_key': fred_config.api_key,
                'rate_limit': fred_config.rate_limit,
                'timeout': fred_config.timeout,
                'retry_config': fred_config.retry_config
            }
        elif source_lower == 'haver':
            haver_config = self.config.haver
            return {
                'source_name': 'Haver',
                'base_url': haver_config.base_url,
                'api_key': None,  # Haver uses username/password
                'rate_limit': haver_config.rate_limit,
                'timeout': haver_config.timeout,
                'retry_config': haver_config.retry_config
            }
        else:
            raise ConfigurationError(f"Unsupported data source: {source}")
    
    def validate_credentials(self, source: str) -> bool:
        """
        Validate credentials for a data source
        
        Args:
            source: Data source name ('fred' or 'haver')
            
        Returns:
            True if credentials are valid
            
        Raises:
            ConfigurationError: If source is not supported
        """
        if not self.config_loaded:
            self.load_config()
        
        source_lower = source.lower()
        
        if source_lower == 'fred':
            return bool(self.config.fred.api_key and len(self.config.fred.api_key) == 32)
        elif source_lower == 'haver':
            return bool(
                self.config.haver.username and 
                self.config.haver.password and
                len(self.config.haver.username) >= 3 and
                len(self.config.haver.password) >= 6
            )
        else:
            raise ConfigurationError(f"Unsupported data source: {source}")
    
    def get_missing_credentials(self, source: str) -> List[str]:
        """
        Get list of missing credentials for a data source
        
        Args:
            source: Data source name ('fred' or 'haver')
            
        Returns:
            List of missing credential names
            
        Raises:
            ConfigurationError: If source is not supported
        """
        if not self.config_loaded:
            self.load_config()
        
        source_lower = source.lower()
        missing = []
        
        if source_lower == 'fred':
            if not self.config.fred.api_key:
                missing.append('FRED_API_KEY')
            elif len(self.config.fred.api_key) != 32:
                missing.append('FRED_API_KEY (invalid format)')
        elif source_lower == 'haver':
            if not self.config.haver.username:
                missing.append('HAVER_USERNAME')
            if not self.config.haver.password:
                missing.append('HAVER_PASSWORD')
        else:
            raise ConfigurationError(f"Unsupported data source: {source}")
        
        return missing
    
    def save_config(self, file_path: str) -> None:
        """
        Save current configuration to file
        
        Args:
            file_path: Path to save configuration file
            
        Raises:
            ConfigurationError: If saving fails
        """
        try:
            config_dict = {
                'fred': {
                    'base_url': self.config.fred.base_url,
                    'rate_limit': self.config.fred.rate_limit,
                    'timeout': self.config.fred.timeout,
                    'retry_config': self.config.fred.retry_config
                    # Note: Don't save sensitive credentials
                },
                'haver': {
                    'base_url': self.config.haver.base_url,
                    'rate_limit': self.config.haver.rate_limit,
                    'timeout': self.config.haver.timeout,
                    'retry_config': self.config.haver.retry_config,
                    'default_database': self.config.haver.default_database
                    # Note: Don't save sensitive credentials
                },
                'cache_dir': self.config.cache_dir,
                'temp_dir': self.config.temp_dir,
                'max_workers': self.config.max_workers,
                'default_start_date': self.config.default_start_date,
                'output_format': self.config.output_format,
                'logging': self.config.logging
            }
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            self.logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {str(e)}") from e
    
    def get_credential_setup_instructions(self) -> Dict[str, str]:
        """
        Get instructions for setting up credentials
        
        Returns:
            Dictionary with setup instructions for each source
        """
        return {
            'fred': '''
FRED API Setup Instructions:
1. Visit https://fred.stlouisfed.org/docs/api/api_key.html
2. Create a free account with FRED
3. Generate your API key
4. Set environment variable: export FRED_API_KEY="your-32-character-api-key"
5. Or add to your ~/.bashrc or ~/.zshrc for persistence
''',
            'haver': '''
Haver Analytics Setup Instructions:
1. Contact Haver Analytics to obtain subscription credentials
2. Set environment variables:
   export HAVER_USERNAME="your-username"
   export HAVER_PASSWORD="your-password"
3. Or add to your ~/.bashrc or ~/.zshrc for persistence
'''
        }


# Global configuration manager instance
_global_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """
    Get global configuration manager instance (singleton pattern)
    
    Returns:
        Global configuration manager instance
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigurationManager()
        _global_config_manager.load_config()
    
    return _global_config_manager


def reset_config_manager() -> None:
    """Reset global configuration manager (useful for testing)"""
    global _global_config_manager
    _global_config_manager = None


# Convenience functions for common operations

def get_fred_config() -> FREDConfig:
    """Get FRED configuration from global manager"""
    return get_config_manager().get_fred_config()


def get_haver_config() -> HaverConfig:
    """Get Haver configuration from global manager"""
    return get_config_manager().get_haver_config()


def validate_source_credentials(source: str) -> bool:
    """Validate credentials for a data source"""
    return get_config_manager().validate_credentials(source)


def get_setup_instructions() -> Dict[str, str]:
    """Get credential setup instructions"""
    return get_config_manager().get_credential_setup_instructions()