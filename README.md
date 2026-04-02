Blink Desk
==========

A lightweight ticketing system for agent orchestration, developers, and command-line workflows. Uses SQLite with Python stdlib only.

---

Quick Start
==========

Python Library
--------------

```bash
pip install blinkdesk
```

```python
from blinkdesk import TicketingSystem

system = TicketingSystem("tickets.db")
system.init_database()

ticket = system.create_ticket(
    title="Initial setup complete",
    description="Database initialized and ready for use"
)
print(f"Created ticket #{ticket.id}: {ticket.title}")
```

MCP Server
----------

```bash
pip install blinkdesk[mcp]
bd -d tickets.db init
bd -d tickets.db mcp stdio
```

Add to your agent config:

```json
{
  "mcpServers": {
    "blinkdesk": {
      "command": "bd",
      "args": ["-d", "/path/to/tickets.db", "mcp", "stdio"]
    }
  }
}
```

HTTP and SSE transports also supported.

CLI
---

```bash
bd -d tickets.db ticket create --title "Test"
bd -d tickets.db ticket list
```

---

Core Concepts
============

**Tickets** track issues, TODO items, bugs, anything - they represent work that needs to be tracked. Each ticket has a title, optional description, a current state, and optionally an assignee.

**Entities** are the people, teams, or agents who can own tickets. Think of them as your users or groups. Each entity has a slug (like "alice" or "support-team") and a display name.

**States** are the stages tickets can be in - like TODO, IN_PROGRESS, and DONE. You define these in your schema file, so the workflow matches how your team actually works.

**Comments** let you add discussion to a ticket. Useful for context, updates, or just keeping a record of decisions.

**Audit Log** records every change - who did what and when. Great for accountability and debugging.

---

Features
========

- **Zero dependencies** - Pure Python with SQLite
- **MCP server** - Full AI assistant integration
- **Python API** - Clean, typed interface
- **CLI interface** - Scriptable command-line tools
- **Audit logging** - Complete change history
- **State machine** - Configurable workflows
- **Entity management** - Users and teams

---

Installation
===========

```bash
# Core library
pip install blinkdesk

# With MCP support
pip install blinkdesk[mcp]

# Development
pip install -e ".[dev]"
```

---

Python API
==========

Blink Desk provides a clear API for Python applications to access the ticketing system.

TicketingSystem
---------------

The main entry point. Open a database and you're ready to go:

```python
from blinkdesk import TicketingSystem

system = TicketingSystem("tickets.db")
system.init_database()  # Creates tables if they don't exist
```

Always close the system when done:

```python
system.close()
# Or use context manager
with TicketingSystem("tickets.db") as system:
    # work with system
```

Working with Tickets
--------------------

Create, read, update - the usual CRUD operations:

```python
# Create
ticket = system.create_ticket("Fix the login bug")

# Read
ticket = system.get_ticket(42)
all_tickets = system.list_tickets()

# Update title/description
updated = system.update_ticket(ticket, title="Fixed the login bug")

# Change state
state = system.get_state_by_slug("closed")
transitioned = system.transition_ticket(ticket, state)

# Assign
entity = system.get_entity_by_slug("alice")
assigned = system.assign_ticket(ticket, entity)

# Add a comment
commented = system.add_comment(ticket, entity, "This is now fixed")
```

Entities and States
-------------------

Entities are users or teams. States are your workflow stages:

```python
# Create an entity
entity = system.create_entity("alice", "Alice Developer")

# Get states from the state machine
sm = system.get_state_machine()
open_state = sm.get_state_by_slug("open")
```

What Else?
----------

- `get_comments(ticket)` - Get all comments on a ticket
- `get_ticket_log(ticket)` - Full audit trail of changes
- `get_config(key)` / `set_config(key, value)` - System configuration
- `list_entities()` - All users/teams

That's the basics. Check the code if you need more detail.

---

MCP Integration
===============

Blink Desk's MCP server lets you connect AI assistant with the ticketing directly.

Setup
-----

Create a minimal schema file to define your states and entities:

