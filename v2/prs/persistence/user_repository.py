"""Staff account storage (split out of V1 ``repositories.py``)."""
from typing import Optional

from .database import Database


class UserRepository:
    """Reads and writes staff accounts."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def get(self, username: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

    def add(self, username: str, role: str, password_hash: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO users VALUES (?,?,?)",
            (username, role, password_hash))
        self._db.commit()
