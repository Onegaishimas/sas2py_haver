# Technical Design Document: Configuration Management System

## 1. System Architecture

### Context Diagram
**Current System**: Federal Reserve ETL Pipeline with multi-source data extraction, error handling framework, and logging infrastructure
**Feature Integration**: Configuration management provides centralized settings for all system components, including data sources, error handling, and logging configuration
**External Dependencies**: Environment variables, configuration files, API endpoints, file system access

### Architecture Patterns
**Design Pattern**: Singleton Pattern with Factory Pattern for data source configurations
**Architectural Style**: Centralized configuration with hierarchical precedence
**Communication Pattern**: Synchronous configuration access with lazy loading and validation

## 2. Component Design

### High-Level Components
**Configuration Manager Component**: Singleton pattern for global configuration access
- Purpose: Centralized configuration management with multi-source support
- Interface: Global access methods with type-safe configuration objects
- Dependencies: Environment variables, file system, type validation framework

**Data Source Configuration Component**: Specialized configuration for API clients
- Purpose: Data source specific configuration with credential validation
- Interface: Configuration objects with connection testing capabilities
- Dependencies: Configuration manager, credential validation, network access

**Validation Component**: Configuration validation and setup guidance
- Purpose: Runtime validation with clear error messages and resolution steps
- Interface: Validation methods with detailed error reporting
- Dependencies: Type definitions, error handling framework, logging

### Class/Module Structure
```
config.py                         # Main configuration management
├── ConfigurationManager         # Singleton configuration manager
├── get_config_manager()        # Global access function
├── FREDConfig                  # FRED API configuration dataclass
├── HaverConfig                # Haver Analytics configuration dataclass
├── LoggingConfig              # Logging system configuration
├── CacheConfig               # Cache and temp file configuration
└── validate_configuration()   # Configuration validation logic

utils/
├── type_definitions.py         # Configuration type definitions
│   ├── DataSourceConfigDict   # Data source configuration schema
│   ├── LoggingConfigDict     # Logging configuration schema
│   └── ValidationResultDict  # Validation result schema
└── exceptions.py              # Configuration-specific exceptions
    ├── ConfigurationError     # Base configuration error
    ├── MissingConfigError    # Required configuration missing
    └── InvalidConfigError    # Configuration validation failure
```

## 3. Data Flow

### Request/Response Flow
1. **Input**: System component requests configuration via get_config_manager()
2. **Validation**: Configuration manager checks cache and validates if needed
3. **Processing**: Load configuration from sources in priority order (env > file > defaults)
4. **Validation**: Validate configuration values and test connections where applicable
5. **Response**: Return type-safe configuration object or raise configuration error

### Data Transformation
**Environment Variables** → **Configuration Parse** → **Type Validation** → **Connection Testing** → **Configuration Object**

Detailed transformation flow:
- Environment variables parsed and type-converted
- Configuration files loaded and merged with environment settings
- Default values applied for missing optional configuration
- Type validation ensures configuration object integrity
- Connection testing validates API credentials and endpoints

### State Management  
**State Storage**: Configuration cached in singleton instance after first successful load
**State Updates**: Configuration can be refreshed on demand for testing and development
**State Persistence**: Configuration state persists for application lifetime

## 4. Database Design

### Entity Relationship Diagram
```
[ConfigurationSource] ──< provides >── [ConfigurationValue]
    |                                      |
[source_type, priority,             [key, value, validation_status,
 source_location]                    last_validated]
```

### Schema Design
**Configuration Sources**: Multi-source configuration hierarchy
```python
{
    "environment_variables": {
        "FRED_API_KEY": "masked_value",
        "HAVER_USERNAME": "masked_value",
        "ETL_LOG_LEVEL": "INFO"
    },
    "config_files": {
        "config/settings.json": {
            "fred_base_url": "https://api.stlouisfed.org/fred",
            "logging": {"level": "INFO", "file_path": "logs/"}
        }
    },
    "defaults": {
        "rate_limits": {"fred": 120, "haver": 10},
        "timeouts": {"connection": 30, "read": 60}
    }
}
```

### Data Access Patterns
**Read Operations**: Configuration accessed through singleton with caching
**Write Operations**: Configuration updates through environment variables or files
**Caching Strategy**: Full configuration cached after first load with refresh capability
**Migration Strategy**: Configuration schema versioning with backward compatibility

## 5. API Design

