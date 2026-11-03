"""Visit notes and category review.

This is the only package that uses ai_integration. It checks that a patient
exists through the ``PatientLookup`` interface, not the concrete
``PatientService`` (V2, Weakness 3).
"""
from typing import Optional

from ..ai_integration.suggester import ICategorySuggester, Suggestion
from ..patient.interfaces import PatientLookup
from ..persistence.audit_repository import AuditRepository
from ..persistence.database import Database
from ..persistence.visit_repository import VisitRepository
from .models import VisitError, VisitNote


class VisitService:
    """Business rules for visit notes."""

    def __init__(self, visits: VisitRepository, patients: PatientLookup,
                 suggester: ICategorySuggester, audit: AuditRepository,
                 db: Database) -> None:
        self._visits = visits
        self._patients = patients
        self._suggester = suggester
        self._audit = audit
        self._db = db

    def _require_patient(self, patient_id: str) -> None:
        if not self._patients.exists(patient_id):
            raise VisitError(f"No patient found for ID: {patient_id}")

    def add_note(self, patient_id: str, visit_date: str, text: str,
                 actor: str) -> VisitNote:
        """Validate and save a note with no category.

        The note and its audit entry are written in ONE transaction
        (Weakness 5): if either write fails, neither is saved.
        """
        self._require_patient(patient_id)
        note = VisitNote(patient_id=patient_id, visit_date=visit_date,
                         note_text=text, staff_user=actor)  # validates
        with self._db.transaction():
            note_id = self._visits.insert(
                note.patient_id, note.visit_date, note.note_text, actor)
            self._audit.log(actor, "ADD_NOTE", f"{patient_id} note {note_id}")
        return self.get_note(note_id)

    def get_note(self, note_id: int) -> VisitNote:
        row = self._visits.get(note_id)
        if row is None:
            raise VisitError(f"No visit note {note_id}.")
        return VisitNote.from_row(row)

    def suggest_category(self, note_id: int) -> Optional[Suggestion]:
        """Ask the suggester using ONLY the note text. None = unavailable."""
        note = self.get_note(note_id)
        try:
            return self._suggester.suggest(note.note_text)
        except Exception:
            return None

    def set_category(self, note_id: int, category: str, source: str,
                     actor: str) -> VisitNote:
        """Store a category that staff accepted or chose.

        Reads the note once and returns the updated note directly, without
        reading it from the database again (Weakness 4).
        """
        note = self.get_note(note_id)
        updated = note.with_category(category, source)  # validates
        self._visits.set_category(note_id, updated.category,
                                  updated.category_source)
        self._audit.log(actor, "SET_CATEGORY",
                        f"{note.patient_id} note {note_id}: "
                        f"{category} ({source})")
        return updated

    def history(self, patient_id: str) -> list:
        """All notes of one patient, newest visit date first."""
        self._require_patient(patient_id)
        return [VisitNote.from_row(r)
                for r in self._visits.for_patient(patient_id)]
