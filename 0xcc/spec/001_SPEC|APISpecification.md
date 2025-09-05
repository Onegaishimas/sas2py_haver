# API Specification: Federal Reserve ETL Pipeline

## 1. Overview

The Federal Reserve ETL Pipeline provides a unified Python API for extracting economic data from multiple sources including the Federal Reserve Economic Data (FRED) and Haver Analytics. This document specifies the complete public API interface, data formats, and integration patterns.

**API Version**: 1.0  
**Base Package**: `federal_reserve_etl`  
**Python Compatibility**: 3.8+  
**Status**: Implemented and Validated

## 2. Factory API

### create_data_source()

**Function Signature**:
```python
def create_data_source(source: str, api_key: str = None, **config) -> DataSource
```

**Description**: Creates a data source instance for the specified source type with appropriate configuration and validation.

**Parameters**:
- `source` (str, required): Data source type identifier
  - Valid values: `'fred'`, `'haver'`
  - Case insensitive
- `api_key` (str, required): API key for authentication
  - FRED: Must be exactly 32 characters
  - Haver: Variable length, subscription dependent
- `**config` (dict, optional): Additional configuration parameters
  - `base_url` (str): Custom API endpoint URL
  - `timeout` (int): Request timeout in seconds (default: 30)
  - `subscription_type` (str): For Haver only - 'basic', 'standard', 'premium'

**Returns**: 
- `DataSource`: Configured data source instance ready for use

**Exceptions**:
- `ValueError`: If source type is not supported
- `ConfigurationError`: If required configuration is missing or invalid

**Examples**:
```python
# Basic FRED data source
fred = create_data_source('fred', api_key='your_32_char_fred_api_key')

# FRED with custom configuration
fred = create_data_source(
    'fred', 
    api_key='your_fred_api_key',
    timeout=60,
    base_url='https://custom-fred-api.example.com'
)

# Haver Analytics data source
haver = create_data_source(
    'haver', 
    api_key='your_haver_api_key',
    subscription_type='premium'
)

# Context manager usage (recommended)
with create_data_source('fred', api_key='your_key') as fred:
    df = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
```

## 3. DataSource Interface

### Connection Management

#### connect()
**Method Signature**:
```python
def connect(self) -> bool
```

**Description**: Establishes connection to the data source and validates credentials.

**Returns**: 
- `bool`: True if connection successful, False otherwise

**Exceptions**:
- `AuthenticationError`: If API credentials are invalid
- `ConnectionError`: If unable to reach the service

**Example**:
```python
fred = create_data_source('fred', api_key='your_key')
if fred.connect():
    print("Successfully connected to FRED API")
else:
    print("Connection failed")
```

#### disconnect()
**Method Signature**:
```python
def disconnect(self) -> None
```

**Description**: Cleans up connection resources and marks the data source as disconnected.

**Returns**: None

**Example**:
```python
fred.disconnect()
assert fred.is_connected == False
```

#### Context Manager Support
**Usage Pattern**:
```python
with create_data_source('fred', api_key='your_key') as fred:
    # Connection automatically established
    df = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
    # Connection automatically cleaned up on exit
```

### Data Extraction

#### get_data()
**Method Signature**:
```python
def get_data(self, 
            variables: Union[str, List[str]], 
            start_date: Union[str, datetime], 
            end_date: Union[str, datetime]) -> pd.DataFrame
```

**Description**: Extracts economic data for specified variables and date range.

**Parameters**:
- `variables` (str or List[str], required): Variable code(s) to extract
  - Single variable: `'FEDFUNDS'`
  - Multiple variables: `['FEDFUNDS', 'DGS10', 'UNRATE']`
  - Case sensitive, must match exact API variable codes
- `start_date` (str or datetime, required): Start date for data extraction
  - String format: `'YYYY-MM-DD'` (e.g., `'2023-01-01'`)
  - Datetime object: `datetime(2023, 1, 1)`
- `end_date` (str or datetime, required): End date for data extraction
  - Same format options as start_date
  - Must be >= start_date

**Returns**: 
- `pd.DataFrame`: Time series data with DatetimeIndex and variable columns
  - Index: `pd.DatetimeIndex` with name `'date'`
  - Columns: Variable codes as column names
  - Values: Numeric data with `pd.NA` for missing observations
  - Sorted by date in ascending order

**Exceptions**:
- `ValidationError`: If parameters are invalid (dates, variable format)
- `DataRetrievalError`: If API call fails or data unavailable
- `ConnectionError`: If not connected to service
- `AuthenticationError`: If credentials become invalid during request

**Data Format**:
```python
# Example return DataFrame
                FEDFUNDS  DGS10  UNRATE
date                                  
2023-01-01         4.33   3.88     3.5
2023-02-01         4.57   3.53     3.6
2023-03-01         4.65   3.47     3.5
```

