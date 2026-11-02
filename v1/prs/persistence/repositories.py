"""Repositories: the only code that runs SQL.

Repositories take and return plain values (dicts / primitives), so the
persistence package depends on no other PRS package.
"""
import sqlite3
from datetime import datetime
from typing import Optional

from .database import Database


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class UserRepository:
    """Reads and writes staff accounts."""

    def __init__(self, db: Database) -> None:
        self._conn = db.conn

    def get(self, username: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

    def add(self, username: str, role: str, password_hash: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO users VALUES (?,?,?)",
            (username, role, password_hash))
        self._conn.commit()


class PatientRepository:
    """Reads and writes patients and their change history."""

    def __init__(self, db: Database) -> None:
        self._conn = db.conn

    def insert(self, patient_id: str, name: str, dob: str, phone: str,
               address: str, emergency_contact: str) -> None:
        """Insert a patient. Raises sqlite3.IntegrityError on a duplicate ID."""
        self._conn.execute(
            "INSERT INTO patients VALUES (?,?,?,?,?,?,?)",
            (patient_id, name, dob, phone, address, emergency_contact,
             _now()))
        self._conn.commit()

    def get(self, patient_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM patients WHERE patient_id = ?",
            (patient_id,)).fetchone()
        return dict(row) if row else None

    def count(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM patients").fetchone()[0]

    def update_with_history(self, patient_id: str, new_values: dict,
                            changes: list, changed_by: str) -> None:
        """Apply the new column values and store each change, atomically.

        ``changes`` is a list of (field_name, old_value, new_value).
        """
        assignments = ", ".join(f"{column} = ?" for column in new_values)
        try:
            self._conn.execute(
                f"UPDATE patients SET {assignments} WHERE patient_id = ?",
                (*new_values.values(), patient_id))
            for field_name, old, new in changes:
                self._conn.execute(
                    "INSERT INTO patient_changes (patient_id, field_name, "
                    "old_value, new_value, changed_by, changed_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (patient_id, field_name, old, new, changed_by, _now()))
            self._conn.commit()
        except sqlite3.Error:
            self._conn.rollback()
            raise

    def change_history(self, patient_id: str) -> list:
        rows = self._conn.execute(
            "SELECT * FROM patient_changes WHERE patient_id = ? "
            "ORDER BY id DESC", (patient_id,)).fetchall()
        return [dict(r) for r in rows]


class VisitRepository:
    """Reads and writes visit notes."""

    def __init__(self, db: Database) -> None:
        self._conn = db.conn

    def insert(self, patient_id: str, visit_date: str, note_text: str,
               staff_user: str) -> int:
        """Insert an uncategorized note and return its id."""
        cursor = self._conn.execute(
            "INSERT INTO visit_notes (patient_id, visit_date, note_text, "
            "staff_user, entered_at) VALUES (?,?,?,?,?)",
            (patient_id, visit_date, note_text, staff_user, _now()))
        self._conn.commit()
        return cursor.lastrowid

    def get(self, note_id: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM visit_notes WHERE note_id = ?",
            (note_id,)).fetchone()
        return dict(row) if row else None

    def set_category(self, note_id: int, category: Optional[str],
                     source: Optional[str]) -> None:
        self._conn.execute(
            "UPDATE visit_notes SET category = ?, category_source = ? "
            "WHERE note_id = ?", (category, source, note_id))
        self._conn.commit()

    def for_patient(self, patient_id: str) -> list:
        """Notes of one patient, newest visit date first."""
        rows = self._conn.execute(
            "SELECT * FROM visit_notes WHERE patient_id = ? "
            "ORDER BY visit_date DESC, note_id DESC",
            (patient_id,)).fetchall()
        return [dict(r) for r in rows]


class AuditRepository:
    """Append-only log of who did what and when."""

    def __init__(self, db: Database) -> None:
        self._conn = db.conn

    def log(self, username: str, action: str, detail: str) -> None:
        self._conn.execute(
            "INSERT INTO audit_log (ts, username, action, detail) "
            "VALUES (?,?,?,?)", (_now(), username, action, detail))
        self._conn.commit()

    def recent(self, limit: int = 200) -> list:
        rows = self._conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
