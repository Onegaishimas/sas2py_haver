# Create Technical Design Document (TDD)

## Purpose
Generate Technical Design Documents that translate feature requirements into architectural design and technical specifications.

## When to Use
- After Feature PRD is complete and approved
- Before beginning detailed implementation planning
- When designing complex features that need architectural clarity

## Instructions

### Option A: Direct TDD Creation
```
Please create a Technical Design Document (TDD) for [FEATURE NAME] based on [FEATURE PRD FILE].

Requirements:
1. System Architecture - How the feature fits into overall system
2. Component Design - Modules, classes, and their responsibilities
3. Data Flow - How information moves through the system
4. Database Design - Schema, relationships, and data access patterns
5. API Design - External interfaces and contracts
6. Security Considerations - Authentication, authorization, data protection
7. Performance Considerations - Scalability, caching, optimization
8. Error Handling - Exception management and recovery strategies
9. Testing Strategy - How the feature will be validated
10. Implementation Phases - Development approach and milestones

Context: [Reference the Feature PRD and existing system architecture]

Output: Save as 0xcc/tdds/[###]_FTDD|[feature-name].md

Focus on HOW the feature will be built, not WHAT it does.
```

### Option B: Research-Enhanced Creation
```
🔍 Research first: Use /mcp ref search '[technology] architectural patterns [feature type]'

Then create a TDD for [FEATURE NAME] incorporating current architectural best practices and design patterns.
[Include same requirements as Option A]
```

## Template Structure

```markdown
# Technical Design Document: [Feature Name]

## 1. System Architecture

### Context Diagram
**Current System**: [How existing system components relate]
**Feature Integration**: [Where this feature fits in the system]
**External Dependencies**: [Outside systems or services used]

### Architecture Patterns
**Design Pattern**: [MVC, Repository, Factory, etc.]
**Architectural Style**: [RESTful, Event-driven, etc.]
**Communication Pattern**: [Synchronous/Asynchronous, Message Queues, etc.]

## 2. Component Design

### High-Level Components
**Component A**: [Name and primary responsibility]
- Purpose: [What this component does]
- Interface: [How other components interact with it]
- Dependencies: [What this component needs]

**Component B**: [Name and primary responsibility]
- Purpose: [What this component does]
- Interface: [How other components interact with it]
- Dependencies: [What this component needs]

### Class/Module Structure
```
FeatureModule/
├── controllers/
│   ├── FeatureController.py      # HTTP request handling
│   └── ValidationController.py   # Input validation
├── services/
│   ├── FeatureService.py         # Business logic
│   └── ExternalAPIService.py     # Third-party integrations
├── models/
│   ├── FeatureModel.py           # Data models
│   └── DTOs/                     # Data transfer objects
├── repositories/
│   └── FeatureRepository.py      # Data access layer
└── utilities/
    ├── FeatureHelpers.py         # Utility functions
    └── Constants.py              # Configuration constants
```

## 3. Data Flow

### Request/Response Flow
1. **Input**: [How requests enter the system]
2. **Validation**: [How inputs are validated and sanitized]
3. **Processing**: [Business logic and transformations]
4. **Data Access**: [Database queries and updates]
5. **Response**: [How results are formatted and returned]

### Data Transformation
**Input Format** → **Processing Steps** → **Output Format**
[Detailed description of how data changes through the system]

### State Management  
**State Storage**: [Where application state is maintained]
**State Updates**: [How state changes are managed]
**State Persistence**: [How state survives application restarts]

## 4. Database Design

### Entity Relationship Diagram
```
[Entity1] ──< [Relationship] >── [Entity2]
    |                               |
[Attributes]                  [Attributes]
```

### Schema Design
**Table: feature_data**
- `id` (Primary Key, UUID)
- `user_id` (Foreign Key, References users.id)  
- `data_field` (VARCHAR(255), NOT NULL)
- `status` (ENUM: active, inactive, pending)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, ON UPDATE CURRENT_TIMESTAMP)

### Data Access Patterns
**Read Operations**: [How data is queried and retrieved]
**Write Operations**: [How data is created and updated]
**Caching Strategy**: [What data is cached and when]
**Migration Strategy**: [How schema changes are handled]

## 5. API Design

### REST Endpoints (if applicable)
```
GET    /api/v1/features           # List all features
POST   /api/v1/features           # Create new feature
GET    /api/v1/features/{id}      # Get specific feature
PUT    /api/v1/features/{id}      # Update feature
DELETE /api/v1/features/{id}      # Delete feature
```

### Request/Response Schemas
**Create Feature Request:**
```json
{
  "name": "string (required)",
  "description": "string (optional)",
  "settings": {
    "enabled": "boolean",
    "priority": "integer"
  }
}
```

**Feature Response:**
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "status": "string",
  "created_at": "ISO8601 datetime",
  "settings": {
    "enabled": "boolean",
    "priority": "integer"
  }
}
```

