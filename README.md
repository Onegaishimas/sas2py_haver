# Federal Reserve ETL Pipeline

A production-ready ETL (Extract, Transform, Load) pipeline for extracting economic data from Federal Reserve Economic Data (FRED) and Haver Analytics APIs. Built with comprehensive error handling, structured logging, and extensive testing.

## 🚀 Features

### Core Functionality
- **FRED API Integration**: Extract data from Federal Reserve Economic Data with intelligent rate limiting (120 req/min)
- **Haver Analytics Support**: Connect to Haver Analytics API for enterprise economic datasets
- **Factory Pattern**: Dynamic data source instantiation with unified interface
- **Context Manager Support**: Automatic connection management and resource cleanup

### Production Features
- **Comprehensive Error Handling**: 7-tier exception hierarchy with context preservation and retry logic
- **Structured Logging**: Production-ready logging with sensitive data masking and file rotation
- **Configuration Management**: Environment-based configuration with credential security
- **Multiple Export Formats**: CSV, JSON, and Excel with metadata preservation

### Developer Experience
- **Interactive Analysis**: Jupyter notebook for data exploration and visualization
- **Extensive Testing**: 65+ unit tests and 19 integration tests using real API calls
- **Type Safety**: Full type hints and validation throughout
- **API Documentation**: Comprehensive docstrings and examples

## 📋 Requirements

