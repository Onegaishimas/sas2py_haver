# Create Project PRD (Product Requirements Document)

## Purpose
Generate a comprehensive Project PRD that establishes the project vision, scope, and feature breakdown.

## When to Use
- Starting a new project
- Need to clarify project scope and requirements
- Before beginning any technical work

## Instructions

### Option A: Direct Creation
Use this prompt template to create a Project PRD:

```
Please create a Project PRD (Product Requirements Document) for [PROJECT NAME].

Context: [Provide 2-3 sentences about the project's purpose and goals]

Requirements:
1. Project Overview - Clear problem statement and solution approach
2. Target Users - Who will use this and their needs  
3. Core Features - 3-5 main features that deliver value
4. Success Metrics - How we'll measure success
5. Technical Constraints - Any limitations or requirements
6. Timeline - High-level phases and milestones

Output: Save as 0xcc/prds/000_PPRD|[project-name].md

Focus on the "why" and "what" - avoid implementation details.
```

### Option B: Research-Enhanced Creation
If MCP research server is available:

```
🔍 Research first: Use /mcp ref search 'PRD templates software development'

Then create a Project PRD for [PROJECT NAME] using best practices from the research.
[Include same requirements as Option A]
```

## Template Structure

```markdown
# Project PRD: [Project Name]

## 1. Project Overview
**Problem Statement**: What problem are we solving?
**Solution Approach**: High-level how we'll solve it
**Value Proposition**: Why this matters

## 2. Target Users
**Primary Users**: Who will use this most?
**Use Cases**: Key scenarios and workflows
**User Needs**: What they need to accomplish

## 3. Core Features
**Feature 1**: [Name] - [Brief description and value]
**Feature 2**: [Name] - [Brief description and value]
**Feature 3**: [Name] - [Brief description and value]

## 4. Success Metrics
**Technical**: Performance, reliability measures
**User**: Adoption, satisfaction indicators
**Business**: ROI, efficiency gains

## 5. Technical Constraints
**Technology**: Required/preferred tech stack
**Performance**: Speed, scale requirements
**Integration**: External systems/APIs
**Security**: Data protection needs

## 6. Development Timeline
**Phase 1**: MVP - Core functionality
**Phase 2**: Enhancement - Additional features  
**Phase 3**: Scale - Performance and polish
```

## Next Steps After PRD
1. Review PRD with stakeholders if applicable
2. Use `002_create-adr.md` to establish technical architecture
3. Update `CLAUDE.md` with project context
4. Begin feature development using `003_create-feature-prd.md`

## Quality Checklist
- [ ] Clear problem statement that anyone can understand
- [ ] Specific user needs and use cases identified
- [ ] Features prioritized by value/importance
- [ ] Success metrics are measurable
- [ ] Technical constraints are realistic
- [ ] Timeline has logical phases

## Example Usage
```
Please create a Project PRD for "Personal Finance Dashboard".

Context: Users need a simple way to track expenses, set budgets, and visualize spending patterns across multiple accounts and categories.

[Continue with template requirements...]
```