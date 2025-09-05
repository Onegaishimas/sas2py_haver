# Create Technical Implementation Document (TID)

## Purpose
Generate Technical Implementation Documents that provide specific coding guidance, implementation hints, and development strategies based on Technical Design Documents.

## When to Use
- After Technical Design Document (TDD) is complete and approved
- Before generating actionable task lists
- When developers need specific implementation guidance

## Instructions

### Option A: Direct TID Creation
```
Please create a Technical Implementation Document (TID) for [FEATURE NAME] based on [TDD FILE].

Requirements:
1. Implementation Strategy - Development approach and coding patterns
2. Code Structure - Specific classes, methods, and file organization
3. Key Algorithms - Detailed implementation of complex logic
4. Integration Points - How to connect with existing systems
5. Configuration - Settings, environment variables, and deployment config
6. Testing Implementation - Specific test cases and testing utilities
7. Development Tools - Required libraries, frameworks, and tools
8. Code Examples - Sample implementations and usage patterns
9. Performance Implementation - Specific optimization techniques
10. Deployment Considerations - Build, packaging, and deployment steps

Context: [Reference the TDD and existing codebase patterns]

Output: Save as 0xcc/tids/[###]_FTID|[feature-name].md

Focus on specific implementation details and coding guidance.
```

### Option B: Research-Enhanced Creation
```
🔍 Research first: Use /mcp ref search '[technology] implementation patterns [specific technique]'

Then create a TID for [FEATURE NAME] incorporating current implementation best practices and proven coding patterns.
[Include same requirements as Option A]
```

## Template Structure

```markdown
# Technical Implementation Document: [Feature Name]

## 1. Implementation Strategy

### Development Approach
**Methodology**: [TDD, BDD, Agile iteration, etc.]
**Order of Implementation**: [Which components to build first and why]
**Integration Strategy**: [How to integrate incrementally with existing system]
**Risk Mitigation**: [How to handle technical risks during development]

### Coding Patterns
**Design Patterns**: [Specific patterns to use - Factory, Observer, etc.]
**Code Organization**: [How to structure classes and modules]
**Naming Conventions**: [Specific naming rules for this feature]
**Documentation Standards**: [Docstring and comment requirements]

## 2. Code Structure

### Directory Structure
```
src/[feature_name]/
├── __init__.py                   # Module initialization
├── controllers/
│   ├── __init__.py
│   ├── feature_controller.py     # Main API controller
│   └── validation_controller.py  # Input validation logic
├── services/
│   ├── __init__.py
│   ├── feature_service.py        # Core business logic
│   ├── integration_service.py    # External API integration
│   └── cache_service.py          # Caching layer
├── models/
│   ├── __init__.py
│   ├── feature_model.py          # Database models
│   └── dto/
│       ├── __init__.py
│       ├── request_dto.py        # Request data structures
│       └── response_dto.py       # Response data structures
├── repositories/
│   ├── __init__.py
│   └── feature_repository.py     # Data access layer
├── utils/
│   ├── __init__.py
│   ├── validators.py             # Custom validation functions
│   ├── formatters.py             # Data formatting utilities
│   └── constants.py              # Feature-specific constants
└── exceptions/
    ├── __init__.py
    └── feature_exceptions.py     # Custom exception classes
```

### Key Class Definitions
```python
# services/feature_service.py
class FeatureService:
    def __init__(self, repository: FeatureRepository, cache: CacheService):
        self.repository = repository
        self.cache = cache
        self.logger = logging.getLogger(__name__)
    
    async def create_feature(self, user_id: str, data: dict) -> Feature:
        """
        Create new feature instance with validation and caching
        
        Args:
            user_id: ID of the user creating the feature
            data: Feature configuration data
            
        Returns:
            Feature: Created feature instance
            
        Raises:
            ValidationError: If data is invalid
            PermissionError: If user lacks permissions
        """
        # Implementation details here
        pass
```

## 3. Key Algorithms

### Core Business Logic
**Algorithm: [Name of complex algorithm]**
```python
def complex_calculation(input_data: Dict[str, Any]) -> ProcessedResult:
    """
    Detailed description of the algorithm's purpose and approach
    
    Time Complexity: O(n log n)
    Space Complexity: O(n)
    """
    # Step 1: Data preprocessing
    normalized_data = normalize_input(input_data)
    
    # Step 2: Core computation
    intermediate_results = []
    for item in sorted(normalized_data.items()):
        result = process_item(item)
        intermediate_results.append(result)
    
    # Step 3: Result aggregation
    final_result = aggregate_results(intermediate_results)
    
    return ProcessedResult(
        value=final_result,
        metadata=create_metadata(input_data)
    )
