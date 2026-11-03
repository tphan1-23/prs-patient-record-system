"""Entry point: wires the packages together and starts the web server.

Run with:  python app.py
"""
import os
from pathlib import Path

from prs.ai_integration.suggester import build_suggester
from prs.authentication.audit_service import AuditService
from prs.authentication.service import AuthService
from prs.patient.service import PatientService
from prs.persistence.audit_repository import AuditRepository
from prs.persistence.database import Database
from prs.persistence.patient_repository import PatientRepository
from prs.persistence.user_repository import UserRepository
from prs.persistence.visit_repository import VisitRepository
from prs.ui import create_app
from prs.visit.service import VisitService

DEMO_PASSWORD = "password123"


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines from a git-ignored .env file into os.environ.

    Variables already set in the terminal win over the file.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def seed_demo_data(auth, patients, visits) -> None:
    """Create the demo logins and a few FAKE patients on first run."""
    auth.create_user("staff1", "staff", DEMO_PASSWORD)
    auth.create_user("manager1", "manager", DEMO_PASSWORD)
    if patients.count() > 0:
        return
    for name, dob, phone, address, contact, note in [
        ("Alex Rivera", "1985-03-14", "555-0101", "12 Oak St, Faketown",
         "Sam Rivera 555-0111", "Dry cough and mild wheezing for three days."),
        ("Jordan Lee", "1992-11-02", "555-0102", "34 Pine Ave, Faketown",
         "Chris Lee 555-0112", "Nausea and stomach cramps after meals."),
        ("Taylor Brooks", "1970-07-29", "555-0103", "56 Elm Rd, Faketown",
         "Morgan Brooks 555-0113", "Left knee pain after a fall."),
    ]:
        patient = patients.register(name, dob, phone, address, contact,
                                    "seed")
        visits.add_note(patient.patient_id, "2025-01-15", note, "seed")


def build_app():
    """Construct every service and return the Flask app."""
    load_env_file(Path(__file__).with_name(".env"))
    db = Database("prs.db")
    audit = AuditRepository(db)
    auth = AuthService(UserRepository(db))
    patients = PatientService(PatientRepository(db), audit)
    visits = VisitService(VisitRepository(db), patients,
                          build_suggester(), audit, db)
    seed_demo_data(auth, patients, visits)
    return create_app(auth, patients, visits, AuditService(audit))


if __name__ == "__main__":
    build_app().run(debug=False)
