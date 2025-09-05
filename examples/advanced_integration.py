#!/usr/bin/env python3
"""
Advanced Integration Examples - Federal Reserve ETL Pipeline

This script demonstrates advanced integration patterns, including:
- Multi-source data combination
- Custom data processing workflows
- Integration with popular data science libraries
- Production deployment patterns
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from federal_reserve_etl import create_data_source
from federal_reserve_etl.utils.logging import setup_logging
from federal_reserve_etl.utils.exceptions import FederalReserveETLError


class EconomicDataPipeline:
    """
    Advanced ETL pipeline for economic data integration
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.setup_logging()
        
    def setup_logging(self):
        """Initialize logging configuration"""
        log_level = self.config.get('log_level', 'INFO')
        setup_logging(log_level=log_level, console_output=True)
        
    def extract_fred_data(self, variables: List[str], start_date: str, end_date: str) -> Optional['pd.DataFrame']:
        """Extract data from FRED API with error handling"""
        try:
            with create_data_source('fred', **self.config) as fred:
                print(f"📊 Extracting FRED data: {variables}")
                
                # Get data and metadata
                data = fred.get_data(variables, start_date, end_date)
                metadata = fred.get_metadata(variables)
                
                # Add metadata as attributes
                for var in variables:
                    if var in metadata and var in data.columns:
                        data[var].attrs = metadata[var]
                
                print(f"✅ FRED extraction successful: {data.shape}")
                return data
                
        except FederalReserveETLError as e:
            print(f"❌ FRED extraction failed: {e}")
            return None
            
    def extract_haver_data(self, variables: List[str], start_date: str, end_date: str) -> Optional['pd.DataFrame']:
        """Extract data from Haver API with graceful fallback"""
        try:
            with create_data_source('haver', **self.config) as haver:
                print(f"📊 Extracting Haver data: {variables}")
                
                data = haver.get_data(variables, start_date, end_date)
                metadata = haver.get_metadata(variables)
                
                # Add metadata as attributes
                for var in variables:
                    if var in metadata and var in data.columns:
                        data[var].attrs = metadata[var]
                
                print(f"✅ Haver extraction successful: {data.shape}")
                return data
                
        except FederalReserveETLError as e:
            print(f"⚠️  Haver extraction failed (graceful fallback): {e}")
            return None
        except Exception as e:
            print(f"⚠️  Haver not available: {e}")
            return None
            
    def combine_data_sources(self, fred_data: 'pd.DataFrame', haver_data: Optional['pd.DataFrame']) -> 'pd.DataFrame':
        """Combine data from multiple sources with metadata preservation"""
        print("🔗 Combining data sources...")
        
        if haver_data is not None:
            # Combine dataframes
            combined = pd.concat([fred_data, haver_data], axis=1)
            print(f"✅ Combined data shape: {combined.shape}")
        else:
            combined = fred_data.copy()
            print(f"✅ Using FRED data only: {combined.shape}")
        
        # Sort by date and forward fill missing values
        combined = combined.sort_index()
        combined = combined.fillna(method='forward')
        
        return combined
        
    def apply_transformations(self, data: 'pd.DataFrame') -> 'pd.DataFrame':
        """Apply common economic data transformations"""
        print("⚙️  Applying data transformations...")
        
        transformed = data.copy()
        
        # Calculate year-over-year changes for rates
        for col in transformed.columns:
            if any(keyword in col.upper() for keyword in ['RATE', 'PERCENT', '%']):
                transformed[f'{col}_YoY_Change'] = transformed[col].diff(12)  # Assumes monthly data
        
        # Calculate moving averages
        for col in transformed.columns:
            if not col.endswith('_YoY_Change'):  # Don't calculate MA for changes
                transformed[f'{col}_3M_MA'] = transformed[col].rolling(window=3).mean()
                transformed[f'{col}_12M_MA'] = transformed[col].rolling(window=12).mean()
        
        print(f"✅ Transformations applied. New shape: {transformed.shape}")
        return transformed
        
    def generate_economic_indicators(self, data: 'pd.DataFrame') -> Dict:
        """Calculate key economic indicators and relationships"""
        print("📈 Generating economic indicators...")
        
        indicators = {}
        
        # Yield curve analysis (if both rates available)
        if 'FEDFUNDS' in data.columns and 'DGS10' in data.columns:
            data['Yield_Spread'] = data['DGS10'] - data['FEDFUNDS']
            indicators['current_yield_spread'] = data['Yield_Spread'].iloc[-1]
            indicators['avg_yield_spread'] = data['Yield_Spread'].mean()
            
        # Volatility analysis
        for col in data.select_dtypes(include=[float, int]).columns:
            if not any(suffix in col for suffix in ['_MA', '_Change', '_Spread']):
                volatility = data[col].rolling(window=12).std()
                indicators[f'{col}_volatility'] = volatility.iloc[-1]
        
        # Trend analysis
        for col in data.select_dtypes(include=[float, int]).columns:
            if not any(suffix in col for suffix in ['_MA', '_Change', '_Spread']):
                recent_trend = data[col].tail(6).pct_change().mean() * 100
                indicators[f'{col}_6m_trend_pct'] = recent_trend
        
        print(f"✅ Generated {len(indicators)} economic indicators")
        return indicators
        
    def export_results(self, data: 'pd.DataFrame', indicators: Dict, output_dir: str = 'output'):
        """Export results in multiple formats with comprehensive documentation"""
        print(f"💾 Exporting results to {output_dir}...")
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export data to CSV
        csv_file = Path(output_dir) / f'economic_data_{timestamp}.csv'
        data.to_csv(csv_file)
        print(f"✅ CSV exported: {csv_file}")
        
        # Export to Excel with multiple sheets
        excel_file = Path(output_dir) / f'economic_analysis_{timestamp}.xlsx'
        with pd.ExcelWriter(excel_file) as writer:
            # Raw data
            data.to_excel(writer, sheet_name='Raw_Data')
            
            # Summary statistics
            data.describe().to_excel(writer, sheet_name='Summary_Stats')
            
            # Economic indicators
            indicators_df = pd.DataFrame.from_dict(indicators, orient='index', columns=['Value'])
            indicators_df.to_excel(writer, sheet_name='Economic_Indicators')
            
            # Correlation matrix
            correlation_matrix = data.select_dtypes(include=[float, int]).corr()
            correlation_matrix.to_excel(writer, sheet_name='Correlations')
        
        print(f"✅ Excel exported: {excel_file}")
        
        # Export indicators to JSON
        json_file = Path(output_dir) / f'economic_indicators_{timestamp}.json'
        with open(json_file, 'w') as f:
            json.dump(indicators, f, indent=2, default=str)
        print(f"✅ JSON exported: {json_file}")
        
        # Create summary report
        self._create_summary_report(data, indicators, output_dir, timestamp)
        
    def _create_summary_report(self, data: 'pd.DataFrame', indicators: Dict, output_dir: str, timestamp: str):
        """Create a markdown summary report"""
        report_file = Path(output_dir) / f'economic_report_{timestamp}.md'
        
        with open(report_file, 'w') as f:
            f.write(f"# Economic Data Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Data Overview\n\n")
            f.write(f"- **Data Points:** {len(data)} observations\n")
            f.write(f"- **Variables:** {len(data.columns)} variables\n")
            f.write(f"- **Date Range:** {data.index.min()} to {data.index.max()}\n\n")
            
            f.write("## Variables Analyzed\n\n")
            for col in data.columns:
                if hasattr(data[col], 'attrs') and data[col].attrs:
                    title = data[col].attrs.get('title', col)
                    units = data[col].attrs.get('units', 'N/A')
                    f.write(f"- **{col}:** {title} ({units})\n")
                else:
                    f.write(f"- **{col}:** Economic indicator\n")
            
            f.write("\n## Key Economic Indicators\n\n")
            for indicator, value in indicators.items():
                if isinstance(value, float):
                    f.write(f"- **{indicator}:** {value:.4f}\n")
                else:
                    f.write(f"- **{indicator}:** {value}\n")
            
            f.write("\n## Data Quality Notes\n\n")
            missing_data = data.isnull().sum()
            if missing_data.sum() > 0:
                f.write("Missing data points:\n")
                for col, missing_count in missing_data[missing_data > 0].items():
                    f.write(f"- {col}: {missing_count} missing values\n")
            else:
                f.write("- No missing data points detected\n")
        
        print(f"✅ Report exported: {report_file}")


