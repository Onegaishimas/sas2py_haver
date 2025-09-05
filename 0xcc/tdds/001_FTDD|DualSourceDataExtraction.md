# Technical Design Document: Dual-Source Data Extraction

## 1. System Architecture

### Context Diagram
**Current System Components**:
- Command-line interface (`extract_fed_data.py`)
- Core ETL package (`src/federal_reserve_etl/`)
- Interactive Jupyter notebook interface
- Configuration management system

**Feature Integration**: 
- Data extraction feature serves as the core foundation
- All interfaces (CLI, Python API, Jupyter) depend on this functionality
- Configuration system provides API credentials and settings

**External Dependencies**:
- FRED API (Federal Reserve Economic Data)
- Haver Analytics API (optional enhanced data source)
- Internet connectivity for real-time data access

### Architecture Patterns
**Design Pattern**: Factory Pattern with Abstract Base Class
- Enables dynamic instantiation of different data source types
- Provides consistent interface across implementations
- Supports future extension to additional data sources

**Architectural Style**: Layered Architecture
- **Presentation Layer**: CLI and Jupyter interfaces
- **Business Logic Layer**: Data extraction and transformation
- **Data Access Layer**: API client implementations
- **Infrastructure Layer**: Configuration, logging, error handling

**Communication Pattern**: Synchronous HTTP API calls
- REST API communication for FRED
- HTTP API communication for Haver Analytics
- Request/response pattern with retry logic for resilience

## 2. Component Design

### High-Level Components

**DataSourceFactory Component**
- Purpose: Create appropriate data source instances based on type
- Interface: `create_data_source(source_type: str, **config) -> DataSource`
- Dependencies: Data source implementations, configuration validation

**Abstract DataSource Component**
- Purpose: Define consistent interface for all data source implementations
- Interface: Abstract methods for connect, disconnect, get_data, get_metadata
- Dependencies: Base exception classes, typing definitions

**FRED Client Component**
- Purpose: Implement FRED API integration with rate limiting
- Interface: Concrete implementation of DataSource interface
- Dependencies: HTTP client, rate limiting utilities, data validation

**Haver Client Component**
- Purpose: Implement Haver Analytics API integration
- Interface: Concrete implementation of DataSource interface  
- Dependencies: HTTP client, data format transformation utilities

### Class/Module Structure
```
src/federal_reserve_etl/
├── __init__.py                     # Public API exports and factory
├── config.py                       # Configuration management
├── data_sources/
│   ├── __init__.py                # Factory exports
│   ├── base.py                    # Abstract DataSource class
│   ├── fred_client.py             # FRED API implementation
│   └── haver_client.py            # Haver Analytics implementation
└── utils/
    ├── __init__.py                # Utility exports
    ├── exceptions.py              # Exception hierarchy
    ├── error_handling.py          # Retry logic and decorators
    └── logging.py                 # Centralized logging
```

### Key Class Definitions
```python
# data_sources/base.py
class DataSource(ABC):
    """Abstract base class for all data source implementations"""
    
    def __init__(self, api_key: str, **config):
        self.api_key = api_key
        self.config = config
        self.is_connected = False
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection and validate credentials"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection resources"""
        pass
    
    @abstractmethod
    async def get_data(self, variables: Union[str, List[str]], 
                      start_date: Union[str, datetime], 
                      end_date: Union[str, datetime]) -> pd.DataFrame:
        """Extract data for specified variables and date range"""
        pass
    
    @abstractmethod
    async def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Any]:
        """Get metadata for specified variables"""
        pass
    
    @abstractmethod
    def validate_response(self, response: requests.Response) -> bool:
        """Validate API response format and content"""
        pass
    
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

## 3. Data Flow

### Request/Response Flow
1. **User Request**: Application receives data extraction request via CLI or Python API
2. **Factory Creation**: `create_data_source()` validates source type and creates appropriate client
3. **Connection**: Data source establishes connection and validates API credentials
4. **Parameter Validation**: Input parameters validated for format and business rules
5. **API Request**: HTTP request sent to appropriate API with rate limiting
6. **Response Processing**: API response validated and transformed to standard format
7. **Data Standardization**: Raw API data converted to pandas DataFrame with DatetimeIndex
8. **Metadata Enrichment**: Variable metadata retrieved and formatted consistently
9. **Output**: Standardized DataFrame and metadata returned to user

### Data Transformation Pipeline
**FRED API Response → Standard DataFrame**:
```
FRED JSON Response:
{
  "observations": [
    {"date": "2023-01-01", "value": "4.25"},
    {"date": "2023-02-01", "value": "4.50"}
  ]
}

