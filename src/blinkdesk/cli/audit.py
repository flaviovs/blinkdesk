"""Audit command handlers."""

import argparse

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path


def cmd_audit_list(args: argparse.Namespace) -> None:
    """List audit log lines."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        logs = system.list_audit_logs()
        if not logs:
            print("No audit log entries found.")
            return
        for created_at, line in logs:
            print(f"{created_at} {line}")
    finally:
        system.close()


def cmd_audit_prune(args: argparse.Namespace) -> None:
    """Prune audit log lines older than the retention period."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        removed = system.prune_audit_logs()
        print(f"Pruned {removed} audit log entr{'y' if removed == 1 else 'ies'}.")
    finally:
        system.close()