### Function/Method Interfaces
```python
# Global configuration access
def get_config_manager() -> ConfigurationManager:
    """Get singleton configuration manager instance"""

# Main configuration manager
class ConfigurationManager:
    def __init__(self):
        """Initialize configuration manager with lazy loading"""
    
    def get_fred_config(self) -> FREDConfig:
        """Get FRED API configuration with validation"""
    
    def get_haver_config(self) -> HaverConfig:  
        """Get Haver Analytics configuration with validation"""
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging system configuration"""
    
    def validate_configuration(self) -> ValidationResult:
        """Validate all configuration and test connections"""
    
    def refresh_configuration(self) -> None:
        """Reload configuration from all sources"""

# Data source configuration classes
@dataclass
class FREDConfig:
    api_key: str
    base_url: str = "https://api.stlouisfed.org/fred"
    rate_limit_per_minute: int = 120
    timeout_seconds: int = 30
    max_retries: int = 3
    
    def validate_credentials(self) -> bool:
        """Test API key validity with real API call"""
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get parameters for API client initialization"""

@dataclass  
class HaverConfig:
    username: str
    password: str
    server_url: str
    database: str = "DLX"
    rate_limit_per_second: int = 10
    connection_timeout: int = 60
    
    def validate_credentials(self) -> bool:
        """Test authentication with Haver API"""
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get parameters for API client initialization"""
```

### Configuration Schema
```python
# Environment variable configuration
ENVIRONMENT_VARIABLES = {
    # FRED Configuration
    "FRED_API_KEY": {"required": True, "type": str, "sensitive": True},
    
    # Haver Configuration  
    "HAVER_USERNAME": {"required": True, "type": str, "sensitive": False},
    "HAVER_PASSWORD": {"required": True, "type": str, "sensitive": True},
    "HAVER_SERVER": {"required": False, "type": str, "default": "haver.com"},
    
    # System Configuration
    "ETL_LOG_LEVEL": {"required": False, "type": str, "default": "INFO"},
    "ETL_CACHE_DIR": {"required": False, "type": str, "default": "~/.federal_reserve_etl/cache"}
}

# Configuration file schema
CONFIG_FILE_SCHEMA = {
    "api_endpoints": {
        "fred_base_url": str,
        "haver_base_url": str
    },
    "rate_limits": {
        "fred_requests_per_minute": int,
        "haver_requests_per_second": int
    },
    "logging": {
        "level": str,
        "file_path": str,
        "max_file_size": str
    }
}
```

## 6. Security Considerations

### Authentication
**Required Authentication**: No additional authentication - manages existing API credentials
**Token Management**: Secure storage and validation of API keys and authentication tokens
**Session Management**: Configuration lifetime tied to application process

### Authorization  
**Permission Model**: Configuration access restricted to application components
**Access Controls**: Sensitive configuration values masked in logs and error messages
**Data Filtering**: Configuration validation filters and sanitizes user input

### Data Protection
**Sensitive Data**: API keys, passwords, and credentials never logged in plaintext
**Encryption**: Support for encrypted configuration files and environment variable encryption
**Input Sanitization**: Configuration values validated and sanitized before use
**SQL Injection Prevention**: N/A - no direct database operations from configuration

## 7. Performance Considerations

### Scalability Design
**Horizontal Scaling**: Thread-safe singleton pattern supports multi-threaded access
**Vertical Scaling**: Configuration memory usage bounded and predictable
**Database Scaling**: No database dependencies - file and environment variable based

### Optimization Strategies
**Caching**: Full configuration cached after first load to minimize repeated parsing
**Database Indexes**: N/A - no database operations
**Async Processing**: Configuration validation can be performed asynchronously
**Resource Pooling**: Configuration objects reused across components

### Performance Targets
**Response Time**: Configuration access <1ms after initialization
**Throughput**: Configuration validation <5 seconds on application startup
**Resource Usage**: Configuration memory usage <10MB regardless of complexity

## 8. Error Handling

### Exception Hierarchy
```
ConfigurationError (Base)
├── MissingConfigError           # Required configuration missing
│   ├── MissingCredentialsError # API credentials not provided
│   └── MissingFileError        # Configuration file not found
├── InvalidConfigError          # Configuration validation failure
│   ├── InvalidFormatError     # Configuration format issues
│   ├── InvalidValueError      # Configuration value validation
│   └── InvalidTypeError       # Type conversion failures
├── ConnectionTestError         # Credential validation failure
│   ├── InvalidCredentialsError # Bad API credentials
│   └── NetworkError           # Connection testing failure
└── ConfigurationLoadError      # Configuration loading issues
    ├── FileAccessError        # File permission or access issues
    └── ParsingError          # Configuration file parsing errors
```

### Error Response Format
```python
{
    "error_type": "MissingCredentialsError",
    "message": "FRED API key is required but not configured",
    "context": {
        "missing_config": "FRED_API_KEY",
        "config_source": "environment_variable",
        "validation_time": "2025-09-01T10:30:45Z"
    },
    "suggestion": "Set the FRED_API_KEY environment variable with your FRED API key",
    "setup_guidance": {
        "step_1": "Register at https://fred.stlouisfed.org/docs/api/api_key.html",
        "step_2": "export FRED_API_KEY='your_api_key_here'",
        "step_3": "Restart the application to load the new configuration"
    }
}
```

