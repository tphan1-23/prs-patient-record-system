"""Visit note storage (split out of V1 ``repositories.py``)."""
from typing import Optional

from .database import Database, now


class VisitRepository:
    """Reads and writes visit notes."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def insert(self, patient_id: str, visit_date: str, note_text: str,
               staff_user: str) -> int:
        """Insert an uncategorized note and return its id.

        Joins the caller's ``Database.transaction()`` if one is open.
        """
        cursor = self._conn.execute(
            "INSERT INTO visit_notes (patient_id, visit_date, note_text, "
            "staff_user, entered_at) VALUES (?,?,?,?,?)",
            (patient_id, visit_date, note_text, staff_user, now()))
        self._db.commit()
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
        self._db.commit()

    def for_patient(self, patient_id: str) -> list:
        """Notes of one patient, newest visit date first."""
        rows = self._conn.execute(
            "SELECT * FROM visit_notes WHERE patient_id = ? "
            "ORDER BY visit_date DESC, note_id DESC",
            (patient_id,)).fetchall()
        return [dict(r) for r in rows]
