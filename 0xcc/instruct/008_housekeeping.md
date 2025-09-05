# Housekeeping - Session Management and Context Preservation

## Purpose
Manage development sessions, preserve context between sessions, and maintain project organization.

## When to Use
- At the end of development sessions
- When starting new sessions
- When context becomes too large or fragmented
- For regular project maintenance

## Session End Protocol

### Before Ending Session
```
Please create a checkpoint before ending this session.

Tasks to complete:
1. Update CLAUDE.md with current status and progress
2. Commit any pending work with clear commit messages
3. Clean up temporary files and artifacts
4. Update task lists with current progress
5. Note next steps for resume

Current status: [Brief description of where you are]
Next session should: [Specific action to start with]
```

### Checkpoint Creation
```bash
# 1. Update project status
# Edit CLAUDE.md with current phase and next steps

# 2. Commit completed work
git add .
git commit -m "checkpoint: [brief description] - Next: [specific action]"

# 3. Clean temporary files
rm -f *.tmp *.log temp_*
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 4. Update documentation
# Ensure README.md reflects current capabilities
# Update any changed API or usage examples
```

## Session Resume Protocol

### Standard Resume Sequence
```
Please help me resume where I left off.

Load context:
@CLAUDE.md
@0xcc/session_state.json (if exists)
@[current task list or document being worked on]

Show me:
1. Current project status
2. Last completed task
3. Next action to take
4. Any blockers or issues from last session
```

### Manual Context Recovery
```
# If automated resume doesn't work:

# Load essential project context
@CLAUDE.md
@README.md
@0xcc/prds/000_PPRD|[project-name].md  
@0xcc/adrs/000_PADR|[project-name].md

# Check recent work
git log --oneline -10
git status

# Load current work area
ls -la 0xcc/*/
@[most recently modified task list or document]

# Specific next action: [from CLAUDE.md or last commit]
```

## Context Management

### When Context Gets Too Large
```
My context is getting too large and I'm losing track.

Please:
1. Save current session state to 0xcc/session_state.json
2. Create a clean context with just essential files:
   - CLAUDE.md (project overview)
   - Current task list
   - Any files actively being worked on
3. Provide a focused summary of where we are
4. Confirm next specific action to take
```

### Session State Tracking
Create `0xcc/session_state.json`:
```json
{
  "project_name": "Federal Reserve ETL Pipeline",
  "current_phase": "MVP Complete",
  "last_session_date": "2024-08-29",
  "current_task_list": "0xcc/tasks/001_FTASKS|DualSourceDataExtraction.md",
  "current_task_id": "7.4",
  "current_task_description": "Integration testing complete",
  "next_action": "Consider unit testing or deployment documentation",
  "active_files": [
    "CLAUDE.md",
    "Federal_Reserve_ETL_Interactive.ipynb",
    "tests/integration/test_fred_api_connectivity.py"
  ],
  "blockers": [],
  "notes": "MVP fully validated with 19 integration tests passing"
}
```

### File Organization Cleanup
```bash
# Remove temporary and cache files
find . -name "*.tmp" -delete
find . -name "*.log" -delete
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete

# Organize project files
# Ensure all source code is in src/
# Ensure all tests are in tests/
# Ensure all docs are in appropriate locations

# Update .gitignore for any new file patterns
```

## Quality Maintenance

### Regular Maintenance Tasks
```
Please perform regular project maintenance:

1. Code Quality:
   - Run linting tools if available
   - Check for dead code or unused imports
   - Verify all functions have proper docstrings
   - Ensure consistent code formatting

2. Documentation:
   - Update README.md with any new features
   - Check that all examples still work
   - Update API documentation if interfaces changed
   - Verify installation instructions are current

3. Testing:
   - Run full test suite to ensure everything passes
   - Check test coverage if tools available
   - Update tests for any changed functionality
   - Remove obsolete or broken tests

4. Dependencies:
   - Check for unused dependencies in requirements
   - Verify all imports are still needed
   - Update dependency versions if safe to do so
```

### Project Health Checks
```
Please assess current project health:

Technical Health:
- [ ] All tests passing
- [ ] No broken functionality
- [ ] Code follows established standards
- [ ] Documentation up to date
- [ ] No security vulnerabilities

Project Organization:
- [ ] File structure follows ADR standards  
- [ ] No unnecessary files or directories
- [ ] Git history is clean and meaningful
- [ ] Task lists reflect current status
- [ ] CLAUDE.md reflects actual project state

Development Readiness:
- [ ] Next steps are clearly defined
- [ ] Development environment ready
- [ ] All required credentials/keys available
- [ ] Framework structure intact
```

## Transcript Management

### Save Session Transcript
```
Please save the session transcript for future reference.

Format: markdown file with:
- Session date and duration
- Major accomplishments  
- Key decisions made
- Code changes summary
- Next steps identified
- Any lessons learned

Save to: 0xcc/transcripts/session_[YYYY-MM-DD]_[session-number].md
```

### Transcript Template
```markdown
# Development Session - [Date]

## Session Overview
- **Duration**: [Hours]
- **Focus**: [Main area of work]
- **Status**: [Starting status] → [Ending status]

## Accomplishments
- [Major achievement 1]
- [Major achievement 2]
- [etc.]

## Key Decisions
- [Decision 1 and rationale]
- [Decision 2 and rationale]

## Code Changes
- Files modified: [list]
- New features: [list]
- Bug fixes: [list]
- Tests added: [list]

## Challenges and Solutions
- **Challenge**: [Issue encountered]
- **Solution**: [How it was resolved]

## Next Session
- **Start with**: [Specific task or file]
- **Priority**: [What should be done first]
- **Context**: [Any important notes for next session]
```

## Emergency Recovery

### If Project State is Lost
```
# Project appears corrupted or context completely lost

Please help recover the project:

1. Check git history: git log --oneline -20
2. Load last known good state from CLAUDE.md
3. Verify core functionality still works
4. Identify what was lost and needs restoration
5. Create recovery plan with priorities

Most critical files to restore:
- Project source code (src/ directory)
- Working tests (tests/ directory)  
- Configuration (requirements.txt, setup.py)
- Documentation (README.md, CLAUDE.md)
```

### Framework Recovery
```
# If 0xcc framework structure is damaged

Please restore the framework:

1. Recreate directory structure: 0xcc/{adrs,instruct,prds,tdds,tids,tasks}
2. Restore essential instruction files from this document
3. Recreate CLAUDE.md with current project status
4. Restore any existing PRDs, ADRs, or task lists from git
5. Update session state tracking
```