**Examples**:
```python
# Single variable extraction
df = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')

# Multiple variables extraction  
df = fred.get_data(
    variables=['FEDFUNDS', 'DGS10', 'UNRATE'],
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# Using datetime objects
from datetime import datetime
df = fred.get_data(
    'FEDFUNDS',
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31)
)

# Handle missing data
df = fred.get_data('FEDFUNDS', '2023-12-25', '2023-12-31')  # Holiday period
print(df.isna().sum())  # Check for missing values
```

#### get_metadata()
**Method Signature**:
```python
def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Any]
```

**Description**: Retrieves metadata information for specified variables.

**Parameters**:
- `variables` (str or List[str], required): Variable code(s) for metadata retrieval
  - Same format as `get_data()` variables parameter

**Returns**: 
- `Dict[str, Any]`: Dictionary with variable codes as keys and metadata as values

**Metadata Structure**:
```python
{
    'FEDFUNDS': {
        'code': 'FEDFUNDS',
        'name': 'Federal Funds Rate',
        'description': 'Interest rate at which depository institutions...',
        'source': 'FRED',
        'units': 'Percent',
        'frequency': 'Monthly',
        'last_updated': '2023-12-15T10:30:00Z'
    }
}
```

**Exceptions**:
- `ValidationError`: If variable codes are invalid
- `DataRetrievalError`: If metadata retrieval fails
- `ConnectionError`: If not connected to service

**Examples**:
```python
# Single variable metadata
metadata = fred.get_metadata('FEDFUNDS')
print(metadata['FEDFUNDS']['name'])  # "Federal Funds Rate"

# Multiple variables metadata
metadata = fred.get_metadata(['FEDFUNDS', 'DGS10'])
for var, info in metadata.items():
    print(f"{var}: {info['name']} ({info['units']})")
```

#### get_variable_metadata()
**Method Signature**:
```python
def get_variable_metadata(self, variable: str) -> Dict[str, Any]
```

**Description**: Retrieves metadata for a single variable (convenience method).

**Parameters**:
- `variable` (str, required): Single variable code

**Returns**: 
- `Dict[str, Any]`: Metadata dictionary for the specified variable

**Example**:
```python
metadata = fred.get_variable_metadata('FEDFUNDS')
print(f"Units: {metadata['units']}")
print(f"Description: {metadata['description']}")
```

### Validation and Utility Methods

#### validate_response()
**Method Signature**:
```python
def validate_response(self, response) -> bool
```

**Description**: Validates API response format and content (primarily for internal use).

**Parameters**:
- `response`: API response object (requests.Response or equivalent)

**Returns**: 
- `bool`: True if response is valid and properly formatted

**Exceptions**:
- `DataRetrievalError`: If response format is invalid

## 4. Configuration API

### validate_source_credentials()
**Function Signature**:
```python
def validate_source_credentials(source: str) -> bool
```

**Description**: Validates that credentials are available and properly formatted for a data source.

**Parameters**:
- `source` (str, required): Data source type ('fred' or 'haver')

**Returns**: 
- `bool`: True if valid credentials are available

**Example**:
```python
from federal_reserve_etl import validate_source_credentials

if validate_source_credentials('fred'):
    print("FRED credentials are properly configured")
else:
    print("FRED_API_KEY environment variable missing or invalid")
```

### get_config_manager()
**Function Signature**:
```python
def get_config_manager() -> ConfigManager
```

**Description**: Returns singleton instance of the configuration manager.

**Returns**: 
- `ConfigManager`: Configuration management instance

**ConfigManager Methods**:
```python
config_mgr = get_config_manager()

# Check credentials
is_valid = config_mgr.validate_credentials('fred')

# Get missing credentials
missing = config_mgr.get_missing_credentials('haver')  # Returns ['HAVER_API_KEY']

# Get data source configuration
fred_config = config_mgr.get_data_source_config('fred')
```

## 5. Exception Hierarchy

### Base Exception
```python
class FederalReserveETLError(Exception):
    """Base exception for all Federal Reserve ETL operations"""
    pass
```

### Connection Exceptions
```python
class ConnectionError(FederalReserveETLError):
    """Network connectivity or service unavailability issues"""
    
    # Common scenarios:
    # - Network timeout
    # - Service temporarily unavailable  
    # - DNS resolution failure
    pass

class AuthenticationError(FederalReserveETLError):
    """Invalid API credentials or authentication failure"""
    
    # Common scenarios:
    # - Invalid API key
    # - Expired credentials
    # - Insufficient permissions
    pass
```

