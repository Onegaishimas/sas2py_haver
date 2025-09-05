# Federal Reserve ETL Pipeline - Examples

This directory contains comprehensive examples demonstrating various usage patterns and integration scenarios for the Federal Reserve ETL Pipeline.

## 📋 Example Categories

### 1. Basic Usage Examples (`basic_usage.py`)

Demonstrates fundamental usage patterns:

**Features:**
- Single variable extraction
- Multiple variables extraction  
- Comprehensive error handling
- Rate limiting demonstration
- Configuration patterns

**Run Example:**
```bash
# Set up environment
export FRED_API_KEY="your_32_character_api_key"

# Run basic examples
cd examples
python basic_usage.py
```

**What It Demonstrates:**
- ✅ Factory pattern usage with `create_data_source()`
- ✅ Context manager patterns for automatic cleanup
- ✅ Error handling for different scenarios
- ✅ Data export to CSV and Excel formats
- ✅ Configuration customization

### 2. Advanced Integration (`advanced_integration.py`)

Demonstrates production-ready integration patterns:

**Features:**
- Multi-source data combination (FRED + Haver)
- Custom ETL pipeline class
- Data transformations and economic indicators
- Visualization library integration
- Machine learning integration
- Production deployment patterns

**Dependencies:**
```bash
pip install matplotlib seaborn scikit-learn plotly
```

**Run Example:**
```bash
cd examples
python advanced_integration.py
```

**What It Demonstrates:**
- ✅ Production-ready pipeline architecture
- ✅ Multi-source data integration
- ✅ Economic indicator calculations
- ✅ Integration with pandas, matplotlib, sklearn
- ✅ Comprehensive data export with metadata

### 3. Docker Deployment (`docker_deployment.py`)

Creates complete containerization configuration:

**Features:**
- Production Dockerfile
- Docker Compose for multi-service deployment
- Kubernetes manifests
- Deployment automation scripts
- Monitoring and health checks

**Run Example:**
```bash
cd examples
python docker_deployment.py
```

**Generated Files:**
- `Dockerfile` - Production container definition
- `docker-compose.yml` - Multi-service stack
- `k8s/` - Kubernetes deployment manifests
- `docker/` - Support files (entrypoint, configs)
- `*.sh` - Deployment automation scripts

## 🚀 Quick Start Guide

### Option 1: Basic Local Usage

1. **Set up credentials:**
   ```bash
   export FRED_API_KEY="your_32_character_api_key"
   # Optional for Haver
   export HAVER_USERNAME="your_username"
   export HAVER_PASSWORD="your_password"
   ```

2. **Run basic example:**
   ```bash
   python examples/basic_usage.py
   ```

3. **Check output:**
   - CSV files with economic data
   - Excel files with data and metadata
   - Console output with extraction progress

### Option 2: Advanced Pipeline

1. **Install additional dependencies:**
   ```bash
   pip install matplotlib seaborn scikit-learn plotly
   ```

2. **Run advanced example:**
   ```bash
   python examples/advanced_integration.py
   ```

3. **Review generated analysis:**
   - Multi-format data exports
   - Economic indicators and correlations
   - Visualizations and model results

### Option 3: Docker Deployment

1. **Generate deployment files:**
   ```bash
   python examples/docker_deployment.py
   ```

2. **Configure environment:**
   ```bash
   cp .env.template .env
   # Edit .env with your API keys
   ```

3. **Deploy with Docker:**
   ```bash
   ./build_docker.sh
   ./run_docker.sh
   ```

## 📊 Example Outputs

### Data Files Generated

| File Type | Example | Description |
|-----------|---------|-------------|
| **CSV** | `federal_funds_2023.csv` | Raw time series data |
| **Excel** | `economic_indicators_2023.xlsx` | Data + metadata sheets |
| **JSON** | `economic_indicators_20231201.json` | Economic indicators |
| **PNG** | `economic_analysis.png` | Visualization charts |

### Console Output Example

```
🚀 Federal Reserve ETL Pipeline - Usage Examples
============================================================
✅ FRED API key configured: abcd...wxyz
📊 Example 1: Single Variable Extraction
==================================================
📈 Extracting Federal Funds Rate from 2023-01-01 to 2023-12-31
✅ Retrieved 252 observations
📋 Variable: Federal Funds Effective Rate
📏 Units: Percent
🔄 Frequency: Daily
💾 Data saved to: federal_funds_rate_2023-01-01_to_2023-12-31.csv
```

## 🔧 Integration Patterns

### Pattern 1: Simple Script Integration

