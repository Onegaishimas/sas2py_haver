#!/usr/bin/env python3
"""
Federal Reserve Data Extraction Tool

Command-line interface for extracting economic data from Federal Reserve
data sources including FRED and Haver Analytics APIs.

Usage:
    python extract_fed_data.py --source fred --variables FEDFUNDS,DGS10 --start-date 2020-01-01 --end-date 2020-12-31
    python extract_fed_data.py --source haver --variables GDP,CPI --output data.csv
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from federal_reserve_etl import (
    create_data_source,
    get_config_manager,
    validate_source_credentials,
    get_setup_instructions,
    setup_logging,
    get_logger
)
from federal_reserve_etl.utils import (
    ConfigurationError,
    ConnectionError,
    AuthenticationError,
    DataRetrievalError,
    ValidationError
)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description='Federal Reserve Data Extraction Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract FRED data for federal funds rate and 10-year treasury
  python extract_fed_data.py --source fred --variables FEDFUNDS,DGS10 \\
    --start-date 2020-01-01 --end-date 2020-12-31 --output fred_rates.csv

  # Extract Haver data with custom configuration
  python extract_fed_data.py --source haver --variables GDP,CPI \\
    --start-date 2019-01-01 --output haver_data.csv --format json

  # List available configuration and check credentials
  python extract_fed_data.py --check-credentials

  # Get setup instructions for data sources
  python extract_fed_data.py --setup-help

Environment Variables:
  FRED_API_KEY       FRED API authentication key
  HAVER_USERNAME     Haver Analytics username  
  HAVER_PASSWORD     Haver Analytics password
  FED_ETL_CACHE_DIR  Cache directory for downloaded data
  FED_ETL_LOG_LEVEL  Logging level (DEBUG, INFO, WARNING, ERROR)
        """
    )
    
    # Data source selection
    parser.add_argument(
        '--source', '-s',
        choices=['fred', 'haver', 'FRED', 'HAVER'],
        help='Data source to extract from (fred or haver)'
    )
    
    # Variable specification
    parser.add_argument(
        '--variables', '-v',
        type=str,
        help='Comma-separated list of variable codes (e.g., FEDFUNDS,DGS10)'
    )
    
    # Date range specification
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date in YYYY-MM-DD format (default: 1 year ago)'
    )
    
    parser.add_argument(
        '--end-date', 
        type=str,
        help='End date in YYYY-MM-DD format (default: today)'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json', 'excel'],
        default='csv',
        help='Output format (default: csv)'
    )
    
    parser.add_argument(
        '--wide-format',
        action='store_true',
        help='Output in wide format (variables as columns, default)'
    )
    
    parser.add_argument(
        '--long-format',
        action='store_true', 
        help='Output in long format (date, variable, value columns)'
    )
    
    # API configuration
    parser.add_argument(
        '--fred-api-key',
        type=str,
        help='FRED API key (overrides FRED_API_KEY environment variable)'
    )
    
    parser.add_argument(
        '--haver-username',
        type=str,
        help='Haver username (overrides HAVER_USERNAME environment variable)'
    )
    
    parser.add_argument(
        '--haver-password',
        type=str,
        help='Haver password (overrides HAVER_PASSWORD environment variable)'
    )
    
    # Operational options
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--rate-limit',
        type=int,
        help='Custom rate limit (requests per minute for FRED, per second for Haver)'
    )
    
    parser.add_argument(
        '--include-metadata',
        action='store_true',
        help='Include variable metadata in output'
    )
    
    parser.add_argument(
        '--cache',
        action='store_true',
        help='Enable data caching'
    )
    
    # Utility options
    parser.add_argument(
        '--check-credentials',
        action='store_true',
        help='Check credential configuration and exit'
    )
    
    parser.add_argument(
        '--setup-help',
        action='store_true',
        help='Show credential setup instructions and exit'
    )
    
    parser.add_argument(
        '--list-sources',
        action='store_true',
        help='List available data sources and exit'
    )
    
    parser.add_argument(
        '--validate-variables',
        action='store_true',
        help='Validate variable codes without extracting data'
    )
    
    # Logging configuration
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log to file instead of console'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress all output except errors'
    )
    
    parser.add_argument(
        '--verbose', '-V',
        action='store_true', 
        help='Enable verbose output'
    )
    
    # Version info
    parser.add_argument(
        '--version',
        action='version',
        version='Federal Reserve ETL Tool v0.1.0'
    )
    
    return parser


def setup_logging_from_args(args: argparse.Namespace) -> None:
    """
    Configure logging based on command-line arguments
    
    Args:
        args: Parsed command-line arguments
    """
    # Determine log level
    if args.quiet:
        level = 'ERROR'
    elif args.verbose:
        level = 'DEBUG'  
    else:
        level = args.log_level
    
    # Configure logging (force initialization to prevent duplicates)
    setup_logging(
        log_level=level,
        log_file=args.log_file,
        enable_console=not args.quiet,
        force_reinit=True
    )


