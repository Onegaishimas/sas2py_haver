#!/usr/bin/env python3
"""
Basic Usage Examples - Federal Reserve ETL Pipeline

This script demonstrates basic usage patterns for extracting Federal Reserve
economic data using the ETL pipeline.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from federal_reserve_etl import create_data_source
from federal_reserve_etl.utils.logging import setup_logging
from federal_reserve_etl.utils.exceptions import (
    AuthenticationError,
    DataRetrievalError,
    RateLimitError,
    ConnectionError
)


def setup_environment():
    """Set up logging and verify API credentials"""
    print("🔧 Setting up Federal Reserve ETL Pipeline...")
    
    # Initialize logging
    setup_logging(log_level='INFO', console_output=True)
    
    # Check for required API key
    fred_key = os.getenv('FRED_API_KEY')
    if not fred_key:
        print("❌ FRED_API_KEY environment variable is required")
        print("   Get your API key from: https://fred.stlouisfed.org/docs/api/api_key.html")
        print("   Then run: export FRED_API_KEY='your_32_character_key'")
        return False
    
    if len(fred_key) != 32:
        print(f"❌ FRED API key should be 32 characters, got {len(fred_key)}")
        return False
    
    print(f"✅ FRED API key configured: {fred_key[:4]}...{fred_key[-4:]}")
    return True


def basic_single_variable_example():
    """Example: Extract Federal Funds Rate for the last year"""
    print("\n📊 Example 1: Single Variable Extraction")
    print("=" * 50)
    
    # Calculate date range (last 12 months)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    try:
        with create_data_source('fred') as fred:
            print(f"📈 Extracting Federal Funds Rate from {start_date} to {end_date}")
            
            # Get data
            data = fred.get_data('FEDFUNDS', start_date, end_date)
            
            # Get metadata
            metadata = fred.get_variable_metadata('FEDFUNDS')
            
            print(f"✅ Retrieved {len(data)} observations")
            print(f"📋 Variable: {metadata['title']}")
            print(f"📏 Units: {metadata['units']}")
            print(f"🔄 Frequency: {metadata['frequency']}")
            
            # Show recent data
            print(f"\n📊 Recent data (last 5 observations):")
            print(data.tail())
            
            # Save to file
            output_file = f"federal_funds_rate_{start_date}_to_{end_date}.csv"
            data.to_csv(output_file)
            print(f"💾 Data saved to: {output_file}")
            
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
    except DataRetrievalError as e:
        print(f"❌ Data retrieval failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def multiple_variables_example():
    """Example: Extract multiple economic indicators"""
    print("\n📊 Example 2: Multiple Variables Extraction")
    print("=" * 50)
    
    # Define economic indicators
    variables = {
        'FEDFUNDS': 'Federal Funds Rate',
        'DGS10': '10-Year Treasury Rate',
        'UNRATE': 'Unemployment Rate',
        'CPIAUCSL': 'Consumer Price Index'
    }
    
    # Date range: 2023
    start_date = '2023-01-01'
    end_date = '2023-12-31'
    
    try:
        with create_data_source('fred') as fred:
            print(f"📈 Extracting {len(variables)} variables from {start_date} to {end_date}")
            
            # Get data for all variables
            data = fred.get_data(list(variables.keys()), start_date, end_date)
            
            # Get metadata for all variables
            metadata = fred.get_metadata(list(variables.keys()))
            
            print(f"✅ Retrieved data with shape: {data.shape}")
            
            # Display variable information
            print("\n📋 Variables extracted:")
            for var_code, description in variables.items():
                if var_code in metadata:
                    var_meta = metadata[var_code]
                    print(f"  • {var_code}: {var_meta.get('title', description)}")
                    print(f"    Units: {var_meta.get('units', 'N/A')}")
                    print(f"    Frequency: {var_meta.get('frequency', 'N/A')}")
            
            # Show data summary
            print(f"\n📊 Data summary:")
            print(data.describe())
            
            # Save to Excel with multiple sheets
            output_file = f"economic_indicators_{start_date}_to_{end_date}.xlsx"
            with pd.ExcelWriter(output_file) as writer:
                data.to_excel(writer, sheet_name='Data')
                
                # Create metadata sheet
                metadata_df = pd.DataFrame.from_dict(metadata, orient='index')
                metadata_df.to_excel(writer, sheet_name='Metadata')
            
            print(f"💾 Data saved to: {output_file}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def error_handling_example():
    """Example: Demonstrate comprehensive error handling"""
    print("\n📊 Example 3: Error Handling Demonstration")
    print("=" * 50)
    
    # Test cases for different error scenarios
    test_cases = [
        {
            'name': 'Invalid Variable Code',
            'variables': 'INVALID_VAR_CODE',
            'start_date': '2023-01-01',
            'end_date': '2023-01-31'
        },
        {
            'name': 'Invalid Date Range',
            'variables': 'FEDFUNDS',
            'start_date': '2050-01-01',  # Future date
            'end_date': '2050-12-31'
        },
        {
            'name': 'Empty Date Range',
            'variables': 'FEDFUNDS', 
            'start_date': '2023-01-02',
            'end_date': '2023-01-01'  # End before start
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        try:
            with create_data_source('fred') as fred:
                data = fred.get_data(
                    test_case['variables'],
                    test_case['start_date'], 
                    test_case['end_date']
                )
                print(f"✅ Unexpected success: {len(data)} observations")
                
        except AuthenticationError as e:
            print(f"❌ Authentication Error: {e}")
            print(f"   Context: {e.context}")
            
        except DataRetrievalError as e:
            print(f"⚠️  Data Retrieval Error: {e}")
            print(f"   Context: {e.context}")
            
        except ValidationError as e:
            print(f"⚠️  Validation Error: {e}")
            print(f"   Context: {e.context}")
            
        except RateLimitError as e:
            print(f"⏳ Rate Limit Error: {e}")
            if hasattr(e, 'wait_time'):
                print(f"   Suggested wait time: {e.wait_time} seconds")
            
        except ConnectionError as e:
            print(f"🌐 Connection Error: {e}")
            print(f"   Context: {e.context}")
            
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")


def rate_limiting_example():
    """Example: Demonstrate rate limiting behavior"""
    print("\n📊 Example 4: Rate Limiting Demonstration")
    print("=" * 50)
    
    # Create data source with custom rate limiting
    config = {
        'rate_limit': 10,  # Much slower than default 120
        'timeout': 30
    }
    
    try:
        with create_data_source('fred', **config) as fred:
            print(f"🚦 Using custom rate limit: {config['rate_limit']} requests/minute")
            
            # Make several rapid requests
            variables = ['FEDFUNDS', 'DGS10', 'UNRATE', 'CPIAUCSL', 'GDP']
            results = {}
            
            for i, variable in enumerate(variables, 1):
                print(f"📊 Request {i}/{len(variables)}: {variable}")
                start_time = datetime.now()
                
                try:
                    data = fred.get_data(variable, '2023-01-01', '2023-01-31')
                    end_time = datetime.now()
                    elapsed = (end_time - start_time).total_seconds()
                    
                    results[variable] = {
                        'observations': len(data),
                        'elapsed_time': elapsed
                    }
                    
                    print(f"   ✅ Success: {len(data)} observations in {elapsed:.2f}s")
                    
                except RateLimitError as e:
                    print(f"   ⏳ Rate limited: {e}")
                    print(f"      Pipeline will automatically retry...")
                    
            print(f"\n📊 Summary of requests:")
            for var, result in results.items():
                print(f"  {var}: {result['observations']} obs in {result['elapsed_time']:.2f}s")
                
    except Exception as e:
        print(f"❌ Error: {e}")


def configuration_examples():
    """Example: Different configuration patterns"""
    print("\n📊 Example 5: Configuration Patterns")
    print("=" * 50)
    
    configurations = [
        {
            'name': 'Default Configuration',
            'config': {}
        },
        {
            'name': 'High Timeout Configuration',
            'config': {'timeout': 60, 'max_retries': 5}
        },
        {
            'name': 'Conservative Rate Limiting',
            'config': {'rate_limit': 60, 'retry_delay': 2.0}
        }
    ]
    
    for config_example in configurations:
        print(f"\n🔧 {config_example['name']}:")
        config = config_example['config']
        
        if config:
            for key, value in config.items():
                print(f"   {key}: {value}")
        else:
            print("   Using default settings")
        
        try:
            with create_data_source('fred', **config) as fred:
                # Test with a simple request
                data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-05')
                print(f"   ✅ Success: {len(data)} observations retrieved")
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")


def main():
    """Run all examples"""
    print("🚀 Federal Reserve ETL Pipeline - Usage Examples")
    print("=" * 60)
    
    # Set up environment
    if not setup_environment():
        return 1
    
    # Import pandas here after we know the environment is set up
    global pd
    import pandas as pd
    
    # Run examples
    try:
        basic_single_variable_example()
        multiple_variables_example()
        error_handling_example()
        rate_limiting_example()
        configuration_examples()
        
        print("\n🎉 All examples completed successfully!")
        print("💡 Check the generated files for exported data")
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Examples failed with error: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)