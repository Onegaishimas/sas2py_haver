# Create Feature PRD - Individual Feature Requirements

## Purpose
Generate detailed Product Requirements Documents for individual features, providing specific requirements and user stories.

## When to Use
- After Project PRD and ADR are complete
- Before designing technical implementation for a feature
- When adding new features to existing projects

## Instructions

### Option A: Direct Feature PRD Creation
```
Please create a Feature PRD for [FEATURE NAME] in the [PROJECT NAME] project.

Context from Project PRD: [Brief summary of project and how this feature fits]

Requirements:
1. Feature Overview - Clear description and value proposition
2. User Stories - Specific scenarios and user workflows  
3. Functional Requirements - What the feature must do
4. Non-Functional Requirements - Performance, security, usability
5. API/Interface Specification - How users interact with the feature
6. Data Requirements - What data is needed and how it's structured
7. Acceptance Criteria - How we know the feature is done
8. Dependencies - What other features or systems this relies on

Output: Save as 0xcc/prds/[###]_FPRD|[feature-name].md

Focus on user needs and specific requirements - avoid implementation details.
```

### Option B: Research-Enhanced Creation
```
🔍 Research first: Use /mcp ref search '[feature type] requirements best practices'

Then create a Feature PRD for [FEATURE NAME] incorporating current best practices and user experience patterns.
[Include same requirements as Option A]
```

## Template Structure

```markdown
# Feature PRD: [Feature Name]

## 1. Feature Overview
**Purpose**: What problem does this feature solve?
**Value Proposition**: Why is this valuable to users?
**Scope**: What's included and what's explicitly out of scope?
**Priority**: How important is this feature? (Critical/High/Medium/Low)

## 2. User Stories

### Primary User Stories
**As a [user type]**
**I want to [capability]**  
**So that [benefit/value]**

**Acceptance Criteria:**
- [ ] [Specific, testable condition]
- [ ] [Another specific condition]
- [ ] [Error handling condition]

### Secondary User Stories
[Additional user stories for edge cases or less common scenarios]

## 3. Functional Requirements

### Core Functionality
**FR1**: [Requirement ID] - [Clear, specific requirement]
**FR2**: [Requirement ID] - [Another specific requirement]
**FR3**: [Requirement ID] - [Error handling requirement]

### Input/Output Specifications
**Inputs**: What data/parameters the feature accepts
**Outputs**: What the feature produces or returns
**Data Validation**: What constitutes valid input
**Error Responses**: How invalid inputs are handled

## 4. Non-Functional Requirements

### Performance
**Response Time**: [Specific timing requirements]
**Throughput**: [Volume/capacity requirements]  
**Scalability**: [Growth expectations]

### Security
**Authentication**: [Who can access this feature]
**Authorization**: [What permissions are required]
**Data Protection**: [How sensitive data is handled]

### Usability  
**User Experience**: [Ease of use requirements]
**Accessibility**: [Accessibility standards to meet]
**Documentation**: [Help/documentation requirements]

## 5. API/Interface Specification

### User Interface (if applicable)
**Input Fields**: [What users can enter/select]
**Display Elements**: [What information is shown]
**Navigation**: [How users move through the feature]
**Responsive Design**: [Mobile/tablet considerations]

### Programmatic Interface (if applicable)
**Endpoints**: [API endpoints or function signatures]
**Parameters**: [Required and optional parameters]
**Response Format**: [Structure of returned data]
**Error Codes**: [Specific error responses]

## 6. Data Requirements

### Data Model
**Entities**: [What data objects are involved]
**Attributes**: [Properties of each entity]
**Relationships**: [How entities connect to each other]
**Constraints**: [Data validation rules and limits]

### Data Sources
**Input Sources**: [Where data comes from]
**External Services**: [Third-party APIs or services used]
**Data Storage**: [How/where data is persisted]
**Data Lifecycle**: [Creation, updates, deletion policies]

## 7. Business Rules

### Logic Rules
**BR1**: [Business rule ID] - [Specific business logic]
**BR2**: [Business rule ID] - [Another business rule]
**BR3**: [Business rule ID] - [Exception handling rule]

### Workflow Rules
**Process Flow**: [Step-by-step workflow description]
**Decision Points**: [Where choices/branches occur]
**Validation Points**: [Where data/process validation happens]

## 8. Dependencies

### Internal Dependencies
**Features**: [Other features this depends on]
**Components**: [System components required]
**Data**: [Required data or data structures]

### External Dependencies  
**Services**: [Third-party services required]
**APIs**: [External APIs used]
**Libraries**: [Required software libraries]

## 9. Acceptance Criteria

### Feature Complete When:
- [ ] All functional requirements implemented
- [ ] All user stories satisfied with acceptance criteria met
- [ ] Non-functional requirements verified
- [ ] Integration with dependent systems working
- [ ] Error handling covers identified scenarios
- [ ] Documentation complete and accurate

### Quality Gates
- [ ] Code review completed
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing  
- [ ] Performance requirements verified
- [ ] Security requirements verified
- [ ] User acceptance testing completed

## 10. Out of Scope

### Explicitly Not Included
**Features**: [What similar features are NOT part of this PRD]
**Integrations**: [What integrations are NOT included]
**Performance**: [What performance levels are NOT targeted]

### Future Considerations
**Enhancements**: [Potential future improvements]
**Related Features**: [Features that might be added later]
**Scalability**: [Future scaling considerations]
```

## Next Steps After Feature PRD
1. Review Feature PRD with stakeholders/users if applicable
2. Use `004_create-tdd.md` to design technical implementation
3. Update project documentation with new feature scope
4. Consider impact on existing features and system architecture

## Quality Checklist
- [ ] User stories reflect real user needs and scenarios
- [ ] Functional requirements are specific and testable
- [ ] Non-functional requirements include measurable criteria
- [ ] Interface specifications are complete and clear
- [ ] Data requirements cover all necessary information
- [ ] Dependencies are identified and realistic
- [ ] Acceptance criteria provide clear completion definition
- [ ] Out of scope items prevent feature creep

## Example Usage
```
Please create a Feature PRD for "Data Export" in the Personal Finance Dashboard project.

Context: Users need to export their financial data for tax preparation, analysis in other tools, and backup purposes. This builds on the existing data visualization and account management features.

[Continue with template requirements...]
```