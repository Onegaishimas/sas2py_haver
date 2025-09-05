# Process Task List - Execute Development Tasks

## Purpose
Guide systematic execution of development tasks with proper tracking, testing, and quality assurance.

## When to Use
- After generating task lists from TIDs
- During active development phases
- When working through feature implementation

## Instructions

### Task Execution Protocol

```
Please use systematic task execution for [TASK LIST FILE].

Execution Rules:
1. Work on ONE task at a time, in priority order
2. Mark tasks in progress: [ ] → [~] → [x] when complete
3. Ask permission before moving to next major task
4. Run tests after completing each task
5. Clean up any temporary files
6. Commit completed tasks with descriptive messages

Quality Gates:
- All tests must pass before marking task complete
- No debugging artifacts (console.log, print statements)  
- Code follows project standards from ADR
- Documentation updated if required

For each completed task:
1. Update task status in markdown file
2. Run: pytest (or project test command)
3. Clean temporary files
4. Stage changes: git add [files]
5. Commit: git commit -m "feat: [description] - Task [#] complete"
```

## Task Status Indicators

| Status | Symbol | Meaning | Usage |
|--------|--------|---------|--------|
| Pending | `[ ]` | Not started | Default for all new tasks |
| In Progress | `[~]` | Currently working | Only ONE task at a time |
| Complete | `[x]` | Finished and tested | After all quality checks pass |
| Blocked | `[?]` | Needs clarification | When requirements unclear |

## Commit Message Standards

```bash
# Feature Implementation
git commit -m "feat: implement user authentication - Task 2.3 complete"

# Bug Fixes  
git commit -m "fix: resolve API timeout issue - Task 4.2 complete"

# Testing
git commit -m "test: add integration tests for data export - Task 5.1 complete"

# Documentation
git commit -m "docs: update API usage examples - Task 6.4 complete"
```

## Quality Checkpoints

### Before Marking Task Complete
- [ ] Functionality works as specified
- [ ] All relevant tests pass
- [ ] No temporary or debug code remains
- [ ] Error handling implemented properly
- [ ] Code follows project naming conventions
- [ ] Documentation updated if public interface changed

### Before Moving to Next Task
- [ ] Previous task fully complete and committed
- [ ] Working directory clean (git status)
- [ ] No broken functionality introduced
- [ ] Task list file updated with progress

## Testing Integration

### Test Commands by Project Type
```bash
# Python Projects
pytest tests/
python -m pytest tests/unit/
python -m pytest tests/integration/

# Node.js Projects  
npm test
npm run test:unit
npm run test:integration

# Custom Projects
# Check project README or ADR for specific commands
```

### Test Failure Response
1. **Read error message carefully** - understand what failed
2. **Check recent changes** - what did you just modify?
3. **Run individual test** - isolate the specific failure
4. **Fix the issue** - address root cause, not just symptoms
5. **Re-run full test suite** - ensure no regressions
6. **Update task status only after all tests pass**

## Session Management

### End of Development Session
```bash
# Update task progress
# Commit any completed work
git add .
git commit -m "wip: progress on [current task] - resuming in next session"

# Update CLAUDE.md with current status
# Note: Next session should start with current task
```

### Session Recovery
```bash
# Check where you left off
@CLAUDE.md
@0xcc/tasks/[current-task-list].md

# Review what was completed
git log --oneline -10

# Continue with current in-progress task
```

## Error Handling

### When Tasks are Unclear
1. **Review source documents** - Check PRD, TDD, TID for context
2. **Ask for clarification** - Don't guess at requirements
3. **Break down complex tasks** - Split into smaller, clearer steps
4. **Update task description** - Make it clearer for future reference

### When Tests Fail
1. **Don't skip testing** - Fix the issue, don't work around it
2. **Understand the failure** - Read error messages completely
3. **Fix root cause** - Don't just make tests pass superficially
4. **Ensure all tests pass** - Run full suite, not just failing test

### When Blocked
1. **Mark task as [?]** - Use blocked status indicator
2. **Document the blocker** - What specifically needs clarification?
3. **Ask for help** - Provide context about what you tried
4. **Work on other tasks** - Don't let one blocker stop all progress

## Example Task Execution

```markdown
### Current Task Progress

- [x] 1.1 Set up project structure  
- [x] 1.2 Install dependencies
- [~] 1.3 Implement authentication system
  - [x] User model created
  - [x] Login endpoint implemented  
  - [ ] Password hashing (currently working on)
  - [ ] JWT token generation
- [ ] 1.4 Add input validation
- [ ] 1.5 Write authentication tests
```

## Success Indicators
- [ ] Tasks completed in logical order
- [ ] All tests passing consistently  
- [ ] Clean git history with meaningful commits
- [ ] No accumulation of technical debt
- [ ] Progress visible and well-documented
- [ ] Each task delivers working functionality