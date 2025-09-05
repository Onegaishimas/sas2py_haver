"""
End-to-end workflow tests for Federal Reserve ETL Pipeline

Tests complete data extraction workflows using real API calls,
including multi-source data integration, export functionality,
and error recovery scenarios.
"""

import pytest
import pandas as pd
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.federal_reserve_etl import create_data_source
from src.federal_reserve_etl.data_sources import FREDDataSource, HaverDataSource
from src.federal_reserve_etl.utils.exceptions import (
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    ValidationError
)

# Test configuration
FRED_API_KEY = os.getenv('FRED_API_KEY')
HAVER_USERNAME = os.getenv('HAVER_USERNAME')
HAVER_PASSWORD = os.getenv('HAVER_PASSWORD')

SKIP_FRED_TESTS = FRED_API_KEY is None
SKIP_HAVER_TESTS = HAVER_USERNAME is None or HAVER_PASSWORD is None
SKIP_MULTI_SOURCE_TESTS = SKIP_FRED_TESTS or SKIP_HAVER_TESTS


def skip_if_no_fred():
    return pytest.mark.skipif(SKIP_FRED_TESTS, reason="FRED_API_KEY not set")

def skip_if_no_haver():
    return pytest.mark.skipif(SKIP_HAVER_TESTS, reason="HAVER credentials not set")

def skip_if_no_multi_source():
    return pytest.mark.skipif(SKIP_MULTI_SOURCE_TESTS, reason="Both FRED and Haver credentials required")


class TestSingleSourceWorkflows:
    """Test complete workflows with single data sources"""
    
    @skip_if_no_fred()
    def test_fred_complete_workflow(self):
        """Test complete FRED data extraction workflow"""
        # Test data extraction workflow
        with create_data_source('fred') as fred:
            # 1. Verify connection
            assert fred.is_connected
            assert isinstance(fred, FREDDataSource)
            
            # 2. Get metadata for variables
            metadata = fred.get_variable_metadata('FEDFUNDS')
            assert isinstance(metadata, dict)
            assert 'name' in metadata
            
            # 3. Extract data for single variable
            single_var_data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-31')
            assert isinstance(single_var_data, pd.DataFrame)
            assert 'FEDFUNDS' in single_var_data.columns
            assert len(single_var_data) > 0
            
            # 4. Extract data for multiple variables
            multi_var_data = fred.get_data(
                ['FEDFUNDS', 'DGS10', 'UNRATE'], 
                '2023-01-01', '2023-01-31'
            )
            assert isinstance(multi_var_data, pd.DataFrame)
            expected_vars = ['FEDFUNDS', 'DGS10', 'UNRATE']
            available_vars = [var for var in expected_vars if var in multi_var_data.columns]
            assert len(available_vars) >= 2  # At least 2 variables should be available
            
            # 5. Verify data quality
            for var in available_vars:
                # Should have some non-null values
                assert multi_var_data[var].notna().sum() > 0
                
                # Values should be reasonable for economic indicators
                numeric_values = pd.to_numeric(multi_var_data[var], errors='coerce').dropna()
                if len(numeric_values) > 0:
                    assert (numeric_values >= 0).all()  # Economic indicators typically non-negative
                    assert (numeric_values <= 100).all()  # Reasonable upper bound for rates
    
    @skip_if_no_haver()
    def test_haver_complete_workflow(self):
        """Test complete Haver data extraction workflow"""
        # Test data extraction workflow
        with create_data_source('haver') as haver:
            # 1. Verify connection
            assert haver.is_connected
            assert isinstance(haver, HaverDataSource)
            
            try:
                # 2. Get metadata for common economic variable
                metadata = haver.get_variable_metadata('GDP')
                assert isinstance(metadata, dict)
                
                # 3. Extract data
                data = haver.get_data('GDP', '2022-01-01', '2022-12-31')
                assert isinstance(data, pd.DataFrame)
                assert 'GDP' in data.columns
                assert len(data) > 0
                
                # 4. Verify data quality
                assert data['GDP'].notna().sum() > 0
                
            except DataRetrievalError:
                # GDP might not be available in test subscription
                pytest.skip("GDP variable not available in test Haver subscription")
    
    @skip_if_no_fred()
    def test_fred_historical_data_workflow(self):
        """Test FRED workflow with historical data across multiple years"""
        with create_data_source('fred') as fred:
            # Extract longer historical range
            data = fred.get_data(
                ['FEDFUNDS', 'DGS10'], 
                '2020-01-01', '2022-12-31'
            )
            
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 500  # Should have substantial amount of data
            
            # Verify date range
            assert data.index.min() >= pd.Timestamp('2020-01-01')
            assert data.index.max() <= pd.Timestamp('2022-12-31')
            
            # Both variables should have substantial data
            assert data['FEDFUNDS'].notna().sum() > 500
            assert data['DGS10'].notna().sum() > 500


