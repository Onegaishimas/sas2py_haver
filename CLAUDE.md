# Project: Federal Reserve ETL Pipeline

## Current Status
- **Phase:** Documentation Complete - Full 0xcc Framework Implementation
- **Last Session:** September 2, 2025 - Task list generation from TIDs
- **Next Steps:** Optional enhancements and maintenance planning
- **Active Document:** All 0xcc framework documents complete (PRD → TDD → TID → TASKS)
- **Current Feature:** Complete system with comprehensive documentation for 7 features

## Quick Resume Commands
```bash
# Enhanced XCC session start sequence
"Please help me resume where I left off"
# Or manual if needed:
@CLAUDE.md
@0xcc/session_state.json
ls -la 0xcc/*/

# Research integration (when ref MCP server available)
# Format: "Use /mcp ref search '[context-specific search term]'"

# Load project context (after Project PRD exists)
@0xcc/prds/000_PPRD|federal-reserve-etl.md
@0xcc/adrs/000_PADR|federal-reserve-etl.md

# Load current work area based on phase
@0xcc/prds/      # For PRD work
@0xcc/tdds/      # For TDD work  
@0xcc/tids/      # For TID work
@0xcc/tasks/     # For task execution
```

## Housekeeping Commands
```bash
"Please create a checkpoint"        # Save complete state
"Please help me resume"            # Restore context for new session
"My context is getting too large"  # Clean context, restore essentials
"Please save the session transcript" # Save session transcript
"Please show me project status"    # Display current state
```

## Project Standards
**Technology Stack:**
- Python 3.8+ for core development
- pandas>=2.0.0 for data manipulation
- requests>=2.28.0 for API communication
- pytest>=7.0.0 for testing framework
- Jupyter notebooks for interactive analysis

**Development Standards:**
- Abstract base classes with comprehensive error handling
- Factory pattern for data source instantiation
- Decorator-based retry logic with exponential backoff
- Type hints and Google-style docstrings
- Integration testing with real API calls (no mocking)
- Centralized logging with structured output

**Architecture Principles:**
- Single responsibility principle for each module
- Comprehensive exception hierarchy with context preservation
- Rate limiting compliance for external APIs
- Context manager patterns for resource management
- Configuration management with environment variables

## AI Dev Tasks Framework Workflow

### Document Creation Sequence
1. **Project Foundation**
   - `000_PPRD|federal-reserve-etl.md` � `0xcc/prds/` (Project PRD)
   - `000_PADR|federal-reserve-etl.md` � `0xcc/adrs/` (Architecture Decision Record)
   - Update this CLAUDE.md with Project Standards from ADR

2. **Feature Development** (repeat for each feature)
   - `[###]_FPRD|[feature-name].md` � `0xcc/prds/` (Feature PRD)
   - `[###]_FTDD|[feature-name].md` � `0xcc/tdds/` (Technical Design Doc)
   - `[###]_FTID|[feature-name].md` � `0xcc/tids/` (Technical Implementation Doc)
   - `[###]_FTASKS|[feature-name].md` � `0xcc/tasks/` (Task List)

### Instruction Documents Reference
- `@0xcc/instruct/001_create-project-prd.md` - Creates project vision and feature breakdown
- `@0xcc/instruct/002_create-adr.md` - Establishes tech stack and standards
- `@0xcc/instruct/003_create-feature-prd.md` - Details individual feature requirements
- `@0xcc/instruct/004_create-tdd.md` - Creates technical architecture and design
- `@0xcc/instruct/005_create-tid.md` - Provides implementation guidance and coding hints
- `@0xcc/instruct/006_generate-tasks.md` - Generates actionable development tasks
- `@0xcc/instruct/007_process-task-list.md` - Guides task execution and progress tracking
- `@0xcc/instruct/008_housekeeping.md` - Session management and context preservation

## Document Inventory

### Project Level Documents
-  0xcc/prds/000_PPRD|federal-reserve-etl.md (Project PRD) - Complete
-  0xcc/adrs/000_PADR|federal-reserve-etl.md (Architecture Decision Record) - Complete

### Feature Documents
-  0xcc/prds/001_FPRD|DualSourceDataExtraction.md (Feature PRD) - Complete
-  0xcc/tdds/001_FTDD|DualSourceDataExtraction.md (Technical Design Doc) - Complete
-  0xcc/tids/001_FTID|DualSourceDataExtraction.md (Technical Implementation Doc) - Complete
-  0xcc/tasks/001_FTASKS|DualSourceDataExtraction.md (Task List) - Complete

### Additional Features
-  0xcc/tasks/002_FTASKS|VariableMappingTransformationEngine.md (Task List) - Generated
-  0xcc/tasks/003_FTASKS|HistoricalDataRangeManagement.md (Task List) - Generated

### Status Indicators
-  **Complete:** Document finished and reviewed
- � **In Progress:** Currently being worked on
- L **Pending:** Not yet started
- = **Needs Update:** Requires revision based on changes

## Feature Priority Order

**Completed Features:**
1.  **Dual-Source Data Extraction** (Core/MVP) - Complete with FRED and Haver APIs
2.  **Integration Testing** (Critical) - 19 tests passing with real API calls  
3.  **Interactive Analysis** (Important) - Jupyter notebook with visualization
4.  **Export Capabilities** (Important) - CSV, JSON, Excel with metadata

**Future Enhancements:**
1. Variable Mapping Transformation Engine (Enhancement)
2. Historical Data Range Management (Enhancement)
3. Unit Testing Suite (Quality)
4. Deployment Documentation (Operations)

---

**Framework Version:** 1.1 (with 0xcc organization)  
**Last Updated:** September 2, 2025 - Complete 0xcc Framework Documentation  
**Project Started:** August 29, 2024  
**Structure:** Complete 0xcc framework implementation with comprehensive documentation coverage