```python
from federal_reserve_etl import create_data_source

# Basic usage pattern
with create_data_source('fred') as fred:
    data = fred.get_data('FEDFUNDS', '2023-01-01', '2023-12-31')
    data.to_csv('output.csv')
```

### Pattern 2: Class-Based Pipeline

```python
from examples.advanced_integration import EconomicDataPipeline

# Production pipeline pattern
pipeline = EconomicDataPipeline({'rate_limit': 100})
fred_data = pipeline.extract_fred_data(['FEDFUNDS', 'DGS10'], '2023-01-01', '2023-12-31')
pipeline.export_results(fred_data, {}, 'output/')
```

### Pattern 3: Jupyter Notebook Integration

```python
# In Jupyter notebook
%load_ext autoreload
%autoreload 2

import sys
sys.path.append('../src')

from federal_reserve_etl import create_data_source
import matplotlib.pyplot as plt

# Interactive analysis
with create_data_source('fred') as fred:
    data = fred.get_data(['FEDFUNDS', 'DGS10'], '2020-01-01', '2023-12-31')
    data.plot(figsize=(12, 6), title='Interest Rates')
    plt.show()
```

## 🐳 Deployment Scenarios

### Scenario 1: Development Environment

```bash
# Local development
python examples/basic_usage.py
```

### Scenario 2: Single Container Deployment

```bash
# Build and run container
python examples/docker_deployment.py
./build_docker.sh
./run_docker.sh
```

### Scenario 3: Multi-Service Stack

```bash
# Full stack with Redis, PostgreSQL, monitoring
docker-compose up -d
```

### Scenario 4: Kubernetes Deployment

```bash
# Production Kubernetes deployment
./deploy_k8s.sh
kubectl get pods -n federal-reserve-etl
```

## 📚 Learning Path

### Beginner: Start Here

1. **Read main [README.md](../README.md)** for overview
2. **Run `basic_usage.py`** to understand core concepts
3. **Check generated files** to see output formats
4. **Modify variables and dates** in the examples

### Intermediate: Build Skills

1. **Run `advanced_integration.py`** for production patterns
2. **Study the `EconomicDataPipeline` class** architecture
3. **Experiment with visualizations** and data transformations
4. **Try different data sources** and time ranges

### Advanced: Production Deployment

1. **Generate Docker configs** with `docker_deployment.py`
2. **Customize configurations** for your environment
3. **Deploy with monitoring** and health checks
4. **Scale with Kubernetes** for production workloads

## 🔍 Troubleshooting Examples

### Common Issues and Solutions

**Issue: Import Error**
```bash
ModuleNotFoundError: No module named 'federal_reserve_etl'
```
**Solution:**
```bash
# Ensure you're in the project root directory
cd /path/to/sas-code-examples_root
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python examples/basic_usage.py
```

**Issue: API Key Not Found**
```bash
ConfigurationError: FRED API key is required
```
**Solution:**
```bash
# Set environment variable
export FRED_API_KEY="your_32_character_api_key"
# Or create .env file with credentials
```

**Issue: Rate Limit Exceeded**
```bash
RateLimitError: FRED API rate limit exceeded
```
**Solution:**
- Examples include automatic retry logic
- Check console output for retry messages
- Consider reducing request frequency in config

**Issue: Missing Optional Dependencies**
```bash
ImportError: No module named 'matplotlib'
```
**Solution:**
```bash
# Install visualization dependencies
pip install matplotlib seaborn plotly scikit-learn

# Or install all extras
pip install -e .[jupyter,docs]
```

## 📞 Support and Resources

- **Main Documentation**: [README.md](../README.md)
- **API Reference**: [docs/API_REFERENCE.md](../docs/API_REFERENCE.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)
- **Credentials Setup**: [docs/API_CREDENTIALS_SETUP.md](../docs/API_CREDENTIALS_SETUP.md)

## 🤝 Contributing Examples

To add new examples:

1. Create new Python file in `examples/` directory
2. Follow existing naming convention (`category_description.py`)
3. Include comprehensive docstrings and error handling
4. Add entry to this README with description and usage
5. Test with various scenarios and document outputs

**Example Template:**
```python
#!/usr/bin/env python3
"""
New Example - Federal Reserve ETL Pipeline

Description of what this example demonstrates.
"""

import sys
from pathlib import Path

# Standard example setup
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from federal_reserve_etl import create_data_source

def main():
    """Main example function"""
    print("🚀 New Example Starting...")
    
    # Your example code here
    
    return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
```

---

**Last Updated**: September 2025  
**Version**: 1.0.0