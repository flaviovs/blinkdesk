# BlinkDesk - Agent Guidelines

Lightweight ticketing system using SQLite. Core runtime and MCP integrations use Python stdlib only; only development dependencies may use optional extras defined in `pyproject.toml`. Follows Semantic Versioning 2.0.0.

## Essential Project Structure

```
blinkdesk/
├── src/blinkdesk/
│   ├── system.py           # TicketingSystem (main entry point)
│   ├── _db.py              # Database schema & initialization
│   ├── cli/main.py         # Main `bd` CLI script entry point
│   └── [other modules]     # Value objects: ticket.py, entity.py, etc.
├── tests/                  # Unit tests split by concern
│   ├── _base.py            # Shared test fixture/helpers
│   ├── test_system_core.py # TicketingSystem behavior
│   ├── test_cli_*.py       # CLI command coverage
│   ├── test_mcp.py         # MCP adapter tests
│   └── test_*.py           # Additional focused suites
└── pyproject.toml          # Build configuration
```

## Key Classes & Patterns

- **TicketingSystem**: Main API entry point
- **Value Objects**: Ticket, Entity, TicketState, Comment, TicketLog (immutable)
- Use `from_row(cls, row)` to create objects from DB
- Always use parameterized queries
- Composite PK tables use `WITHOUT ROWID`

## Database Schema

| Table | Purpose | Key |
|-------|---------|-----|
| entities | Users/teams | entity_id (PK), slug (unique) |
| ticket_states | Ticket states | state_id (PK), slug |
| tickets | Main ticket table | ticket_id (PK), title, state_id FK |
| comments | Ticket comments | (ticket_id, comment_id) PK |
| config | System configuration | key (PK) |

## Versioning

- Database schema version must not be bumped when schema changes are part of the
  current unreleased work

## Essential Commands

```bash
# Run all tests
python -m unittest discover --start-directory=tests --pattern="test_*.py" --buffer --failfast

# Run a focused test module
python -m unittest tests.test_cli_ticket --buffer --failfast

# Run linter
python -m ruff check src/

# Run type checker
python -m mypy src/

# Run dead code analysis
python -m vulture src/ tests/
```

## CLI Usage

Main command is `bd`:

```bash
# Initialize database
bd -d mydb.db init schema.toml

# Create ticket
bd -d mydb.db ticket create --title "Issue"

# List tickets
bd -d mydb.db ticket list

# Run MCP server
bd -d mydb.db mcp stdio
```

## Code Requirements

- Python 3.11+
- Core runtime has no external dependencies
- Use unittest
- Run unittest/lint/type/dead-code checks only when Python files (`*.py`) changed
- Keep Python `import` and `from ... import` statements at module top-level unless strictly necessary
- Always use type hints
- Use absolute imports
- Add Google Standard docstrings to public APIs
- Add or update unit tests for behavior changes
- Document user-facing changes in CHANGELOG.md
- When manually testing the `bd` CLI, use `$VIRTUAL_ENV/tmp` for temporary databases

## Definition of Done

- Behavior changes have corresponding unit test additions or updates
- When Python files changed, run `unittest`, `ruff`, `mypy`, and `vulture` checks and fix reported issues
- CLI behavior changes are manually smoke-tested using a temporary DB under `$VIRTUAL_ENV/tmp`
- User-facing behavior changes are documented in `CHANGELOG.md`
- `README.md` is updated when user-facing commands, flags, or workflows change
- Runtime dependency boundary is preserved (stdlib-only under `src/blinkdesk/`)
- Changes are scoped to the request; avoid unrelated edits

## Version Handling
- Version is in `src/blinkdesk/__init__.py`
- Only bump version when explicitly requested
- Determine bump level according to changes since last version
- Use Semantic Versioning: patch for bug fixes, minor for new features
- **Never bump major version unless the user explicitly requests it**
- After bumping version, you must ensure that `CHANGELOG.md` is updated

## Changelog Guidelines

- Sections must always be in release order after "Unreleased". Example:
  ```
  ## [Unreleased]

  ### {Added/Changed/Etc.}

  - ...

  ## [0.4.0] - 2026-04-02

  ...

  ## [0.3.0] - 2026-04-02

  ...
  ```
- "Unreleased" section must always come first
- You must add sub-sections (`### Fixed`, `### Added`, etc.) to "Unreleased"
- One changeset = one line
- Focus on user-facing behavior, not implementation details
- Do not document what can be discovered by `git diff`
- Keep entries brief and meaningful

## Git Guidelines

- Do not run destructive history-rewrite commands (for example, `git reset --hard`, `git rebase`) unless explicitly permitted.
- Avoid creating or switching branches unless explicitly requested.
- Never run `git push`.
- Commit only when explicitly requested by the user.
- Before committing, ensure `README.md` includes user-visible changes.
- Before committing, ensure documentation matches current code behavior; code
  is the source of truth.
- Keep commit titles under 50 characters.
- Add a body only if strictly necessary; when added, wrap text at 72 columns.
