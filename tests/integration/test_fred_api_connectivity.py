"""
Integration Tests for FRED API Connectivity

Real-world tests using actual FRED API calls to validate the complete
ETL pipeline functionality. No mocking - all tests use live API.

Requirements:
- FRED_API_KEY environment variable must be set
- Network connectivity to api.stlouisfed.org
- pytest for test execution
"""

import os
import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from federal_reserve_etl import (
    create_data_source,
    FREDDataSource,
    get_config_manager,
    validate_source_credentials
)
from federal_reserve_etl.utils import (
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    ValidationError
)


class TestFREDAPIConnectivity:
    """Integration tests for FRED API connectivity and data extraction"""
    
    @classmethod
    def setup_class(cls):
        """Setup for all tests in this class"""
        cls.api_key = os.getenv('FRED_API_KEY')
        if not cls.api_key:
            pytest.skip("FRED_API_KEY environment variable not set")
        
        # Validate API key format
        if len(cls.api_key) != 32:
            pytest.skip("Invalid FRED_API_KEY format - must be 32 characters")
    
    def test_fred_api_key_validation(self):
        """Test that our API key is valid and credentials work"""
        assert validate_source_credentials('fred'), "FRED credentials should be valid"
    
    def test_fred_data_source_creation(self):
        """Test creating FRED data source with factory pattern"""
        fred = create_data_source('fred', api_key=self.api_key)
        assert isinstance(fred, FREDDataSource)
        assert fred.api_key == self.api_key
    
    def test_fred_connection_lifecycle(self):
        """Test complete FRED connection lifecycle"""
        fred = create_data_source('fred', api_key=self.api_key)
        
        # Test connection
        assert fred.connect() == True
        assert fred.is_connected == True
        
        # Test disconnection
        fred.disconnect()
        assert fred.is_connected == False
    
    def test_fred_context_manager(self):
        """Test FRED data source context manager pattern"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            assert fred.is_connected == True
            # Connection should be active inside context
        # Connection should be closed after context
        assert fred.is_connected == False
    
    @pytest.mark.parametrize("variable,expected_columns", [
        ("FEDFUNDS", ["FEDFUNDS"]),
        ("DGS10", ["DGS10"]),
        ("TB3MS", ["TB3MS"]),
    ])
    def test_single_variable_extraction(self, variable, expected_columns):
        """Test extracting single variables from FRED"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Get recent data (last 30 days)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            df = fred.get_data(
                variables=variable,
                start_date=start_date,
                end_date=end_date
            )
            
            # Validate DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert isinstance(df.index, pd.DatetimeIndex)
            assert list(df.columns) == expected_columns
            assert len(df) > 0, f"Should have data for {variable}"
    
    def test_multiple_variable_extraction(self):
        """Test extracting multiple variables simultaneously"""
        variables = ["FEDFUNDS", "DGS10", "TB3MS"]
        
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Get data for first quarter of 2023
            df = fred.get_data(
                variables=variables,
                start_date="2023-01-01",
                end_date="2023-03-31"
            )
            
            # Validate DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert isinstance(df.index, pd.DatetimeIndex)
            
            # Should have all requested variables as columns
            for var in variables:
                assert var in df.columns, f"Missing variable {var}"
            
            # Should have data (some columns may have NaN for weekends/holidays)
            assert len(df) > 0, "Should have observations for Q1 2023"
            
            # Check date range
            assert df.index.min().strftime('%Y-%m-%d') >= "2023-01-01"
            assert df.index.max().strftime('%Y-%m-%d') <= "2023-03-31"
    
    def test_historical_data_extraction(self):
        """Test extracting historical data from different time periods"""
        test_cases = [
            ("2020-01-01", "2020-01-31", "Recent historical data"),
            ("2010-01-01", "2010-01-31", "10+ years historical data"),
            ("2000-01-01", "2000-01-31", "20+ years historical data"),
        ]
        
        with create_data_source('fred', api_key=self.api_key) as fred:
            for start_date, end_date, description in test_cases:
                df = fred.get_data(
                    variables="FEDFUNDS",
                    start_date=start_date,
                    end_date=end_date
                )
                
                assert isinstance(df, pd.DataFrame), f"Failed for {description}"
                assert len(df) > 0, f"No data for {description}"
                
                # Validate date range
                assert df.index.min().strftime('%Y-%m-%d') >= start_date
                assert df.index.max().strftime('%Y-%m-%d') <= end_date
    
    def test_metadata_retrieval(self):
        """Test retrieving metadata for FRED variables"""
        variables = ["FEDFUNDS", "DGS10"]
        
        with create_data_source('fred', api_key=self.api_key) as fred:
            metadata = fred.get_metadata(variables)
            
            # Validate metadata structure
            assert isinstance(metadata, dict)
            assert len(metadata) == len(variables)
            
            for var in variables:
                assert var in metadata, f"Missing metadata for {var}"
                
                var_meta = metadata[var]
                assert 'code' in var_meta
                assert 'name' in var_meta
                assert 'source' in var_meta
                assert var_meta['source'] == 'FRED'
                assert var_meta['code'] == var
    
    def test_get_variable_metadata_single(self):
        """Test getting metadata for a single variable"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            metadata = fred.get_variable_metadata("FEDFUNDS")
            
            assert isinstance(metadata, dict)
            assert metadata['code'] == 'FEDFUNDS'
            assert metadata['source'] == 'FRED'
            assert 'name' in metadata
            assert 'description' in metadata
    
    def test_rate_limiting_behavior(self):
        """Test FRED API rate limiting (120 requests per minute)"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Make multiple rapid requests
            start_time = datetime.now()
            
            for i in range(5):  # Conservative test - stay well under limit
                df = fred.get_data(
                    variables="FEDFUNDS",
                    start_date="2023-01-01",
                    end_date="2023-01-31"
                )
                assert len(df) > 0
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Should take at least some time due to rate limiting
            assert duration >= 2.0, "Rate limiting should enforce minimum delays"
    
    def test_error_handling_invalid_variable(self):
        """Test error handling for invalid variable codes"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Test with obviously invalid variable code
            with pytest.raises(DataRetrievalError):
                fred.get_data(
                    variables="INVALID_VAR_CODE_12345",
                    start_date="2023-01-01",
                    end_date="2023-01-31"
                )
    
    def test_error_handling_invalid_dates(self):
        """Test error handling for invalid date ranges"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Test with invalid date range (start > end) - should raise ValidationError
            with pytest.raises(ValidationError):
                fred.get_data(
                    variables="FEDFUNDS",
                    start_date="2023-12-31",
                    end_date="2023-01-01"  # End before start
                )
            
            # Test with future dates - should raise DataRetrievalError (no data available)
            future_start = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            future_end = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
            
            with pytest.raises(DataRetrievalError):
                fred.get_data(
                    variables="FEDFUNDS",
                    start_date=future_start,
                    end_date=future_end
                )
    
    def test_different_date_formats(self):
        """Test different date input formats"""
        with create_data_source('fred', api_key=self.api_key) as fred:
            # Test string dates
            df1 = fred.get_data(
                variables="FEDFUNDS",
                start_date="2023-01-01",
                end_date="2023-01-31"
            )
            
            # Test datetime objects  
            from datetime import datetime
            start_dt = datetime(2023, 1, 1)
            end_dt = datetime(2023, 1, 31)
            
            df2 = fred.get_data(
                variables="FEDFUNDS",
                start_date=start_dt,
                end_date=end_dt
            )
            
            # Results should be identical
            assert len(df1) == len(df2)
            assert df1.equals(df2)
    
    def test_authentication_error_simulation(self):
        """Test authentication error with invalid API key"""
        # Test with properly formatted but invalid API key
        invalid_key = '1234567890123456789012345678901X'  # 32 chars, alphanumeric but wrong
        
        fred = create_data_source('fred', api_key=invalid_key)
        
        # Should fail when trying to connect
        with pytest.raises(AuthenticationError):
            fred.connect()


