# Troubleshooting Guide

This comprehensive guide helps diagnose and resolve common issues with the Federal Reserve ETL Pipeline.

## 📋 Quick Diagnosis

### 🩺 Health Check Script

Run this script to diagnose common issues:

```python
#!/usr/bin/env python3
"""
Federal Reserve ETL Pipeline Health Check
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check Python environment and dependencies"""
    print("🐍 Environment Check")
    print(f"   Python version: {sys.version}")
    print(f"   Working directory: {Path.cwd()}")
    
    required_packages = ['pandas', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}: Available")
        except ImportError:
            print(f"   ❌ {package}: Missing")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def check_credentials():
    """Check API credential configuration"""
    print("\n🔐 Credential Check")
    
    fred_key = os.getenv('FRED_API_KEY')
    haver_user = os.getenv('HAVER_USERNAME')
    haver_pass = os.getenv('HAVER_PASSWORD')
    
    # FRED credentials
    if fred_key:
        if len(fred_key) == 32:
            print(f"   ✅ FRED API Key: Valid format ({fred_key[:4]}...{fred_key[-4:]})")
        else:
            print(f"   ❌ FRED API Key: Invalid length ({len(fred_key)}, expected 32)")
    else:
        print("   ❌ FRED API Key: Not set")
    
    # Haver credentials
    if haver_user and haver_pass:
        print(f"   ✅ Haver credentials: Set ({haver_user})")
    else:
        print("   ⚠️  Haver credentials: Not set (optional)")
    
    return bool(fred_key and len(fred_key) == 32)

def check_imports():
    """Check pipeline imports"""
    print("\n📦 Import Check")
    
    try:
        from src.federal_reserve_etl import create_data_source
        print("   ✅ Main factory: Available")
    except ImportError as e:
        print(f"   ❌ Main factory: Failed ({e})")
        return False
    
    try:
        from src.federal_reserve_etl.utils.exceptions import FederalReserveETLError
        print("   ✅ Exception handling: Available")
    except ImportError as e:
        print(f"   ❌ Exception handling: Failed ({e})")
        return False
    
    try:
        from src.federal_reserve_etl.utils.logging import setup_logging
        print("   ✅ Logging system: Available")
    except ImportError as e:
        print(f"   ❌ Logging system: Failed ({e})")
        return False
    
    return True

def test_connectivity():
    """Test API connectivity"""
    print("\n🌐 Connectivity Check")
    
    try:
        import requests
        response = requests.get('https://api.stlouisfed.org/fred/series?series_id=FEDFUNDS&api_key=test&file_type=json', timeout=10)
        if response.status_code == 400:  # Expected for invalid API key
            print("   ✅ FRED API: Reachable")
        else:
            print(f"   ⚠️  FRED API: Unexpected response ({response.status_code})")
    except Exception as e:
        print(f"   ❌ FRED API: Connection failed ({e})")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Federal Reserve ETL Pipeline - Health Check")
    print("=" * 60)
    
    env_ok = check_environment()
    cred_ok = check_credentials()
    import_ok = check_imports()
    conn_ok = test_connectivity()
    
    print("\n📊 Health Summary:")
    print(f"   Environment: {'✅ OK' if env_ok else '❌ Issues'}")
    print(f"   Credentials: {'✅ OK' if cred_ok else '❌ Issues'}")
    print(f"   Imports: {'✅ OK' if import_ok else '❌ Issues'}")
    print(f"   Connectivity: {'✅ OK' if conn_ok else '❌ Issues'}")
    
    if all([env_ok, cred_ok, import_ok, conn_ok]):
        print("\n🎉 All systems operational!")
    else:
        print("\n⚠️  Issues detected. See sections below for solutions.")
```

## 🚨 Common Issues and Solutions

### 1. Installation and Environment Issues

#### Issue: Import Error
```
ImportError: No module named 'src.federal_reserve_etl'
```

**Diagnosis**:
```bash
python -c "import sys; print('\\n'.join(sys.path))"
ls -la src/federal_reserve_etl/
```

**Solutions**:
1. **Check working directory**:
   ```bash
   cd /path/to/sas-code-examples_root
   python -c "from src.federal_reserve_etl import create_data_source"
   ```