### Data Operation Exceptions
```python
class DataRetrievalError(FederalReserveETLError):
    """API response errors or data unavailable"""
    
    # Common scenarios:
    # - Invalid variable codes
    # - Data not available for requested period
    # - API service errors
    pass

class ValidationError(FederalReserveETLError):
    """Invalid input parameters or data format"""
    
    # Common scenarios:
    # - Invalid date format
    # - Start date after end date
    # - Empty variable list
    pass

class RateLimitError(FederalReserveETLError):
    """API rate limit exceeded"""
    
    # Automatic retry logic typically handles this
    # Raised only when rate limit cannot be managed
    pass

class ConfigurationError(FederalReserveETLError):
    """Missing or invalid configuration"""
    
    # Common scenarios:
    # - Missing API key environment variables
    # - Invalid configuration parameters
    pass
```

### Exception Usage Patterns
```python
try:
    with create_data_source('fred', api_key='invalid_key') as fred:
        df = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
        
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Handle by prompting for valid API key
    
except ValidationError as e:
    print(f"Invalid parameters: {e}")
    # Handle by correcting input parameters
    
except DataRetrievalError as e:
    print(f"Data retrieval failed: {e}")
    # Handle by retrying with different parameters
    
except ConnectionError as e:
    print(f"Connection failed: {e}")
    # Handle by retrying later or checking network
```

## 6. Data Format Specifications

### DataFrame Format
**Index Specification**:
- Type: `pd.DatetimeIndex`
- Name: `'date'`
- Format: Date only (no time component)
- Timezone: None (dates are interpreted as local to data source)
- Sorting: Always ascending by date

**Column Specification**:
- Names: Exact variable codes as requested (case-sensitive)
- Type: `float64` for numeric data
- Missing Values: Represented as `pd.NA`
- Ordering: Same order as requested in variables list

**Example DataFrame Structure**:
```python
# DataFrame.info() output
<class 'pandas.core.frame.DataFrame'>
DatetimeIndex: 365 entries, 2023-01-01 to 2023-12-31
Data columns (total 3 columns):
 #   Column    Non-Null Count  Dtype  
---  ------    --------------  -----  
 0   FEDFUNDS  365 non-null    float64
 1   DGS10     365 non-null    float64
 2   UNRATE    12 non-null     float64
dtypes: float64(3)
```

### Metadata Format
**Standard Metadata Fields**:
```python
{
    'code': str,           # Variable code (matches column name)
    'name': str,           # Human-readable name
    'description': str,    # Detailed description
    'source': str,         # Data source ('FRED', 'Haver Analytics')
    'units': str,          # Units of measurement
    'frequency': str,      # Data frequency (Daily, Weekly, Monthly, etc.)
    'last_updated': str    # ISO 8601 timestamp of last update
}
```

**Extended Metadata Fields** (source-dependent):
```python
{
    # FRED-specific fields
    'series_id': str,      # FRED series identifier
    'observation_start': str,  # First available date
    'observation_end': str,    # Last available date
    'popularity': int,         # FRED popularity ranking
    
    # Haver-specific fields  
    'database': str,       # Haver database name
    'geo': str,           # Geographic coverage
    'vintage': str        # Data vintage information
}
```

## 7. Rate Limiting and Performance

### FRED API Rate Limiting
- **Limit**: 120 requests per minute
- **Implementation**: Automatic compliance with token bucket algorithm
- **Behavior**: Requests automatically delayed to respect limits
- **Multiple Variables**: Each variable requires separate API call

### Haver Analytics Rate Limiting
- **Limit**: Varies by subscription (60-1200 requests/minute)
- **Implementation**: Configurable based on subscription type
- **Behavior**: Automatic throttling based on subscription level

### Performance Characteristics
**Response Times** (typical):
- Single variable, recent data (1 year): < 2 seconds
- Single variable, historical data (20 years): < 5 seconds  
- Multiple variables (5 variables): < 15 seconds
- Large datasets (10+ years, 10+ variables): < 60 seconds

**Memory Usage**:
- Approximately 1MB per 100,000 observations
- DataFrame overhead: ~200 bytes per row
- Metadata: ~1KB per variable

## 8. Integration Patterns

### Basic Usage Pattern
```python
import os
from federal_reserve_etl import create_data_source

# Set up API key (ideally in environment)
os.environ['FRED_API_KEY'] = 'your_api_key_here'

# Extract data
with create_data_source('fred', api_key=os.getenv('FRED_API_KEY')) as fred:
    # Single variable
    fed_funds = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
    
    # Multiple variables  
    indicators = fred.get_data(
        ['FEDFUNDS', 'DGS10', 'UNRATE'], 
        '2023-01-01', 
        '2023-12-31'
    )
    
    # Get metadata
    metadata = fred.get_metadata(['FEDFUNDS', 'DGS10', 'UNRATE'])
```