```

### Data Processing Pipelines
**Pipeline: [Name of data pipeline]**
```python
class DataProcessingPipeline:
    def __init__(self):
        self.processors = [
            ValidationProcessor(),
            TransformationProcessor(),
            EnrichmentProcessor(),
            OutputProcessor()
        ]
    
    async def process(self, raw_data: RawData) -> ProcessedData:
        """Process data through the entire pipeline"""
        current_data = raw_data
        
        for processor in self.processors:
            try:
                current_data = await processor.process(current_data)
                self.logger.info(f"Completed {processor.__class__.__name__}")
            except ProcessingError as e:
                self.logger.error(f"Pipeline failed at {processor.__class__.__name__}: {e}")
                raise
                
        return current_data
```

## 4. Integration Points

### Database Integration
**Connection Management:**
```python
# repositories/feature_repository.py
class FeatureRepository:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        
    async def create(self, feature_data: dict) -> Feature:
        """Create new feature in database with proper transaction handling"""
        async with self.db.transaction():
            # Insert main feature record
            feature_id = await self.db.execute(
                "INSERT INTO features (name, description, user_id, created_at) VALUES ($1, $2, $3, $4) RETURNING id",
                feature_data['name'], 
                feature_data.get('description'),
                feature_data['user_id'],
                datetime.utcnow()
            )
            
            # Insert related configuration data
            if 'settings' in feature_data:
                await self.db.execute(
                    "INSERT INTO feature_settings (feature_id, settings) VALUES ($1, $2)",
                    feature_id,
                    json.dumps(feature_data['settings'])
                )
                
            return await self.get_by_id(feature_id)
```

### External API Integration
**Service Integration:**
```python
# services/integration_service.py
class ExternalAPIService:
    def __init__(self, api_client: HTTPClient, config: APIConfig):
        self.client = api_client
        self.config = config
        self.rate_limiter = RateLimiter(max_calls=100, time_window=60)
    
    @retry(max_attempts=3, backoff=exponential_backoff)
    async def fetch_external_data(self, request_params: dict) -> ExternalData:
        """Fetch data from external API with retry logic and rate limiting"""
        await self.rate_limiter.acquire()
        
        try:
            response = await self.client.post(
                f"{self.config.base_url}/data",
                json=request_params,
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code != 200:
                raise APIError(f"External API returned {response.status_code}: {response.text}")
                
            return ExternalData.from_api_response(response.json())
            
        except HTTPError as e:
            self.logger.error(f"HTTP error during external API call: {e}")
            raise IntegrationError(f"Failed to fetch external data: {e}")
```

## 5. Configuration

### Environment Variables
```python
# config/settings.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class FeatureConfig:
    # Database configuration
    database_url: str = os.getenv('DATABASE_URL', 'postgresql://localhost/app')
    database_pool_size: int = int(os.getenv('DB_POOL_SIZE', '10'))
    
    # External API configuration
    external_api_url: str = os.getenv('EXTERNAL_API_URL', 'https://api.example.com')
    external_api_key: str = os.getenv('EXTERNAL_API_KEY', '')
    external_api_timeout: int = int(os.getenv('API_TIMEOUT', '30'))
    
    # Feature-specific configuration
    feature_cache_ttl: int = int(os.getenv('FEATURE_CACHE_TTL', '3600'))
    max_concurrent_processing: int = int(os.getenv('MAX_CONCURRENT', '5'))
    enable_debug_logging: bool = os.getenv('DEBUG', '').lower() == 'true'
    
    # Validation configuration
    max_name_length: int = int(os.getenv('MAX_NAME_LENGTH', '255'))
    allowed_file_types: list = os.getenv('ALLOWED_FILES', 'pdf,csv,xlsx').split(',')

def get_feature_config() -> FeatureConfig:
    """Get feature configuration with validation"""
    config = FeatureConfig()
    
    # Validate required configuration
    if not config.external_api_key:
        raise ConfigurationError("EXTERNAL_API_KEY environment variable is required")
        
    return config
```

### Application Configuration
```python
# config/app_config.py
FEATURE_SETTINGS = {
    'processing': {
        'batch_size': 100,
        'max_retries': 3,
        'retry_delay': 1.0,
        'timeout_seconds': 300
    },
    'caching': {
        'default_ttl': 3600,
        'max_size': 1000,
        'eviction_policy': 'LRU'
    },
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'handlers': ['console', 'file']
    }
}
```

## 6. Testing Implementation

### Unit Test Structure
```python
# tests/unit/test_feature_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.feature.services.feature_service import FeatureService
from src.feature.models.feature_model import Feature
from src.feature.exceptions.feature_exceptions import ValidationError