def validate_date_arguments(args: argparse.Namespace) -> tuple[str, str]:
    """
    Validate and normalize date arguments
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
        
    Raises:
        ValidationError: If date arguments are invalid
    """
    logger = get_logger(__name__)
    
    # Set default dates if not provided
    if not args.start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        logger.info(f"Using default start date: {start_date}")
    else:
        start_date = args.start_date
    
    if not args.end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"Using default end date: {end_date}")
    else:
        end_date = args.end_date
    
    # Validate date format
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        raise ValidationError(
            f"Invalid date format. Use YYYY-MM-DD: {str(e)}",
            field="date_format"
        )
    
    # Validate date range
    if start_dt >= end_dt:
        raise ValidationError(
            "Start date must be before end date",
            field="date_range"
        )
    
    # Check for reasonable date range
    if (end_dt - start_dt).days > 10000:  # ~27 years
        logger.warning("Large date range requested - this may take a long time")
    
    return start_date, end_date


def parse_variables(variable_string: str) -> List[str]:
    """
    Parse comma-separated variable string
    
    Args:
        variable_string: Comma-separated variable codes
        
    Returns:
        List of variable codes
        
    Raises:
        ValidationError: If variable string is invalid
    """
    if not variable_string or not variable_string.strip():
        raise ValidationError(
            "Variable list cannot be empty",
            field="variables"
        )
    
    # Split by comma and clean up
    variables = [var.strip().upper() for var in variable_string.split(',')]
    variables = [var for var in variables if var]  # Remove empty strings
    
    if not variables:
        raise ValidationError(
            "No valid variable codes found",
            field="variables"
        )
    
    # Basic validation
    for var in variables:
        if len(var) > 50:
            raise ValidationError(
                f"Variable code too long: {var}",
                field="variable_length"
            )
        if not var.replace('_', '').replace('-', '').isalnum():
            raise ValidationError(
                f"Invalid variable code format: {var}",
                field="variable_format"
            )
    
    return variables


def check_credentials_command() -> int:
    """
    Check credential configuration and report status
    
    Returns:
        Exit code (0 for success, 1 for missing credentials)
    """
    logger = get_logger(__name__)
    config_mgr = get_config_manager()
    
    print("Federal Reserve ETL - Credential Status Check")
    print("=" * 50)
    
    sources = ['fred', 'haver']
    all_valid = True
    
    for source in sources:
        source_name = source.upper()
        print(f"\n{source_name} Data Source:")
        
        try:
            is_valid = validate_source_credentials(source)
            if is_valid:
                print(f"  ✅ Credentials: Valid")
            else:
                print(f"  ❌ Credentials: Invalid or missing")
                missing = config_mgr.get_missing_credentials(source)
                for cred in missing:
                    print(f"     Missing: {cred}")
                all_valid = False
                
        except Exception as e:
            print(f"  ❌ Error checking credentials: {str(e)}")
            all_valid = False
    
    if all_valid:
        print(f"\n✅ All credentials are properly configured!")
        return 0
    else:
        print(f"\n❌ Some credentials are missing or invalid.")
        print(f"Use --setup-help for configuration instructions.")
        return 1


def setup_help_command() -> int:
    """
    Display credential setup instructions
    
    Returns:
        Exit code (always 0)
    """
    config_mgr = get_config_manager()
    instructions = config_mgr.get_credential_setup_instructions()
    
    print("Federal Reserve ETL - Setup Instructions")
    print("=" * 50)
    
    for source, instruction in instructions.items():
        print(f"\n{source.upper()} Setup:")
        print(instruction)
    
    print("\nAdditional Configuration:")
    print("""
Optional Environment Variables:
  FED_ETL_CACHE_DIR   Directory for caching data (default: .cache/federal_reserve_etl)
  FED_ETL_LOG_LEVEL   Logging level (DEBUG, INFO, WARNING, ERROR)
  FED_ETL_MAX_WORKERS Maximum concurrent workers (default: 4)

Configuration File:
  You can also create a JSON configuration file at:
  - federal_reserve_etl_config.json (current directory)
  - ~/.federal_reserve_etl/config.json (user home)
  - /etc/federal_reserve_etl/config.json (system-wide)
    """)
    
    return 0


def list_sources_command() -> int:
    """
    List available data sources
    
    Returns:
        Exit code (always 0)
    """
    from federal_reserve_etl.data_sources import get_available_sources
    
    print("Federal Reserve ETL - Available Data Sources")
    print("=" * 50)
    
    sources = get_available_sources()
    for source_id, class_name in sources.items():
        print(f"  {source_id:10} -> {class_name}")
    
    print(f"\nTotal: {len(sources)} data sources available")
    return 0


