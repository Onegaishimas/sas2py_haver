# Technical Implementation Document: Configuration Management System

## 1. Implementation Strategy

### Development Approach
**Methodology**: Configuration-first design with singleton pattern and hierarchical precedence
**Order of Implementation**: Type definitions → Configuration classes → Validation → Singleton manager → Integration
**Integration Strategy**: Centralized configuration injection through dependency patterns
**Risk Mitigation**: Fail-fast validation with clear setup guidance and fallback defaults

### Coding Patterns
**Design Patterns**: Singleton Pattern, Dataclass Pattern, Factory Pattern for data source configs
**Code Organization**: Single config.py module with specialized configuration classes
**Naming Conventions**: Config classes end with "Config", environment variables use UPPER_SNAKE_CASE
**Documentation Standards**: Google-style docstrings with setup examples and validation explanations

## 2. Code Structure

### Directory Structure
```
src/federal_reserve_etl/
├── config.py                    # Main configuration management system
└── utils/
    └── type_definitions.py      # Configuration type definitions and schemas
```

### Key Class Definitions

#### Singleton Configuration Manager
```python
# config.py
import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .utils.exceptions import ConfigurationError
from .utils.type_definitions import DataSourceConfigDict

class ConfigurationManager:
    """
    Singleton configuration manager with multi-source support.
    
    Features:
    - Hierarchical configuration precedence (env > file > defaults)
    - Lazy initialization with caching
    - Comprehensive validation with setup guidance
    - Thread-safe singleton implementation
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logger = logging.getLogger(__name__)
        self._config_cache = {}
        self._validation_results = {}
        self._config_sources = self._discover_config_sources()
        self._initialized = True
        
        # Initialize configuration on first access
        self._load_all_configurations()
    
    def _discover_config_sources(self) -> List[Path]:
        """Discover available configuration file sources"""
        config_paths = [
            Path.cwd() / "config" / "settings.json",
            Path.cwd() / "federal_reserve_etl.json",
            Path.home() / ".federal_reserve_etl" / "config.json",
            Path("/etc/federal_reserve_etl/config.json")
        ]
        
        # Filter to existing files
        existing_paths = [p for p in config_paths if p.exists() and p.is_file()]
        
        if existing_paths:
            self.logger.info(f"Found configuration files: {[str(p) for p in existing_paths]}")
        
        return existing_paths
    
    def _load_all_configurations(self):
        """Load all configuration types during initialization"""
        try:
            # Pre-load all configuration types to catch errors early
            self.get_fred_config()
            self.get_haver_config()
            self.get_logging_config()
            self.get_cache_config()
            
            self.logger.info("All configurations loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configurations during initialization: {e}")
            # Don't raise here - let individual config access handle errors
    
    def get_fred_config(self) -> 'FREDConfig':
        """Get FRED API configuration with validation"""
        if 'fred' not in self._config_cache:
            self._config_cache['fred'] = self._create_fred_config()
        return self._config_cache['fred']
    
    def get_haver_config(self) -> 'HaverConfig':
        """Get Haver Analytics configuration with validation"""
        if 'haver' not in self._config_cache:
            self._config_cache['haver'] = self._create_haver_config()
        return self._config_cache['haver']
    
    def get_logging_config(self) -> 'LoggingConfig':
        """Get logging system configuration"""
        if 'logging' not in self._config_cache:
            self._config_cache['logging'] = self._create_logging_config()
        return self._config_cache['logging']
    
    def get_cache_config(self) -> 'CacheConfig':
        """Get cache and temporary file configuration"""
        if 'cache' not in self._config_cache:
            self._config_cache['cache'] = self._create_cache_config()
        return self._config_cache['cache']
    
    def _create_fred_config(self) -> 'FREDConfig':
        """Create FRED configuration with multi-source loading"""
        # Environment variables (highest priority)
        env_config = {
            'api_key': os.getenv('FRED_API_KEY', ''),
            'base_url': os.getenv('FRED_BASE_URL', ''),
            'rate_limit_per_minute': int(os.getenv('FRED_RATE_LIMIT', '0')),
            'timeout_seconds': int(os.getenv('FRED_TIMEOUT', '0')),
            'max_retries': int(os.getenv('FRED_MAX_RETRIES', '0'))
        }
        
        # Configuration file values (medium priority)
        file_config = self._load_from_config_files(['fred', 'api_endpoints'])
        
        # Default values (lowest priority)
        default_config = {
            'api_key': '',
            'base_url': 'https://api.stlouisfed.org/fred',
            'rate_limit_per_minute': 120,
            'timeout_seconds': 30,
            'max_retries': 3
        }
        
        # Merge configurations (env overrides file overrides defaults)
        merged_config = {**default_config, **file_config, **{k: v for k, v in env_config.items() if v}}
        
        # Create and validate configuration
        fred_config = FREDConfig(**merged_config)
        self._validate_fred_config(fred_config)
        
        return fred_config
    
    def _create_haver_config(self) -> 'HaverConfig':
        """Create Haver Analytics configuration with multi-source loading"""
        # Environment variables (highest priority)
        env_config = {
            'username': os.getenv('HAVER_USERNAME', ''),
            'password': os.getenv('HAVER_PASSWORD', ''),
            'server_url': os.getenv('HAVER_SERVER', ''),
            'database': os.getenv('HAVER_DATABASE', ''),
            'rate_limit_per_second': int(os.getenv('HAVER_RATE_LIMIT', '0')),
            'connection_timeout': int(os.getenv('HAVER_TIMEOUT', '0'))
        }
        
        # Configuration file values
        file_config = self._load_from_config_files(['haver', 'api_endpoints'])
        
        # Default values
        default_config = {
            'username': '',
            'password': '',
            'server_url': 'https://api.haver.com',
            'database': 'DLX',
            'rate_limit_per_second': 10,
            'connection_timeout': 60
        }
        
        # Merge configurations
        merged_config = {**default_config, **file_config, **{k: v for k, v in env_config.items() if v}}
        
        # Create and validate configuration
        haver_config = HaverConfig(**merged_config)
        self._validate_haver_config(haver_config)
        
        return haver_config
    
    def _load_from_config_files(self, config_path: List[str]) -> Dict[str, Any]:
        """Load configuration values from JSON files"""
        result = {}
        
        for config_file in self._config_sources:
            try:
                with open(config_file, 'r') as f:
                    file_data = json.load(f)
                
                # Navigate nested configuration path
                current_data = file_data
                for path_segment in config_path:
                    if isinstance(current_data, dict) and path_segment in current_data:
                        current_data = current_data[path_segment]
                    else:
                        current_data = {}
                        break
                
                if isinstance(current_data, dict):
                    result.update(current_data)
                    self.logger.debug(f"Loaded config from {config_file}: {list(current_data.keys())}")
                
            except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
                self.logger.warning(f"Could not load config from {config_file}: {e}")
        
        return result
    
    def _validate_fred_config(self, config: 'FREDConfig') -> None:
        """Validate FRED configuration with detailed error reporting"""
        missing_configs = []
        validation_errors = []
        
        # Required field validation
        if not config.api_key:
            missing_configs.append('FRED_API_KEY')
        elif len(config.api_key) != 32:
            validation_errors.append(f"FRED API key must be exactly 32 characters (got {len(config.api_key)})")
        
        if not config.base_url:
            missing_configs.append('FRED_BASE_URL')
        elif not config.base_url.startswith(('http://', 'https://')):
            validation_errors.append("FRED base URL must start with http:// or https://")
        
        # Range validation
        if config.rate_limit_per_minute <= 0:
            validation_errors.append("FRED rate limit must be greater than 0")
        elif config.rate_limit_per_minute > 1000:
            validation_errors.append("FRED rate limit seems too high (>1000/min)")
        
        if config.timeout_seconds <= 0:
            validation_errors.append("FRED timeout must be greater than 0")
        elif config.timeout_seconds > 300:
            validation_errors.append("FRED timeout seems too high (>300s)")
        
        # Report errors
        if missing_configs:
            raise ConfigurationError(
                f"Missing required FRED configuration: {', '.join(missing_configs)}",
                missing_config=missing_configs,
                suggestion=self._get_fred_setup_guidance()
            )
        
        if validation_errors:
            raise ConfigurationError(
                f"FRED configuration validation failed: {'; '.join(validation_errors)}",
                context={'validation_errors': validation_errors},
                suggestion="Check your FRED configuration values"
            )
        
        # Store validation result
        self._validation_results['fred'] = {
            'status': 'valid',
            'timestamp': time.time(),
            'config_source': self._get_config_source_summary('fred')
        }
    
    def _get_fred_setup_guidance(self) -> str:
        """Get setup guidance for FRED configuration"""
        return """
FRED API Setup Guide:
1. Register for a FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html
2. Set the environment variable: export FRED_API_KEY='your_32_character_key'
3. Optionally set: export FRED_BASE_URL='https://api.stlouisfed.org/fred'
4. Restart the application to load the new configuration

Example:
export FRED_API_KEY='abcd1234efgh5678ijkl9012mnop3456'
export FRED_RATE_LIMIT=120
export FRED_TIMEOUT=30
        """.strip()
    
    def validate_all_configurations(self) -> Dict[str, Any]:
        """Validate all configurations and return comprehensive report"""
        validation_report = {
            'overall_status': 'unknown',
            'timestamp': time.time(),
            'configurations': {}
        }
        
        config_types = ['fred', 'haver', 'logging', 'cache']
        all_valid = True
        
        for config_type in config_types:
            try:
                if config_type == 'fred':
                    self.get_fred_config()
                elif config_type == 'haver':
                    self.get_haver_config()
                elif config_type == 'logging':
                    self.get_logging_config()
                elif config_type == 'cache':
                    self.get_cache_config()
                
                validation_report['configurations'][config_type] = {
                    'status': 'valid',
                    'source': self._get_config_source_summary(config_type)
                }
                
            except ConfigurationError as e:
                all_valid = False
                validation_report['configurations'][config_type] = {
                    'status': 'invalid',
                    'error': str(e),
                    'suggestion': e.suggestion,
                    'missing_config': getattr(e, 'missing_config', [])
                }
            except Exception as e:
                all_valid = False
                validation_report['configurations'][config_type] = {
                    'status': 'error',
                    'error': f"Unexpected error: {str(e)}"
                }
        
        validation_report['overall_status'] = 'valid' if all_valid else 'invalid'
        
        return validation_report
    
    def _get_config_source_summary(self, config_type: str) -> Dict[str, Any]:
        """Get summary of configuration sources for a specific config type"""
        return {
            'environment_variables': self._get_env_vars_for_type(config_type),
            'config_files': [str(p) for p in self._config_sources],
            'defaults_used': True  # Always true since we have defaults
        }
    
    def _get_env_vars_for_type(self, config_type: str) -> List[str]:
        """Get list of environment variables for configuration type"""
        env_var_map = {
            'fred': ['FRED_API_KEY', 'FRED_BASE_URL', 'FRED_RATE_LIMIT', 'FRED_TIMEOUT', 'FRED_MAX_RETRIES'],
            'haver': ['HAVER_USERNAME', 'HAVER_PASSWORD', 'HAVER_SERVER', 'HAVER_DATABASE', 'HAVER_RATE_LIMIT', 'HAVER_TIMEOUT'],
            'logging': ['ETL_LOG_LEVEL', 'ETL_LOG_FILE', 'ETL_LOG_FORMAT'],
            'cache': ['ETL_CACHE_DIR', 'ETL_CACHE_SIZE', 'ETL_TEMP_DIR']
        }
        
        env_vars = env_var_map.get(config_type, [])
        return [var for var in env_vars if os.getenv(var)]

@dataclass
class FREDConfig:
    """
    FRED API configuration with validation and connection testing.
    
    Environment Variables:
    - FRED_API_KEY: Required 32-character API key
    - FRED_BASE_URL: API base URL (default: https://api.stlouisfed.org/fred)
    - FRED_RATE_LIMIT: Requests per minute (default: 120)
    - FRED_TIMEOUT: Request timeout in seconds (default: 30)
    - FRED_MAX_RETRIES: Maximum retry attempts (default: 3)
    """
    
    api_key: str
    base_url: str = "https://api.stlouisfed.org/fred"
    rate_limit_per_minute: int = 120
    timeout_seconds: int = 30
    max_retries: int = 3
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Ensure base_url doesn't end with slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url.rstrip('/')
    
    def validate_credentials(self) -> bool:
        """
        Test FRED API credentials with actual API call.
        
        Returns:
            bool: True if credentials are valid
            
        Raises:
            AuthenticationError: If credentials are invalid
            ConnectionError: If API is unreachable
        """
        import requests
        from .utils.exceptions import AuthenticationError, ConnectionError
        
        try:
            response = requests.get(
                f"{self.base_url}/series/categories",
                params={'api_key': self.api_key, 'file_type': 'json', 'limit': 1},
                timeout=self.timeout_seconds
            )
            
            if response.status_code == 400:
                raise AuthenticationError("FRED API key is invalid", api_source="FRED")
            elif response.status_code == 403:
                raise AuthenticationError("FRED API key access denied", api_source="FRED")
            elif response.status_code != 200:
                raise ConnectionError(f"FRED API returned status {response.status_code}")
            
            return True
            
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to FRED API: {str(e)}")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get parameters for FRED API client initialization"""
        return {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'timeout': self.timeout_seconds,
            'rate_limit': self.rate_limit_per_minute,
            'max_retries': self.max_retries
        }

@dataclass
class HaverConfig:
    """
    Haver Analytics configuration with validation and connection testing.
    
    Environment Variables:
    - HAVER_USERNAME: Required username for Haver account
    - HAVER_PASSWORD: Required password for Haver account
    - HAVER_SERVER: Server URL (default: https://api.haver.com)
    - HAVER_DATABASE: Database name (default: DLX)
    - HAVER_RATE_LIMIT: Requests per second (default: 10)
    - HAVER_TIMEOUT: Connection timeout in seconds (default: 60)
    """
    
    username: str
    password: str
    server_url: str = "https://api.haver.com"
    database: str = "DLX"
    rate_limit_per_second: int = 10
    connection_timeout: int = 60
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Ensure server_url doesn't end with slash
        if self.server_url.endswith('/'):
            self.server_url = self.server_url.rstrip('/')
    
    def validate_credentials(self) -> bool:
        """
        Test Haver Analytics credentials with actual connection.
        
        Returns:
            bool: True if credentials are valid
            
        Raises:
            AuthenticationError: If credentials are invalid
            ConnectionError: If server is unreachable
        """
        # Note: Actual implementation would depend on Haver API specifics
        # This is a placeholder implementation
        import requests
        from .utils.exceptions import AuthenticationError, ConnectionError
        
        try:
            # Placeholder: Haver-specific authentication test
            response = requests.post(
                f"{self.server_url}/auth",
                json={'username': self.username, 'password': self.password},
                timeout=self.connection_timeout
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Haver Analytics credentials invalid", api_source="HAVER")
            elif response.status_code != 200:
                raise ConnectionError(f"Haver server returned status {response.status_code}")
            
            return True
            
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to Haver server: {str(e)}")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get parameters for Haver API client initialization"""
        return {
            'username': self.username,
            'password': self.password,
            'server_url': self.server_url,
            'database': self.database,
            'timeout': self.connection_timeout,
            'rate_limit': self.rate_limit_per_second
        }

@dataclass
class LoggingConfig:
    """
    Logging system configuration.
    
    Environment Variables:
    - ETL_LOG_LEVEL: Logging level (default: INFO)
    - ETL_LOG_FILE: Log file path (optional)
    - ETL_LOG_FORMAT: Log format - 'json' or 'text' (default: text)
    - ETL_LOG_MAX_SIZE: Maximum log file size (default: 100MB)
    - ETL_LOG_BACKUP_COUNT: Number of backup files (default: 5)
    """
    
    level: str = "INFO"
    file_path: Optional[str] = None
    format_type: str = "text"  # 'json' or 'text'
    max_file_size: str = "100MB"
    backup_count: int = 5
    console_output: bool = True
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Load from environment variables
        self.level = os.getenv('ETL_LOG_LEVEL', self.level).upper()
        self.file_path = os.getenv('ETL_LOG_FILE', self.file_path)
        self.format_type = os.getenv('ETL_LOG_FORMAT', self.format_type).lower()
        self.max_file_size = os.getenv('ETL_LOG_MAX_SIZE', self.max_file_size)
        self.backup_count = int(os.getenv('ETL_LOG_BACKUP_COUNT', str(self.backup_count)))
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.level not in valid_levels:
            raise ConfigurationError(
                f"Invalid log level '{self.level}'. Must be one of: {', '.join(valid_levels)}",
                suggestion=f"Set ETL_LOG_LEVEL to one of: {', '.join(valid_levels)}"
            )
        
        # Validate format type
        valid_formats = ['json', 'text']
        if self.format_type not in valid_formats:
            raise ConfigurationError(
                f"Invalid log format '{self.format_type}'. Must be one of: {', '.join(valid_formats)}",
                suggestion=f"Set ETL_LOG_FORMAT to one of: {', '.join(valid_formats)}"
            )

@dataclass
class CacheConfig:
    """
    Cache and temporary file configuration.
    
    Environment Variables:
    - ETL_CACHE_DIR: Cache directory path (default: ~/.federal_reserve_etl/cache)
    - ETL_TEMP_DIR: Temporary files directory (default: ~/.federal_reserve_etl/temp)
    - ETL_CACHE_MAX_SIZE: Maximum cache size in MB (default: 1000)
    - ETL_CACHE_TTL: Default cache TTL in seconds (default: 3600)
    """
    
    cache_dir: str = field(default_factory=lambda: str(Path.home() / ".federal_reserve_etl" / "cache"))
    temp_dir: str = field(default_factory=lambda: str(Path.home() / ".federal_reserve_etl" / "temp"))
    max_size_mb: int = 1000
    default_ttl_seconds: int = 3600
    
    def __post_init__(self):
        """Post-initialization validation and directory creation"""
        # Load from environment variables
        self.cache_dir = os.getenv('ETL_CACHE_DIR', self.cache_dir)
        self.temp_dir = os.getenv('ETL_TEMP_DIR', self.temp_dir)
        self.max_size_mb = int(os.getenv('ETL_CACHE_MAX_SIZE', str(self.max_size_mb)))
        self.default_ttl_seconds = int(os.getenv('ETL_CACHE_TTL', str(self.default_ttl_seconds)))
        
        # Expand user paths
        self.cache_dir = str(Path(self.cache_dir).expanduser().resolve())
        self.temp_dir = str(Path(self.temp_dir).expanduser().resolve())
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create cache and temp directories if they don't exist"""
        for directory in [self.cache_dir, self.temp_dir]:
            dir_path = Path(directory)
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                
                # Test write permissions
                test_file = dir_path / ".write_test"
                test_file.touch()
                test_file.unlink()
                
            except (PermissionError, OSError) as e:
                raise ConfigurationError(
                    f"Cannot create or write to directory '{directory}': {e}",
                    context={'directory': directory, 'error': str(e)},
                    suggestion=f"Check permissions or set alternative directory with ETL_CACHE_DIR/ETL_TEMP_DIR"
                )

# Global configuration manager instance
def get_config_manager() -> ConfigurationManager:
    """Get singleton configuration manager instance"""
    return ConfigurationManager()
```

