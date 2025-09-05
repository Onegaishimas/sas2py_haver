# 0xcc Framework - Instruction Documents

This directory contains the instruction documents that guide the AI development workflow using the 0xcc framework.

## Document Overview

| Document | Purpose | Usage |
|----------|---------|-------|
| `001_create-project-prd.md` | Project vision and feature breakdown | Initial project setup |
| `002_create-adr.md` | Technology stack and architecture decisions | After PRD creation |
| `003_create-feature-prd.md` | Individual feature requirements | For each new feature |
| `004_create-tdd.md` | Technical design and architecture | After feature PRD |
| `005_create-tid.md` | Implementation guidance and hints | Before coding begins |
| `006_generate-tasks.md` | Actionable development tasks | From TIDs to tasks |
| `007_process-task-list.md` | Task execution and tracking | During development |
| `008_housekeeping.md` | Session management and cleanup | Between sessions |

## Workflow Sequence

1. **Project Setup**: Use `001_create-project-prd.md` to establish project vision
2. **Architecture**: Use `002_create-adr.md` to define technical standards
3. **Features**: For each feature, use `003` → `004` → `005` → `006` → `007`
4. **Maintenance**: Use `008_housekeeping.md` for session management

## Framework Integration

These instructions are designed to work with:
- Claude Code IDE integration
- MCP research server (when available)
- Git version control workflow
- Pytest testing framework
- Jupyter notebook development

## Current Project Status

**Federal Reserve ETL Pipeline**:
- ✅ Project PRD completed
- ✅ Architecture decisions made  
- ✅ Core features implemented
- ✅ MVP validated with real API testing
- 📋 Ready for enhancement features or deployment preparation