↓ Transform ↓

pandas DataFrame:
                FEDFUNDS
date                    
2023-01-01         4.25
2023-02-01         4.50
```

**Haver API Response → Standard DataFrame**:
```
Haver Proprietary Format:
<data>
  <series code="FFUNDS">
    <obs date="20230101" value="4.25"/>
    <obs date="20230201" value="4.50"/>
  </series>
</data>

↓ Transform ↓

Same pandas DataFrame format as FRED
```

### State Management
**Connection State**: Each data source maintains connection status
- `is_connected`: Boolean indicating active connection
- `last_request_time`: Timestamp for rate limiting calculations
- `request_count`: Counter for rate limiting compliance

**Error State**: Comprehensive error tracking and recovery
- Failed requests logged with context for debugging
- Retry attempts tracked to prevent infinite loops
- Rate limiting state preserved across requests

## 4. Database Design

### Data Structures (In-Memory)
Since this is a real-time extraction system without persistent storage, data structures are maintained in memory:

**DataFrame Structure**:
```python
# Standard DataFrame format for all sources
df = pd.DataFrame({
    'FEDFUNDS': [4.25, 4.50, 4.75],
    'DGS10': [3.42, 3.48, 3.55],
    'UNRATE': [3.7, 3.6, 3.5]
}, index=pd.DatetimeIndex([
    '2023-01-01', '2023-02-01', '2023-03-01'
], name='date'))
```

**Metadata Structure**:
```python
metadata = {
    'FEDFUNDS': {
        'code': 'FEDFUNDS',
        'name': 'Federal Funds Rate',
        'source': 'FRED',
        'description': 'Interest rate at which depository institutions...',
        'units': 'Percent',
        'frequency': 'Monthly',
        'last_updated': '2023-12-01T10:30:00Z'
    }
}
```

### Data Access Patterns
**Read Operations**: 
- Real-time API requests for each data extraction
- No local caching (future enhancement opportunity)
- Rate-limited requests to comply with API restrictions

**Data Validation**:
- Response format validation (JSON structure for FRED)
- Data type validation (numeric values, valid dates)
- Completeness checks (handle missing observations)

## 5. API Design

### External API Integration

**FRED API Endpoints**:
```python
BASE_URL = "https://api.stlouisfed.org/fred"

# Get series observations
GET /series/observations
Parameters:
- series_id: Variable code (e.g., 'FEDFUNDS')
- api_key: Authentication key
- file_type: 'json'
- observation_start: Start date (YYYY-MM-DD)
- observation_end: End date (YYYY-MM-DD)

# Get series metadata
GET /series
Parameters:
- series_id: Variable code
- api_key: Authentication key
- file_type: 'json'
```

**Haver Analytics API Integration**:
```python
# Custom endpoint structure (subscription dependent)
BASE_URL = "https://api.haver.com/data"

