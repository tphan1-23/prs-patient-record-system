"""Patient storage (split out of V1 ``repositories.py``).

Takes and returns plain values (dicts / primitives), so the persistence
package still depends on no other PRS package.
"""
from typing import Optional

from .database import Database, now


class PatientRepository:
    """Reads and writes patients and their change history."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def insert(self, patient_id: str, name: str, dob: str, phone: str,
               address: str, emergency_contact: str) -> None:
        """Insert a patient. Raises sqlite3.IntegrityError on a duplicate ID."""
        self._conn.execute(
            "INSERT INTO patients VALUES (?,?,?,?,?,?,?)",
            (patient_id, name, dob, phone, address, emergency_contact,
             now()))
        self._db.commit()

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
        with self._db.transaction():  # rolls back everything on any error
            self._conn.execute(
                f"UPDATE patients SET {assignments} WHERE patient_id = ?",
                (*new_values.values(), patient_id))
            for field_name, old, new in changes:
                self._conn.execute(
                    "INSERT INTO patient_changes (patient_id, field_name, "
                    "old_value, new_value, changed_by, changed_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (patient_id, field_name, old, new, changed_by, now()))

    def change_history(self, patient_id: str) -> list:
        rows = self._conn.execute(
            "SELECT * FROM patient_changes WHERE patient_id = ? "
            "ORDER BY id DESC", (patient_id,)).fetchall()
        return [dict(r) for r in rows]
