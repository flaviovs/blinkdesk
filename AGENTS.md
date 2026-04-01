# Blink Desk - Agent Guidelines

This is a lightweight ticketing system using SQLite with no external dependencies (Python stdlib only).

Uses Semantic Versioning 2.0.0.

## Project Structure

```
blinkdesk/
├── src/blinkdesk/          # Main package
│   ├── __init__.py         # Exports public API
│   ├── _db.py              # Database initialization & schema
│   ├── _types.py           # Type definitions for config dictionaries
│   ├── cli/                  # CLI module (subcommands)
│   │   ├── __init__.py       # CLI entry point & argument parsing
│   │   ├── ticket.py         # Ticket commands
│   │   ├── config.py         # Config commands
│   │   └── db.py             # Database commands
│   ├── comment.py            # Comment value object
│   ├── comment.py          # Comment value object
│   ├── entity.py           # Entity value object (users/teams)
│   ├── init.py             # Database initialization command
│   ├── state.py            # TicketState, TicketStateMachine
│   ├── system.py           # TicketingSystem (main entry point)
│   ├── ticket.py           # Ticket value object
│   └── ticket_log.py       # TicketLog, TicketLogAction
├── tests/                  # Unit tests (unittest)
└── pyproject.toml
```

## Database Schema

| Table | Purpose | Key |
|-------|---------|-----|
| entities | Users/teams (assignees) | entity_id (PK), slug (unique), name |
| ticket_states | Ticket states (open, closed, etc.) | state_id (PK), slug, name |
| state_transitions | Allowed state transitions | (from_state_id, to_state_id) PK |
| tickets | Main ticket table | ticket_id (PK), title, state_id FK, assignee_entity_id FK |
| ticket_logs | Audit log for ticket changes | (ticket_id, ticket_log_id) PK |
| comments | Ticket comments | (ticket_id, comment_id) PK |
| config | System configuration | key (PK), value |

Relationships: tickets → ticket_states, tickets → entities (assignee), ticket_logs → tickets, comments → tickets, comments → entities

## Architecture

### Key Classes
- **TicketingSystem**: Main entry point, coordinates all operations
- **Value Objects**: Ticket, Entity, TicketState, Comment, TicketLog (immutable, frozen dataclass)
- **TicketStateMachine**: Manages states and transitions

### Patterns
- Value objects use `from_row(cls, row)` to create from DB
- All DB queries use parameterized queries
- Composite PK tables use `WITHOUT ROWID` for storage optimization

## Build / Lint / Test Commands

```bash
# Install package with dev dependencies
pip install -e ".[dev]"

# Run all tests
python -m unittest --buffer --failfast tests/test_blinkdesk.py

# Run a single test
python -m unittest --buffer --failfast tests.test_blinkdesk.TestBlinkDesk.test_create_and_get_ticket -v

# Run linter (ruff)
ruff check src/

# Fix auto-fixable issues
ruff check src/ --fix

# Run type checker (mypy)
mypy src/
```

## Code Style Guidelines

### General

- **Python version**: 3.11+ (minimum 3.11)
- **No external dependencies**: Use only Python stdlib modules
- **Testing**: Use `unittest` (not pytest)

### Imports

- Use absolute imports: `from blinkdesk.system import TicketingSystem`
- Group imports in order: stdlib, third-party, local
- Do NOT use wildcard imports (`from x import *`)

### Formatting

PEP8

### Type Hints

- **Always** use type hints for function signatures and return types
- Use `sqlite3.Row` directly for DB rows (not `dict[str, object]`)
- Use `Literal` for string literals when appropriate
- Use `type: ignore[code]` or `cast()` only when necessary (avoid suppressing errors)

### Documentation

- Add docstrings to modules, classes, methods and functions
- Docstrings can be omitted from private objects or when usage is clear
- Use Google Standard docstrings
- **All user-facing changes must be documented in `CHANGELOG.md`**
- **Do not** edit old entries in `CHANGELOG.md`
- Document only high-level changes, not every commit detail
- Avoid entries that can be inferred from Git commit history

### Error Handling

- Raise descriptive `ValueError` for invalid operations

### Database Patterns

- Always use parameterized queries (no string formatting)
- Use `WITHOUT ROWID` for tables with composite PKs

### API Design

- `TicketingSystem` is the main entry point