### Error Handling Pattern
```python
from federal_reserve_etl import create_data_source
from federal_reserve_etl.utils import (
    AuthenticationError, ValidationError, DataRetrievalError
)

def safe_data_extraction(source, api_key, variables, start_date, end_date):
    """Robust data extraction with comprehensive error handling"""
    
    try:
        with create_data_source(source, api_key=api_key) as ds:
            return ds.get_data(variables, start_date, end_date)
            
    except AuthenticationError:
        print("Invalid API credentials - please check your API key")
        return None
        
    except ValidationError as e:
        print(f"Invalid parameters: {e}")
        return None
        
    except DataRetrievalError as e:
        print(f"Data not available: {e}")
        return None
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
df = safe_data_extraction('fred', api_key, 'FEDFUNDS', '2023-01-01', '2023-12-31')
if df is not None:
    print(f"Successfully extracted {len(df)} observations")
```

### Batch Processing Pattern
```python
import pandas as pd
from datetime import datetime, timedelta

def extract_multiple_periods(variables, start_year, end_year, freq='yearly'):
    """Extract data for multiple time periods to manage large requests"""
    
    all_data = []
    current_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    with create_data_source('fred', api_key=os.getenv('FRED_API_KEY')) as fred:
        while current_date <= end_date:
            # Calculate period end date
            if freq == 'yearly':
                period_end = datetime(current_date.year, 12, 31)
            elif freq == 'monthly':
                next_month = current_date.replace(day=28) + timedelta(days=4)
                period_end = next_month - timedelta(days=next_month.day)
            
            period_end = min(period_end, end_date)
            
            try:
                period_data = fred.get_data(
                    variables, 
                    current_date.strftime('%Y-%m-%d'),
                    period_end.strftime('%Y-%m-%d')
                )
                
                all_data.append(period_data)
                print(f"Extracted {current_date.year}: {len(period_data)} observations")
                
            except Exception as e:
                print(f"Failed to extract {current_date.year}: {e}")
            
            # Move to next period
            if freq == 'yearly':
                current_date = datetime(current_date.year + 1, 1, 1)
            elif freq == 'monthly':
                current_date = period_end + timedelta(days=1)
    
    # Combine all periods
    if all_data:
        return pd.concat(all_data, sort=True)
    else:
        return pd.DataFrame()

# Usage for large historical extractions
historical_data = extract_multiple_periods(
    variables=['FEDFUNDS', 'DGS10'], 
    start_year=2000, 
    end_year=2023
)
```

### Export Pattern
```python
import json
from pathlib import Path

def export_data_with_metadata(df, metadata, base_filename):
    """Export data and metadata to multiple formats"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # CSV export (data only)
    csv_path = f"{base_filename}_{timestamp}.csv"
    df.to_csv(csv_path, index=True)
    print(f"Data exported to: {csv_path}")
    
    # JSON export (data + metadata)
    json_path = f"{base_filename}_{timestamp}.json"
    export_data = {
        'data': df.reset_index().to_dict('records'),
        'metadata': metadata,
        'export_info': {
            'timestamp': datetime.now().isoformat(),
            'observations': len(df),
            'variables': list(df.columns),
            'date_range': {
                'start': df.index.min().isoformat() if len(df) > 0 else None,
                'end': df.index.max().isoformat() if len(df) > 0 else None
            }
        }
    }
    
    with open(json_path, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    print(f"Data and metadata exported to: {json_path}")
    
    return csv_path, json_path

# Usage
with create_data_source('fred', api_key=api_key) as fred:
    df = fred.get_data(['FEDFUNDS', 'DGS10'], '2023-01-01', '2023-12-31')
    metadata = fred.get_metadata(['FEDFUNDS', 'DGS10'])
    
    csv_file, json_file = export_data_with_metadata(df, metadata, 'economic_data')
```

## 9. API Versioning and Compatibility

### Version Information
- **Current Version**: 1.0
- **Compatibility**: Semantic versioning (MAJOR.MINOR.PATCH)
- **Breaking Changes**: Only in major version updates
- **Deprecation Policy**: 6 months notice for breaking changes

### Version Checking
```python
import federal_reserve_etl
print(federal_reserve_etl.__version__)  # "1.0.0"
```

### Backward Compatibility
- All 1.x versions maintain backward compatibility
- New optional parameters may be added in minor versions
- New data sources may be added in minor versions
- Bug fixes and security updates in patch versions

---

**Document Status**: ✅ Complete - Production API Specification  
**Last Updated**: August 29, 2024  
**Version**: 1.0 (Reflects Implemented API)  
**Next Review**: When planning API changes or additions