POST /extract
Headers:
- Authorization: Bearer {api_key}
- Content-Type: application/json
Body:
{
  "series": ["FFUNDS", "TB10Y"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "format": "json"
}
```

### Internal API Design
**Factory Function**:
```python
def create_data_source(source: str, **config) -> DataSource:
    """
    Create data source instance with validation and configuration
    
    Args:
        source: 'fred' or 'haver'
        **config: API keys and source-specific settings
        
    Returns:
        Configured DataSource instance
        
    Raises:
        ValueError: Unsupported source type
        ConfigurationError: Missing required configuration
    """
    if source.lower() == 'fred':
        return FREDDataSource(**config)
    elif source.lower() == 'haver':
        return HaverDataSource(**config)
    else:
        raise ValueError(f"Unsupported data source: {source}")
```

**DataSource Interface**:
```python
class FREDDataSource(DataSource):
    def __init__(self, api_key: str, base_url: str = None, timeout: int = 30):
        super().__init__(api_key)
        self.base_url = base_url or "https://api.stlouisfed.org/fred"
        self.timeout = timeout
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(max_requests=120, time_window=60)
    
    async def get_data(self, variables: Union[str, List[str]], 
                      start_date: Union[str, datetime], 
                      end_date: Union[str, datetime]) -> pd.DataFrame:
        """Implementation with FRED-specific API calls and transformations"""
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Parameter conversion
        variables_list = [variables] if isinstance(variables, str) else variables
        start_str = self._format_date(start_date)
        end_str = self._format_date(end_date)
        
        # Multiple API calls for multiple variables
        all_data = {}
        for variable in variables_list:
            response = await self._fetch_series_data(variable, start_str, end_str)
            all_data[variable] = self._parse_observations(response)
        
        # Combine into single DataFrame
        return self._create_dataframe(all_data)
```

## 6. Security Considerations

### Authentication Design
**API Key Management**:
```python
# Environment variable loading with validation
def load_api_credentials():
    fred_key = os.getenv('FRED_API_KEY')
    haver_key = os.getenv('HAVER_API_KEY')
    
    if fred_key and len(fred_key) != 32:
        raise ConfigurationError("FRED API key must be 32 characters")
    
    return {
        'fred': fred_key,
        'haver': haver_key
    }
```

**Credential Validation**:
- API keys validated during connection establishment
- Test request made to verify credential validity
- Invalid credentials result in clear error messages
- Credentials never logged or exposed in error output

### Data Protection
**Input Sanitization**:
```python
def validate_variable_code(variable: str) -> str:
    """Validate and sanitize variable codes"""
    if not isinstance(variable, str):
        raise ValidationError("Variable code must be string")
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[^A-Z0-9_]', '', variable.upper())
    
    if len(sanitized) == 0:
        raise ValidationError("Invalid variable code format")
    
    return sanitized
```

**Network Security**:
- All API communication over HTTPS only
- Request timeouts to prevent hanging connections
- No sensitive data in URL parameters (API keys in headers when possible)

### Error Information Security
**Safe Error Messages**:
```python
# Good: Informative but secure
raise AuthenticationError("Invalid API credentials. Please check your FRED_API_KEY.")

# Bad: Exposes sensitive information  
# raise AuthenticationError(f"API key {api_key} is invalid")
```

## 7. Performance Considerations

### Rate Limiting Design
**FRED API Rate Limiting**:
```python
class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests  # 120 for FRED
        self.time_window = time_window    # 60 seconds
        self.requests = deque()
    
    async def acquire(self):
        """Block until request can be made within rate limits"""
        now = time.time()
        
        # Remove old requests outside time window
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        # Wait if at rate limit
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            await asyncio.sleep(sleep_time)
        
        self.requests.append(now)
```

### Memory Optimization
**Streaming Data Processing**:
- Process API responses immediately without full buffering
- Use pandas chunking for very large datasets
- Implement generator patterns for batch processing

**Connection Pooling**:
```python
# Reuse HTTP connections for multiple requests
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=3
)
session.mount('https://', adapter)
```

### Caching Strategy (Future Enhancement)
**Response Caching**:
- Cache frequent metadata requests
- Implement TTL-based cache invalidation
- Use Redis or local file cache for persistence

## 8. Error Handling

### Exception Hierarchy
```python
# Base exception for all ETL errors
class FederalReserveETLError(Exception):
    """Base exception for Federal Reserve ETL operations"""
    pass

# Connection and authentication errors
class ConnectionError(FederalReserveETLError):
    """Network connectivity or service unavailability"""
    pass

class AuthenticationError(FederalReserveETLError):
    """Invalid API credentials or authentication failure"""
    pass

# Data operation errors
class DataRetrievalError(FederalReserveETLError):
    """API response errors or data unavailable"""
    pass

class ValidationError(FederalReserveETLError):
    """Invalid input parameters or data format"""
    pass

class RateLimitError(FederalReserveETLError):
    """API rate limit exceeded"""
    pass
