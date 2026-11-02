"""Patient registration, lookup and updates."""
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..persistence.repositories import AuditRepository, PatientRepository


class PatientError(Exception):
    """Raised for invalid patient input or an unknown patient."""


@dataclass
class Patient:
    """A patient record. The Patient ID is exposed read-only."""

    name: str
    date_of_birth: str
    phone: str = ""
    address: str = ""
    emergency_contact: str = ""
    _patient_id: str = ""
    created_at: str = ""

    @property
    def patient_id(self) -> str:
        return self._patient_id


class PatientService:
    """Business rules for patients."""

    UPDATABLE = ("name", "date_of_birth", "phone", "address",
                 "emergency_contact")

    def __init__(self, patients: PatientRepository,
                 audit: AuditRepository) -> None:
        self._patients = patients
        self._audit = audit

    @staticmethod
    def _to_patient(row: dict) -> Patient:
        return Patient(
            name=row["name"], date_of_birth=row["date_of_birth"],
            phone=row["phone"], address=row["address"],
            emergency_contact=row["emergency_contact"],
            _patient_id=row["patient_id"], created_at=row["created_at"])

    @staticmethod
    def _check_dob(value: str) -> str:
        try:
            dob = date.fromisoformat(value)
        except ValueError:
            raise PatientError("Date of birth must be YYYY-MM-DD.")
        if dob > date.today():
            raise PatientError("Date of birth cannot be in the future.")
        return dob.isoformat()

    def register(self, name: str, dob: str, phone: str, address: str,
                 emergency_contact: str, actor: str) -> Patient:
        """Create a patient with a system-generated, unique Patient ID."""
        if not name or not name.strip():
            raise PatientError("Patient name cannot be blank.")
        dob = self._check_dob(dob)
        for _ in range(5):
            patient_id = "PRS-" + uuid.uuid4().hex[:8].upper()
            try:
                self._patients.insert(
                    patient_id, name.strip(), dob, phone.strip(),
                    address.strip(), emergency_contact.strip())
            except sqlite3.IntegrityError:
                continue  # ID collision: draw another one
            self._audit.log(actor, "CREATE_PATIENT", patient_id)
            return self.get(patient_id)
        raise PatientError("Could not generate a unique Patient ID.")

    def find(self, patient_id: str) -> Optional[Patient]:
        """Return the patient, or None if the ID does not exist."""
        row = self._patients.get(patient_id.strip())
        return self._to_patient(row) if row else None

    def get(self, patient_id: str) -> Patient:
        """Return the patient or raise PatientError."""
        patient = self.find(patient_id)
        if patient is None:
            raise PatientError(f"No patient found for ID: {patient_id}")
        return patient

    def update(self, patient_id: str, changes: dict, actor: str) -> Patient:
        """Change permitted fields and record each change in the history."""
        patient = self.get(patient_id)
        if "patient_id" in changes:
            raise PatientError("The Patient ID can never be changed.")
        unknown = set(changes) - set(self.UPDATABLE)
        if unknown:
            raise PatientError(f"These fields cannot be changed: {sorted(unknown)}")
        if "name" in changes and not changes["name"].strip():
            raise PatientError("Patient name cannot be blank.")
        if "date_of_birth" in changes:
            changes["date_of_birth"] = self._check_dob(
                changes["date_of_birth"])
        new_values, history = {}, []
        for field_name, value in changes.items():
            value = value.strip()
            old = getattr(patient, field_name)
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
