# Feature PRD: Dual-Source Data Extraction

## 1. Feature Overview

**Purpose**: Enable unified data extraction from both Federal Reserve Economic Data (FRED) and Haver Analytics APIs through a single, consistent interface.

**Value Proposition**: 
- Eliminates need for separate integration code for each data source
- Provides consistent data format regardless of source API differences
- Enables seamless switching between data sources
- Reduces development time for data analysis workflows

**Scope**: 
- FRED API integration with rate limiting compliance
- Haver Analytics API integration with format standardization
- Factory pattern for dynamic source selection
- Unified error handling across both sources

**Priority**: Critical (MVP Core Feature)

## 2. User Stories

### Primary User Stories

**US1: As a financial analyst**
**I want to extract data from FRED using simple Python commands**
**So that I can quickly get economic indicators for my analysis**

**Acceptance Criteria:**
- [ ] Can specify FRED as data source with `create_data_source('fred')`
- [ ] Can extract single variables like Federal Funds Rate
- [ ] Can extract multiple variables in one request
- [ ] Receives data in standardized DataFrame format
- [ ] Gets clear error messages for invalid variables or API issues

**US2: As a research economist**
**I want to use the same interface for both FRED and Haver data**
**So that I can compare datasets from different sources without changing code**

**Acceptance Criteria:**
- [ ] Same `get_data()` method works for both FRED and Haver sources
- [ ] Both sources return data in identical DataFrame format
- [ ] Both sources provide metadata in consistent structure
- [ ] Can switch between sources by changing factory parameter only

**US3: As a data pipeline developer**
**I want automatic retry logic and rate limiting**
**So that my automated data collection is reliable and compliant**

**Acceptance Criteria:**
- [ ] FRED requests automatically comply with 120 requests/minute limit
- [ ] Haver requests respect subscription-based rate limits
- [ ] Transient failures are automatically retried with backoff
- [ ] Permanent failures are clearly identified and reported

### Secondary User Stories

**US4: As a Python developer**
**I want context manager support for data sources**
**So that I can ensure proper connection management**

**Acceptance Criteria:**
- [ ] Can use `with create_data_source('fred') as fred:` syntax
- [ ] Connections are automatically established on enter
- [ ] Connections are automatically cleaned up on exit
- [ ] Exception handling preserves context manager behavior

## 3. Functional Requirements

### Core Functionality

**FR1: Data Source Factory**
- System must provide `create_data_source(source_type, **config)` function
- Must support 'fred' and 'haver' as source types
- Must accept API keys and configuration parameters
- Must return appropriate DataSource instance

**FR2: Unified Data Interface**
- All data sources must implement `get_data(variables, start_date, end_date)` method
- Must return pandas DataFrame with DatetimeIndex
- Must support both single variable (string) and multiple variables (list) input
- Must support both string dates ('YYYY-MM-DD') and datetime objects

**FR3: Metadata Retrieval**
- All data sources must implement `get_metadata(variables)` method
- Must return dictionary with variable descriptions, units, and source information
- Must include data frequency and last updated information where available

**FR4: Connection Management**
- All data sources must implement `connect()` and `disconnect()` methods
- Must support context manager protocol (`__enter__` and `__exit__`)
- Must validate API credentials during connection

### Input/Output Specifications

**Inputs**:
- `source_type`: String ('fred' or 'haver')
- `variables`: String or List[str] of variable codes
- `start_date`: String (YYYY-MM-DD) or datetime object
- `end_date`: String (YYYY-MM-DD) or datetime object
- `api_key`: String containing valid API key

**Outputs**:
- `DataFrame`: pandas DataFrame with DatetimeIndex and variable columns
- `Metadata`: Dictionary with variable information and descriptions

**Data Validation**:
- Variable codes must be non-empty strings
- Date ranges must be valid (start <= end)
- API keys must match expected format for each source

**Error Responses**:
- `ValidationError`: Invalid input parameters
- `AuthenticationError`: Invalid or missing API credentials
- `DataRetrievalError`: API errors or data unavailable
- `ConnectionError`: Network or service unavailability

## 4. Non-Functional Requirements

### Performance
**Response Time**: 
- Single variable requests: < 5 seconds for recent data (last 5 years)
- Multiple variable requests: < 15 seconds for up to 10 variables
- Historical data: < 30 seconds for 20+ years of data

**Throughput**:
- FRED: Support up to 120 requests per minute (API limit compliance)
- Haver: Support subscription-based limits (configurable)
- Concurrent requests: Support up to 5 simultaneous data extractions

### Reliability
**Error Handling**: 99% of transient failures should be automatically resolved through retry logic
**Rate Limiting**: 100% compliance with API rate limits to prevent service suspension
**Data Integrity**: Zero data corruption or format inconsistencies

### Security
**API Key Management**: 
- API keys stored in environment variables only
- No API keys logged or exposed in error messages
- Credential validation before making requests

**Data Protection**:
- All API communications over HTTPS
- Input validation to prevent injection attacks
- Secure error messages (no sensitive data exposure)

### Usability
**Consistency**: Identical interface across all supported data sources
**Error Messages**: Clear, actionable error messages with specific guidance
**Documentation**: Comprehensive docstrings and usage examples

## 5. API/Interface Specification

### Factory Interface
```python
def create_data_source(source: str, **config) -> DataSource:
    """
    Create a data source instance for the specified source type.
    
    Args:
        source: 'fred' or 'haver'
        **config: Source-specific configuration (api_key, etc.)
    
    Returns:
        DataSource instance ready for use
        
    Raises:
        ValueError: If source type is not supported
        ConfigurationError: If required config is missing
    """
```