class TestFeatureService:
    @pytest.fixture
    def mock_repository(self):
        return Mock()
    
    @pytest.fixture
    def mock_cache(self):
        return Mock()
    
    @pytest.fixture
    def feature_service(self, mock_repository, mock_cache):
        return FeatureService(mock_repository, mock_cache)
    
    @pytest.mark.asyncio
    async def test_create_feature_success(self, feature_service, mock_repository):
        # Arrange
        user_id = "user123"
        feature_data = {"name": "Test Feature", "description": "Test description"}
        expected_feature = Feature(id="feature123", name="Test Feature")
        mock_repository.create.return_value = expected_feature
        
        # Act
        result = await feature_service.create_feature(user_id, feature_data)
        
        # Assert
        assert result == expected_feature
        mock_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_feature_validation_error(self, feature_service):
        # Arrange
        user_id = "user123"
        invalid_data = {"description": "Missing name"}
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await feature_service.create_feature(user_id, invalid_data)
        
        assert "name is required" in str(exc_info.value)
```

### Integration Test Examples
```python
# tests/integration/test_feature_api.py
import pytest
import asyncio
from httpx import AsyncClient
from src.main import app
from tests.fixtures.database import test_database

@pytest.mark.asyncio
async def test_create_feature_api_integration():
    """Test full API integration for feature creation"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Arrange
        feature_data = {
            "name": "Integration Test Feature",
            "description": "Created during integration testing"
        }
        
        # Act
        response = await client.post(
            "/api/v1/features",
            json=feature_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == feature_data["name"]
        assert "id" in response_data
        assert "created_at" in response_data
```

### Test Utilities
```python
# tests/utils/test_helpers.py
import uuid
from datetime import datetime
from src.feature.models.feature_model import Feature

def create_test_feature(**overrides) -> Feature:
    """Create a test feature with default values"""
    defaults = {
        'id': str(uuid.uuid4()),
        'name': 'Test Feature',
        'description': 'Test description',
        'user_id': str(uuid.uuid4()),
        'created_at': datetime.utcnow(),
        'status': 'active'
    }
    defaults.update(overrides)
    return Feature(**defaults)

async def setup_test_data(db_connection):
    """Set up test data for integration tests"""
    # Create test users
    test_user = await create_test_user(db_connection)
    
    # Create test features
    test_features = []
    for i in range(3):
        feature = await create_test_feature(
            db_connection,
            name=f"Test Feature {i}",
            user_id=test_user.id
        )
        test_features.append(feature)
    
    return {
        'user': test_user,
        'features': test_features
    }
```

## 7. Development Tools

### Required Dependencies
```python
# requirements.txt additions
# Core dependencies for this feature
sqlalchemy>=2.0.0      # Database ORM
alembic>=1.8.0         # Database migrations
pydantic>=2.0.0        # Data validation
httpx>=0.24.0          # Async HTTP client
redis>=4.5.0           # Caching
celery>=5.2.0          # Background tasks

# Development dependencies
pytest-asyncio>=0.21.0 # Async testing
pytest-mock>=3.10.0    # Mock utilities
factory-boy>=3.2.0     # Test data factories
```

### Development Scripts
```bash
#!/bin/bash
# scripts/dev_setup.sh
echo "Setting up development environment for feature..."

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run database migrations
alembic upgrade head

# Create test database
createdb app_test

# Run initial tests
pytest tests/unit/

echo "Development environment ready!"
```

### Code Generation Tools
```python
# scripts/generate_feature_boilerplate.py
import os
import sys
from pathlib import Path

def generate_feature_structure(feature_name: str):
    """Generate boilerplate code structure for new feature"""
    
    feature_dir = Path(f"src/{feature_name}")
    
    # Create directory structure
    directories = [
        "controllers", "services", "models", "repositories", 
        "utils", "exceptions", "models/dto"
    ]
    
    for directory in directories:
        (feature_dir / directory).mkdir(parents=True, exist_ok=True)
        (feature_dir / directory / "__init__.py").touch()
    
    # Generate basic service template
    service_template = f'''
class {feature_name.title()}Service:
    def __init__(self, repository, cache):
        self.repository = repository
        self.cache = cache
    
    async def create(self, data: dict):
        """Create new {feature_name}"""
        # TODO: Implement creation logic
        pass
    '''
    
    with open(feature_dir / "services" / f"{feature_name}_service.py", "w") as f:
        f.write(service_template)
    
    print(f"Feature structure created at {feature_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_feature_boilerplate.py <feature_name>")
        sys.exit(1)
    
    generate_feature_structure(sys.argv[1])
```

## 8. Code Examples

### Complete Implementation Example
```python
# Complete implementation of a core feature component
# services/feature_service.py

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.feature.models.feature_model import Feature
from src.feature.repositories.feature_repository import FeatureRepository
from src.feature.services.cache_service import CacheService
from src.feature.exceptions.feature_exceptions import (
    FeatureNotFoundError, 
    ValidationError, 
    PermissionError
)
from src.feature.utils.validators import validate_feature_data
from src.feature.utils.constants import MAX_FEATURES_PER_USER

@dataclass
class FeatureCreationResult:
    feature: Feature
    warnings: List[str]

class FeatureService:
    def __init__(self, repository: FeatureRepository, cache: CacheService):
        self.repository = repository
        self.cache = cache
        self.logger = logging.getLogger(__name__)

    async def create_feature(self, user_id: str, data: Dict[str, Any]) -> FeatureCreationResult:
        """
        Create a new feature with comprehensive validation and error handling
        
        Args:
            user_id: ID of the user creating the feature
            data: Feature configuration data
            
        Returns:
            FeatureCreationResult: Created feature and any warnings
            
        Raises:
            ValidationError: If data is invalid
            PermissionError: If user lacks permissions or exceeds limits
        """
        # Validate input data
        validation_result = validate_feature_data(data)
        if not validation_result.is_valid:
            raise ValidationError(f"Invalid feature data: {validation_result.errors}")
        
        # Check user permissions and limits
        await self._check_user_permissions(user_id, data)
        
        # Check if user has reached feature limit
        user_feature_count = await self.repository.count_user_features(user_id)
        if user_feature_count >= MAX_FEATURES_PER_USER:
            raise PermissionError(f"User has reached maximum features limit ({MAX_FEATURES_PER_USER})")
        
        # Create feature
        try:
            feature = await self.repository.create({
                **data,
                'user_id': user_id,
                'status': 'active',
                'created_at': datetime.utcnow()
            })
            
            # Cache the new feature
            await self.cache.set(f"feature:{feature.id}", feature, ttl=3600)
            
            # Invalidate user's feature list cache
            await self.cache.delete(f"user_features:{user_id}")
            
            self.logger.info(f"Feature {feature.id} created for user {user_id}")
            
            return FeatureCreationResult(
                feature=feature,
                warnings=validation_result.warnings
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create feature for user {user_id}: {e}")
            raise
    
    async def get_feature(self, feature_id: str, user_id: str) -> Feature:
        """Get feature by ID with user permission check"""
        # Try cache first
        cached_feature = await self.cache.get(f"feature:{feature_id}")
        if cached_feature:
            feature = Feature.from_cache(cached_feature)
        else:
            feature = await self.repository.get_by_id(feature_id)
            if not feature:
                raise FeatureNotFoundError(f"Feature {feature_id} not found")
            
            # Cache for future requests
            await self.cache.set(f"feature:{feature_id}", feature, ttl=3600)
        
        # Check permissions
        if feature.user_id != user_id:
            raise PermissionError("User does not have access to this feature")
        
        return feature
    
    async def _check_user_permissions(self, user_id: str, data: Dict[str, Any]) -> None:
        """Check if user has permissions for the requested feature configuration"""
        # Example permission checks
        if data.get('premium_features') and not await self._is_premium_user(user_id):
            raise PermissionError("Premium features require premium subscription")
        
        if data.get('api_access') and not await self._has_api_access(user_id):
            raise PermissionError("User does not have API access permissions")
    
    async def _is_premium_user(self, user_id: str) -> bool:
        """Check if user has premium subscription"""
        # Implementation would check subscription status
        return True  # Placeholder
    
    async def _has_api_access(self, user_id: str) -> bool:
        """Check if user has API access"""
        # Implementation would check API permissions
        return True  # Placeholder
```

## 9. Performance Implementation

### Caching Strategy
```python
# services/cache_service.py
import redis
import json
import pickle
from typing import Any, Optional
from datetime import timedelta

class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=False)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with automatic deserialization"""
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return pickle.loads(cached_data)
            return None
        except Exception as e:
            logging.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            serialized_data = pickle.dumps(value)
            return self.redis.setex(key, ttl, serialized_data)
        except Exception as e:
            logging.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logging.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def get_or_set(self, key: str, factory_func, ttl: int = 3600) -> Any:
        """Get from cache or compute and cache the result"""
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Compute new value
        new_value = await factory_func()
        await self.set(key, new_value, ttl)
        return new_value
