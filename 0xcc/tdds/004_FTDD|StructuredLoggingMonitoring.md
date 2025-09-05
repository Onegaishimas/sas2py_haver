# Technical Design Document: Structured Logging and Monitoring

## 1. System Architecture

### Context Diagram
**Current System**: Federal Reserve ETL Pipeline with error handling, configuration management, and multi-source data extraction
**Feature Integration**: Logging framework provides observability across all system operations, integrating with error handling, performance monitoring, and operational analysis
**External Dependencies**: File system, console output, log aggregation systems (ELK, Splunk), monitoring platforms (Prometheus, Grafana)

### Architecture Patterns
**Design Pattern**: Observer Pattern with Template Method Pattern for specialized loggers
**Architectural Style**: Centralized logging with multiple output channels and structured data format
**Communication Pattern**: Asynchronous logging with buffering to minimize performance impact

## 2. Component Design

### High-Level Components
**Centralized Logger Setup Component**: Main logging configuration and initialization
- Purpose: Configure logging system with multiple handlers and consistent formatting
- Interface: Setup functions with configurable log levels and output destinations
- Dependencies: Configuration management, file system access, console output

**Structured Formatter Component**: JSON and human-readable log formatting
- Purpose: Convert log records to structured formats for machine parsing and human consumption
- Interface: Standard Python logging formatter interface with custom field handling
- Dependencies: JSON serialization, timestamp formatting, sensitive data masking

**Specialized Logger Component**: API operation, performance, and audit logging
- Purpose: Domain-specific logging with standardized context and metrics
- Interface: Specialized logging methods for different operation types
- Dependencies: Base logging framework, performance monitoring, context management

**Stream Handler Component**: Custom output handling with proper stream management
- Purpose: Ensure proper log output ordering and stream flushing for real-time monitoring
- Interface: Standard Python logging handler interface with enhanced stream control
- Dependencies: Console output streams, file handles, log rotation

### Class/Module Structure
```
utils/
└── logging.py                    # Main logging framework
    ├── setup_logging()          # Central logging configuration
    ├── FlushingStreamHandler    # Custom stream handler with flushing
    ├── StructuredFormatter      # JSON log formatter
    ├── SensitiveDataMasker     # Credential and PII masking
    ├── APIOperationLogger      # API request/response logging
    ├── PerformanceLogger       # Timing and resource usage logging
    └── AuditLogger            # User action and data access logging

config.py                        # Logging configuration integration
├── LoggingConfig              # Logging system configuration dataclass
└── get_logging_config()       # Configuration access for logging setup

data_sources/                    # Logging integration points
├── base.py                    # Base class with integrated logging
├── fred_client.py            # FRED API operation logging
└── haver_client.py           # Haver API operation logging
```

## 3. Data Flow

### Request/Response Flow
1. **Input**: System operation or event triggers logging call
2. **Validation**: Log level filtering and sensitive data detection
3. **Processing**: Log record creation with structured context and formatting
4. **Output**: Multi-channel output (console, file, remote) with proper formatting
5. **Archival**: Log rotation and cleanup based on configuration parameters

### Data Transformation
**Log Event** → **Context Enrichment** → **Sensitive Data Masking** → **Format Selection** → **Multi-Channel Output**

Detailed transformation flow:
- Log events enriched with timestamp, context, and operation metadata
- Sensitive data (API keys, credentials) automatically detected and masked
- Format selection based on output destination (JSON for files, human-readable for console)
- Concurrent output to multiple channels with appropriate formatting

### State Management  
**State Storage**: Log buffers maintained in memory for batching and performance
**State Updates**: Real-time log record processing with asynchronous output
**State Persistence**: Log files with rotation and archival for long-term storage

## 4. Database Design

### Entity Relationship Diagram
```
[LogEntry] ──< contains >── [ContextData]
    |                           |
[timestamp, level,         [operation_id, user_id,
 logger, message]          performance_data, metadata]
    |
    └── [OutputChannel]
        |
    [file, console, remote]
```

### Schema Design
**Structured Log Format**: JSON-based log entries with consistent schema
```json
{
  "timestamp": "2025-09-01T10:30:45.123Z",
  "level": "INFO",
  "logger": "federal_reserve_etl.data_sources.fred",
  "message": "FRED API request completed successfully",
  "context": {
    "operation_id": "req_abc123",
    "user_id": "analyst_001",
    "function_name": "get_data",
    "parameters": {
      "series_id": "GDP",
      "date_range": "2020-01-01 to 2023-12-31"
    }
  },
  "performance": {
    "duration_ms": 1250,
    "response_size_kb": 45.2,
    "memory_usage_mb": 12.5
  },
  "metadata": {
    "environment": "production",
    "version": "1.0.0",
    "hostname": "etl-server-01"
  }
}
```

### Data Access Patterns
**Read Operations**: Log analysis through file access and log aggregation systems
**Write Operations**: Asynchronous log writing with buffering and batch processing
**Caching Strategy**: Log buffer caching with configurable flush intervals
**Migration Strategy**: Log format versioning with backward compatibility

## 5. API Design