## 3. Key Algorithms

### Configuration Precedence Resolution
```python
def resolve_configuration_value(env_var: str, file_path: List[str], default_value: Any) -> Any:
    """
    Resolve configuration value using hierarchical precedence.
    
    Algorithm: Environment Variable → Config File → Default Value
    Time Complexity: O(n) where n is number of config files
    Space Complexity: O(1)
    """
    # Highest priority: Environment variable
    env_value = os.getenv(env_var)
    if env_value is not None:
        return convert_env_value(env_value, type(default_value))
    
    # Medium priority: Configuration files (in order)
    for config_source in get_config_sources():
        file_value = get_nested_config_value(config_source, file_path)
        if file_value is not None:
            return file_value
    
    # Lowest priority: Default value
    return default_value

def convert_env_value(env_value: str, target_type: type) -> Any:
    """Convert environment variable string to target type"""
    if target_type == bool:
        return env_value.lower() in ('true', '1', 'yes', 'on')
    elif target_type == int:
        return int(env_value)
    elif target_type == float:
        return float(env_value)
    else:
        return env_value

def get_nested_config_value(config_data: Dict[str, Any], path: List[str]) -> Any:
    """Navigate nested configuration structure using path"""
    current_data = config_data
    for path_segment in path:
        if isinstance(current_data, dict) and path_segment in current_data:
            current_data = current_data[path_segment]
        else:
            return None
    return current_data
```