```

### Database Optimization
```python
# repositories/optimized_feature_repository.py
class OptimizedFeatureRepository:
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def get_user_features_optimized(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Feature]:
        """Get user features with optimized query and pagination"""
        query = """
        SELECT f.id, f.name, f.description, f.status, f.created_at,
               fs.settings,
               COUNT(fa.id) as activity_count
        FROM features f
        LEFT JOIN feature_settings fs ON f.id = fs.feature_id
        LEFT JOIN feature_activity fa ON f.id = fa.feature_id
        WHERE f.user_id = $1 AND f.status = 'active'
        GROUP BY f.id, fs.settings
        ORDER BY f.created_at DESC
        LIMIT $2 OFFSET $3
        """
        
        rows = await self.db.fetch(query, user_id, limit, offset)
        return [self._row_to_feature(row) for row in rows]
    
    async def bulk_update_features(self, updates: List[Dict]) -> int:
        """Bulk update multiple features efficiently"""
        if not updates:
            return 0
        
        # Use UNNEST for bulk operations
        query = """
        UPDATE features SET
            name = bulk_data.name,
            description = bulk_data.description,
            updated_at = NOW()
        FROM (
            SELECT 
                unnest($1::uuid[]) as id,
                unnest($2::text[]) as name,
                unnest($3::text[]) as description
        ) as bulk_data
        WHERE features.id = bulk_data.id
        """
        
        ids = [update['id'] for update in updates]
        names = [update['name'] for update in updates]
        descriptions = [update.get('description', '') for update in updates]
        
        result = await self.db.execute(query, ids, names, descriptions)
        return int(result.split()[-1])  # Extract affected row count
