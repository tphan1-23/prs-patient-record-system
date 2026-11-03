"""Visit note domain objects.

V2 (Weakness 2): ``VisitNote`` validates its own date, text and category in
``__post_init__`` instead of ``VisitService`` doing it, and
``with_category()`` returns the categorised note (used for Weakness 4).
"""
from dataclasses import dataclass, replace
from datetime import date
from typing import Mapping, Optional

from ..ai_integration.suggester import CATEGORIES

MAX_NOTE_LENGTH = 2000
CATEGORY_SOURCES = ("ai-suggested", "staff-chosen")


class VisitError(Exception):
    """Raised for invalid note or category input."""


@dataclass(frozen=True)
class VisitNote:
    """One visit note. ``category`` is None while Uncategorized.

    ``note_id`` and ``entered_at`` are None/empty until the note is saved.
    """

    patient_id: str
    visit_date: str
    note_text: str
    staff_user: str
    note_id: Optional[int] = None
    entered_at: str = ""
    category: Optional[str] = None
    category_source: Optional[str] = None

    def __post_init__(self) -> None:
        try:
            visit = date.fromisoformat(self.visit_date)
        except (TypeError, ValueError):
            raise VisitError("Visit date must be YYYY-MM-DD.")
        if visit > date.today():
            raise VisitError("Visit date cannot be in the future.")
        if not self.note_text or not self.note_text.strip():
            raise VisitError("Note text cannot be blank.")
        if len(self.note_text) > MAX_NOTE_LENGTH:
            raise VisitError(
                f"Note text cannot exceed {MAX_NOTE_LENGTH} characters.")
        if self.category is not None:
            if self.category not in CATEGORIES:
                raise VisitError(f"Invalid category '{self.category}'.")
            if self.category_source not in CATEGORY_SOURCES:
                raise VisitError("The category source must be recorded.")
        object.__setattr__(self, "visit_date", visit.isoformat())
        object.__setattr__(self, "note_text", self.note_text.strip())

    @property
    def category_label(self) -> str:
        return self.category or "Uncategorized"

    def with_category(self, category: str, source: str) -> "VisitNote":
        """Return a copy of this note with the category set (validated)."""
        return replace(self, category=category, category_source=source)

    @classmethod
    def from_row(cls, row: Mapping) -> "VisitNote":
        """Build a VisitNote from a database row."""
        return cls(**row)