class TestEndToEndWorkflows:
    """End-to-end integration tests for complete workflows"""
    
    @classmethod
    def setup_class(cls):
        """Setup for all tests in this class"""
        cls.api_key = os.getenv('FRED_API_KEY')
        if not cls.api_key:
            pytest.skip("FRED_API_KEY environment variable not set")
    
    def test_csv_export_workflow(self):
        """Test complete CSV export workflow"""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            with create_data_source('fred', api_key=self.api_key) as fred:
                df = fred.get_data(
                    variables=["FEDFUNDS", "DGS10"],
                    start_date="2023-01-01",
                    end_date="2023-01-31"
                )
                
                # Export to CSV
                df.to_csv(output_path, index=True)
                
                # Verify file was created and has content
                assert Path(output_path).exists()
                assert Path(output_path).stat().st_size > 0
                
                # Read back and validate
                df_read = pd.read_csv(output_path, index_col=0, parse_dates=True)
                assert isinstance(df_read.index, pd.DatetimeIndex)
                assert 'FEDFUNDS' in df_read.columns
                assert 'DGS10' in df_read.columns
                
        finally:
            # Cleanup
            if Path(output_path).exists():
                Path(output_path).unlink()
    
    def test_json_export_workflow(self):
        """Test complete JSON export workflow"""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            with create_data_source('fred', api_key=self.api_key) as fred:
                df = fred.get_data(
                    variables="FEDFUNDS",
                    start_date="2023-01-01",
                    end_date="2023-01-31"
                )
                
                # Get metadata
                metadata = fred.get_metadata(["FEDFUNDS"])
                
                # Create JSON structure
                output_data = {
                    'data': df.reset_index().to_dict('records'),
                    'metadata': metadata
                }
                
                # Export to JSON
                with open(output_path, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                
                # Verify file was created and has content
                assert Path(output_path).exists()
                assert Path(output_path).stat().st_size > 0
                
                # Read back and validate
                with open(output_path, 'r') as f:
                    data_read = json.load(f)
                
                assert 'data' in data_read
                assert 'metadata' in data_read
                assert isinstance(data_read['data'], list)
                assert len(data_read['data']) > 0
                assert 'FEDFUNDS' in data_read['metadata']
                
        finally:
            # Cleanup
            if Path(output_path).exists():
                Path(output_path).unlink()
    
    def test_configuration_workflow(self):
        """Test configuration management workflow"""
        config_mgr = get_config_manager()
        
        # Test credential validation
        assert config_mgr.validate_credentials('fred')
        
        # Test missing credentials detection
        missing = config_mgr.get_missing_credentials('haver')  # Should be missing
        assert len(missing) > 0
        
        # Test data source config generation
        fred_config = config_mgr.get_data_source_config('fred')
        assert fred_config['source_name'] == 'FRED'
        assert fred_config['rate_limit'] == 120
        assert fred_config['api_key'] == self.api_key


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Setup logging for test session"""
    import logging
    logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])