# Blink Desk - Agent Guidelines

Lightweight ticketing system using SQLite with Python stdlib only. Follows Semantic Versioning 2.0.0.

## Essential Project Structure

```
blinkdesk/
├── src/blinkdesk/
│   ├── system.py           # TicketingSystem (main entry point)
│   ├── _db.py              # Database schema & initialization
│   ├── cli/main.py         # Main CLI entry point
│   └── [other modules]     # Value objects: ticket.py, entity.py, etc.
├── tests/                  # Unit tests (unittest)
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
python -m unittest --buffer --failfast tests/test_blinkdesk.py

# Run linter
ruff check src/

# Run type checker
mypy src/
```

## CLI Usage

Main command is `bd`:

```bash
# Initialize database
bd -d mydb.db init config.toml

# Create ticket
bd -d mydb.db ticket create --title "Issue"

# List tickets
bd -d mydb.db ticket list

# Run MCP server
bd -d mydb.db mcp stdio
```

For testing, create databases in `$VIRTUAL_ENV/tmp` to avoid cluttering the working directory:

```bash
# Create test database for testing
bd -d $VIRTUAL_ENV/tmp/test.db init config.toml

# Run tests with the test database
bd -d $VIRTUAL_ENV/tmp/test.db ticket create --title "Test ticket"
```

## Code Requirements

- Python 3.11+
- No external dependencies
- Use unittest
- Always use type hints
- Use absolute imports
- Add Google Standard docstrings to public APIs
- All changes need unit tests
- Document user-facing changes in CHANGELOG.md
