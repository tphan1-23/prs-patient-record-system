"""SQLite connection and schema. All SQL lives in the persistence package.

V2 changes:
* Weakness 1 - a trigger makes ``patients.patient_id`` immutable in the
  database itself, so even raw SQL cannot change a Patient ID.
* Weakness 5 - ``Database.transaction()`` groups several repository writes
  into one all-or-nothing unit of work.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    emergency_contact TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patient_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visit_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    visit_date TEXT NOT NULL,
    note_text TEXT NOT NULL,
    staff_user TEXT NOT NULL,
    entered_at TEXT NOT NULL,
    category TEXT,
    category_source TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS block_patient_id_update
BEFORE UPDATE OF patient_id ON patients
BEGIN
    SELECT RAISE(ABORT, 'Patient ID is immutable');
END;
"""


def now() -> str:
    """Current local time as an ISO string (seconds precision)."""
    return datetime.now().isoformat(timespec="seconds")


class Database:
    """Owns the SQLite connection, creates the tables and runs transactions."""

    def __init__(self, path: str = "prs.db") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._depth = 0  # > 0 while inside transaction()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run every write inside the ``with`` block as one unit.

        Commits once at the end if all writes succeed. If any write (or any
        other code in the block) raises, every write is rolled back and the
        error is re-raised. Nested calls join the outer transaction.
        """
        self._depth += 1
        try:
            yield self.conn
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self.conn.rollback()
            raise
        self._depth -= 1
        if self._depth == 0:
            self.conn.commit()

    def commit(self) -> None:
        """Commit a single write, unless it is part of a larger transaction.

        Repositories call this instead of ``conn.commit()`` so that their
        writes can be grouped by ``transaction()``.
        """
        if self._depth == 0:
            self.conn.commit()
