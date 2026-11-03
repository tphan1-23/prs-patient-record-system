"""Patient registration, lookup and updates.

V2: field validation now lives in ``Patient`` (models.py), updates take a
``PatientUpdateSpec``, and the service implements ``PatientLookup``.
"""
import sqlite3
import uuid
from typing import Optional

from ..persistence.audit_repository import AuditRepository
from ..persistence.patient_repository import PatientRepository
from .interfaces import PatientLookup
from .models import Patient, PatientError, PatientUpdateSpec


class PatientService(PatientLookup):
    """Business rules for patients."""

    def __init__(self, patients: PatientRepository,
                 audit: AuditRepository) -> None:
        self._patients = patients
        self._audit = audit

    def register(self, name: str, dob: str, phone: str, address: str,
                 emergency_contact: str, actor: str) -> Patient:
        """Create a patient with a system-generated, unique Patient ID."""
        # The constructor validates name and date of birth.
        new = Patient(name=name, date_of_birth=dob, phone=phone,
                      address=address, emergency_contact=emergency_contact)
        for _ in range(5):
            patient_id = "PRS-" + uuid.uuid4().hex[:8].upper()
            try:
                self._patients.insert(
                    patient_id, new.name, new.date_of_birth, new.phone,
                    new.address, new.emergency_contact)
            except sqlite3.IntegrityError:
                continue  # ID collision: draw another one
            self._audit.log(actor, "CREATE_PATIENT", patient_id)
            return self.get(patient_id)
        raise PatientError("Could not generate a unique Patient ID.")

    def find(self, patient_id: str) -> Optional[Patient]:
        """Return the patient, or None if the ID does not exist."""
        row = self._patients.get(patient_id.strip())
        return Patient.from_row(row) if row else None

    def exists(self, patient_id: str) -> bool:
        """PatientLookup: True if the patient is registered."""
        return self.find(patient_id) is not None

    def get(self, patient_id: str) -> Patient:
        """Return the patient or raise PatientError."""
        patient = self.find(patient_id)
        if patient is None:
            raise PatientError(f"No patient found for ID: {patient_id}")
        return patient

    def update(self, patient_id: str, spec: PatientUpdateSpec,
               actor: str) -> Patient:
        """Change permitted fields and record each change in the history."""
        if not isinstance(spec, PatientUpdateSpec):
            raise PatientError(
                "Updates must be given as a PatientUpdateSpec; "
                "the Patient ID can never be changed.")
        patient = self.get(patient_id)
        updated = spec.apply_to(patient)  # validates the new values
        new_values, history = {}, []
        for field_name in PatientUpdateSpec.field_names():
            old, value = getattr(patient, field_name), getattr(updated,
                                                               field_name)
            if value != old:
                new_values[field_name] = value
                history.append((field_name, old, value))
        if history:
            self._patients.update_with_history(
                patient_id, new_values, history, actor)
            self._audit.log(actor, "UPDATE_PATIENT",
                            f"{patient_id}: {', '.join(new_values)}")
        return self.get(patient_id)

    def count(self) -> int:
        """Number of registered patients."""
        return self._patients.count()

    def change_history(self, patient_id: str) -> list:
        return self._patients.change_history(patient_id)