```bash
cat > schema.toml << 'EOF'
[[entities]]
slug = "ai"
name = "AI Assistant"

[[entities]]
slug = "alice"
name = "Alice"

[[states]]
slug = "open"
name = "Open"

[[states]]
slug = "in_progress"
name = "In Progress"

[[states]]
slug = "closed"
name = "Closed"

# Who can move to what
[[transitions]]
from_state = "open"
to_state = "in_progress"

[[transitions]]
from_state = "in_progress"
to_state = "closed"
EOF

bd -d tickets.db init schema.toml
```

Then start the server:

```bash
bd -d tickets.db mcp stdio
```

Agent Configuration
-------------------

Add this to your agent's MCP settings:

```json
{
  "mcpServers": {
    "blinkdesk": {
      "command": "bd",
      "args": ["-d", "/path/to/tickets.db", "mcp", "stdio"]
    }
  }
}
```

Works with any MCP-compatible agent.

What Your Agent Can Do
----------------------

| Tool | What it does |
|------|--------------|
| `ticket_list` | List tickets, optionally filter by state or assignee |
| `ticket_get` | Get a specific ticket by ID |
| `ticket_create` | Create a new ticket |
| `ticket_update` | Update title, description, state, or assignee |
| `ticket_comment_add` | Add a comment to a ticket |
| `entity_list` | List all entities (users/teams) |
| `entity_get` | Look up an entity by slug |

Example Conversations
---------------------

**Creating a ticket:**
> "Can you create a ticket for the login bug?"
> ```python
> ticket_create(title="Login bug", description="Users can't log in after the latest update")
> ```

**Updating state:**
> "Move ticket #42 to in_progress"
> ```python
> ticket_update(ticket_id=42, state="in_progress")
> ```

**Adding context:**
> "Comment on ticket #42 that I'm looking into it"
> ```python
> ticket_comment_add(ticket_id=42, entity="alice", comment="Investigating this now")
> ```

The server exposes these as proper MCP tools - your agent can discover and use them naturally.

---

CLI Reference
=============

Blink Desk provides the `bd` command. Use `-d` to specify your database, or set `BLINKDESK_DATABASE`.

Basics
------

```bash
bd -d tickets.db init schema.toml    # Initialize with schema
bd -d tickets.db ticket create --title "Bug fix"
bd -d tickets.db ticket list         # List tickets
bd -d tickets.db ticket get 42       # View ticket details
```

Run `bd --help` or `bd <command> --help` for all available options.

Database Maintenance
--------------------

Blink Desk supports SQLite auto-vacuum configuration through the CLI:

```bash
# Read current auto-vacuum mode
bd -d tickets.db db get vacuum_mode

# Set mode (none, full, incremental)
bd -d tickets.db db set vacuum_mode incremental

# Read current journal mode
bd -d tickets.db db get journal_mode

# Set journal mode (delete, truncate, persist, memory, wal, off)
bd -d tickets.db db set journal_mode wal
```

Notes:

- New databases created with `bd init` default to `auto_vacuum = incremental`.
- This default is applied only when creating a fresh database file; existing databases are not changed.
- On `TicketingSystem.close()`, Blink Desk runs `PRAGMA main.incremental_vacuum` with 1% probability.

---

Schema Definition
=================

Blink Desk uses TOML files to set up your database with the states, entities, and workflow rules you want.

You define your states and entities once at setup time. This keeps the database schema simple and lets you model whatever workflow you need - simple bug tracking, full Kanban, support tickets, personal tasks.

See [example.schema.toml](./example.schema.toml) for a complete working example with full documentation of each section.

Using a Schema File
-------------------

```bash
bd -d tickets.db init schema.toml
```

This creates the database and seeds it with your entities, states, and transitions.

---

Environment Variables
=====================

- `BLINKDESK_DATABASE` - Path to database file (alternative to `-d` flag)

---

Development
===========

```bash
# Run tests
python -m unittest --buffer --failfast tests/test_blinkdesk.py

# Run linter
ruff check src/

# Run type checker
mypy src/
```

---

License
=======

MIT