### Function/Method Interfaces
```python
# Main logging setup
def setup_logging(log_level: str = "INFO",
                 log_file: Optional[str] = None,
                 enable_console: bool = True,
                 structured_format: bool = True,
                 max_file_size: str = "100MB",
                 backup_count: int = 5) -> logging.Logger:
    """Configure centralized logging with multiple outputs and structured format"""

# Custom stream handler
class FlushingStreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        """Stream handler with automatic flushing for real-time output"""
    
    def emit(self, record):
        """Emit log record with immediate stream flushing"""

# Structured formatter
class StructuredFormatter(logging.Formatter):
    def __init__(self, include_performance: bool = True,
                 mask_sensitive: bool = True):
        """JSON formatter with performance data and sensitive data masking"""
    
    def format(self, record) -> str:
        """Format log record as structured JSON with context enrichment"""

# Specialized logging functions
def log_api_request(logger: logging.Logger,
                   source: str,
                   endpoint: str,
                   parameters: Dict[str, Any],
                   timing_start: float) -> None:
    """Log API request with timing and parameter information"""

def log_api_response(logger: logging.Logger,
                    source: str,
                    response_code: int,
                    response_size: int,
                    timing_duration: float,
                    success: bool) -> None:
    """Log API response with performance and success metrics"""

def log_performance_metrics(logger: logging.Logger,
                          operation: str,
                          duration_ms: float,
                          memory_usage_mb: float,
                          throughput_records_per_sec: float) -> None:
    """Log operation performance metrics for analysis"""
```

### Log Message Standards
```python
# API Operation Logging
LOG_MESSAGES = {
    "api_request_start": "Starting {source} API request for {operation}",
    "api_request_complete": "{source} API request completed successfully",
    "api_request_failed": "{source} API request failed: {error_message}",
    "api_rate_limit": "{source} API rate limit reached, waiting {backoff_time}s",
    
    # Performance Logging  
    "performance_summary": "Operation performance summary for {operation}",
    "memory_usage": "Memory usage: {current_mb}MB (peak: {peak_mb}MB)",
    "throughput_metrics": "Processed {record_count} records in {duration_ms}ms",
    
    # Error and Audit Logging
    "error_context": "Error occurred in {operation}: {error_details}",
    "user_action": "User {user_id} performed {action} on {resource}",
    "data_access": "Data access: {user_id} retrieved {series_count} series"
}
```

## 6. Security Considerations

### Authentication
**Required Authentication**: No additional authentication - operates within application security context
**Token Management**: Logging system does not store or transmit authentication tokens
**Session Management**: Log context tied to operation lifecycle, not user sessions

### Authorization  
**Permission Model**: Logging access controlled through file system permissions
**Access Controls**: Log files protected with appropriate read/write permissions
**Data Filtering**: Sensitive information filtered before logging to prevent exposure

### Data Protection
**Sensitive Data**: API keys, passwords, and PII automatically detected and masked
**Encryption**: Log files can be encrypted at rest using file system encryption
**Input Sanitization**: Log message content sanitized to prevent injection attacks
**SQL Injection Prevention**: N/A - no database operations from logging system

## 7. Performance Considerations

### Scalability Design
**Horizontal Scaling**: Thread-safe logging with minimal contention across multiple processes
**Vertical Scaling**: Configurable log levels and buffering to manage memory and disk usage
**Database Scaling**: N/A - file-based logging with optional integration to log aggregation systems

### Optimization Strategies
**Caching**: Log message formatting cached where possible to reduce CPU overhead
**Database Indexes**: N/A - file-based system with external indexing through log aggregation
**Async Processing**: Asynchronous log writing with background thread processing
**Resource Pooling**: Log handler reuse and efficient stream management

### Performance Targets
**Response Time**: Logging overhead <2% of total operation time
**Throughput**: Log writing does not block main ETL operations
**Resource Usage**: Log buffer memory usage bounded and configurable

## 8. Error Handling

### Exception Hierarchy
```
LoggingError (Base)
├── LogSetupError              # Logging initialization failures
│   ├── InvalidLogLevelError  # Invalid log level specification
│   └── FileAccessError       # Log file creation/access issues
├── LogFormatError            # Log formatting and serialization issues
│   ├── JSONSerializationError # JSON formatting failures
│   └── MessageFormattingError # String formatting failures
└── LogOutputError            # Log output and handler issues
    ├── StreamWriteError      # Console/file stream writing issues
    └── RotationError        # Log rotation and cleanup failures
```

### Error Response Format
```python
{
    "error_type": "FileAccessError",
    "message": "Unable to create log file at specified location",
    "context": {
        "log_file_path": "/var/log/federal_reserve_etl.log",
        "error_time": "2025-09-01T10:30:45Z",
        "system_error": "Permission denied"
    },
    "suggestion": "Check file permissions or specify alternative log directory",
    "fallback_action": "Logging will continue to console output only"
}
```

### Recovery Strategies
**Transient Failures**: Continue logging to alternate outputs (console if file fails)
**Permanent Failures**: Graceful degradation with console-only logging
**Partial Failures**: Log formatting failures default to simple string representation

