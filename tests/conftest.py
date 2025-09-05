"""
Pytest configuration for Federal Reserve ETL Pipeline tests

Global test configuration, fixtures, and utilities for the complete
test suite including integration and unit tests.
"""

import pytest
import os
import tempfile
from pathlib import Path
import logging

# Add src to path for all tests
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.fixture(scope="session")
def fred_api_key():
    """Fixture providing FRED API key for integration tests"""
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        pytest.skip("FRED_API_KEY environment variable not set")
    return api_key


@pytest.fixture(scope="session")
def temp_output_dir():
    """Fixture providing temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Setup logging for test session"""
    # Configure logging to be less verbose during tests
    logging.basicConfig(
        level=logging.WARNING,  # Only show warnings and errors
        format='%(name)s - %(levelname)s - %(message)s'
    )
    
    # Set federal_reserve_etl logger to INFO for test visibility
    logger = logging.getLogger('federal_reserve_etl')
    logger.setLevel(logging.INFO)


@pytest.fixture
def sample_variables():
    """Fixture providing commonly used test variables"""
    return {
        'single': 'FEDFUNDS',
        'multiple': ['FEDFUNDS', 'DGS10', 'TB3MS'],
        'historical': 'FEDFUNDS',
        'recent': ['FEDFUNDS', 'DGS10']
    }


@pytest.fixture
def date_ranges():
    """Fixture providing test date ranges"""
    from datetime import datetime, timedelta
    
    today = datetime.now()
    return {
        'recent_month': (
            (today - timedelta(days=30)).strftime('%Y-%m-%d'),
            today.strftime('%Y-%m-%d')
        ),
        'q1_2023': ('2023-01-01', '2023-03-31'),
        'january_2023': ('2023-01-01', '2023-01-31'),
        'historical_2020': ('2020-01-01', '2020-12-31'),
        'historical_2010': ('2010-01-01', '2010-12-31')
    }


def pytest_configure(config):
    """Pytest configuration hook"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring API access"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark tests that make API calls as slow
        if any(keyword in item.name.lower() for keyword in ['api', 'fred', 'haver', 'connectivity']):
            item.add_marker(pytest.mark.slow)


# Custom assertions for data validation
def assert_valid_dataframe(df, expected_columns=None, min_rows=1):
    """Custom assertion for validating DataFrame structure"""
    import pandas as pd
    
    assert isinstance(df, pd.DataFrame), "Expected pandas DataFrame"
    assert len(df) >= min_rows, f"Expected at least {min_rows} rows, got {len(df)}"
    
    if expected_columns:
        for col in expected_columns:
            assert col in df.columns, f"Missing expected column: {col}"
    
    # Check for DatetimeIndex if DataFrame has date data
    if hasattr(df, 'index') and len(df) > 0:
        if any('date' in str(col).lower() for col in df.columns) or isinstance(df.index, pd.DatetimeIndex):
            assert isinstance(df.index, pd.DatetimeIndex), "Expected DatetimeIndex for time series data"


def assert_valid_metadata(metadata, expected_variables):
    """Custom assertion for validating metadata structure"""
    assert isinstance(metadata, dict), "Expected metadata dictionary"
    
    for var in expected_variables:
        assert var in metadata, f"Missing metadata for variable: {var}"
        
        var_meta = metadata[var]
        required_fields = ['code', 'name', 'source']
        
        for field in required_fields:
            assert field in var_meta, f"Missing required metadata field '{field}' for variable {var}"
        
        assert var_meta['code'] == var, f"Metadata code mismatch for {var}"


# Add custom assertions to pytest namespace
pytest.assert_valid_dataframe = assert_valid_dataframe
pytest.assert_valid_metadata = assert_valid_metadata