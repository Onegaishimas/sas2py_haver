"""
Setup configuration for Federal Reserve ETL Pipeline

Package distribution setup following ADR specifications for
production-ready command-line ETL tool.
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Federal Reserve Data ETL Pipeline"

# Read requirements from requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Filter out comments and empty lines
            return [line.strip() for line in lines 
                   if line.strip() and not line.startswith('#')]
    return []

setup(
    name="federal-reserve-etl",
    version="1.0.0",  # MVP release version
    author="Federal Reserve ETL Team",
    author_email="noreply@example.com",
    description="Production-ready ETL pipeline for Federal Reserve economic data with comprehensive error handling",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/user/federal-reserve-etl",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        # Development Status
        "Development Status :: 5 - Production/Stable",  # MVP completed with 65+ tests
        
        # Intended Audience
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry", 
        "Intended Audience :: Science/Research",
        
        # License
        "License :: OSI Approved :: MIT License",
        
        # Operating Systems
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS", 
        "Operating System :: Microsoft :: Windows",
        
        # Programming Language
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        
        # Topics
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database :: Front-Ends",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        
        # Framework
        "Framework :: Jupyter",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0", 
            "pytest-mock>=3.8.0",
            "freezegun>=1.2.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
            "ipdb>=0.13.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "coverage>=7.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "sphinxcontrib-napoleon>=0.7",
            "myst-parser>=1.0.0",
        ],
        "jupyter": [
            "jupyter>=1.0.0",
            "notebook>=6.5.0",
            "ipykernel>=6.20.0",
            "matplotlib>=3.6.0",
            "seaborn>=0.12.0", 
            "plotly>=5.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "federal-reserve-etl=federal_reserve_etl.cli:main",
            "extract-fed-data=federal_reserve_etl.cli:main",
        ]
    },
    include_package_data=True,
    package_data={
        "federal_reserve_etl": [
            "data/*.json",
            "data/*.csv",
            "config/*.yaml",
            "config/*.ini",
        ],
    },
    zip_safe=False,
    keywords=[
        "federal-reserve", "fred", "haver-analytics", "economic-data", 
        "etl", "data-pipeline", "finance", "economics", "api-client",
        "data-extraction", "financial-data", "time-series", "production-ready"
    ],
    project_urls={
        "Documentation": "https://github.com/user/federal-reserve-etl/docs",
        "Source": "https://github.com/user/federal-reserve-etl",
        "Bug Reports": "https://github.com/user/federal-reserve-etl/issues",
        "API Reference": "https://github.com/user/federal-reserve-etl/docs/API_REFERENCE.md",
        "Troubleshooting": "https://github.com/user/federal-reserve-etl/docs/TROUBLESHOOTING.md",
    },
    # Testing configuration
    test_suite="tests",
    tests_require=[
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-mock>=3.10.0",
    ],
)