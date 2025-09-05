# Create Architecture Decision Record (ADR)

## Purpose
Generate an Architecture Decision Record that establishes technology stack, development standards, and architectural principles for the project.

## When to Use
- After Project PRD is complete
- Before beginning technical implementation
- When major architectural decisions need documentation

## Instructions

### Option A: Direct Creation
Use this prompt template to create an ADR:

```
Please create an Architecture Decision Record (ADR) for [PROJECT NAME].

Based on the Project PRD requirements, establish:

1. Technology Stack - Core languages, frameworks, and tools
2. Architecture Pattern - How components will be organized
3. Development Standards - Code quality, testing, documentation
4. Data Management - Storage, processing, and security approaches
5. Integration Strategy - External services, APIs, deployment
6. Decision Rationale - Why these choices support project goals

Context: [Reference the PRD and any specific technical requirements]

Output: Save as 0xcc/adrs/000_PADR|[project-name].md

Focus on decisions that impact the entire project structure.
```

### Option B: Research-Enhanced Creation
If MCP research server is available:

```
🔍 Research first: Use /mcp ref search '[technology] architecture best practices [project type]'

Then create an ADR for [PROJECT NAME] incorporating current best practices.
[Include same requirements as Option A]
```

## Template Structure

```markdown
# Architecture Decision Record: [Project Name]

## 1. Technology Stack

### Core Technologies
**Language**: [Primary language] - [Version/rationale]
**Framework**: [Main framework] - [Why chosen]
**Database**: [Data storage] - [Justification]
**Testing**: [Test framework] - [Approach]

### Supporting Tools
**Package Management**: [Tool and rationale]
**Code Quality**: [Linting, formatting tools]
**Documentation**: [Documentation approach]
**Development Environment**: [IDE, containers, etc.]

## 2. Architecture Pattern
**Overall Pattern**: [MVC, microservices, layered, etc.]
**Component Organization**: [How code is structured]
**Data Flow**: [How information moves through system]
**External Interfaces**: [APIs, file systems, etc.]

## 3. Development Standards

### Code Quality
**Style Guide**: [Naming conventions, formatting]
**Documentation**: [Docstring standards, README requirements]
**Error Handling**: [Exception strategies, logging]
**Testing Strategy**: [Unit, integration, coverage targets]

### Project Structure
**Directory Layout**: [How files and folders are organized]
**File Naming**: [Conventions for different file types]
**Import Management**: [How modules are imported/organized]

## 4. Data Management
**Data Models**: [How data is structured]
**Storage Strategy**: [Files, databases, caching]
**Security**: [Authentication, encryption, sensitive data]
**Backup/Recovery**: [Data protection strategies]

## 5. Integration Strategy
**External APIs**: [How third-party services are used]
**Configuration**: [Environment variables, config files]
**Deployment**: [How application is packaged/deployed]
**Monitoring**: [Logging, error tracking, metrics]

## 6. Decision Rationale
**Technology Choices**: [Why this stack supports the PRD goals]
**Trade-offs**: [What we're optimizing for vs. against]
**Future Considerations**: [How decisions support scalability]
**Risk Mitigation**: [How architecture reduces project risks]
```

## Next Steps After ADR
1. Update `CLAUDE.md` with Project Standards section from ADR
2. Set up development environment according to ADR specifications
3. Begin feature development using `003_create-feature-prd.md`
4. Establish project structure and initial scaffolding

## Quality Checklist
- [ ] Technology choices align with PRD requirements
- [ ] Architecture supports scalability and maintainability
- [ ] Development standards are specific and actionable
- [ ] Security and data protection addressed
- [ ] Integration points clearly defined
- [ ] Decisions are justified with rationale

## Example Usage
```
Please create an Architecture Decision Record for "Personal Finance Dashboard".

Based on the PRD requirements for real-time data processing, user authentication, and third-party bank integrations:

[Continue with template requirements...]
```