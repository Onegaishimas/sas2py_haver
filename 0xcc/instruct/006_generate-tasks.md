# Generate Tasks - Convert TIDs to Actionable Development Tasks

## Purpose
Transform Technical Implementation Documents (TIDs) into specific, actionable task lists that guide development work.

## When to Use
- After completing Technical Implementation Documents (TIDs)
- Before beginning development work on a feature
- When breaking down complex implementations into manageable steps

## Instructions

### Option A: Direct Task Generation
```
Please generate an actionable task list from [TID FILE].

Requirements:
1. Break implementation into specific, testable tasks
2. Order tasks by logical dependencies
3. Include testing and quality assurance tasks
4. Provide clear acceptance criteria for each task
5. Estimate complexity/effort where helpful
6. Include file paths and specific technical details

Output format:
- Hierarchical task list with sub-tasks
- Clear completion criteria
- Priority indicators (Core/MVP vs Nice-to-have)
- File references for implementation locations

Save as: 0xcc/tasks/[###]_FTASKS|[feature-name].md
```

### Option B: Research-Enhanced Generation
```
🔍 Research first: Use /mcp ref search 'software development task breakdown [technology]'

Then generate tasks from [TID FILE] using industry best practices for task organization and estimation.
```

## Task List Structure

```markdown
# Task List: [Feature Name]

## Relevant Files
[List all files that will be created or modified]

### Core Implementation Files
- `path/to/file.py` - Brief description of purpose
- `path/to/test.py` - Test coverage for above

### Configuration Files  
- `config/settings.py` - Configuration management
- `requirements.txt` - Dependencies

## Tasks

- [ ] 1.0 [Major Task Group Name]
  - [ ] 1.1 [Specific sub-task with clear deliverable]
  - [ ] 1.2 [Another specific sub-task]
  - [ ] 1.3 [Testing task for above functionality]

- [ ] 2.0 [Next Major Task Group]
  - [ ] 2.1 [Specific implementation task]
  - [ ] 2.2 [Integration or connection task]
  - [ ] 2.3 [Error handling and edge cases]
  - [ ] 2.4 [Testing and validation]

### Notes
- Task dependencies and prerequisites
- Special considerations or gotchas
- Links to external documentation if needed
```

## Task Quality Standards

### Good Task Characteristics
- **Specific**: Clear what needs to be done
- **Testable**: Can verify when complete
- **Atomic**: Single responsibility, can't be broken down further
- **Estimable**: Reasonable scope (2-8 hours of work)
- **Independent**: Minimal dependencies on other incomplete tasks

### Task Examples

**Good Tasks:**
```markdown
- [ ] 2.3 Implement rate limiting decorator in utils/rate_limiter.py
  - Accept max_calls and time_window parameters
  - Use Redis or memory cache for tracking
  - Raise RateLimitError when exceeded
  - Include exponential backoff logic

- [ ] 3.1 Create User model in models/user.py  
  - Fields: email, password_hash, created_at, is_active
  - Validation: email format, password complexity
  - Methods: check_password(), generate_token()
  - Include database migration file
```

**Poor Tasks:**
```markdown
- [ ] Make authentication work (too vague)
- [ ] Fix all the bugs (not specific)
- [ ] Implement the entire API (too large)
- [ ] Handle edge cases (what edge cases?)
```

## Task Prioritization

### Priority Levels
| Level | Symbol | Meaning | Example |
|-------|--------|---------|---------|
| Critical | 🔴 | Blocks other work | Database connection |
| Core/MVP | ⭐ | Essential functionality | User login |
| Important | 🔵 | Valuable but not blocking | Email notifications |
| Enhancement | 🟡 | Nice to have | Advanced filtering |
| Future | ⚪ | Maybe later | Premium features |

### Task Organization
```markdown
## Core MVP Tasks (Complete First)
- [x] 1.0 Database setup and models ⭐
- [ ] 2.0 Authentication system ⭐  
- [ ] 3.0 Basic CRUD operations ⭐

## Important Features (Complete After MVP)
- [ ] 4.0 Data validation and sanitization 🔵
- [ ] 5.0 Error handling and logging 🔵
- [ ] 6.0 API documentation 🔵

## Enhancement Features (Complete When Time Allows)
- [ ] 7.0 Advanced search functionality 🟡
- [ ] 8.0 Email notifications 🟡
- [ ] 9.0 Data export capabilities 🟡
```

## Testing Integration

### Test Task Templates
```markdown
- [ ] [#].3 Unit tests for [component]
  - Test happy path scenarios
  - Test error conditions and edge cases
  - Achieve >90% code coverage
  - Mock external dependencies

- [ ] [#].4 Integration tests for [feature]
  - Test end-to-end workflows
  - Test with real external services where appropriate
  - Validate data persistence and retrieval
  - Test error recovery mechanisms
```

### Quality Assurance Tasks
```markdown
- [ ] [#].5 Code quality and documentation
  - Add docstrings to all public functions
  - Ensure code follows project style guide
  - Remove debug code and TODOs
  - Update README with new functionality

- [ ] [#].6 Performance and security review
  - Profile critical code paths
  - Review for security vulnerabilities
  - Validate input sanitization
  - Check for memory leaks or resource issues
```

## Task Tracking

### Status Indicators
- `[ ]` = Not started
- `[~]` = In progress (only one task should have this status)
- `[x]` = Complete and tested
- `[?]` = Blocked or needs clarification

### Progress Updates
```markdown
### Current Progress (Updated: 2024-08-29)
- [x] 1.0 Setup and Infrastructure (100%)
- [~] 2.0 Authentication System (60%)
  - [x] 2.1 User model created
  - [x] 2.2 Password hashing implemented
  - [~] 2.3 JWT token generation (in progress)
  - [ ] 2.4 Login/logout endpoints
- [ ] 3.0 Data Management (0%)
```

## Handoff to Execution

### Before Starting Development
1. Review task list for completeness and logic
2. Ensure all dependencies are clearly marked
3. Verify test tasks are included for each feature
4. Confirm file structure aligns with project ADR
5. Load task list into development environment

### Execution Protocol
```
Use @0xcc/instruct/007_process-task-list.md for systematic task execution:

- Work on one task at a time
- Mark progress in real-time
- Run tests after each completed task
- Commit completed tasks with descriptive messages
- Ask for guidance when blocked
```

## Task List Maintenance

### During Development
- Update task status as work progresses
- Add newly discovered tasks as they emerge
- Mark dependencies between tasks
- Note any changes in scope or requirements
- Track time estimates vs. actual time

### After Completion
- Mark all tasks as complete
- Document any deviations from original plan
- Note lessons learned for future task generation
- Archive completed task list with final status
- Update project documentation with new capabilities