```

### Retry Logic Implementation
```python
def retry_on_failure(max_attempts: int = 3, backoff_factor: float = 1.0):
    """Decorator for implementing retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (ConnectionError, requests.Timeout) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = backoff_factor * (2 ** attempt)
                        await asyncio.sleep(delay)
                except (AuthenticationError, ValidationError):
                    # Don't retry authentication or validation errors
                    raise
            
            # All attempts failed
            raise DataRetrievalError(f"Request failed after {max_attempts} attempts") from last_exception
        
        return wrapper
    return decorator
```

### Recovery Strategies
**Graceful Degradation**:
- Continue processing available variables if some fail
- Return partial results with warning messages
- Preserve successful data even if metadata retrieval fails

**Context Preservation**:
```python
def log_error_with_context(logger, error, context):
    """Log error with full context for debugging"""
    logger.error(
        "Data extraction failed",
        extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': datetime.utcnow().isoformat()
        }
    )
```

## 9. Testing Strategy

### Integration Testing Approach
**Real API Testing**:
```python
class TestFREDAPIIntegration:
    @pytest.fixture(scope="class")
    def fred_api_key(self):
        key = os.getenv('FRED_API_KEY')
        if not key:
            pytest.skip("FRED_API_KEY not available")
        return key
    
    def test_fred_single_variable_extraction(self, fred_api_key):
        """Test extracting single variable from FRED API"""
        with create_data_source('fred', api_key=fred_api_key) as fred:
            df = fred.get_data(
                variables='FEDFUNDS',
                start_date='2023-01-01',
                end_date='2023-01-31'
            )
            
            assert isinstance(df, pd.DataFrame)
            assert isinstance(df.index, pd.DatetimeIndex)
            assert 'FEDFUNDS' in df.columns
            assert len(df) > 0
```

**Error Scenario Testing**:
```python
def test_invalid_api_key_handling(self):
    """Test handling of invalid API credentials"""
    invalid_key = 'invalid_key_12345678901234567890'
    
    fred = create_data_source('fred', api_key=invalid_key)
    
    with pytest.raises(AuthenticationError) as exc_info:
        fred.connect()
    
    assert "Invalid API credentials" in str(exc_info.value)
```

### Performance Testing
**Rate Limiting Validation**:
```python
def test_fred_rate_limiting_compliance():
    """Verify FRED rate limiting prevents API violations"""
    with create_data_source('fred', api_key=fred_api_key) as fred:
        start_time = time.time()
        
        # Make multiple rapid requests
        for i in range(5):
            df = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-31')
            assert len(df) > 0
        
        elapsed_time = time.time() - start_time
        
        # Should enforce minimum delays between requests
        assert elapsed_time >= 2.0  # Conservative estimate
```

### Data Quality Testing
**Format Validation**:
```python
def test_data_format_consistency():
    """Verify consistent data format across sources"""
    # Test both sources return identical DataFrame structure
    fred_df = fred_client.get_data('FEDFUNDS', '2023-01-01', '2023-01-31')
    haver_df = haver_client.get_data('FFUNDS', '2023-01-01', '2023-01-31')  # Equivalent variable
    
    assert fred_df.index.dtype == haver_df.index.dtype
    assert isinstance(fred_df.index, pd.DatetimeIndex)
    assert isinstance(haver_df.index, pd.DatetimeIndex)
```

## 10. Implementation Phases

### Phase 1: Foundation (Week 1)
**Deliverables**:
- [x] Abstract DataSource base class with complete interface
- [x] Exception hierarchy with proper inheritance
- [x] Configuration management for API credentials
- [x] Basic logging framework with structured output

**Acceptance Criteria**:
- [x] Base class enforces required methods through abstract interface
- [x] Exception hierarchy provides specific error types
- [x] Configuration validates API key formats and accessibility

### Phase 2: FRED Integration (Week 2)
**Deliverables**:
- [x] Complete FRED API client implementation
- [x] Rate limiting mechanism for 120 requests/minute compliance
- [x] Data extraction with proper DataFrame formatting
- [x] Metadata retrieval with consistent structure
- [x] Comprehensive error handling for FRED-specific issues

**Acceptance Criteria**:
- [x] FRED client passes all integration tests with real API
- [x] Rate limiting prevents API violations under load
- [x] Data format matches specification exactly

### Phase 3: Haver Integration (Week 2)
**Deliverables**:
- [x] Haver Analytics API client implementation
- [x] Data format transformation to match FRED structure
- [x] Subscription-aware rate limiting
- [x] Error handling for Haver-specific API responses

**Acceptance Criteria**:
- [x] Haver client provides identical interface to FRED client
- [x] Data output format matches FRED exactly
- [x] Integration tests verify API connectivity

### Phase 4: Integration and Testing (Week 3)
**Deliverables**:
- [x] Factory pattern implementation with dynamic source selection
- [x] Context manager support for both data sources
- [x] Comprehensive integration test suite (19 tests)
- [x] Performance validation and optimization

**Acceptance Criteria**:
- [x] Factory creates correct data source instances
- [x] All integration tests pass with real API calls
- [x] Performance meets specified requirements
- [x] Error handling covers all identified scenarios

### Dependencies and Risks
**Critical Dependencies**:
- Valid FRED API key for development and testing
- Network connectivity for real API integration testing
- Haver Analytics API access for complete testing

**Technical Risks**:
- API rate limiting may slow development and testing
- API format changes could break integration
- Network reliability affects test consistency

**Mitigation Strategies**:
- Use test API keys with higher rate limits when possible
- Implement comprehensive response validation
- Add circuit breaker patterns for network resilience

---

**Document Status**: ✅ Complete - Reflects Implemented Design  
**Last Updated**: August 29, 2024  
**Version**: 1.0 (Post-Implementation Documentation)  
**Implementation Status**: Fully implemented with 19 integration tests passing