def demonstrate_visualization_integration():
    """Example: Integration with visualization libraries"""
    print("\n📊 Visualization Integration Example")
    print("=" * 50)
    
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Extract sample data
        with create_data_source('fred') as fred:
            data = fred.get_data(['FEDFUNDS', 'DGS10'], '2020-01-01', '2023-12-31')
        
        # Create visualizations
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Federal Reserve Economic Data Analysis', fontsize=16)
        
        # Time series plot
        data.plot(ax=axes[0, 0], title='Interest Rates Over Time')
        axes[0, 0].set_ylabel('Rate (%)')
        
        # Yield spread
        data['Yield_Spread'] = data['DGS10'] - data['FEDFUNDS'] 
        data['Yield_Spread'].plot(ax=axes[0, 1], title='10Y-Fed Funds Spread', color='green')
        axes[0, 1].set_ylabel('Spread (%)')
        
        # Distribution plot
        data['FEDFUNDS'].hist(ax=axes[1, 0], bins=30, alpha=0.7)
        axes[1, 0].set_title('Federal Funds Rate Distribution')
        axes[1, 0].set_xlabel('Rate (%)')
        
        # Correlation heatmap
        correlation = data.corr()
        sns.heatmap(correlation, ax=axes[1, 1], annot=True, cmap='coolwarm', center=0)
        axes[1, 1].set_title('Correlation Matrix')
        
        plt.tight_layout()
        plt.savefig('economic_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("✅ Visualization created: economic_analysis.png")
        
    except ImportError as e:
        print(f"⚠️  Visualization libraries not available: {e}")
    except Exception as e:
        print(f"❌ Visualization failed: {e}")


def demonstrate_machine_learning_integration():
    """Example: Integration with machine learning libraries"""
    print("\n📊 Machine Learning Integration Example")
    print("=" * 50)
    
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_squared_error, r2_score
        
        # Extract economic data
        with create_data_source('fred') as fred:
            data = fred.get_data(['FEDFUNDS', 'DGS10', 'UNRATE'], '2010-01-01', '2023-12-31')
        
        # Prepare features and target
        # Predict unemployment rate using interest rates
        data_clean = data.dropna()
        X = data_clean[['FEDFUNDS', 'DGS10']]
        y = data_clean['UNRATE']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"✅ Model Training Complete:")
        print(f"   Mean Squared Error: {mse:.4f}")
        print(f"   R² Score: {r2:.4f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\n📊 Feature Importance:")
        for _, row in feature_importance.iterrows():
            print(f"   {row['feature']}: {row['importance']:.4f}")
            
    except ImportError as e:
        print(f"⚠️  Machine learning libraries not available: {e}")
    except Exception as e:
        print(f"❌ Machine learning integration failed: {e}")