class TestMultiSourceWorkflows:
    """Test workflows combining multiple data sources"""
    
    @skip_if_no_multi_source()
    def test_fred_and_haver_integration(self):
        """Test integration of FRED and Haver data sources"""
        fred_data = None
        haver_data = None
        
        # Extract data from FRED
        with create_data_source('fred') as fred:
            fred_data = fred.get_data(['FEDFUNDS', 'DGS10'], '2022-01-01', '2022-12-31')
        
        # Extract data from Haver  
        with create_data_source('haver') as haver:
            try:
                haver_data = haver.get_data('GDP', '2022-01-01', '2022-12-31')
            except DataRetrievalError:
                pytest.skip("GDP not available in Haver test subscription")
        
        # Verify both extractions successful
        assert isinstance(fred_data, pd.DataFrame)
        assert isinstance(haver_data, pd.DataFrame)
        assert len(fred_data) > 0
        assert len(haver_data) > 0
        
        # Test data alignment and integration
        if len(haver_data) > 0 and len(fred_data) > 0:
            # Find common date range
            fred_start, fred_end = fred_data.index.min(), fred_data.index.max()
            haver_start, haver_end = haver_data.index.min(), haver_data.index.max()
            
            common_start = max(fred_start, haver_start)
            common_end = min(fred_end, haver_end)
            
            if common_start < common_end:
                # Filter to common date range
                fred_common = fred_data[common_start:common_end]
                haver_common = haver_data[common_start:common_end]
                
                # Combine data
                combined = pd.concat([fred_common, haver_common], axis=1)
                
                assert isinstance(combined, pd.DataFrame)
                assert len(combined) > 0
                
                # Should have columns from both sources
                fred_cols = [col for col in fred_common.columns if col in combined.columns]
                haver_cols = [col for col in haver_common.columns if col in combined.columns]
                
                assert len(fred_cols) > 0
                assert len(haver_cols) > 0
    
    @skip_if_no_fred()
    def test_multiple_fred_sessions(self):
        """Test multiple FRED sessions in sequence"""
        datasets = []
        
        # Session 1: Get federal funds rate
        with create_data_source('fred') as fred1:
            data1 = fred1.get_data('FEDFUNDS', '2023-01-01', '2023-06-30')
            datasets.append(('FEDFUNDS', data1))
        
        # Session 2: Get treasury rate
        with create_data_source('fred') as fred2:
            data2 = fred2.get_data('DGS10', '2023-01-01', '2023-06-30')
            datasets.append(('DGS10', data2))
        
        # Session 3: Get unemployment rate
        with create_data_source('fred') as fred3:
            data3 = fred3.get_data('UNRATE', '2023-01-01', '2023-06-30')
            datasets.append(('UNRATE', data3))
        
        # Verify all sessions successful
        assert len(datasets) == 3
        for var_name, data in datasets:
            assert isinstance(data, pd.DataFrame)
            assert var_name in data.columns
            assert len(data) > 0
        
        # Combine all datasets
        combined_data = pd.DataFrame()
        for var_name, data in datasets:
            if combined_data.empty:
                combined_data = data.copy()
            else:
                combined_data = combined_data.join(data, how='outer')
        
        assert isinstance(combined_data, pd.DataFrame)
        assert len(combined_data) > 0
        expected_columns = ['FEDFUNDS', 'DGS10', 'UNRATE']
        available_columns = [col for col in expected_columns if col in combined_data.columns]
        assert len(available_columns) >= 2


