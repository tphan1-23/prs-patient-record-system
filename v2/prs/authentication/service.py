"""Sign-in, roles and the 15 minute inactivity timeout."""
import hashlib
import hmac
import os
import secrets
import threading
import time
from typing import Optional

from ..persistence.user_repository import UserRepository
from .models import ROLES, AuthError, User

SESSION_TIMEOUT_SECONDS = 15 * 60


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Return 'salt$hash' using PBKDF2-SHA256."""
    salt = salt or os.urandom(8).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt = stored.split("$", 1)[0]
    return hmac.compare_digest(stored, hash_password(password, salt))


class AuthService:
    """Authenticates users and tracks their sessions in memory."""

    def __init__(self, users: UserRepository,
                 timeout: int = SESSION_TIMEOUT_SECONDS) -> None:
        self._users = users
        self._timeout = timeout
        self._sessions = {}  # token -> [User, last_activity]
        self._lock = threading.Lock()

    def create_user(self, username: str, role: str, password: str) -> None:
        """Add an account (used for the demo users)."""
        if role not in ROLES:
            raise AuthError(f"Unknown role '{role}'.")
        self._users.add(username, role, hash_password(password))

    def login(self, username: str, password: str) -> str:
        """Check credentials and return a new session token."""
        record = self._users.get(username)
        if record is None or not verify_password(
                password, record["password_hash"]):
            raise AuthError("Invalid username or password.")
        token = secrets.token_hex(16)
        with self._lock:
            self._sessions[token] = [
                User(record["username"], record["role"]), time.time()]
        return token

    def logout(self, token: Optional[str]) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def validate(self, token: Optional[str]) -> User:
        """Return the session's user and refresh its activity time.

        Raises AuthError if there is no session or it has been inactive
        for more than 15 minutes.
        """
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                raise AuthError("Please sign in.")
            user, last_activity = session
            if time.time() - last_activity > self._timeout:
                del self._sessions[token]
                raise AuthError(
                    "You were signed out after 15 minutes of inactivity.")
            session[1] = time.time()
            return user

    @staticmethod
    def require_manager(user: User) -> None:
        if not user.is_manager:
            raise AuthError("Only a clinic manager can do that.")
