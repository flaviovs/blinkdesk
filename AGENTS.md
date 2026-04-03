# BlinkDesk - Agent Guidelines

Lightweight ticketing system using SQLite with Python stdlib only. Follows Semantic Versioning 2.0.0.

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

## Essential Commands

```bash
# Run all tests
python -m unittest discover -s tests -p "test_*.py" --buffer --failfast

# Run linter
ruff check src/

# Run type checker
mypy src/
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
- No external dependencies
- Use unittest
- Run unittest/lint/type checks only when Python files (`*.py`) changed
- Always use type hints
- Use absolute imports
- Add Google Standard docstrings to public APIs
- All changes need unit tests
- Document user-facing changes in CHANGELOG.md
- When manually testing the `bd` CLI, use `$VIRTUAL_ENV/tmp` for temporary databases

## Version Handling
- Version is in `src/blinkdesk/__init__.py`
- Only bump version when explicitly requested
- Determine bump level according to changes since last version
- Use Semantic Versioning: patch for bug fixes, minor for new features
- **Never bump major version unless the user explicitly requests it**
- After bumping version, you must ensure that `CHANGELOG.md` is updated
- When releasing a version, keep the `## Unreleased` section for future changes

## Changelog Guidelines

- Sections must follow the order: `## Unreleased` first, then `## X.Y.Z` (released versions)
- Changes must always be added under an `## Unreleased` section
- One changeset = one line
- Focus on user-facing behavior, not implementation details
- Do not document what can be discovered by `git diff`
- Keep entries brief and meaningful

## Git Guidelines

- Do not use write commands (`git branch`, `git rebase`, etc.) unless explicitly permitted.
- Never run `git push`.
- Commit only when explicitly requested by the user.
- Keep commit titles under 50 characters.
- Add a body only if strictly necessary; when added, wrap text at 72 columns.