def production_deployment_example():
    """Example: Production deployment patterns"""
    print("\n📊 Production Deployment Example")
    print("=" * 50)
    
    # Configuration for production environment
    production_config = {
        'rate_limit': 100,  # Conservative rate limiting
        'timeout': 60,      # Longer timeout for stability
        'max_retries': 5,   # More retries for reliability
        'retry_delay': 2.0  # Longer delays between retries
    }
    
    # Create pipeline
    pipeline = EconomicDataPipeline(production_config)
    
    # Production data extraction workflow
    fred_variables = ['FEDFUNDS', 'DGS10', 'UNRATE', 'CPIAUCSL']
    haver_variables = ['GDP', 'PAYEMS']  # Example Haver variables
    
    # Date range for analysis
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=2*365)).strftime('%Y-%m-%d')  # 2 years
    
    print(f"🏭 Production pipeline execution:")
    print(f"   Date range: {start_date} to {end_date}")
    print(f"   FRED variables: {fred_variables}")
    print(f"   Haver variables: {haver_variables}")
    
    # Execute pipeline
    try:
        # Extract data from sources
        fred_data = pipeline.extract_fred_data(fred_variables, start_date, end_date)
        haver_data = pipeline.extract_haver_data(haver_variables, start_date, end_date)
        
        if fred_data is not None:
            # Combine and transform data
            combined_data = pipeline.combine_data_sources(fred_data, haver_data)
            transformed_data = pipeline.apply_transformations(combined_data)
            
            # Generate indicators
            indicators = pipeline.generate_economic_indicators(transformed_data)
            
            # Export results
            pipeline.export_results(transformed_data, indicators)
            
            print("🎉 Production pipeline completed successfully!")
            
        else:
            print("❌ Production pipeline failed: No data extracted")
            
    except Exception as e:
        print(f"❌ Production pipeline failed: {e}")


def main():
    """Run advanced integration examples"""
    print("🚀 Federal Reserve ETL Pipeline - Advanced Integration Examples")
    print("=" * 70)
    
    # Check environment
    if not os.getenv('FRED_API_KEY'):
        print("❌ FRED_API_KEY environment variable is required")
        return 1
    
    # Import pandas globally
    global pd
    import pandas as pd
    
    # Run examples
    try:
        production_deployment_example()
        demonstrate_visualization_integration()
        demonstrate_machine_learning_integration()
        
        print("\n🎉 All advanced examples completed!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Examples failed: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)