class TestDataExportWorkflows:
    """Test complete workflows including data export"""
    
    @skip_if_no_fred()
    def test_csv_export_workflow(self):
        """Test complete workflow with CSV export"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract data
            with create_data_source('fred') as fred:
                data = fred.get_data(['FEDFUNDS', 'DGS10'], '2023-01-01', '2023-01-31')
            
            # Export to CSV
            csv_path = Path(temp_dir) / 'fred_data.csv'
            data.to_csv(csv_path)
            
            # Verify export
            assert csv_path.exists()
            assert csv_path.stat().st_size > 0
            
            # Read back and verify
            reimported = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            assert isinstance(reimported, pd.DataFrame)
            assert len(reimported) == len(data)
            
            # Verify columns present
            for col in data.columns:
                if col in reimported.columns:
                    # Allow for some NaN differences due to CSV roundtrip
                    orig_non_null = data[col].notna().sum()
                    reimp_non_null = reimported[col].notna().sum()
                    assert abs(orig_non_null - reimp_non_null) <= 1
    
    @skip_if_no_fred()
    def test_json_export_workflow(self):
        """Test complete workflow with JSON export"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract data with metadata
            metadata = {}
            with create_data_source('fred') as fred:
                data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-31')
                metadata['FEDFUNDS'] = fred.get_variable_metadata('FEDFUNDS')
            
            # Export to JSON
            json_path = Path(temp_dir) / 'fred_data.json'
            
            # Create export structure with data and metadata
            export_data = {
                'data': data.to_dict('records'),
                'metadata': metadata,
                'export_timestamp': datetime.now().isoformat(),
                'date_range': {
                    'start': data.index.min().isoformat(),
                    'end': data.index.max().isoformat()
                }
            }
            
            import json
            with open(json_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            # Verify export
            assert json_path.exists()
            assert json_path.stat().st_size > 0
            
            # Read back and verify
            with open(json_path, 'r') as f:
                reimported = json.load(f)
            
            assert 'data' in reimported
            assert 'metadata' in reimported
            assert 'export_timestamp' in reimported
            assert 'date_range' in reimported
            
            # Verify data integrity
            assert len(reimported['data']) == len(data)
            assert 'FEDFUNDS' in reimported['metadata']
    
    @skip_if_no_fred()
    def test_excel_export_workflow(self):
        """Test complete workflow with Excel export"""
        pytest.importorskip("openpyxl", reason="openpyxl not available for Excel export")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract multiple datasets
            datasets = {}
            metadata = {}
            
            with create_data_source('fred') as fred:
                # Multiple variables
                for var in ['FEDFUNDS', 'DGS10', 'UNRATE']:
                    try:
                        datasets[var] = fred.get_data(var, '2023-01-01', '2023-01-31')
                        metadata[var] = fred.get_variable_metadata(var)
                    except DataRetrievalError:
                        # Some variables might not be available
                        continue
            
            if not datasets:
                pytest.skip("No FRED variables available for Excel export test")
            
            # Export to Excel with multiple sheets
            excel_path = Path(temp_dir) / 'fred_data.xlsx'
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Data sheets
                for var_name, data in datasets.items():
                    data.to_excel(writer, sheet_name=f'{var_name}_data')
                
                # Metadata sheet
                if metadata:
                    metadata_df = pd.DataFrame.from_dict(metadata, orient='index')
                    metadata_df.to_excel(writer, sheet_name='metadata')
            
            # Verify export
            assert excel_path.exists()
            assert excel_path.stat().st_size > 0
            
            # Read back and verify
            reimported_sheets = pd.read_excel(excel_path, sheet_name=None, index_col=0)
            
            # Should have at least one data sheet
            data_sheets = [name for name in reimported_sheets.keys() if name.endswith('_data')]
            assert len(data_sheets) >= 1
            
            # Verify data integrity for first sheet
            first_sheet = data_sheets[0]
            var_name = first_sheet.replace('_data', '')
            if var_name in datasets:
                original = datasets[var_name]
                reimported = reimported_sheets[first_sheet]
                
                assert len(reimported) == len(original)
                assert var_name in reimported.columns


class TestErrorRecoveryWorkflows:
    """Test workflows with error conditions and recovery"""
    
    @skip_if_no_fred()
    def test_partial_failure_recovery(self):
        """Test workflow recovery from partial failures"""
        with create_data_source('fred') as fred:
            # Mix valid and invalid variables
            variables = ['FEDFUNDS', 'INVALID_VAR_123', 'DGS10', 'ANOTHER_INVALID']
            
            # Should handle invalid variables gracefully
            data = fred.get_data(variables, '2023-01-01', '2023-01-31')
            
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0
            
            # Should have at least the valid variables
            valid_vars = ['FEDFUNDS', 'DGS10']
            available_valid_vars = [var for var in valid_vars if var in data.columns]
            assert len(available_valid_vars) >= 1  # At least one should succeed
            
            # Invalid variables should not be present
            invalid_vars = ['INVALID_VAR_123', 'ANOTHER_INVALID']
            for invalid_var in invalid_vars:
                assert invalid_var not in data.columns
    
    def test_authentication_error_handling(self):
        """Test handling of authentication errors"""
        # Test with invalid FRED API key
        with pytest.raises(AuthenticationError):
            with create_data_source('fred', api_key='invalid_key_format'):
                pass
        
        # Test with invalid Haver credentials
        with pytest.raises(AuthenticationError):
            with create_data_source('haver', username='invalid', password='invalid'):
                pass
    
    @skip_if_no_fred()
    def test_network_resilience_workflow(self):
        """Test workflow resilience to temporary network issues"""
        # This test verifies the retry logic works
        with create_data_source('fred') as fred:
            # Make multiple requests to test retry mechanisms
            successful_requests = 0
            max_requests = 5
            
            for i in range(max_requests):
                try:
                    data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-05')
                    if isinstance(data, pd.DataFrame) and len(data) > 0:
                        successful_requests += 1
                except (ConnectionError, DataRetrievalError):
                    # Some requests might fail due to network issues
                    continue
            
            # Should have at least some successful requests
            assert successful_requests >= 1


class TestPerformanceWorkflows:
    """Test performance characteristics of workflows"""
    
    @skip_if_no_fred()
    def test_large_dataset_workflow(self):
        """Test workflow with larger dataset"""
        start_time = datetime.now()
        
        with create_data_source('fred') as fred:
            # Request 3 years of daily data
            data = fred.get_data(
                ['FEDFUNDS', 'DGS10'], 
                '2021-01-01', '2023-12-31'
            )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 1000  # Should have substantial data
        
        # Performance assertion - should complete within reasonable time
        assert duration < 30  # Should complete within 30 seconds
        
        # Data quality checks
        for col in data.columns:
            if col in data.columns:
                assert data[col].notna().sum() > 500  # Should have substantial data
    
    @skip_if_no_fred()
    def test_rate_limiting_compliance(self):
        """Test that workflows comply with rate limiting"""
        start_time = datetime.now()
        request_count = 0
        
        with create_data_source('fred') as fred:
            # Make several metadata requests (lightweight)
            variables = ['FEDFUNDS', 'DGS10', 'UNRATE', 'CPIAUCSL']
            
            for var in variables:
                try:
                    metadata = fred.get_variable_metadata(var)
                    if isinstance(metadata, dict):
                        request_count += 1
                except DataRetrievalError:
                    # Some variables might not be available
                    continue
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should have made multiple requests
        assert request_count >= 2
        
        # Rate limiting should prevent requests from being too fast
        # FRED allows 120 requests/minute, so 4 requests should take at least some time
        if request_count >= 4:
            assert duration > 1  # Should take at least 1 second for rate limiting


class TestWorkflowDocumentation:
    """Test workflows match documented usage patterns"""
    
    @skip_if_no_fred()
    def test_readme_example_workflow(self):
        """Test workflow from README examples"""
        # This matches the README example
        from src.federal_reserve_etl import create_data_source
        
        # Test the documented workflow
        with create_data_source('fred') as fred:
            # Extract data as shown in README
            df = fred.get_data(
                variables=['FEDFUNDS', 'DGS10'],
                start_date='2023-01-01',
                end_date='2023-01-31'
            )
            
            # Get metadata as shown in README
            metadata = fred.get_variable_metadata('FEDFUNDS')
            
            # Verify results match expectations
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
            assert isinstance(metadata, dict)
            
            # Should have the requested variables
            expected_vars = ['FEDFUNDS', 'DGS10']
            available_vars = [var for var in expected_vars if var in df.columns]
            assert len(available_vars) >= 1
    
    @skip_if_no_fred()
    def test_jupyter_notebook_workflow(self):
        """Test workflow similar to Jupyter notebook"""
        # Simulate interactive analysis workflow
        results = {}
        
        with create_data_source('fred') as fred:
            # Step 1: Explore available data
            metadata = fred.get_variable_metadata('FEDFUNDS')
            results['metadata'] = metadata
            
            # Step 2: Extract initial dataset
            data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-03-31')
            results['data'] = data
            
            # Step 3: Expand to multiple variables
            multi_data = fred.get_data(
                ['FEDFUNDS', 'DGS10'], 
                '2023-01-01', '2023-03-31'
            )
            results['multi_data'] = multi_data
        
        # Verify all steps completed successfully
        assert 'metadata' in results
        assert 'data' in results  
        assert 'multi_data' in results
        
        assert isinstance(results['metadata'], dict)
        assert isinstance(results['data'], pd.DataFrame)
        assert isinstance(results['multi_data'], pd.DataFrame)
        
        assert len(results['data']) > 0
        assert len(results['multi_data']) > 0