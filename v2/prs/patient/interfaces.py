"""Interfaces the patient package offers to other packages.

V2 (Weakness 3): the visit package depends on this small abstraction instead
of the concrete ``PatientService``.
"""
from abc import ABC, abstractmethod


class PatientLookup(ABC):
    """Anything that can tell whether a patient exists."""

    @abstractmethod
    def exists(self, patient_id: str) -> bool:
        """Return True if a patient with this ID is registered."""
