"""Audit log storage (split out of V1 ``repositories.py``)."""
from .database import Database, now


class AuditRepository:
    """Append-only log of who did what and when."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def log(self, username: str, action: str, detail: str) -> None:
        """Write one entry. Joins the caller's transaction if one is open."""
        self._conn.execute(
            "INSERT INTO audit_log (ts, username, action, detail) "
            "VALUES (?,?,?,?)", (now(), username, action, detail))
        self._db.commit()

    def recent(self, limit: int = 200) -> list:
        rows = self._conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