### DataSource Interface
```python
class DataSource(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection and validate credentials"""
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection resources"""
        
    @abstractmethod
    async def get_data(self, variables: Union[str, List[str]], 
                      start_date: Union[str, datetime], 
                      end_date: Union[str, datetime]) -> pd.DataFrame:
        """Extract data for specified variables and date range"""
        
    @abstractmethod
    async def get_metadata(self, variables: Union[str, List[str]]) -> Dict[str, Any]:
        """Get metadata for specified variables"""
        
    @abstractmethod
    def validate_response(self, response: Any) -> bool:
        """Validate API response format and content"""
```

### Usage Examples
```python
# Basic usage
with create_data_source('fred', api_key=fred_key) as fred:
    df = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
    metadata = fred.get_metadata(['FEDFUNDS'])

# Multiple variables
variables = ['FEDFUNDS', 'DGS10', 'UNRATE']
df = fred.get_data(variables, '2023-01-01', '2023-12-31')

# Source switching
haver = create_data_source('haver', api_key=haver_key)
df_haver = haver.get_data('FFUNDS', '2023-01-01', '2023-12-31')
```

## 6. Data Requirements

### Data Model
**Primary Entity**: Economic Time Series
- **Attributes**: Date (index), Variable Values (columns), Metadata (separate dict)
- **Format**: pandas DataFrame with DatetimeIndex
- **Frequency**: Varies by variable (daily, weekly, monthly, quarterly, annual)

**Variable Codes**: 
- FRED uses mnemonics like 'FEDFUNDS', 'DGS10', 'UNRATE'
- Haver uses similar codes but may have different naming conventions
- System must preserve original variable names as column headers

### Data Sources
**FRED API**:
- Base URL: https://api.stlouisfed.org/fred/
- Authentication: API key parameter
- Response Format: XML or JSON (use JSON)
- Rate Limit: 120 requests per minute

**Haver Analytics API**:
- Base URL: Subscription-dependent
- Authentication: API key header
- Response Format: Proprietary (requires transformation)
- Rate Limit: Varies by subscription level

### Data Lifecycle
**Extraction**: Real-time API calls (no local caching initially)
**Transformation**: Standardize to pandas DataFrame format
**Validation**: Check data completeness and format consistency
**Output**: Return to user immediately (no persistence)

## 7. Business Rules

### Data Access Rules
**BR1: Rate Limit Compliance**
- FRED requests must not exceed 120 per minute
- Haver requests must respect subscription limits
- System must implement automatic throttling

**BR2: API Key Validation**
- API keys must be validated before making requests
- Invalid keys must generate clear error messages
- System must not cache invalid credentials

**BR3: Data Format Standardization**
- All sources must return data in identical DataFrame format
- Date columns must use pandas DatetimeIndex
- Missing data must be represented as NaN consistently

### Error Handling Rules
**BR4: Retry Logic**
- Transient failures (5xx errors) trigger automatic retry
- Maximum 3 retry attempts with exponential backoff
- Permanent failures (4xx errors) reported immediately

**BR5: Graceful Degradation**
- Partial data availability should not fail entire request
- Missing variables should be reported in metadata
- Network timeouts should be handled gracefully

## 8. Dependencies

### Internal Dependencies
**Base Infrastructure**: Abstract DataSource class must be implemented first
**Configuration System**: API key management and validation required
**Error Handling**: Exception hierarchy must be established

### External Dependencies
**FRED API Access**: Valid API key from Federal Reserve Economic Data
**Haver Analytics Access**: Valid subscription and API credentials (optional)
**Network Connectivity**: Reliable internet connection to API endpoints

**Python Dependencies**:
- pandas >= 2.0.0 for DataFrame operations
- requests >= 2.28.0 for HTTP API calls
- python-dateutil for flexible date parsing

## 9. Acceptance Criteria

### Feature Complete When:
- [x] Factory pattern creates both FRED and Haver data sources
- [x] Both sources implement identical interface methods
- [x] Data extraction works for single and multiple variables
- [x] Date handling supports both string and datetime inputs
- [x] Error handling covers all identified failure modes
- [x] Rate limiting prevents API violations
- [x] Context manager pattern works correctly
- [x] Metadata extraction provides complete information

### Quality Gates:
- [x] Integration tests pass with real API calls
- [x] Error scenarios handled gracefully
- [x] Performance requirements met for standard operations
- [x] API rate limits respected in all scenarios
- [x] Data format consistency across sources verified
- [x] Documentation complete with usage examples

## 10. Out of Scope

### Explicitly Not Included
**Data Persistence**: No local database or file caching
**Data Transformation**: No aggregation, calculations, or derived metrics
**Visualization**: No charting or graphical output capabilities
**Scheduling**: No automated or recurring data collection

**Advanced Features**: 
- Real-time streaming data
- Complex data joins or merging
- Data quality scoring or anomaly detection
- Multi-user access control

### Future Considerations
**Caching Layer**: Local storage for frequently accessed data
**Additional Sources**: Bloomberg, Yahoo Finance, other financial APIs
**Data Transformation**: Built-in calculation and aggregation functions
**Performance Optimization**: Parallel processing and request batching

---

**Document Status**: ✅ Complete - Feature Implemented and Validated  
**Last Updated**: August 29, 2024  
**Version**: 1.0 (Post-Implementation Documentation)  
**Implementation Status**: MVP Complete with 19 Integration Tests Passing