### Recovery Strategies
**Transient Failures**: Retry configuration loading with exponential backoff
**Permanent Failures**: Clear error message with setup guidance and resolution steps
**Partial Failures**: Load available configuration, warn about missing optional settings

## 9. Testing Strategy

### Unit Testing
**Components to Test**: 
- Configuration manager singleton behavior and thread safety
- Data source configuration validation and credential testing
- Environment variable parsing and type conversion
- Configuration precedence and merging logic

**Mock Strategy**: Mock environment variables, file system access, and API calls for credential testing
**Coverage Targets**: 95% code coverage for configuration logic

### Integration Testing
**Integration Points**: 
- Environment variable integration with system environment
- Configuration file loading with various file formats
- API credential validation with real API endpoints
- Error handling integration with logging and error frameworks

**Test Data**: Sample configuration files and environment setups for different scenarios
**Environment**: Test environment with controlled configuration sources

### End-to-End Testing
**User Scenarios**: 
- First-time setup with missing configuration and setup guidance
- Configuration updates and refresh without application restart
- Multi-environment deployment with different configuration sources
- Error scenarios with clear resolution steps

**Automation**: Automated configuration validation in CI/CD pipeline
**Manual Testing**: User experience testing for setup process and error messages

## 10. Implementation Phases

### Phase 1: Core Configuration Framework ✅ (Completed)
- [x] Singleton configuration manager implementation
- [x] Multi-source configuration loading (environment, files, defaults)
- [x] Type-safe configuration dataclasses for all components
- [x] Configuration validation and error handling

### Phase 2: Data Source Integration ✅ (Completed)
- [x] FRED API configuration with credential validation
- [x] Haver Analytics configuration with connection testing
- [x] Data source factory integration with configuration
- [x] API client configuration injection

### Phase 3: System Integration ✅ (Completed)
- [x] Logging configuration integration
- [x] Error handling configuration parameters
- [x] Cache and temporary file configuration
- [x] Global configuration access patterns

### Phase 4: Validation and Documentation ✅ (Completed)
- [x] Comprehensive configuration validation
- [x] Setup guidance and error messages
- [x] Configuration examples and templates
- [x] Integration testing with real API credentials

### Dependencies and Blockers
**Requires**: Type definition framework, error handling system, logging framework
**Provides**: Centralized configuration for all system components
**Risks**: Configuration complexity could overwhelm users, credential security

## 11. Implementation Status

### Completed Implementation ✅
The Configuration Management System is fully implemented and production-ready:

**Key Implementation Files**:
- `src/federal_reserve_etl/config.py`: Complete configuration management system (450+ lines)
- `src/federal_reserve_etl/utils/type_definitions.py`: Configuration type definitions
- Integration with all system components through dependency injection

**Configuration Sources Supported**:
- Environment variables with type conversion and validation
- JSON configuration files with schema validation
- Sensible defaults for all optional configuration
- Configuration precedence: Environment → File → Defaults

**Credential Management**:
- FRED API key validation with test API calls
- Haver Analytics authentication with connection testing
- Secure credential storage without plaintext logging
- Setup guidance for missing or invalid credentials

**Integration Points**:
- Data source factory uses configuration for client initialization
- Error handling framework gets parameters from configuration
- Logging system configured through central configuration
- All system components access configuration through singleton

### Architecture Strengths
- **Type Safety**: All configuration objects are type-safe with runtime validation
- **Security**: Credentials properly masked and secured
- **Usability**: Clear error messages and setup guidance
- **Flexibility**: Multiple configuration sources with clear precedence
- **Testability**: Comprehensive validation with connection testing
- **Performance**: Efficient caching with lazy loading

### Configuration Examples
**Environment Variable Setup**:
```bash
export FRED_API_KEY="your_fred_api_key"
export HAVER_USERNAME="your_haver_username" 
export HAVER_PASSWORD="your_haver_password"
export ETL_LOG_LEVEL="INFO"
```

**Configuration File Example**:
```json
{
  "api_endpoints": {
    "fred_base_url": "https://api.stlouisfed.org/fred",
    "haver_base_url": "https://api.haver.com"
  },
  "rate_limits": {
    "fred_requests_per_minute": 120,
    "haver_requests_per_second": 10
  },
  "logging": {
    "level": "INFO",
    "file_path": "logs/federal_reserve_etl.log"
  }
}
```

---

**Document Status**: ✅ Complete - Production Architecture Documented  
**Last Updated**: September 1, 2025  
**Version**: 1.0 (Post-Implementation Documentation)  
**Implementation Files**: `src/federal_reserve_etl/config.py`, `src/federal_reserve_etl/utils/type_definitions.py`