```

## 10. Deployment Considerations

### Docker Configuration
```dockerfile
# Dockerfile for feature deployment
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY config/ config/
COPY migrations/ migrations/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Database Migration Scripts
```python
# migrations/versions/001_create_feature_tables.py
"""Create feature tables

Revision ID: 001
Revises: 
Create Date: 2024-08-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create features table
    op.create_table('features',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create feature settings table
    op.create_table('feature_settings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('feature_id', UUID(as_uuid=True), nullable=False),
        sa.Column('settings', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['feature_id'], ['features.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('idx_features_user_id', 'features', ['user_id'])
    op.create_index('idx_features_status', 'features', ['status'])
    op.create_index('idx_feature_settings_feature_id', 'feature_settings', ['feature_id'])

def downgrade():
    op.drop_table('feature_settings')
    op.drop_table('features')
```

### Monitoring and Logging
```python
# utils/monitoring.py
import logging
import time
from functools import wraps
from typing import Callable
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

def monitor_performance(func_name: str):
    """Decorator to monitor function performance"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = structlog.get_logger()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    "Function completed successfully",
                    function=func_name,
                    duration=duration,
                    args_count=len(args),
                    kwargs_count=len(kwargs)
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    "Function failed",
                    function=func_name,
                    duration=duration,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                raise
                
        return wrapper
    return decorator

# Usage example
@monitor_performance("feature_creation")
async def create_feature(user_id: str, data: dict) -> Feature:
    # Implementation here
    pass
```
```

## Next Steps After TID
1. Review TID with development team for implementation feasibility
2. Use `006_generate-tasks.md` to convert TID into actionable task list
3. Set up development environment according to TID specifications
4. Begin implementation following the detailed guidance provided

## Quality Checklist
- [ ] Implementation strategy is clear and follows established patterns
- [ ] Code structure supports maintainability and testing
- [ ] Key algorithms are detailed with complexity analysis
- [ ] Integration points have specific implementation guidance
- [ ] Configuration management is comprehensive and secure
- [ ] Testing implementation covers unit, integration, and end-to-end scenarios
- [ ] Development tools and scripts support efficient development
- [ ] Code examples demonstrate proper usage patterns
- [ ] Performance implementation addresses identified bottlenecks
- [ ] Deployment considerations support production requirements

## Example Usage
```
Please create a Technical Implementation Document for "Data Export" based on the TDD in 0xcc/tdds/002_FTDD|DataExport.md.

Context: The system uses FastAPI with SQLAlchemy ORM, PostgreSQL database, and Redis caching. Existing authentication uses JWT tokens. The codebase follows async patterns and uses structured logging.

[Continue with template requirements...]
```