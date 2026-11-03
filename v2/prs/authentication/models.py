"""Authentication domain objects (split out of V1 ``service.py``)."""
from dataclasses import dataclass

ROLES = ("staff", "manager")


class AuthError(Exception):
    """Raised for failed sign-in, expired session or missing permission."""


@dataclass(frozen=True)
class User:
    """A signed-in staff member."""

    username: str
    role: str

    @property
    def is_manager(self) -> bool:
        return self.role == "manager"