2. **Add to Python path**:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:/path/to/sas-code-examples_root"
   ```

3. **Install in development mode**:
   ```bash
   pip install -e .
   ```

#### Issue: Missing Dependencies
```
ImportError: No module named 'pandas'
```

**Solutions**:
1. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Check virtual environment**:
   ```bash
   which python
   pip list | grep pandas
   ```

3. **Reinstall dependencies**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

### 2. Authentication Issues

#### Issue: FRED API Key Invalid
```
AuthenticationError: Invalid FRED API key: Bad Request. The value for variable api_key is not a valid api key.
```

**Diagnosis**:
```python
import os
key = os.getenv('FRED_API_KEY')
print(f"Key length: {len(key) if key else 'Not set'}")
print(f"Key format: {key[:4]}...{key[-4:] if key and len(key) >= 8 else 'Too short'}")
```

**Solutions**:
1. **Verify API key format**:
   - Must be exactly 32 characters
   - Only alphanumeric characters (a-z, A-Z, 0-9)
   - No spaces or special characters

2. **Check environment variable**:
   ```bash
   echo "FRED_API_KEY='$FRED_API_KEY'"
   ```

3. **Test API key manually**:
   ```bash
   curl "https://api.stlouisfed.org/fred/series?series_id=FEDFUNDS&api_key=YOUR_KEY&file_type=json"
   ```

4. **Regenerate API key**:
   - Visit [FRED API Key Management](https://fred.stlouisfed.org/docs/api/api_key.html)
   - Generate new API key
   - Update environment variable

#### Issue: Haver Authentication Failed
```
AuthenticationError: Haver API authentication failed
```

**Diagnosis**:
```python
import os
print(f"Username: {os.getenv('HAVER_USERNAME')}")
print(f"Password set: {'Yes' if os.getenv('HAVER_PASSWORD') else 'No'}")
```

**Solutions**:
1. **Verify credentials with Haver**:
   - Contact support@haver.com
   - Verify account is active
   - Check subscription status

2. **Test credentials**:
   - Try logging into Haver web portal
   - Verify API access is enabled

3. **Check special characters**:
   - Escape special characters in passwords
   - Use quotes in environment variables

### 3. Connection and Network Issues

#### Issue: Connection Timeout
```
ConnectionError: Connection timeout to FRED API: HTTPSConnectionPool(host='api.stlouisfed.org', port=443)
```

**Diagnosis**:
```bash
# Test basic connectivity
ping api.stlouisfed.org
curl -I https://api.stlouisfed.org/fred/

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

**Solutions**:
1. **Check internet connection**:
   ```bash
   curl -I https://google.com
   ```

2. **Configure proxy (if needed)**:
   ```python
   import requests
   proxies = {
       'http': 'http://proxy.company.com:8080',
       'https': 'https://proxy.company.com:8080'
   }
   ```

3. **Increase timeout**:
   ```python
   config = {'timeout': 60}
   fred = create_data_source('fred', config=config)
   ```

4. **Disable VPN temporarily**:
   - Some VPNs block API access
   - Try without VPN to isolate issue

#### Issue: SSL Certificate Error
```
SSLError: HTTPSConnectionPool(host='api.stlouisfed.org', port=443): Max retries exceeded with url
```

**Solutions**:
1. **Update certificates**:
   ```bash
   pip install --upgrade certifi
   ```

2. **Check system time**:
   ```bash
   date  # Ensure system clock is correct
   ```

3. **Bypass SSL (not recommended for production)**:
   ```python
   import requests
   requests.packages.urllib3.disable_warnings()
   ```

### 4. Data Retrieval Issues

#### Issue: No Data Returned
```
DataRetrievalError: No data retrieved for any requested variables
```

**Diagnosis**:
```python
# Test with known good variable
with create_data_source('fred') as fred:
    metadata = fred.get_variable_metadata('FEDFUNDS')
    print(f"Available dates: {metadata.get('observation_start')} to {metadata.get('observation_end')}")
```

**Solutions**:
1. **Check variable codes**:
   - Verify spelling of variable names
   - Use FRED website to search for correct codes
   - Try alternative variable names

2. **Adjust date range**:
   ```python
   # Check data availability
   metadata = fred.get_variable_metadata('FEDFUNDS')
   start_date = metadata.get('observation_start', '1950-01-01')
   end_date = metadata.get('observation_end', '2023-12-31')
   ```

3. **Test with reliable variables**:
   ```python
   # These should always work
   reliable_vars = ['FEDFUNDS', 'DGS10', 'UNRATE']
   data = fred.get_data(reliable_vars, '2023-01-01', '2023-01-31')
   ```

#### Issue: Rate Limit Exceeded
```
RateLimitError: FRED API rate limit exceeded. Wait 45.2 seconds
```

**Solutions**:
1. **Wait for automatic retry** (default behavior):
   ```python
   # Pipeline automatically retries with backoff
   # No action needed
   ```

2. **Reduce request frequency**:
   ```python
   config = {'rate_limit': 60}  # Slower than default 120
   fred = create_data_source('fred', config=config)
   ```

3. **Batch requests**:
   ```python
   # Get multiple variables in one request
   data = fred.get_data(['FEDFUNDS', 'DGS10', 'UNRATE'], '2023-01-01', '2023-12-31')
   ```

