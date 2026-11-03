"""Read access to the audit log for the web interface.

V2 (Weakness 3): routes no longer call ``AuditRepository.recent()``
directly; they go through this service, which also enforces that only a
clinic manager may read the log.
"""
from ..persistence.audit_repository import AuditRepository
from .models import User
from .service import AuthService

AUDIT_PAGE_SIZE = 200


class AuditService:
    """Business rules for viewing the audit log."""

    def __init__(self, audit: AuditRepository) -> None:
        self._audit = audit

    def recent_entries(self, user: User,
                       limit: int = AUDIT_PAGE_SIZE) -> list:
        """Return the newest audit entries. Managers only."""
        AuthService.require_manager(user)  # raises AuthError for staff
        return self._audit.recent(limit)