def extract_data_command(args: argparse.Namespace) -> int:
    """
    Main data extraction command
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger = get_logger(__name__)
    
    try:
        # Validate required arguments
        if not args.source:
            logger.error("Data source (--source) is required for extraction")
            return 1
        
        if not args.variables:
            logger.error("Variables (--variables) are required for extraction")
            return 1
        
        # Parse and validate inputs
        variables = parse_variables(args.variables)
        start_date, end_date = validate_date_arguments(args)
        
        logger.info(f"Extracting data from {args.source.upper()} for variables: {', '.join(variables)}")
        logger.info(f"Date range: {start_date} to {end_date}")
        
        # Create data source configuration
        config = {}
        if args.timeout:
            config['timeout'] = args.timeout
        if args.rate_limit:
            config['rate_limit'] = args.rate_limit
        
        # Create data source with credentials from command line if provided
        create_kwargs = {}
        if args.fred_api_key:
            create_kwargs['api_key'] = args.fred_api_key
        if args.haver_username:
            create_kwargs['username'] = args.haver_username
        if args.haver_password:
            create_kwargs['password'] = args.haver_password
        
        # Create and connect to data source
        data_source = create_data_source(args.source, config=config, **create_kwargs)
        
        with data_source:  # Use context manager for automatic connection management
            logger.info(f"Connected to {args.source.upper()} API")
            
            # Extract data
            df = data_source.get_data(
                variables=variables,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"Data extracted: {df.shape[0]} observations, {df.shape[1]} variables")
            
            # Transform to long format if requested
            if args.long_format and not args.wide_format:
                df_long = df.reset_index().melt(
                    id_vars=['Date'],
                    var_name='InstrumentName', 
                    value_name='InterestRatePct'
                )
                df = df_long
                logger.info("Data transformed to long format")
            
            # Include metadata if requested
            metadata = None
            if args.include_metadata:
                try:
                    metadata = data_source.get_metadata(variables)
                    logger.info("Metadata retrieved")
                except Exception as e:
                    logger.warning(f"Failed to retrieve metadata: {str(e)}")
            
            # Prepare output data before context manager closes
            output_data_prepared = None
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Prepare data for output
                if args.format == 'csv':
                    output_data_prepared = ('csv', df.to_csv(index=True), output_path)
                elif args.format == 'json':
                    json_data = {'data': df.to_dict('records')}
                    if metadata:
                        json_data['metadata'] = metadata
                    output_data_prepared = ('json', json.dumps(json_data, indent=2, default=str), output_path)
                elif args.format == 'excel':
                    output_data_prepared = ('excel', df, metadata, output_path)
            else:
                # Prepare stdout output
                if args.format == 'csv':
                    output_data_prepared = ('csv_stdout', df.to_csv(index=True))
                elif args.format == 'json':
                    json_data = {'data': df.to_dict('records')}
                    if metadata:
                        json_data['metadata'] = metadata
                    output_data_prepared = ('json_stdout', json.dumps(json_data, indent=2, default=str))
                else:
                    output_data_prepared = ('string_stdout', df.to_string())
        
        # Context manager closes here - disconnect happens now
        logger.info("Data extraction completed, connection closed")
        
        # Now handle output after proper cleanup
        if output_data_prepared:
            format_type = output_data_prepared[0]
            
            if format_type == 'csv':
                _, csv_content, output_path = output_data_prepared
                with open(output_path, 'w') as f:
                    f.write(csv_content)
                logger.info(f"✅ Data successfully saved to {output_path}")
                
            elif format_type == 'json':
                _, json_content, output_path = output_data_prepared
                with open(output_path, 'w') as f:
                    f.write(json_content)
                logger.info(f"✅ Data successfully saved to {output_path}")
                
            elif format_type == 'excel':
                _, df_data, metadata_data, output_path = output_data_prepared
                import pandas as pd
                with pd.ExcelWriter(output_path) as writer:
                    df_data.to_excel(writer, sheet_name='Data', index=True)
                    if metadata_data:
                        metadata_df = pd.DataFrame(metadata_data).T
                        metadata_df.to_excel(writer, sheet_name='Metadata', index=True)
                logger.info(f"✅ Data successfully saved to {output_path}")
                
            elif format_type.endswith('_stdout'):
                # Output to stdout
                _, content = output_data_prepared
                print(content)
                logger.info("Data output to stdout")
        
        # Final success message - use logging to ensure proper ordering
        logger.info("=" * 50)
        logger.info("🎉 EXTRACTION COMPLETE")
        logger.info(f"✅ Data source: {args.source.upper()}")
        logger.info(f"📊 Variables: {', '.join(variables)}")  
        logger.info(f"📅 Period: {start_date} to {end_date}")
        if args.output:
            logger.info(f"💾 Output: {output_data_prepared[2] if len(output_data_prepared) > 2 else 'stdout'}")
        logger.info("=" * 50)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except (ConfigurationError, ValidationError) as e:
        logger.error(f"Configuration error: {str(e)}")
        return 1
    except (ConnectionError, AuthenticationError) as e:
        logger.error(f"Connection error: {str(e)}")
        return 1
    except DataRetrievalError as e:
        logger.error(f"Data retrieval error: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if args.verbose:
            import traceback
            logger.debug(traceback.format_exc())
        return 1


def main() -> int:
    """
    Main entry point
    
    Returns:
        Exit code
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Configure logging first
    setup_logging_from_args(args)
    
    # Handle utility commands
    if args.check_credentials:
        return check_credentials_command()
    
    if args.setup_help:
        return setup_help_command()
    
    if args.list_sources:
        return list_sources_command()
    
    # Main data extraction
    return extract_data_command(args)


if __name__ == '__main__':
    sys.exit(main())