### 5. Data Processing Issues

#### Issue: Data Type Errors
```
TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'
```

**Solutions**:
1. **Handle missing data**:
   ```python
   data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-31')
   # Check for NaN values
   print(f"Missing values: {data['FEDFUNDS'].isna().sum()}")
   
   # Fill or drop missing values
   data_filled = data.fillna(method='forward')  # Forward fill
   data_clean = data.dropna()  # Remove missing
   ```

2. **Check data types**:
   ```python
   print(data.dtypes)
   print(data.head())
   ```

3. **Convert data types**:
   ```python
   # Convert to numeric, errors to NaN
   data['FEDFUNDS'] = pd.to_numeric(data['FEDFUNDS'], errors='coerce')
   ```

#### Issue: Memory Error with Large Datasets
```
MemoryError: Unable to allocate 8.00 GiB for an array
```

**Solutions**:
1. **Reduce date range**:
   ```python
   # Process data in chunks
   start_dates = ['2020-01-01', '2021-01-01', '2022-01-01']
   end_dates = ['2020-12-31', '2021-12-31', '2022-12-31']
   
   for start, end in zip(start_dates, end_dates):
       data_chunk = fred.get_data('FEDFUNDS', start, end)
       # Process chunk
   ```

2. **Use fewer variables**:
   ```python
   # Instead of all variables at once
   variables = ['FEDFUNDS', 'DGS10', 'UNRATE', 'CPIAUCSL', 'GDP']
   
   # Process one at a time
   results = {}
   for var in variables:
       results[var] = fred.get_data(var, '2020-01-01', '2022-12-31')
   ```

### 6. Logging and Debugging Issues

#### Issue: No Log Output
```
# No logging messages appear
```

**Solutions**:
1. **Initialize logging**:
   ```python
   from src.federal_reserve_etl.utils.logging import setup_logging
   setup_logging()
   ```

2. **Check log level**:
   ```python
   import logging
   logging.getLogger().setLevel(logging.DEBUG)
   ```

3. **Enable console logging**:
   ```python
   setup_logging(console_output=True, log_level='INFO')
   ```

#### Issue: Log Files Not Created
```
# Log files missing from logs/ directory
```

**Solutions**:
1. **Create logs directory**:
   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

2. **Check permissions**:
   ```bash
   ls -la logs/
   ```

3. **Specify log file path**:
   ```python
   setup_logging(log_file='custom_path/etl.log')
   ```

## 🔧 Advanced Debugging

### Enable Debug Mode

```python
import logging
from src.federal_reserve_etl.utils.logging import setup_logging

# Enable debug logging
setup_logging(log_level='DEBUG', console_output=True)

# Add detailed HTTP logging
logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)
logging.getLogger("requests.packages.urllib3").propagate = True
```

### Network Traffic Debugging

```python
import requests

# Enable HTTP debugging
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

# Now run your pipeline - all HTTP traffic will be logged
```

### Performance Profiling

```python
import cProfile
import pstats

def profile_data_extraction():
    with create_data_source('fred') as fred:
        data = fred.get_data(['FEDFUNDS', 'DGS10'], '2023-01-01', '2023-12-31')
    return data

# Profile the extraction
cProfile.run('profile_data_extraction()', 'profile_stats')

# Analyze results
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative').print_stats(10)
```

## 📞 Getting Help

### 1. Check Documentation First
- [API Credentials Setup](API_CREDENTIALS_SETUP.md)
- [Project README](../README.md)
- [API Reference Documentation](API_REFERENCE.md)

### 2. Run Diagnostics
```bash
# Run health check
python docs/health_check.py

# Run credential validation
python docs/validate_credentials.py

# Test specific functionality
python -c "from src.federal_reserve_etl import create_data_source; print('Import OK')"
```

### 3. Gather Information for Support

When reporting issues, include:
- **Python version**: `python --version`
- **Operating system**: `uname -a` or `ver`
- **Error message**: Full stack trace
- **Minimal reproducing example**
- **Environment variables** (without revealing credentials)

### 4. Contact Information

- **FRED API Issues**: api@stlouisfed.org
- **Haver Analytics Issues**: support@haver.com
- **Pipeline Issues**: Create GitHub issue with diagnostic information

### 5. Community Resources

- **FRED API Documentation**: [https://fred.stlouisfed.org/docs/api/](https://fred.stlouisfed.org/docs/api/)
- **Haver Analytics Support**: [https://www.haver.com/support](https://www.haver.com/support)
- **Stack Overflow**: Tag questions with `fred-api`, `haver-analytics`, `python-etl`

---

**Last Updated**: 2025
**Version**: 1.0.0

*Remember: When in doubt, start with the health check script and work through issues systematically.*