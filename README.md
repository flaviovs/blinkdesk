# Blink Desk

A lightweight ticketing system using SQLite with no external dependencies (Python stdlib only).

## Features

- Create, update, and manage tickets
- State machine for ticket workflow
- Entity management (users/teams)
- Comments on tickets
- Audit logging
- Configuration options
- MCP (Model Context Protocol) server for integration with AI assistants

## Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

1. Initialize a database:
   ```bash
   bd -d mydb.db init config.toml
   ```

2. Create a ticket:
   ```bash
   bd -d mydb.db ticket create --title "My first ticket"
   ```

3. List tickets:
   ```bash
   bd -d mydb.db ticket list
   ```

## Configuration File

Create a TOML file to seed the database:

```toml
[[entities]]
slug = "alice"
name = "Alice"

[[entities]]
slug = "support"
name = "Support Team"

[[states]]
slug = "open"
name = "Open"

[[states]]
slug = "in_progress"
name = "In Progress"

[[states]]
slug = "closed"
name = "Closed"

[[transitions]]
from_state = "open"
to_state = "in_progress"

[[transitions]]
from_state = "in_progress"
to_state = "open"

[[transitions]]
from_state = "in_progress"
to_state = "closed"

[options]
display_prefix = "#"
lock_entities = false
```

## CLI Commands

### Ticket Operations

```bash
bd -d db.db ticket create --title "Issue" --description "Details"
bd -d db.db ticket list
bd -d db.db ticket get <id>
bd -d db.db ticket update <id> --title "New title"
bd -d db.db ticket comment <id> --entity alice --comment "Fixed"
```

### Database Operations

```bash
bd -d db.db db vacuum
bd -d db.db db backup backup.db
bd -d db.db init config.toml
```

### Configuration

```bash
bd -d db.db config get <key>
bd -d db.db config set <key> <value>
bd -d db.db config list

### MCP Operations

```bash
bd -d db.db mcp stdio
```
Start the MCP server for AI assistant integration via stdio.
```

## Environment Variables

- `BLINKDESK_DATABASE` - Path to the database file (alternative to `-d` flag)

## MCP Integration

Blink Desk provides an MCP server that allows AI assistants to interact with the ticketing system. The MCP server exposes tools for:

- Listing and searching tickets
- Creating new tickets
- Updating ticket state
- Adding comments
- Managing entities

To start the MCP server:

```bash
bd -d db.db mcp stdio
```

Add to your AI assistant configuration:

```json
{
  "mcpServers": {
    "blinkdesk": {
      "command": "bd",
      "args": ["-d", "/path/to/db.db", "mcp", "stdio"]
    }
  }
}
```

## Development

```bash
# Run tests
python -m unittest --buffer --failfast tests/test_blinkdesk.py

# Run linter
ruff check src/

# Run type checker
mypy src/
```

## License

MIT
