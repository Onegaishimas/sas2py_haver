# Federal Reserve ETL Pipeline - API Reference

Complete API reference documentation for the Federal Reserve ETL Pipeline.

## 📋 Table of Contents

- [Factory Functions](#factory-functions)
- [Data Source Classes](#data-source-classes)
- [Exception Classes](#exception-classes)
- [Utility Functions](#utility-functions)
- [Configuration](#configuration)
- [Examples](#examples)

## 🏭 Factory Functions

### create_data_source()

Creates and configures data source instances using the factory pattern.

```python
def create_data_source(source_type: str, **kwargs) -> DataSource
```

**Parameters:**
- `source_type` (str): Type of data source ('fred' or 'haver')
- `**kwargs`: Additional configuration parameters

**Returns:**
- `DataSource`: Configured data source instance

**Raises:**
- `ValueError`: Invalid source type
- `ConfigurationError`: Missing required configuration

**Example:**
```python
from src.federal_reserve_etl import create_data_source

# Create FRED data source
fred = create_data_source('fred')

# Create with custom configuration
fred = create_data_source('fred', 
                         api_key='your_key',
                         rate_limit=60,
                         timeout=30)

# Create Haver data source
haver = create_data_source('haver',
                          username='user',
                          password='pass')
```

## 🗃️ Data Source Classes

### DataSource (Abstract Base Class)

Base class defining the interface for all data sources.

```python
class DataSource(ABC):
    def __init__(self, **config)
    def connect(self) -> bool
    def disconnect(self) -> None
    def is_connected(self) -> bool
    def get_data(self, variables: Union[str, List[str]], 
                 start_date: str, end_date: str) -> pd.DataFrame
    def get_variable_metadata(self, variable: str) -> Dict[str, Any]
    def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Any]
```

**Configuration Parameters:**
- `timeout` (int): Request timeout in seconds (default: 30)
- `rate_limit` (int): Requests per minute limit
- `max_retries` (int): Maximum retry attempts (default: 3)
- `retry_delay` (float): Base delay between retries (default: 1.0)

### FREDDataSource

Implementation for Federal Reserve Economic Data API.

```python
class FREDDataSource(DataSource):
    def __init__(self, api_key: str = None, **config)
```

**Parameters:**
- `api_key` (str): FRED API key (32 characters)
- `base_url` (str): API base URL (default: https://api.stlouisfed.org/fred)
- `rate_limit` (int): Requests per minute (default: 120)

**Methods:**

#### connect()
```python
def connect(self) -> bool
```
Establishes connection to FRED API and validates credentials.

**Returns:**
- `bool`: True if connection successful

**Raises:**
- `AuthenticationError`: Invalid API key
- `ConnectionError`: Network connectivity issues

#### get_data()
```python
def get_data(self, variables: Union[str, List[str]], 
             start_date: str, end_date: str) -> pd.DataFrame
```
Retrieves economic data for specified variables and date range.

**Parameters:**
- `variables`: Variable code(s) (e.g., 'FEDFUNDS' or ['FEDFUNDS', 'DGS10'])
- `start_date`: Start date in 'YYYY-MM-DD' format
- `end_date`: End date in 'YYYY-MM-DD' format

**Returns:**
- `pd.DataFrame`: Data with date index and variable columns

**Example:**
```python
# Single variable
data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')

# Multiple variables  
data = fred.get_data(['FEDFUNDS', 'DGS10', 'UNRATE'], 
                     '2023-01-01', '2023-12-31')
```

#### get_variable_metadata()
```python
def get_variable_metadata(self, variable: str) -> Dict[str, Any]
```
Retrieves metadata for a single variable.

**Returns:**
- `dict`: Variable metadata including title, units, frequency, etc.

**Example:**
```python
metadata = fred.get_variable_metadata('FEDFUNDS')
print(f"Title: {metadata['title']}")
print(f"Units: {metadata['units']}")
```

### HaverDataSource

Implementation for Haver Analytics API.

```python
class HaverDataSource(DataSource):
    def __init__(self, username: str = None, password: str = None, **config)
```

**Parameters:**
- `username` (str): Haver Analytics username
- `password` (str): Haver Analytics password
- `base_url` (str): API base URL
- `rate_limit` (int): Requests per minute (varies by subscription)

**Methods:**

Similar interface to FREDDataSource with authentication via username/password.

## ⚠️ Exception Classes

### FederalReserveETLError

Base exception class for all pipeline errors.

```python
class FederalReserveETLError(Exception):
    def __init__(self, message: str, context: Dict[str, Any] = None)
```

**Attributes:**
- `message` (str): Error description
- `context` (dict): Additional error context
- `timestamp` (datetime): When error occurred

### ConnectionError

Network connectivity and communication errors.

```python
class ConnectionError(FederalReserveETLError):
    pass
```

**Common Causes:**
- Network connectivity issues
- API endpoint unavailable
- Proxy configuration problems
- SSL/TLS certificate issues

### AuthenticationError

Authentication and authorization failures.

```python
class AuthenticationError(FederalReserveETLError):
    pass
```

**Common Causes:**
- Invalid API key
- Expired credentials
- Insufficient permissions
- Account suspended

### DataRetrievalError

Data extraction and processing errors.

```python
class DataRetrievalError(FederalReserveETLError):
    pass
```

**Common Causes:**
- Variable not found
- Date range outside availability
- Malformed API response
- Data parsing errors

### ValidationError

Input parameter validation errors.

```python
class ValidationError(FederalReserveETLError):
    pass
```

**Common Causes:**
- Invalid date format
- Missing required parameters
- Out-of-range values
- Unsupported variable codes

### RateLimitError

API rate limit exceeded.

```python
class RateLimitError(FederalReserveETLError):
    def __init__(self, message: str, wait_time: float = None, **kwargs)
```

**Additional Attributes:**
- `wait_time` (float): Seconds to wait before retry

### ConfigurationError

Configuration and setup errors.

```python
class ConfigurationError(FederalReserveETLError):
    pass
```

## 🛠️ Utility Functions

### setup_logging()

Configures structured logging for the pipeline.

```python
def setup_logging(log_level: str = 'INFO',
                  log_file: str = None,
                  console_output: bool = True,
                  max_file_size: int = 10 * 1024 * 1024,
                  backup_count: int = 5) -> None
```

**Parameters:**
- `log_level`: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
- `log_file`: Log file path (auto-generated if None)
- `console_output`: Enable console logging
- `max_file_size`: Max log file size in bytes
- `backup_count`: Number of backup files to keep

**Example:**
```python
from src.federal_reserve_etl.utils.logging import setup_logging

# Basic setup
setup_logging()

# Debug mode with custom file
setup_logging(log_level='DEBUG', 
              log_file='debug.log',
              console_output=True)
```

### mask_sensitive_data()

Masks sensitive information in log messages.

```python
def mask_sensitive_data(message: str, 
                       patterns: List[str] = None) -> str
```

**Parameters:**
- `message`: Original message
- `patterns`: Custom patterns to mask

**Returns:**
- `str`: Message with sensitive data masked

## ⚙️ Configuration

### Environment Variables

The pipeline uses environment variables for configuration:

#### Required
- `FRED_API_KEY`: FRED API key (32 characters)

#### Optional
- `HAVER_USERNAME`: Haver Analytics username
- `HAVER_PASSWORD`: Haver Analytics password
- `LOG_LEVEL`: Logging level (default: INFO)
- `FRED_RATE_LIMIT`: FRED requests per minute (default: 120)
- `HAVER_RATE_LIMIT`: Haver requests per minute (default: 10)

### Configuration Files

#### .env File
```bash
# FRED API Configuration
FRED_API_KEY=your_32_character_fred_api_key

# Haver Analytics Configuration  
HAVER_USERNAME=your_username
HAVER_PASSWORD=your_password

# Pipeline Configuration
LOG_LEVEL=INFO
FRED_RATE_LIMIT=120
HAVER_RATE_LIMIT=10
```

## 📚 Examples

### Basic Usage

```python
import os
from src.federal_reserve_etl import create_data_source

# Set up environment
os.environ['FRED_API_KEY'] = 'your_api_key'

# Create and use data source
with create_data_source('fred') as fred:
    # Get Federal Funds Rate
    data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
    
    # Get metadata
    metadata = fred.get_variable_metadata('FEDFUNDS')
    
    print(f"Retrieved {len(data)} observations")
    print(f"Variable: {metadata['title']}")
```

### Error Handling

```python
from src.federal_reserve_etl import create_data_source
from src.federal_reserve_etl.utils.exceptions import (
    AuthenticationError, 
    DataRetrievalError,
    RateLimitError
)

try:
    with create_data_source('fred') as fred:
        data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
        
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    print(f"Context: {e.context}")
    
except DataRetrievalError as e:
    print(f"Data retrieval failed: {e}")
    
except RateLimitError as e:
    print(f"Rate limit exceeded. Wait {e.wait_time} seconds")
```

### Multi-Source Integration

```python
from src.federal_reserve_etl import create_data_source
import pandas as pd

# Combine data from multiple sources
fred_data = {}
haver_data = {}

# FRED data
with create_data_source('fred') as fred:
    fred_data = fred.get_data(['FEDFUNDS', 'DGS10'], 
                              '2023-01-01', '2023-12-31')

# Haver data (if available)
try:
    with create_data_source('haver') as haver:
        haver_data = haver.get_data(['GDP', 'CPI'], 
                                   '2023-01-01', '2023-12-31')
except Exception as e:
    print(f"Haver not available: {e}")

# Combine datasets
combined = pd.concat([fred_data, haver_data], axis=1)
```

### Export Data

```python
# Export to different formats
data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')

# CSV export
data.to_csv('federal_funds_2023.csv')

# JSON export
data.to_json('federal_funds_2023.json', orient='index', date_format='iso')

# Excel export with metadata
with pd.ExcelWriter('federal_funds_2023.xlsx') as writer:
    data.to_excel(writer, sheet_name='Data')
    
    # Add metadata sheet
    metadata = fred.get_variable_metadata('FEDFUNDS')
    pd.DataFrame([metadata]).to_excel(writer, sheet_name='Metadata')
```

### Custom Configuration

```python
# Custom rate limiting and timeout
config = {
    'rate_limit': 60,      # Slower than default
    'timeout': 60,         # Longer timeout
    'max_retries': 5,      # More retries
    'retry_delay': 2.0     # Longer delay between retries
}

with create_data_source('fred', **config) as fred:
    data = fred.get_data('FEDFUNDS', '2020-01-01', '2023-12-31')
```

### Logging and Debugging

```python
from src.federal_reserve_etl.utils.logging import setup_logging
import logging

# Enable debug logging
setup_logging(log_level='DEBUG', console_output=True)

# Enable HTTP debugging
logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)
logging.getLogger("requests.packages.urllib3").propagate = True

# Now all HTTP traffic will be logged
with create_data_source('fred') as fred:
    data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-31')
```

---

**Last Updated**: September 2025
**Version**: 1.0.0

*For troubleshooting and additional examples, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)*