### Configuration Validation Pipeline
```python
class ConfigurationValidator:
    """
    Configuration validation with detailed error reporting.
    """
    
    def __init__(self):
        self.validation_rules = {}
        self.setup_validation_rules()
    
    def setup_validation_rules(self):
        """Setup validation rules for different configuration types"""
        self.validation_rules = {
            'fred': {
                'api_key': {
                    'required': True,
                    'type': str,
                    'length': 32,
                    'pattern': r'^[a-fA-F0-9]{32}$'
                },
                'base_url': {
                    'required': True,
                    'type': str,
                    'pattern': r'^https?://.+'
                },
                'rate_limit_per_minute': {
                    'required': True,
                    'type': int,
                    'min': 1,
                    'max': 1000
                }
            },
            'haver': {
                'username': {
                    'required': True,
                    'type': str,
                    'min_length': 3
                },
                'password': {
                    'required': True,
                    'type': str,
                    'min_length': 8
                }
            }
        }
    
    def validate_configuration(self, config_type: str, config_data: Dict[str, Any]) -> List[str]:
        """
        Validate configuration data against rules.
        
        Returns:
            List of validation error messages
        """
        rules = self.validation_rules.get(config_type, {})
        errors = []
        
        for field_name, rule in rules.items():
            value = config_data.get(field_name)
            field_errors = self._validate_field(field_name, value, rule)
            errors.extend(field_errors)
        
        return errors
    
    def _validate_field(self, field_name: str, value: Any, rule: Dict[str, Any]) -> List[str]:
        """Validate individual field against rule"""
        errors = []
        
        # Required field check
        if rule.get('required', False) and (value is None or value == ''):
            errors.append(f"{field_name} is required")
            return errors  # Skip other validations if required field is missing
        
        if value is None or value == '':
            return errors  # Skip validations for optional empty fields
        
        # Type validation
        expected_type = rule.get('type')
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"{field_name} must be of type {expected_type.__name__}")
            return errors  # Skip other validations if type is wrong
        
        # String validations
        if isinstance(value, str):
            # Length validation
            if 'length' in rule and len(value) != rule['length']:
                errors.append(f"{field_name} must be exactly {rule['length']} characters")
            
            if 'min_length' in rule and len(value) < rule['min_length']:
                errors.append(f"{field_name} must be at least {rule['min_length']} characters")
            
            if 'max_length' in rule and len(value) > rule['max_length']:
                errors.append(f"{field_name} must be at most {rule['max_length']} characters")
            
            # Pattern validation
            if 'pattern' in rule:
                import re
                if not re.match(rule['pattern'], value):
                    errors.append(f"{field_name} format is invalid")
        
        # Numeric validations
        if isinstance(value, (int, float)):
            if 'min' in rule and value < rule['min']:
                errors.append(f"{field_name} must be at least {rule['min']}")
            
            if 'max' in rule and value > rule['max']:
                errors.append(f"{field_name} must be at most {rule['max']}")
        
        return errors
```

## 4. Integration Points

