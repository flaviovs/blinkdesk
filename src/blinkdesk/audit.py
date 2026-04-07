"""Audit logging helpers backed by SQLite."""

import logging
import sqlite3
from datetime import datetime, timezone

DEFAULT_AUDIT_PRUNE_KEEP_DAYS = 30


class SQLiteAuditLogHandler(logging.Handler):
    """Persist log lines to the audit_logs table."""

    def __init__(self, db_path: str) -> None:
        """Initialize the handler.

        Args:
            db_path: Path to the SQLite database file.
        """
        super().__init__(level=logging.INFO)
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)

    def emit(self, record: logging.LogRecord) -> None:
        """Write a log record to the audit log table."""
        try:
            line = self.format(record)
            now = datetime.now(timezone.utc).isoformat()
            with self._conn:
                self._conn.execute(
                    "INSERT INTO audit_logs (created_at, line) VALUES (?, ?)",
                    (now, line),
                )
        except Exception:
            return

    def close(self) -> None:
        """Close the internal SQLite connection."""
        self._conn.close()
        super().close()