### Function/Method Interfaces (if applicable)
```python
class FeatureService:
    def create_feature(self, user_id: str, feature_data: dict) -> Feature:
        """Create a new feature for the specified user"""
        
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Retrieve feature by ID"""
        
    def update_feature(self, feature_id: str, updates: dict) -> Feature:
        """Update existing feature"""
        
    def delete_feature(self, feature_id: str) -> bool:
        """Remove feature from system"""
```

## 6. Security Considerations

### Authentication
**Required Authentication**: [What authentication is needed]
**Token Management**: [How auth tokens are handled]
**Session Management**: [User session lifecycle]

### Authorization  
**Permission Model**: [Role-based, attribute-based, etc.]
**Access Controls**: [Who can access what resources]
**Data Filtering**: [How data is filtered based on permissions]

### Data Protection
**Sensitive Data**: [What data needs special protection]
**Encryption**: [Data at rest and in transit encryption]
**Input Sanitization**: [How inputs are cleaned and validated]
**SQL Injection Prevention**: [Parameterized queries, ORM usage]

## 7. Performance Considerations

### Scalability Design
**Horizontal Scaling**: [How the feature scales across instances]
**Vertical Scaling**: [Resource requirements and limits]
**Database Scaling**: [Read replicas, sharding, etc.]

### Optimization Strategies
**Caching**: [What to cache and cache invalidation strategy]
**Database Indexes**: [Required indexes for query performance]
**Async Processing**: [Background jobs and queue processing]
**Resource Pooling**: [Connection pools, object pools, etc.]

### Performance Targets
**Response Time**: [Maximum acceptable response times]
**Throughput**: [Requests per second targets]
**Resource Usage**: [Memory, CPU, storage limits]

## 8. Error Handling

### Exception Hierarchy
```
FeatureException (Base)
├── FeatureValidationError    # Input validation failures
├── FeatureNotFoundError      # Resource not found
├── FeaturePermissionError    # Authorization failures
└── FeatureServiceError       # Service/integration failures
```

### Error Response Format
```json
{
  "error": {
    "code": "FEATURE_VALIDATION_ERROR",
    "message": "Feature name is required",
    "details": {
      "field": "name",
      "constraint": "required"
    },
    "request_id": "uuid"
  }
}
```

### Recovery Strategies
**Transient Failures**: [Retry logic and backoff strategies]
**Permanent Failures**: [Error logging and user notification]
**Partial Failures**: [Graceful degradation approaches]

## 9. Testing Strategy

### Unit Testing
**Components to Test**: [Specific classes and methods]
**Mock Strategy**: [What external dependencies to mock]
**Coverage Targets**: [Code coverage percentage goals]

### Integration Testing
**Integration Points**: [External APIs, databases, services]
**Test Data**: [How test data is created and managed]
**Environment**: [Test environment requirements]

### End-to-End Testing
**User Scenarios**: [Critical user workflows to test]
**Automation**: [What tests can be automated]
**Manual Testing**: [What requires human verification]

## 10. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Database schema and migrations
- [ ] Basic model classes and repositories
- [ ] Core service layer structure
- [ ] Basic error handling framework

### Phase 2: Business Logic (Week 2)  
- [ ] Feature creation and management logic
- [ ] Validation and business rules
- [ ] Integration with external services
- [ ] Comprehensive error handling

### Phase 3: API and Integration (Week 3)
- [ ] REST API endpoints or public interfaces
- [ ] Authentication and authorization
- [ ] Input/output serialization
- [ ] API documentation

### Phase 4: Testing and Polish (Week 4)
- [ ] Comprehensive unit test suite
- [ ] Integration testing
- [ ] Performance testing and optimization
- [ ] Documentation and deployment preparation

### Dependencies and Blockers
**Requires**: [What must be complete before starting]
**Provides**: [What this enables for other features]
**Risks**: [Potential technical or timeline risks]
```

## Next Steps After TDD
1. Review TDD with technical team for feasibility and completeness
2. Use `005_create-tid.md` to create implementation guidance
3. Update system architecture documentation if needed
4. Identify any prototype or proof-of-concept work needed

## Quality Checklist
- [ ] Architecture integrates cleanly with existing system
- [ ] Component responsibilities are clear and single-purpose
- [ ] Data flow is logical and efficient
- [ ] Database design supports required queries and scales appropriately
- [ ] API design follows established conventions and patterns
- [ ] Security considerations address identified risks
- [ ] Performance design meets non-functional requirements
- [ ] Error handling covers anticipated failure modes
- [ ] Testing strategy provides adequate coverage and confidence
- [ ] Implementation phases are realistic and properly sequenced

## Example Usage
```
Please create a Technical Design Document for "Data Export" based on the Feature PRD in 0xcc/prds/002_FPRD|DataExport.md.

Context: The existing system uses Django with PostgreSQL, follows REST API patterns, and has established authentication/authorization. The export feature needs to integrate with the existing data visualization and account management systems.

[Continue with template requirements...]
```