### Data Source Factory Integration
```python
# data_sources/__init__.py
from typing import Union
from ..config import get_config_manager
from .fred_client import FREDDataSource
from .haver_client import HaverDataSource

def create_data_source(source_type: str) -> Union[FREDDataSource, HaverDataSource]:
    """
    Factory function for creating data sources with automatic configuration injection.
    
    Args:
        source_type: Type of data source ('fred' or 'haver')
        
    Returns:
        Configured data source instance
        
    Raises:
        ConfigurationError: If configuration is invalid
        ValueError: If source_type is not supported
    """
    config_manager = get_config_manager()
    
    if source_type.lower() == 'fred':
        fred_config = config_manager.get_fred_config()
        return FREDDataSource(fred_config)
    
    elif source_type.lower() == 'haver':
        haver_config = config_manager.get_haver_config()
        return HaverDataSource(haver_config)
    
    else:
        raise ValueError(f"Unsupported data source type: {source_type}")

# Usage in data source clients
# data_sources/fred_client.py
class FREDDataSource(DataSource):
    def __init__(self, config: FREDConfig):
        self.config = config
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.rate_limit = config.rate_limit_per_minute
        self.timeout = config.timeout_seconds
        self.max_retries = config.max_retries
        
        # Validate configuration on initialization
        if not self.api_key:
            raise ConfigurationError(
                "FRED API key is required",
                missing_config=['FRED_API_KEY'],
                suggestion="Set FRED_API_KEY environment variable"
            )
```

### Error Handling Integration
```python
# utils/error_handling.py - Configuration integration
from ..config import get_config_manager

def get_error_handling_config() -> Dict[str, Any]:
    """Get error handling configuration from central config"""
    config_manager = get_config_manager()
    
    # Get error handling specific environment variables
    return {
        'max_retries': int(os.getenv('ETL_MAX_RETRIES', '3')),
        'backoff_base': float(os.getenv('ETL_BACKOFF_BASE', '1.0')),
        'backoff_max': float(os.getenv('ETL_BACKOFF_MAX', '60.0')),
        'enable_error_details': os.getenv('ETL_ERROR_DETAILS', 'true').lower() == 'true'
    }

# Updated decorator with configuration integration
def handle_api_errors(max_retries: Optional[int] = None,
                     backoff_base: Optional[float] = None,
                     **kwargs):
    """Handle API errors with configuration defaults"""
    
    # Get configuration if parameters not provided
    if max_retries is None or backoff_base is None:
        error_config = get_error_handling_config()
        max_retries = max_retries or error_config['max_retries']
        backoff_base = backoff_base or error_config['backoff_base']
    
    # Rest of decorator implementation...
```

### Logging System Integration
```python
# utils/logging.py - Configuration integration
from ..config import get_config_manager

def setup_logging_from_config() -> logging.Logger:
    """Setup logging system using central configuration"""
    config_manager = get_config_manager()
    logging_config = config_manager.get_logging_config()
    
    # Configure logging based on configuration
    return setup_logging(
        log_level=logging_config.level,
        log_file=logging_config.file_path,
        enable_console=logging_config.console_output,
        structured_format=(logging_config.format_type == 'json'),
        max_file_size=logging_config.max_file_size,
        backup_count=logging_config.backup_count
    )

# Automatic logging setup
def get_logger(name: str) -> logging.Logger:
    """Get logger with automatic configuration setup"""
    # Ensure logging is configured
    if not logging.getLogger().handlers:
        setup_logging_from_config()
    
    return logging.getLogger(name)
```

## 5. Configuration

### Environment Variable Schema
```python
# Configuration environment variables with validation
ENVIRONMENT_SCHEMA = {
    # FRED Configuration
    'FRED_API_KEY': {
        'required': True,
        'type': 'string',
        'length': 32,
        'pattern': r'^[a-fA-F0-9]{32}$',
        'description': 'FRED API key from https://fred.stlouisfed.org',
        'example': 'abcd1234efgh5678ijkl9012mnop3456'
    },
    'FRED_BASE_URL': {
        'required': False,
        'type': 'string',
        'default': 'https://api.stlouisfed.org/fred',
        'pattern': r'^https?://.+',
        'description': 'FRED API base URL'
    },
    'FRED_RATE_LIMIT': {
        'required': False,
        'type': 'integer',
        'default': 120,
        'min': 1,
        'max': 1000,
        'description': 'Maximum requests per minute for FRED API'
    },
    
    # Haver Configuration
    'HAVER_USERNAME': {
        'required': True,
        'type': 'string',
        'min_length': 3,
        'description': 'Haver Analytics username'
    },
    'HAVER_PASSWORD': {
        'required': True,
        'type': 'string',
        'min_length': 8,
        'description': 'Haver Analytics password',
        'sensitive': True
    },
    
    # System Configuration
    'ETL_LOG_LEVEL': {
        'required': False,
        'type': 'string',
        'default': 'INFO',
        'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        'description': 'Logging level for the ETL system'
    },
    'ETL_CACHE_DIR': {
        'required': False,
        'type': 'string',
        'default': '~/.federal_reserve_etl/cache',
        'description': 'Directory for caching data files'
    }
}

def generate_env_template() -> str:
    """Generate environment variable template file"""
    template_lines = [
        "# Federal Reserve ETL Pipeline Configuration",
        "# Copy this file to .env and set your values",
        ""
    ]
    
    for var_name, schema in ENVIRONMENT_SCHEMA.items():
        # Add description as comment
        template_lines.append(f"# {schema['description']}")
        
        # Add example if available
        if 'example' in schema:
            template_lines.append(f"# Example: {schema['example']}")
        
        # Add variable with default or placeholder
        if schema.get('sensitive', False):
            template_lines.append(f"# {var_name}=your_{var_name.lower()}_here")
        elif 'default' in schema:
            template_lines.append(f"# {var_name}={schema['default']}")
        else:
            template_lines.append(f"{var_name}=")
        
        template_lines.append("")
    
    return "\n".join(template_lines)
```

### Configuration File Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Federal Reserve ETL Configuration",
  "type": "object",
  "properties": {
    "fred": {
      "type": "object",
      "properties": {
        "base_url": {
          "type": "string",
          "format": "uri",
          "default": "https://api.stlouisfed.org/fred"
        },
        "rate_limit_per_minute": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000,
          "default": 120
        },
        "timeout_seconds": {
          "type": "integer",
          "minimum": 1,
          "maximum": 300,
          "default": 30
        },
        "max_retries": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10,
          "default": 3
        }
      }
    },
    "haver": {
      "type": "object",
      "properties": {
        "server_url": {
          "type": "string",
          "format": "uri",
          "default": "https://api.haver.com"
        },
        "database": {
          "type": "string",
          "default": "DLX"
        },
        "rate_limit_per_second": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 10
        },
        "connection_timeout": {
          "type": "integer",
          "minimum": 1,
          "maximum": 300,
          "default": 60
        }
      }
    },
    "logging": {
      "type": "object",
      "properties": {
        "level": {
          "type": "string",
          "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
          "default": "INFO"
        },
        "format": {
          "type": "string",
          "enum": ["json", "text"],
          "default": "text"
        },
        "file_path": {
          "type": "string"
        },
        "max_file_size": {
          "type": "string",
          "pattern": "^[0-9]+(KB|MB|GB)$",
          "default": "100MB"
        },
        "backup_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 50,
          "default": 5
        }
      }
    },
    "cache": {
      "type": "object",
      "properties": {
        "cache_dir": {
          "type": "string"
        },
        "temp_dir": {
          "type": "string"
        },
        "max_size_mb": {
          "type": "integer",
          "minimum": 10,
          "maximum": 10000,
          "default": 1000
        },
        "default_ttl_seconds": {
          "type": "integer",
          "minimum": 60,
          "maximum": 86400,
          "default": 3600
        }
      }
    }
  }
}
```

## 6. Testing Implementation

### Configuration Testing Framework
```python
# tests/unit/test_configuration.py
import pytest
import os
import tempfile
import json
from unittest.mock import patch, mock_open
from pathlib import Path

from src.federal_reserve_etl.config import ConfigurationManager, FREDConfig, HaverConfig
from src.federal_reserve_etl.utils.exceptions import ConfigurationError