## 9. Testing Strategy

### Unit Testing
**Components to Test**: 
- Structured log formatter with various message types and contexts
- Sensitive data masking with different credential formats
- Custom stream handler with proper flushing behavior
- Log level filtering and message routing

**Mock Strategy**: Mock file system, console streams, and external log aggregation systems
**Coverage Targets**: 90% code coverage for logging infrastructure

### Integration Testing
**Integration Points**: 
- Configuration management integration for logging settings
- Error handling framework integration for error logging
- API client integration for request/response logging
- Performance monitoring integration for metrics logging

**Test Data**: Sample log messages with various data types and sensitive information
**Environment**: Test environment with controlled file system access and permissions

### End-to-End Testing
**User Scenarios**: 
- Complete ETL operation with comprehensive logging across all components
- Log analysis and search using generated structured log data
- Error scenarios with proper error logging and context preservation
- Performance monitoring through log-based metrics

**Automation**: Automated log validation and analysis in CI/CD pipeline
**Manual Testing**: Log readability and usefulness testing by operations team

## 10. Implementation Phases

### Phase 1: Core Logging Infrastructure ✅ (Completed)
- [x] Centralized logging setup with configurable levels and outputs
- [x] Custom stream handler with proper flushing for real-time output
- [x] Structured JSON formatter with timestamp and context enrichment
- [x] Configuration integration for logging parameters

### Phase 2: Specialized Logging ✅ (Completed)
- [x] API operation logging with request/response tracking
- [x] Performance logging with timing and resource usage metrics
- [x] Error logging integration with error handling framework
- [x] Sensitive data masking for credentials and PII protection

### Phase 3: Output Management ✅ (Completed)
- [x] Multi-channel output (console, file, remote) with format selection
- [x] Log rotation and archival with configurable size and retention limits
- [x] File permission management and security considerations
- [x] Integration with external log aggregation systems

### Phase 4: Monitoring Integration ✅ (Completed)
- [x] Performance metrics logging for operational monitoring
- [x] Audit logging for compliance and user action tracking
- [x] Error pattern analysis and alerting integration
- [x] Log analysis examples and operational dashboards

### Dependencies and Blockers
**Requires**: Configuration management, error handling framework, performance monitoring
**Provides**: Comprehensive observability for all system operations
**Risks**: Log volume could impact performance, sensitive data exposure

## 11. Implementation Status

### Completed Implementation ✅
The Structured Logging and Monitoring framework is fully implemented and production-ready:

**Key Implementation Files**:
- `src/federal_reserve_etl/utils/logging.py`: Complete logging framework (350+ lines)
- Integration across all system components with consistent logging patterns
- Configuration management integration for logging parameters

**Logging Capabilities**:
- **Multi-Format Output**: JSON structured logs for machines, human-readable for development
- **Multi-Channel Output**: Console, file, and remote logging with independent configuration
- **Sensitive Data Protection**: Automatic masking of API keys, credentials, and PII
- **Performance Integration**: Timing and resource usage logging for operational monitoring

**Log Categories Implemented**:
- **API Operation Logs**: Request/response logging with timing and parameter information
- **Error Context Logs**: Comprehensive error information with debugging context
- **Performance Logs**: Operation timing, memory usage, and throughput metrics
- **Audit Logs**: User actions and data access for compliance requirements

**Output Management**:
- **Log Rotation**: Size-based rotation with configurable retention policies
- **Stream Management**: Custom handler ensures proper output ordering and flushing
- **Format Selection**: Automatic format selection based on output destination
- **Security**: Proper file permissions and sensitive data masking

### Architecture Strengths
- **Structured Data**: All logs machine-parseable with consistent schema
- **Performance Optimized**: Asynchronous logging with minimal main thread impact
- **Security Conscious**: Automatic sensitive data detection and masking
- **Operationally Ready**: Integration with monitoring and log aggregation systems
- **Developer Friendly**: Clear, readable logs for development and debugging
- **Configurable**: Flexible configuration through central configuration management

### Log Analysis Integration
**Supported Systems**:
- ELK Stack (Elasticsearch, Logstash, Kibana) through JSON format
- Splunk through structured log format with field extraction
- CloudWatch Logs with structured query support
- Prometheus/Grafana through metrics extraction from logs

**Sample Log Analysis Queries**:
```bash
# Find API errors in last hour
jq 'select(.level == "ERROR" and .logger | contains("api"))' logs/federal_reserve_etl.log

# Calculate average API response times
jq -r 'select(.performance.duration_ms) | .performance.duration_ms' logs/federal_reserve_etl.log | awk '{sum+=$1; count++} END {print "Average:", sum/count "ms"}'

# Monitor rate limiting events
grep -E "rate.limit|backoff" logs/federal_reserve_etl.log | jq '.context'
```

---

**Document Status**: ✅ Complete - Production Architecture Documented  
**Last Updated**: September 1, 2025  
**Version**: 1.0 (Post-Implementation Documentation)  
**Implementation Files**: `src/federal_reserve_etl/utils/logging.py`