# API Credentials Setup Guide

This guide provides detailed instructions for setting up API credentials for both FRED and Haver Analytics data sources.

## 📋 Table of Contents

- [FRED API Setup (Required)](#fred-api-setup-required)
- [Haver Analytics Setup (Optional)](#haver-analytics-setup-optional)
- [Environment Variable Configuration](#environment-variable-configuration)
- [Credential Validation](#credential-validation)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## 🏦 FRED API Setup (Required)

### Step 1: Create FRED Account

1. **Visit FRED Website**: Go to [https://fred.stlouisfed.org](https://fred.stlouisfed.org)
2. **Register Account**: Click "My Account" → "Register" 
3. **Fill Registration Form**:
   - Email address
   - Password (8+ characters)
   - Organization (optional)
   - Purpose of use (research, commercial, etc.)
4. **Verify Email**: Check your email and click verification link

### Step 2: Generate API Key

1. **Login**: Sign in to your FRED account
2. **Access API Keys**: Go to [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
3. **Create API Key**:
   - Click "Request API Key"
   - Fill out application form:
     - Application name (e.g., "Federal Reserve ETL Pipeline")
     - Application description
     - Application URL (optional)
   - Submit application
4. **Receive API Key**: You'll receive a 32-character API key immediately

### Step 3: API Key Format

FRED API keys are exactly 32 characters long and alphanumeric:
```
Example: 1234567890abcdef1234567890abcdef
```

### Step 4: Rate Limits

- **Free Tier**: 120 requests per minute
- **No daily limit**
- **Automatic throttling** handled by the pipeline

## 🏢 Haver Analytics Setup (Optional)

### Step 1: Contact Haver Analytics

1. **Visit Haver Website**: Go to [https://www.haver.com](https://www.haver.com)
2. **Contact Sales**: Call +1 (610) 696-4700 or email info@haver.com
3. **Discuss Subscription**: Choose appropriate data package
4. **Complete Purchase**: Follow their commercial licensing process

### Step 2: Receive Credentials

After purchase, Haver Analytics will provide:
- **Username**: Your account username
- **Password**: Your account password  
- **API Documentation**: Custom API access details
- **Database List**: Available databases for your subscription

### Step 3: Credential Format

Haver credentials are typically:
```
Username: your_username (alphanumeric, may include underscores)
Password: your_password (varies, may include special characters)
```

### Step 4: Rate Limits

- **Varies by subscription**: Typically 10-50 requests per minute
- **Custom arrangements**: Available for enterprise customers
- **Automatic handling**: Pipeline manages rate limiting

## 🔧 Environment Variable Configuration

### Option 1: Shell Environment (Recommended for Development)

#### Linux/macOS:
```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.profile
export FRED_API_KEY="your_32_character_fred_api_key"
export HAVER_USERNAME="your_haver_username"  # Optional
export HAVER_PASSWORD="your_haver_password"  # Optional

# Reload shell configuration
source ~/.bashrc
```

#### Windows Command Prompt:
```cmd
set FRED_API_KEY=your_32_character_fred_api_key
set HAVER_USERNAME=your_haver_username
set HAVER_PASSWORD=your_haver_password
```

#### Windows PowerShell:
```powershell
$env:FRED_API_KEY="your_32_character_fred_api_key"
$env:HAVER_USERNAME="your_haver_username"
$env:HAVER_PASSWORD="your_haver_password"
```

### Option 2: .env File (Recommended for Production)

Create a `.env` file in your project root:
```bash
# Federal Reserve ETL Pipeline Credentials

# FRED API (Required)
FRED_API_KEY=your_32_character_fred_api_key

# Haver Analytics (Optional)
HAVER_USERNAME=your_haver_username
HAVER_PASSWORD=your_haver_password

# Configuration Options (Optional)
FRED_RATE_LIMIT=120
HAVER_RATE_LIMIT=10
LOG_LEVEL=INFO
```

**Important**: Add `.env` to your `.gitignore` file!

### Option 3: Python Configuration

```python
import os

# Set credentials programmatically (not recommended for production)
os.environ['FRED_API_KEY'] = 'your_32_character_fred_api_key'
os.environ['HAVER_USERNAME'] = 'your_haver_username'
os.environ['HAVER_PASSWORD'] = 'your_haver_password'

from src.federal_reserve_etl import create_data_source

# Credentials will be automatically detected
fred = create_data_source('fred')
```

## ✅ Credential Validation

### Quick Validation Script

Create `validate_credentials.py`:
```python
#!/usr/bin/env python3
"""
Credential validation script for Federal Reserve ETL Pipeline
"""

import os
from src.federal_reserve_etl import create_data_source

def validate_fred_credentials():
    """Validate FRED API credentials"""
    print("🏦 Validating FRED API credentials...")
    
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("❌ FRED_API_KEY environment variable not set")
        return False
    
    if len(api_key) != 32:
        print(f"❌ FRED API key should be 32 characters, got {len(api_key)}")
        return False
    
    try:
        with create_data_source('fred') as fred:
            # Test connection
            print(f"✅ FRED API key valid: {api_key[:4]}...{api_key[-4:]}")
            
            # Test data retrieval
            data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-01-05')
            print(f"✅ FRED data retrieval successful: {len(data)} records")
            return True
            
    except Exception as e:
        print(f"❌ FRED validation failed: {str(e)}")
        return False

def validate_haver_credentials():
    """Validate Haver Analytics credentials"""
    print("\n🏢 Validating Haver Analytics credentials...")
    
    username = os.getenv('HAVER_USERNAME')
    password = os.getenv('HAVER_PASSWORD')
    
    if not username or not password:
        print("⚠️  Haver credentials not set (optional)")
        return True
    
    try:
        with create_data_source('haver') as haver:
            print(f"✅ Haver credentials valid: {username}")
            return True
            
    except Exception as e:
        print(f"❌ Haver validation failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔐 Federal Reserve ETL Pipeline - Credential Validation")
    print("=" * 60)
    
    fred_valid = validate_fred_credentials()
    haver_valid = validate_haver_credentials()
    
    print("\n📊 Validation Summary:")
    print(f"   FRED API: {'✅ Valid' if fred_valid else '❌ Invalid'}")
    print(f"   Haver API: {'✅ Valid' if haver_valid else '❌ Invalid'}")
    
    if fred_valid:
        print("\n🚀 Ready to extract Federal Reserve data!")
    else:
        print("\n⚠️  Please check your FRED API key configuration.")
```

Run validation:
```bash
python validate_credentials.py
```

### Command Line Validation

```bash
# Test FRED connection
python -c "
from src.federal_reserve_etl import create_data_source
with create_data_source('fred') as fred:
    print('FRED connection:', 'SUCCESS' if fred.is_connected else 'FAILED')
"

# Test Haver connection (if credentials available)
python -c "
from src.federal_reserve_etl import create_data_source
try:
    with create_data_source('haver') as haver:
        print('Haver connection:', 'SUCCESS' if haver.is_connected else 'FAILED')
except Exception as e:
    print('Haver connection: NOT CONFIGURED')
"
```

## 🔒 Security Best Practices

### 1. Environment Variable Security

- **Never commit credentials** to version control
- **Use environment variables** instead of hardcoding
- **Rotate API keys** regularly (every 6-12 months)
- **Limit access** to production credentials

### 2. File Permissions

Secure your credential files:
```bash
# Make .env file readable only by you
chmod 600 .env

# Secure credential scripts
chmod 700 validate_credentials.py
```

### 3. Production Deployment

#### Docker
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY src/ ./src/

# Set credentials via environment variables (not in image)
ENV FRED_API_KEY=""
ENV HAVER_USERNAME=""
ENV HAVER_PASSWORD=""

CMD ["python", "-m", "src.federal_reserve_etl"]
```

#### Kubernetes
```yaml
# k8s-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: fed-etl-credentials
type: Opaque
data:
  fred-api-key: <base64-encoded-key>
  haver-username: <base64-encoded-username>
  haver-password: <base64-encoded-password>
```

### 4. Logging Security

The pipeline automatically masks credentials in logs:
```python
# Automatic credential masking in logs
logger.info("Connecting with API key: abc***xyz")  # Real key is masked
```

## 🔧 Troubleshooting

### FRED API Issues

**Problem**: "Invalid API key" error
```bash
AuthenticationError: Invalid FRED API key: Bad Request. The value for variable api_key is not a valid api key.
```
**Solutions**:
1. Verify API key is exactly 32 characters
2. Check for typos or extra spaces
3. Regenerate API key from FRED website
4. Ensure environment variable is set correctly

**Problem**: Rate limit exceeded
```bash
RateLimitError: FRED API rate limit exceeded. Wait 45.2 seconds
```
**Solutions**:
1. Wait for rate limit reset (automatic)
2. Reduce request frequency
3. Use built-in retry logic (enabled by default)

### Haver Analytics Issues

**Problem**: Authentication failed
```bash
AuthenticationError: Haver API authentication failed
```
**Solutions**:
1. Verify username and password
2. Check subscription status with Haver
3. Ensure API access is enabled for your account
4. Contact Haver support: support@haver.com

**Problem**: Data not available
```bash
DataRetrievalError: Variable not found in Haver database
```
**Solutions**:
1. Check variable name spelling
2. Verify variable exists in your subscribed databases
3. Use Haver's documentation for correct variable codes
4. Contact Haver for available variable lists

### General Issues

**Problem**: Environment variables not loaded
```bash
ConfigurationError: FRED API key is required
```
**Solutions**:
1. Restart terminal/IDE after setting environment variables
2. Check environment variable names (case-sensitive)
3. Use `echo $FRED_API_KEY` to verify variable is set
4. Try absolute path for .env file loading

**Problem**: Network connectivity issues
```bash
ConnectionError: Failed to connect to FRED API: Network error
```
**Solutions**:
1. Check internet connection
2. Verify firewall/proxy settings
3. Test with curl: `curl https://api.stlouisfed.org/fred/series?series_id=FEDFUNDS&api_key=YOUR_KEY&file_type=json`
4. Check for VPN interference

## 📞 Support Contacts

### FRED Support
- **Website**: [https://fred.stlouisfed.org/docs/api/](https://fred.stlouisfed.org/docs/api/)
- **Email**: api@stlouisfed.org
- **Documentation**: [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)

### Haver Analytics Support  
- **Website**: [https://www.haver.com](https://www.haver.com)
- **Phone**: +1 (610) 696-4700
- **Email**: support@haver.com
- **Sales**: info@haver.com

### Pipeline Support
- **Documentation**: See project README.md
- **Issues**: Create GitHub issue with error details
- **Testing**: Run validation script before reporting issues

---

**Last Updated**: 2025
**Version**: 1.0.0