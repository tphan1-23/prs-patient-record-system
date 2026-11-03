"""Patient domain objects.

V2 changes:
* Weakness 1 - ``Patient`` is a frozen dataclass, so neither ``patient_id``
  nor ``_patient_id`` (nor any other field) can be reassigned after creation.
* Weakness 2 - ``Patient`` validates its own fields in ``__post_init__``
  (previously done by ``PatientService``), and updates are described by a
  typed ``PatientUpdateSpec`` instead of an untyped dict.
"""
from dataclasses import dataclass, fields, replace
from datetime import date
from typing import Mapping, Optional


class PatientError(Exception):
    """Raised for invalid patient input or an unknown patient."""


def _valid_dob(value: str) -> str:
    """Return the date of birth as YYYY-MM-DD or raise PatientError."""
    try:
        dob = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise PatientError("Date of birth must be YYYY-MM-DD.")
    if dob > date.today():
        raise PatientError("Date of birth cannot be in the future.")
    return dob.isoformat()


@dataclass(frozen=True)
class Patient:
    """A patient record. Immutable: every field, including the ID, is fixed.

    An empty ``_patient_id`` means the patient has not been saved yet.
    """

    name: str
    date_of_birth: str
    phone: str = ""
    address: str = ""
    emergency_contact: str = ""
    _patient_id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise PatientError("Patient name cannot be blank.")
        # A frozen dataclass must use object.__setattr__ to normalise values
        # during construction; afterwards every assignment is blocked.
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "date_of_birth",
                           _valid_dob(self.date_of_birth))
        for name in ("phone", "address", "emergency_contact"):
            object.__setattr__(self, name, (getattr(self, name) or "").strip())

    @property
    def patient_id(self) -> str:
        return self._patient_id

    @classmethod
    def from_row(cls, row: Mapping) -> "Patient":
        """Build a Patient from a database row."""
        return cls(
            name=row["name"], date_of_birth=row["date_of_birth"],
            phone=row["phone"], address=row["address"],
            emergency_contact=row["emergency_contact"],
            _patient_id=row["patient_id"], created_at=row["created_at"])


@dataclass(frozen=True)
class PatientUpdateSpec:
    """The fields staff may change. ``None`` means "leave unchanged".

    There is deliberately no ``patient_id`` field, so an update can never
    target the Patient ID: ``PatientUpdateSpec(patient_id="X")`` is a
    TypeError.
    """

    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

    @classmethod
    def field_names(cls) -> tuple:
        return tuple(f.name for f in fields(cls))

    @classmethod
    def from_form(cls, form: Mapping) -> "PatientUpdateSpec":
        """Build a spec from submitted form data, ignoring any other keys."""
        return cls(**{name: form.get(name, "") for name in cls.field_names()})

    def apply_to(self, patient: Patient) -> Patient:
        """Return a new, validated Patient with these changes applied."""
        changes = {name: value for name in self.field_names()
                   if (value := getattr(self, name)) is not None}
        return replace(patient, **changes)  # re-runs Patient validation
