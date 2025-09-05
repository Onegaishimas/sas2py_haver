"""
Federal Reserve Data ETL Pipeline

A production-ready command-line ETL tool for extracting Federal Reserve
interest rate and banking metrics from multiple data sources.

Public API:
    - create_data_source: Factory function for data source instantiation
    - FREDDataSource: FRED API client implementation
    - HaverDataSource: Haver Analytics API client implementation
    - Configuration management: get_config_manager(), get_fred_config(), get_haver_config()
    - Utility functions: setup_logging(), validate_dates()
    - transform_to_long_format: Wide-to-long format transformation
    - apply_date_range_filter: Date range filtering and coverage analysis
"""

from .data_sources import DataSource, FREDDataSource, HaverDataSource, create_data_source
from .utils import setup_logging, get_logger
from .config import (
    get_config_manager, 
    get_fred_config, 
    get_haver_config,
    validate_source_credentials,
    get_setup_instructions
)

__version__ = "0.1.0"
__author__ = "Federal Reserve ETL Team"

__all__ = [
    "__version__",
    "__author__",
    "DataSource",
    "FREDDataSource", 
    "HaverDataSource",
    "create_data_source",
    "setup_logging",
    "get_logger",
    "get_config_manager",
    "get_fred_config",
    "get_haver_config",
    "validate_source_credentials",
    "get_setup_instructions"
]