- Python 3.8+
- FRED API Key (required) - Get from [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html)
- Haver Analytics credentials (optional) - Contact [Haver Analytics](https://www.haver.com/)
- Network connectivity to API endpoints

## 🛠️ Installation

### Quick Installation
```bash
git clone <repository-url>
cd sas-code-examples_root
pip install -r requirements.txt
```

### Development Installation
```bash
git clone <repository-url>
cd sas-code-examples_root

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development and testing
```

## 🔑 API Credentials Setup

### FRED API Key (Required)
1. Visit [FRED API Registration](https://fred.stlouisfed.org/docs/api/api_key.html)
2. Create a free account
3. Generate your API key
4. Set environment variable:
   ```bash
   export FRED_API_KEY="your_32_character_api_key_here"
   ```

### Haver Analytics (Optional)
1. Contact [Haver Analytics](https://www.haver.com/) for subscription
2. Receive username and password credentials
3. Set environment variables:
   ```bash
   export HAVER_USERNAME="your_username"
   export HAVER_PASSWORD="your_password"
   ```

### Credential Verification
```bash
# Test FRED credentials
python -c "from src.federal_reserve_etl import create_data_source; print('FRED:', create_data_source('fred').connect())"

# Test Haver credentials (if available)
python -c "from src.federal_reserve_etl import create_data_source; print('Haver:', create_data_source('haver').connect())"
```

## 🔧 Quick Start

### Command Line Interface

```bash
# Extract Federal Funds Rate for 2023
python extract_fed_data.py --source fred --variables FEDFUNDS --start-date 2023-01-01 --end-date 2023-12-31 --output federal_funds_2023.csv

# Extract multiple variables
python extract_fed_data.py --source fred --variables FEDFUNDS,DGS10,UNRATE --start-date 2023-01-01 --end-date 2023-12-31 --format json --output economic_data_2023.json
```

### Python API

```python
from federal_reserve_etl import create_data_source
import os

# Create FRED data source
fred_key = os.getenv('FRED_API_KEY')
with create_data_source('fred', api_key=fred_key) as fred:
    # Extract data
    df = fred.get_data(
        variables=['FEDFUNDS', 'DGS10'],
        start_date='2023-01-01',
        end_date='2023-12-31'
    )
    
    # Get metadata
    metadata = fred.get_metadata(['FEDFUNDS', 'DGS10'])
    
    print(f"Extracted {len(df)} observations")
    print(df.head())
```

### Interactive Jupyter Notebook

Launch the interactive analysis notebook:

```bash
jupyter notebook Federal_Reserve_ETL_Interactive.ipynb
```

The notebook provides:
- Interactive data extraction with progress reporting
- Real-time visualization and analysis
- Export capabilities to multiple formats
- Error handling demonstrations
- Economic data dashboards

## 📊 Supported Data Sources

### FRED (Federal Reserve Economic Data)
- **Rate Limit**: 120 requests per minute
- **Common Variables**:
  - `FEDFUNDS`: Federal Funds Rate
  - `DGS10`: 10-Year Treasury Rate
  - `UNRATE`: Unemployment Rate
  - `CPIAUCSL`: Consumer Price Index

### Haver Analytics
- Custom rate limiting based on subscription
- Enterprise economic data access

## 🧪 Testing

### Test Suite Overview
- **65+ Unit Tests**: Abstract base classes, error handling, FRED/Haver clients, factory patterns, workflows
- **19 Integration Tests**: Real API connectivity and end-to-end workflows
- **Real API Testing**: Uses actual APIs instead of mocks for authentic validation

### Running Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run integration tests (requires API credentials)
pytest tests/integration/ -v

# Run all tests with coverage
pytest --cov=src/federal_reserve_etl --cov-report=html

# Run specific test categories
pytest tests/unit/test_exceptions.py -v  # Exception handling tests
pytest tests/unit/test_fred_client.py -v  # FRED client tests
pytest tests/unit/test_factory_pattern.py -v  # Factory pattern tests
```

### Test Categories

#### Unit Tests
- **Exception Handling**: 46 tests covering 7-tier exception hierarchy
- **Abstract Base Class**: 34 tests for DataSource interface
- **FRED Client**: Connection, data retrieval, metadata, error handling
- **Haver Client**: Authentication, data extraction, validation
- **Factory Pattern**: Dynamic instantiation, configuration, error handling
- **End-to-End Workflows**: Multi-source integration, export functionality

#### Integration Tests
- ✅ API connectivity and authentication
- ✅ Data extraction for single and multiple variables  
- ✅ Historical data retrieval across different time periods
- ✅ Metadata operations and validation
- ✅ Error handling for invalid inputs
- ✅ Rate limiting compliance
- ✅ Export functionality (CSV, JSON, Excel)

## 📁 Project Structure

```
├── src/federal_reserve_etl/           # Main package
│   ├── data_sources/                  # Data source implementations
│   │   ├── base.py                   # Abstract base class
│   │   ├── fred_client.py           # FRED API client
│   │   └── haver_client.py          # Haver API client
│   └── utils/                        # Utilities
│       ├── exceptions.py            # Custom exceptions
│       ├── error_handling.py        # Error handling patterns
│       └── logging.py               # Logging configuration
├── tests/                            # Test suite
│   ├── integration/                  # Integration tests
│   └── conftest.py                  # Test configuration
├── extract_fed_data.py              # CLI interface
├── Federal_Reserve_ETL_Interactive.ipynb  # Interactive notebook
├── requirements.txt                  # Runtime dependencies
└── requirements-dev.txt             # Development dependencies
```

## 🔄 Data Processing Workflow

1. **Connection**: Establish API connection with authentication
2. **Validation**: Validate input parameters and credentials  
3. **Extraction**: Retrieve data with rate limiting and retry logic
4. **Processing**: Transform data into standardized DataFrame format
5. **Metadata**: Enrich data with variable descriptions and metadata
6. **Export**: Save results in requested format (CSV, JSON, Excel)
7. **Cleanup**: Properly close connections and cleanup resources

## ⚡ Performance Features

- **Rate Limiting**: Automatic compliance with API rate limits
- **Retry Logic**: Exponential backoff for transient failures
- **Connection Pooling**: Efficient resource management
- **Streaming**: Memory-efficient processing of large datasets
- **Caching**: Optional caching for metadata and repeated queries

## 🛡️ Error Handling

The pipeline includes comprehensive error handling:

- `ConnectionError`: Network connectivity issues
- `AuthenticationError`: Invalid API credentials
- `DataRetrievalError`: API response errors or data issues
- `ValidationError`: Invalid input parameters
- `RateLimitError`: API rate limit exceeded

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes with tests
4. Run the test suite: `pytest`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:
1. Check the integration tests in `tests/integration/` for usage examples
2. Review the interactive notebook for comprehensive examples
3. Open an issue on GitHub for bugs or feature requests

## 🏆 Project Status

**Status**: ✅ MVP Complete and Validated
- All core features implemented
- Integration tests passing with real API calls
- Interactive analysis capabilities available
- Production-ready error handling and logging

**Last Updated**: August 2024
**Version**: 1.0.0 (MVP Release)