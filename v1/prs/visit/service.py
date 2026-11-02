"""Visit notes and category review.

This is the only package that uses ai_integration, and it uses the patient
package to confirm that a patient exists.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..ai_integration.suggester import (CATEGORIES, ICategorySuggester,
                                        Suggestion)
from ..patient.service import PatientService
from ..persistence.repositories import AuditRepository, VisitRepository

MAX_NOTE_LENGTH = 2000
CATEGORY_SOURCES = ("ai-suggested", "staff-chosen")


class VisitError(Exception):
    """Raised for invalid note or category input."""


@dataclass
class VisitNote:
    """One visit note. ``category`` is None while Uncategorized."""

    note_id: int
    patient_id: str
    visit_date: str
    note_text: str
    staff_user: str
    entered_at: str
    category: Optional[str] = None
    category_source: Optional[str] = None

    @property
    def category_label(self) -> str:
        return self.category or "Uncategorized"


class VisitService:
    """Business rules for visit notes."""

    def __init__(self, visits: VisitRepository, patients: PatientService,
                 suggester: ICategorySuggester,
                 audit: AuditRepository) -> None:
        self._visits = visits
        self._patients = patients
        self._suggester = suggester
        self._audit = audit

    @staticmethod
    def _to_note(row: dict) -> VisitNote:
        return VisitNote(**row)

    def add_note(self, patient_id: str, visit_date: str, text: str,
                 actor: str) -> VisitNote:
        """Validate and save a note with no category."""
        self._patients.get(patient_id)  # raises if the patient is unknown
        try:
            visit = date.fromisoformat(visit_date)
        except ValueError:
            raise VisitError("Visit date must be YYYY-MM-DD.")
        if visit > date.today():
            raise VisitError("Visit date cannot be in the future.")
        if not text or not text.strip():
            raise VisitError("Note text cannot be blank.")
        if len(text) > MAX_NOTE_LENGTH:
            raise VisitError(
                f"Note text cannot exceed {MAX_NOTE_LENGTH} characters.")
        note_id = self._visits.insert(
            patient_id, visit.isoformat(), text.strip(), actor)
        self._audit.log(actor, "ADD_NOTE", f"{patient_id} note {note_id}")
        return self.get_note(note_id)

    def get_note(self, note_id: int) -> VisitNote:
        row = self._visits.get(note_id)
        if row is None:
            raise VisitError(f"No visit note {note_id}.")
        return self._to_note(row)

    def suggest_category(self, note_id: int) -> Optional[Suggestion]:
        """Ask the suggester using ONLY the note text. None = unavailable."""
        note = self.get_note(note_id)
        try:
            return self._suggester.suggest(note.note_text)
        except Exception:
            return None

    def set_category(self, note_id: int, category: str, source: str,
                     actor: str) -> VisitNote:
        """Store a category that staff accepted or chose."""
        note = self.get_note(note_id)
        if category not in CATEGORIES:
            raise VisitError(f"Invalid category '{category}'.")
        if source not in CATEGORY_SOURCES:
            raise VisitError("The category source must be recorded.")
        self._visits.set_category(note_id, category, source)
        self._audit.log(actor, "SET_CATEGORY",
                        f"{note.patient_id} note {note_id}: "
                        f"{category} ({source})")
        return self.get_note(note_id)

    def history(self, patient_id: str) -> list:
        """All notes of one patient, newest visit date first."""
        self._patients.get(patient_id)
        return [self._to_note(r) for r in self._visits.for_patient(patient_id)]