class TestConfigurationManager:
    
    @pytest.fixture
    def clean_environment(self):
        """Fixture to provide clean environment for testing"""
        # Store original environment
        original_env = dict(os.environ)
        
        # Clear configuration-related environment variables
        config_vars = [
            'FRED_API_KEY', 'FRED_BASE_URL', 'FRED_RATE_LIMIT',
            'HAVER_USERNAME', 'HAVER_PASSWORD', 'HAVER_SERVER',
            'ETL_LOG_LEVEL', 'ETL_CACHE_DIR'
        ]
        
        for var in config_vars:
            os.environ.pop(var, None)
        
        yield
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
    
    @pytest.fixture
    def temp_config_file(self):
        """Fixture to create temporary configuration file"""
        config_data = {
            "fred": {
                "base_url": "https://api.stlouisfed.org/fred",
                "rate_limit_per_minute": 100,
                "timeout_seconds": 25
            },
            "haver": {
                "server_url": "https://api.haver.com",
                "database": "DLX"
            },
            "logging": {
                "level": "DEBUG",
                "format": "json"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file_path = f.name
        
        yield config_file_path
        
        # Cleanup
        Path(config_file_path).unlink()
    
    def test_singleton_pattern(self, clean_environment):
        """Test that ConfigurationManager follows singleton pattern"""
        manager1 = ConfigurationManager()
        manager2 = ConfigurationManager()
        
        assert manager1 is manager2
    
    def test_environment_variable_precedence(self, clean_environment):
        """Test that environment variables take precedence over config files"""
        # Set environment variables
        os.environ['FRED_API_KEY'] = 'env_api_key_12345678901234567890'
        os.environ['FRED_RATE_LIMIT'] = '150'
        
        manager = ConfigurationManager()
        fred_config = manager.get_fred_config()
        
        assert fred_config.api_key == 'env_api_key_12345678901234567890'
        assert fred_config.rate_limit_per_minute == 150
    
    def test_config_file_loading(self, clean_environment, temp_config_file):
        """Test configuration loading from JSON files"""
        # Mock config file discovery to return our temp file
        with patch.object(ConfigurationManager, '_discover_config_sources') as mock_discovery:
            mock_discovery.return_value = [Path(temp_config_file)]
            
            # Set required environment variables
            os.environ['FRED_API_KEY'] = 'test_api_key_123456789012345678901'
            os.environ['HAVER_USERNAME'] = 'test_user'
            os.environ['HAVER_PASSWORD'] = 'test_password'
            
            manager = ConfigurationManager()
            fred_config = manager.get_fred_config()
            
            # Should use values from config file
            assert fred_config.rate_limit_per_minute == 100  # From config file
            assert fred_config.timeout_seconds == 25  # From config file
    
    def test_missing_required_configuration(self, clean_environment):
        """Test error handling for missing required configuration"""
        manager = ConfigurationManager()
        
        with pytest.raises(ConfigurationError) as exc_info:
            manager.get_fred_config()
        
        error = exc_info.value
        assert 'FRED_API_KEY' in str(error)
        assert error.missing_config == ['FRED_API_KEY']
        assert error.suggestion is not None
    
    def test_configuration_validation(self, clean_environment):
        """Test configuration validation with invalid values"""
        # Set invalid API key (wrong length)
        os.environ['FRED_API_KEY'] = 'short_key'
        
        manager = ConfigurationManager()
        
        with pytest.raises(ConfigurationError) as exc_info:
            manager.get_fred_config()
        
        error = exc_info.value
        assert "32 characters" in str(error)
    
    def test_validate_all_configurations(self, clean_environment):
        """Test comprehensive configuration validation"""
        # Set minimal required configuration
        os.environ['FRED_API_KEY'] = 'abcd1234efgh5678ijkl9012mnop3456'
        os.environ['HAVER_USERNAME'] = 'test_user'
        os.environ['HAVER_PASSWORD'] = 'test_password123'
        
        manager = ConfigurationManager()
        validation_report = manager.validate_all_configurations()
        
        assert validation_report['overall_status'] == 'valid'
        assert 'fred' in validation_report['configurations']
        assert 'haver' in validation_report['configurations']
        assert validation_report['configurations']['fred']['status'] == 'valid'

class TestFREDConfig:
    
    def test_valid_fred_config_creation(self):
        """Test creation of valid FRED configuration"""
        config = FREDConfig(
            api_key='abcd1234efgh5678ijkl9012mnop3456',
            base_url='https://api.stlouisfed.org/fred',
            rate_limit_per_minute=120
        )
        
        assert config.api_key == 'abcd1234efgh5678ijkl9012mnop3456'
        assert config.base_url == 'https://api.stlouisfed.org/fred'
        assert config.rate_limit_per_minute == 120
    
    def test_base_url_normalization(self):
        """Test that base URL is normalized (trailing slash removal)"""
        config = FREDConfig(
            api_key='abcd1234efgh5678ijkl9012mnop3456',
            base_url='https://api.stlouisfed.org/fred/'  # Note trailing slash
        )
        
        assert config.base_url == 'https://api.stlouisfed.org/fred'  # Should be removed
    
    def test_get_connection_params(self):
        """Test connection parameter extraction"""
        config = FREDConfig(
            api_key='abcd1234efgh5678ijkl9012mnop3456',
            rate_limit_per_minute=100,
            timeout_seconds=25
        )
        
        params = config.get_connection_params()
        
        expected_params = {
            'api_key': 'abcd1234efgh5678ijkl9012mnop3456',
            'base_url': 'https://api.stlouisfed.org/fred',
            'timeout': 25,
            'rate_limit': 100,
            'max_retries': 3
        }
        
        assert params == expected_params
    
    @patch('requests.get')
    def test_validate_credentials_success(self, mock_get):
        """Test successful credential validation"""
        # Mock successful API response
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {'categories': []}
        
        config = FREDConfig(api_key='abcd1234efgh5678ijkl9012mnop3456')
        result = config.validate_credentials()
        
        assert result is True
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_validate_credentials_invalid_key(self, mock_get):
        """Test credential validation with invalid API key"""
        # Mock invalid API key response
        mock_response = mock_get.return_value
        mock_response.status_code = 400
        
        config = FREDConfig(api_key='invalid_key_123456789012345678')
        
        with pytest.raises(AuthenticationError) as exc_info:
            config.validate_credentials()
        
        error = exc_info.value
        assert error.context['api_source'] == 'FRED'

class TestConfigurationUtilities:
    
    def test_generate_env_template(self):
        """Test environment variable template generation"""
        from src.federal_reserve_etl.config import generate_env_template
        
        template = generate_env_template()
        
        # Should contain all required variables
        assert 'FRED_API_KEY=' in template
        assert 'HAVER_USERNAME=' in template
        assert 'ETL_LOG_LEVEL=' in template
        
        # Should contain descriptions
        assert '# FRED API key from' in template
        assert '# Logging level for' in template
    
    def test_configuration_file_schema_validation(self, temp_config_file):
        """Test configuration file against JSON schema"""
        import jsonschema
        from src.federal_reserve_etl.config import CONFIG_FILE_SCHEMA
        
        with open(temp_config_file, 'r') as f:
            config_data = json.load(f)
        
        # Should not raise validation errors
        try:
            jsonschema.validate(config_data, CONFIG_FILE_SCHEMA)
        except jsonschema.ValidationError:
            pytest.fail("Configuration file should be valid according to schema")
```

### Integration Testing
```python
# tests/integration/test_configuration_integration.py
import pytest
import os
import tempfile
from pathlib import Path

from src.federal_reserve_etl.config import get_config_manager
from src.federal_reserve_etl.data_sources import create_data_source
from src.federal_reserve_etl.utils.exceptions import ConfigurationError

class TestConfigurationIntegration:
    
    @pytest.fixture
    def valid_environment(self):
        """Setup valid test environment"""
        # Set valid test credentials
        os.environ['FRED_API_KEY'] = 'abcd1234efgh5678ijkl9012mnop3456'
        os.environ['HAVER_USERNAME'] = 'test_user'
        os.environ['HAVER_PASSWORD'] = 'test_password123'
        
        yield
        
        # Cleanup
        for var in ['FRED_API_KEY', 'HAVER_USERNAME', 'HAVER_PASSWORD']:
            os.environ.pop(var, None)
    
    def test_data_source_factory_with_configuration(self, valid_environment):
        """Test data source factory using configuration manager"""
        # Should successfully create FRED data source
        fred_source = create_data_source('fred')
        
        assert fred_source.api_key == 'abcd1234efgh5678ijkl9012mnop3456'
        assert fred_source.base_url == 'https://api.stlouisfed.org/fred'
    
    def test_configuration_error_propagation(self):
        """Test that configuration errors propagate properly"""
        # Clear environment to trigger configuration error
        for var in ['FRED_API_KEY', 'HAVER_USERNAME', 'HAVER_PASSWORD']:
            os.environ.pop(var, None)
        
        with pytest.raises(ConfigurationError) as exc_info:
            create_data_source('fred')
        
        error = exc_info.value
        assert 'FRED_API_KEY' in str(error)
        assert error.suggestion is not None
    
    def test_logging_configuration_integration(self, valid_environment):
        """Test logging system integration with configuration"""
        config_manager = get_config_manager()
        logging_config = config_manager.get_logging_config()
        
        # Should have valid logging configuration
        assert logging_config.level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert logging_config.format_type in ['json', 'text']
    
    def test_cache_directory_creation(self, valid_environment):
        """Test automatic cache directory creation"""
        config_manager = get_config_manager()
        cache_config = config_manager.get_cache_config()
        
        # Directories should be created automatically
        assert Path(cache_config.cache_dir).exists()
        assert Path(cache_config.temp_dir).exists()
        
        # Should be writable
        test_file = Path(cache_config.cache_dir) / "test_write.txt"
        test_file.write_text("test")
        assert test_file.exists()
        test_file.unlink()
```

## 7. Development Tools

### Configuration Management CLI
```python
# tools/config_manager.py
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from src.federal_reserve_etl.config import get_config_manager, generate_env_template
from src.federal_reserve_etl.utils.exceptions import ConfigurationError

def main():
    parser = argparse.ArgumentParser(description='Federal Reserve ETL Configuration Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate all configurations')
    validate_parser.add_argument('--verbose', '-v', action='store_true', 
                               help='Show detailed validation information')
    
    # Generate template command
    template_parser = subparsers.add_parser('template', help='Generate configuration templates')
    template_parser.add_argument('--type', choices=['env', 'json'], default='env',
                               help='Template type to generate')
    template_parser.add_argument('--output', '-o', help='Output file path')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show current configuration')
    show_parser.add_argument('--type', choices=['fred', 'haver', 'logging', 'cache', 'all'], 
                           default='all', help='Configuration type to show')
    show_parser.add_argument('--hide-sensitive', action='store_true',
                           help='Hide sensitive configuration values')
    
    args = parser.parse_args()
    
    if args.command == 'validate':
        return validate_configuration(args.verbose)
    elif args.command == 'template':
        return generate_template(args.type, args.output)
    elif args.command == 'show':
        return show_configuration(args.type, args.hide_sensitive)
    else:
        parser.print_help()
        return 1

def validate_configuration(verbose: bool = False) -> int:
    """Validate all configurations and report results"""
    try:
        config_manager = get_config_manager()
        validation_report = config_manager.validate_all_configurations()
        
        if validation_report['overall_status'] == 'valid':
            print("✅ All configurations are valid")
            
            if verbose:
                for config_type, details in validation_report['configurations'].items():
                    print(f"  {config_type}: {details['status']}")
                    if 'source' in details:
                        sources = details['source']
                        if sources['environment_variables']:
                            print(f"    Environment variables: {', '.join(sources['environment_variables'])}")
                        if sources['config_files']:
                            print(f"    Config files: {', '.join(sources['config_files'])}")
            
            return 0
        else:
            print("❌ Configuration validation failed")
            
            for config_type, details in validation_report['configurations'].items():
                if details['status'] != 'valid':
                    print(f"\n{config_type} configuration:")
                    print(f"  Status: {details['status']}")
                    print(f"  Error: {details.get('error', 'Unknown error')}")
                    
                    if details.get('suggestion'):
                        print(f"  Suggestion: {details['suggestion']}")
                    
                    if details.get('missing_config'):
                        print(f"  Missing: {', '.join(details['missing_config'])}")
            
            return 1
    
    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}")
        return 1

def generate_template(template_type: str, output_path: str = None) -> int:
    """Generate configuration template"""
    try:
        if template_type == 'env':
            template_content = generate_env_template()
            default_filename = ".env.template"
        elif template_type == 'json':
            template_content = generate_json_template()
            default_filename = "config.template.json"
        else:
            print(f"Unknown template type: {template_type}")
            return 1
        
        if output_path:
            output_file = Path(output_path)
        else:
            output_file = Path(default_filename)
        
        output_file.write_text(template_content)
        print(f"✅ Template generated: {output_file}")
        return 0
    
    except Exception as e:
        print(f"❌ Error generating template: {e}")
        return 1

def show_configuration(config_type: str, hide_sensitive: bool = False) -> int:
    """Show current configuration values"""
    try:
        config_manager = get_config_manager()
        
        if config_type == 'all':
            configs = {
                'fred': config_manager.get_fred_config(),
                'haver': config_manager.get_haver_config(),
                'logging': config_manager.get_logging_config(),
                'cache': config_manager.get_cache_config()
            }
        else:
            if config_type == 'fred':
                configs = {'fred': config_manager.get_fred_config()}
            elif config_type == 'haver':
                configs = {'haver': config_manager.get_haver_config()}
            elif config_type == 'logging':
                configs = {'logging': config_manager.get_logging_config()}
            elif config_type == 'cache':
                configs = {'cache': config_manager.get_cache_config()}
            else:
                print(f"Unknown configuration type: {config_type}")
                return 1
        
        for name, config in configs.items():
            print(f"\n{name.upper()} Configuration:")
            config_dict = config.__dict__ if hasattr(config, '__dict__') else vars(config)
            
            for key, value in config_dict.items():
                if hide_sensitive and key in ['api_key', 'password']:
                    value = '***HIDDEN***'
                print(f"  {key}: {value}")
        
        return 0
    
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        if e.suggestion:
            print(f"Suggestion: {e.suggestion}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

def generate_json_template() -> str:
    """Generate JSON configuration template"""
    template = {
        "fred": {
            "base_url": "https://api.stlouisfed.org/fred",
            "rate_limit_per_minute": 120,
            "timeout_seconds": 30,
            "max_retries": 3
        },
        "haver": {
            "server_url": "https://api.haver.com",
            "database": "DLX",
            "rate_limit_per_second": 10,
            "connection_timeout": 60
        },
        "logging": {
            "level": "INFO",
            "format": "text",
            "max_file_size": "100MB",
            "backup_count": 5
        },
        "cache": {
            "max_size_mb": 1000,
            "default_ttl_seconds": 3600
        }
    }
    
    return json.dumps(template, indent=2)

if __name__ == '__main__':
    sys.exit(main())
```

### Configuration Validation Script
```python
# scripts/validate_config.py
#!/usr/bin/env python3
"""
Configuration validation script for CI/CD pipelines.
Returns exit code 0 for valid configuration, 1 for invalid.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from federal_reserve_etl.config import get_config_manager
from federal_reserve_etl.utils.exceptions import ConfigurationError

def main():
    """Validate configuration for CI/CD pipeline"""
    print("🔍 Validating Federal Reserve ETL configuration...")
    
    try:
        config_manager = get_config_manager()
        validation_report = config_manager.validate_all_configurations()
        
        if validation_report['overall_status'] == 'valid':
            print("✅ Configuration validation passed")
            
            # Show configuration sources for debugging
            print("\nConfiguration sources:")
            for config_type, details in validation_report['configurations'].items():
                if 'source' in details:
                    sources = details['source']
                    env_vars = sources.get('environment_variables', [])
                    config_files = sources.get('config_files', [])
                    
                    print(f"  {config_type}:")
                    if env_vars:
                        print(f"    Environment variables: {', '.join(env_vars)}")
                    if config_files:
                        print(f"    Config files: {', '.join(config_files)}")
                    if not env_vars and not config_files:
                        print(f"    Using defaults only")
            
            return 0
        
        else:
            print("❌ Configuration validation failed")
            
            for config_type, details in validation_report['configurations'].items():
                if details['status'] != 'valid':
                    print(f"\n{config_type} configuration issues:")
                    print(f"  Error: {details.get('error', 'Unknown error')}")
                    
                    if details.get('missing_config'):
                        print(f"  Missing configuration: {', '.join(details['missing_config'])}")
                    
                    if details.get('suggestion'):
                        print(f"  Suggestion: {details['suggestion']}")
            
            return 1
    
    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
```

## 8. Code Examples

### Complete Configuration Integration Example
```python
# Complete example showing configuration integration across the system
# main.py - Application entry point with configuration

import logging
import sys
from pathlib import Path

from src.federal_reserve_etl.config import get_config_manager
from src.federal_reserve_etl.utils.logging import setup_logging_from_config
from src.federal_reserve_etl.utils.exceptions import ConfigurationError
from src.federal_reserve_etl.data_sources import create_data_source

def main():
    """Main application entry point with configuration setup"""
    
    # Step 1: Initialize configuration system
    try:
        print("🔧 Initializing configuration...")
        config_manager = get_config_manager()
        
        # Validate all configurations on startup
        validation_report = config_manager.validate_all_configurations()
        if validation_report['overall_status'] != 'valid':
            print("❌ Configuration validation failed:")
            for config_type, details in validation_report['configurations'].items():
                if details['status'] != 'valid':
                    print(f"  {config_type}: {details.get('error', 'Unknown error')}")
                    if details.get('suggestion'):
                        print(f"    Suggestion: {details['suggestion']}")
            return 1
        
        print("✅ Configuration validation passed")
        
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        if e.suggestion:
            print(f"Suggestion: {e.suggestion}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected configuration error: {e}")
        return 1
    
    # Step 2: Setup logging system using configuration
    try:
        logger = setup_logging_from_config()
        logger.info("Federal Reserve ETL Pipeline starting up")
        logger.info(f"Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Logging setup failed: {e}")
        return 1
    
    # Step 3: Initialize data sources using configuration
    try:
        fred_source = create_data_source('fred')
        haver_source = create_data_source('haver')
        
        logger.info("Data sources initialized successfully")
        
        # Test connections
        with fred_source:
            logger.info("FRED API connection test successful")
        
        with haver_source:
            logger.info("Haver Analytics connection test successful")
        
    except ConfigurationError as e:
        logger.error(f"Data source configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Data source initialization error: {e}")
        return 1
    
    # Step 4: Run main application logic
    try:
        # Example ETL operation
        with fred_source:
            data = fred_source.get_data(['FEDFUNDS', 'GDP'], '2023-01-01', '2023-12-31')
            logger.info(f"Retrieved {len(data)} data points from FRED")
        
        logger.info("ETL pipeline completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"ETL pipeline error: {e}")
        return 1

def show_configuration_status():
    """Utility function to show current configuration status"""
    try:
        config_manager = get_config_manager()
        
        print("📋 Federal Reserve ETL Configuration Status\n")
        
        # Show FRED configuration
        try:
            fred_config = config_manager.get_fred_config()
            print("✅ FRED Configuration:")
            print(f"   Base URL: {fred_config.base_url}")
            print(f"   Rate Limit: {fred_config.rate_limit_per_minute}/min")
            print(f"   Timeout: {fred_config.timeout_seconds}s")
            print(f"   API Key: {'*' * 28}{fred_config.api_key[-4:]}")
        except ConfigurationError as e:
            print(f"❌ FRED Configuration: {e}")
        
        print()
        
        # Show Haver configuration
        try:
            haver_config = config_manager.get_haver_config()
            print("✅ Haver Configuration:")
            print(f"   Server URL: {haver_config.server_url}")
            print(f"   Database: {haver_config.database}")
            print(f"   Rate Limit: {haver_config.rate_limit_per_second}/sec")
            print(f"   Username: {haver_config.username}")
        except ConfigurationError as e:
            print(f"❌ Haver Configuration: {e}")
        
        print()
        
        # Show system configuration
        logging_config = config_manager.get_logging_config()
        cache_config = config_manager.get_cache_config()
        
        print("✅ System Configuration:")
        print(f"   Log Level: {logging_config.level}")
        print(f"   Log Format: {logging_config.format_type}")
        print(f"   Cache Dir: {cache_config.cache_dir}")
        print(f"   Cache Size: {cache_config.max_size_mb}MB")
        
    except Exception as e:
        print(f"❌ Error showing configuration: {e}")

if __name__ == '__main__':
    # Check for special commands
    if len(sys.argv) > 1 and sys.argv[1] == '--show-config':
        show_configuration_status()
        sys.exit(0)
    
    # Run main application
    exit_code = main()
    sys.exit(exit_code)
```

## 9. Performance Implementation

### Lazy Configuration Loading
```python
class OptimizedConfigurationManager(ConfigurationManager):
    """
    Performance-optimized configuration manager with lazy loading.
    """
    
    def __init__(self):
        super().__init__()
        self._config_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def get_fred_config(self) -> FREDConfig:
        """Get FRED config with caching"""
        cache_key = 'fred'
        current_time = time.time()
        
        # Check if cached config is still valid
        if (cache_key in self._config_cache and 
            cache_key in self._cache_timestamps and
            current_time - self._cache_timestamps[cache_key] < self._cache_ttl):
            return self._config_cache[cache_key]
        
        # Create new configuration
        config = self._create_fred_config()
        
        # Cache the configuration
        self._config_cache[cache_key] = config
        self._cache_timestamps[cache_key] = current_time
        
        return config
    
    def refresh_cache(self):
        """Force refresh of configuration cache"""
        self._config_cache.clear()
        self._cache_timestamps.clear()

# Configuration preloader for better startup performance
class ConfigurationPreloader:
    """Preload and validate configurations in parallel"""
    
    def __init__(self):
        self.config_manager = None
        self.preload_thread = None
        self.preload_complete = False
        self.preload_errors = []
    
    def start_preload(self):
        """Start configuration preloading in background thread"""
        import threading
        self.preload_thread = threading.Thread(target=self._preload_worker)
        self.preload_thread.daemon = True
        self.preload_thread.start()
    
    def _preload_worker(self):
        """Background worker to preload configurations"""
        try:
            self.config_manager = get_config_manager()
            
            # Preload all configuration types
            configs_to_load = [
                ('fred', self.config_manager.get_fred_config),
                ('haver', self.config_manager.get_haver_config),
                ('logging', self.config_manager.get_logging_config),
                ('cache', self.config_manager.get_cache_config)
            ]
            
            for config_name, config_loader in configs_to_load:
                try:
                    config_loader()
                except Exception as e:
                    self.preload_errors.append((config_name, str(e)))
            
            self.preload_complete = True
            
        except Exception as e:
            self.preload_errors.append(('system', str(e)))
    
    def wait_for_preload(self, timeout: float = 10.0) -> bool:
        """Wait for preload to complete"""
        if self.preload_thread:
            self.preload_thread.join(timeout=timeout)
            return self.preload_complete
        return False
    
    def get_config_manager(self) -> ConfigurationManager:
        """Get preloaded configuration manager"""
        if not self.preload_complete:
            self.wait_for_preload()
        
        if self.preload_errors:
            raise ConfigurationError(
                f"Configuration preload failed: {'; '.join([f'{name}: {error}' for name, error in self.preload_errors])}"
            )
        
        return self.config_manager
```

### Memory-Efficient Configuration Storage
```python
class CompactConfigurationStorage:
    """Memory-efficient configuration storage using slots"""
    
    __slots__ = ['_configs', '_metadata', '_lock']
    
    def __init__(self):
        self._configs = {}
        self._metadata = {
            'creation_time': time.time(),
            'access_count': 0,
            'last_access': None
        }
        self._lock = threading.RLock()
    
    def store_config(self, config_type: str, config_data: Any):
        """Store configuration data efficiently"""
        with self._lock:
            # Use weakref for large config objects to allow garbage collection
            import weakref
            if hasattr(config_data, '__dict__') and sys.getsizeof(config_data) > 1024:
                self._configs[config_type] = weakref.ref(config_data)
            else:
                self._configs[config_type] = config_data
            
            self._metadata['last_access'] = time.time()
            self._metadata['access_count'] += 1
    
    def get_config(self, config_type: str) -> Any:
        """Retrieve configuration data"""
        with self._lock:
            config = self._configs.get(config_type)
            
            if config is None:
                return None
            
            # Handle weak references
            if hasattr(config, '__call__'):  # It's a weak reference
                actual_config = config()
                if actual_config is None:  # Object was garbage collected
                    del self._configs[config_type]
                    return None
                return actual_config
            
            self._metadata['last_access'] = time.time()
            self._metadata['access_count'] += 1
            return config
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        with self._lock:
            total_size = sys.getsizeof(self._configs) + sys.getsizeof(self._metadata)
            
            for key, value in self._configs.items():
                total_size += sys.getsizeof(key)
                if hasattr(value, '__call__'):  # Weak reference
                    actual_value = value()
                    if actual_value:
                        total_size += sys.getsizeof(actual_value)
                else:
                    total_size += sys.getsizeof(value)
            
            return {
                'total_bytes': total_size,
                'config_count': len(self._configs),
                'access_count': self._metadata['access_count'],
                'creation_time': self._metadata['creation_time'],
                'last_access': self._metadata['last_access']
            }
```

## 10. Deployment Considerations

### Docker Configuration
```dockerfile
# Dockerfile with configuration management
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY scripts/ scripts/

# Create configuration directories
RUN mkdir -p /app/config /app/logs /app/cache

# Set environment variables with defaults
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Configuration defaults
ENV ETL_LOG_LEVEL=INFO
ENV ETL_CACHE_DIR=/app/cache
ENV ETL_LOG_FILE=/app/logs/federal_reserve_etl.log

# Validate configuration on build
RUN python scripts/validate_config.py || echo "Configuration validation failed (expected for build without secrets)"

# Health check with configuration validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from src.federal_reserve_etl.config import get_config_manager; get_config_manager()" || exit 1

# Run the application
CMD ["python", "-m", "src.federal_reserve_etl"]
```

### Kubernetes ConfigMap Integration
```yaml
# k8s-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: federal-reserve-etl-config
  namespace: default
data:
  config.json: |
    {
      "fred": {
        "base_url": "https://api.stlouisfed.org/fred",
        "rate_limit_per_minute": 120,
        "timeout_seconds": 30,
        "max_retries": 3
      },
      "haver": {
        "server_url": "https://api.haver.com",
        "database": "DLX",
        "rate_limit_per_second": 10,
        "connection_timeout": 60
      },
      "logging": {
        "level": "INFO",
        "format": "json",
        "max_file_size": "100MB",
        "backup_count": 5
      },
      "cache": {
        "cache_dir": "/app/cache",
        "temp_dir": "/app/temp",
        "max_size_mb": 1000,
        "default_ttl_seconds": 3600
      }
    }
---
apiVersion: v1
kind: Secret
metadata:
  name: federal-reserve-etl-secrets
  namespace: default
type: Opaque
stringData:
  FRED_API_KEY: "your_fred_api_key_here"
  HAVER_USERNAME: "your_haver_username"
  HAVER_PASSWORD: "your_haver_password"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: federal-reserve-etl
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: federal-reserve-etl
  template:
    metadata:
      labels:
        app: federal-reserve-etl
    spec:
      containers:
      - name: federal-reserve-etl
        image: federal-reserve-etl:latest
        env:
        # Load secrets as environment variables
        - name: FRED_API_KEY
          valueFrom:
            secretKeyRef:
              name: federal-reserve-etl-secrets
              key: FRED_API_KEY
        - name: HAVER_USERNAME
          valueFrom:
            secretKeyRef:
              name: federal-reserve-etl-secrets
              key: HAVER_USERNAME
        - name: HAVER_PASSWORD
          valueFrom:
            secretKeyRef:
              name: federal-reserve-etl-secrets
              key: HAVER_PASSWORD
        volumeMounts:
        # Mount config file
        - name: config-volume
          mountPath: /app/config
        # Mount persistent cache
        - name: cache-volume
          mountPath: /app/cache
      volumes:
      - name: config-volume
        configMap:
          name: federal-reserve-etl-config
      - name: cache-volume
        persistentVolumeClaim:
          claimName: federal-reserve-etl-cache
```

### Production Configuration Monitoring
```python
# monitoring/config_monitor.py
import time
import json
import logging
from typing import Dict, Any
from datetime import datetime

from src.federal_reserve_etl.config import get_config_manager
from src.federal_reserve_etl.utils.exceptions import ConfigurationError

class ConfigurationMonitor:
    """Monitor configuration health and changes in production"""
    
    def __init__(self, check_interval: int = 300):  # 5 minutes
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        self.last_config_hash = None
        self.last_check_time = None
        self.error_count = 0
    
    def start_monitoring(self):
        """Start configuration monitoring loop"""
        self.logger.info("Starting configuration monitoring")
        
        while True:
            try:
                self.check_configuration_health()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                self.logger.info("Configuration monitoring stopped")
                break
            except Exception as e:
                self.logger.error(f"Configuration monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def check_configuration_health(self):
        """Check configuration health and report issues"""
        try:
            config_manager = get_config_manager()
            validation_report = config_manager.validate_all_configurations()
            
            # Calculate configuration hash to detect changes
            config_hash = self._calculate_config_hash(validation_report)
            
            # Check for configuration changes
            if self.last_config_hash and config_hash != self.last_config_hash:
                self.logger.warning("Configuration change detected")
                self._log_config_change(validation_report)
            
            # Check validation status
            if validation_report['overall_status'] != 'valid':
                self.error_count += 1
                self.logger.error(f"Configuration validation failed (error #{self.error_count})")
                
                for config_type, details in validation_report['configurations'].items():
                    if details['status'] != 'valid':
                        self.logger.error(f"{config_type} config error: {details.get('error')}")
                
                # Alert if error count exceeds threshold
                if self.error_count >= 3:
                    self._send_alert(f"Configuration validation has failed {self.error_count} times")
            
            else:
                if self.error_count > 0:
                    self.logger.info(f"Configuration recovered after {self.error_count} errors")
                    self.error_count = 0
            
            self.last_config_hash = config_hash
            self.last_check_time = time.time()
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Configuration health check failed: {e}")
    
    def _calculate_config_hash(self, validation_report: Dict[str, Any]) -> str:
        """Calculate hash of configuration for change detection"""
        import hashlib
        config_str = json.dumps(validation_report, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _log_config_change(self, validation_report: Dict[str, Any]):
        """Log configuration change details"""
        for config_type, details in validation_report['configurations'].items():
            if 'source' in details:
                source_info = details['source']
                self.logger.info(f"{config_type} config sources: {json.dumps(source_info)}")
    
    def _send_alert(self, message: str):
        """Send alert for configuration issues"""
        # Implement alerting mechanism (email, Slack, PagerDuty, etc.)
        self.logger.critical(f"ALERT: {message}")
        
        # Example: Send to monitoring system
        try:
            # This would integrate with your monitoring/alerting system
            # send_to_monitoring_system(message)
            pass
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
```

---

**Document Status**: ✅ Complete - Production Implementation Guide  
**Last Updated**: September 1, 2025  
**Version**: 1.0 (Post-Implementation Documentation)  
**Implementation Files**: 
- `src/federal_reserve_etl/config.py` (Main configuration management system)
- `src/federal_reserve_etl/utils/type_definitions.py` (Configuration type definitions)
- Integration points across all system components