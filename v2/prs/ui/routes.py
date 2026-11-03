"""Flask routes. The UI talks only to authentication, patient and visit."""
from datetime import date
from functools import wraps

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for)

from ..authentication.audit_service import AuditService
from ..authentication.models import AuthError
from ..authentication.service import AuthService
from ..patient.models import PatientError, PatientUpdateSpec
from ..patient.service import PatientService
from ..visit.models import CATEGORIES, VisitError
from ..visit.service import VisitService

SUGGESTION_LABEL = "Suggested category (not a diagnosis)"


def build_blueprint(auth: AuthService, patients: PatientService,
                    visits: VisitService,
                    audit_service: AuditService) -> Blueprint:
    """Create the blueprint with the services injected."""
    bp = Blueprint("prs", __name__)

    def login_required(view):
        """Redirect to the login page unless the session is valid."""
        @wraps(view)
        def wrapper(*args, **kwargs):
            try:
                g.user = auth.validate(session.get("token"))
            except AuthError as error:
                session.clear()
                flash(str(error), "error")
                return redirect(url_for("prs.login"))
            return view(*args, **kwargs)
        return wrapper

    @bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            try:
                session["token"] = auth.login(
                    request.form.get("username", "").strip(),
                    request.form.get("password", ""))
                return redirect(url_for("prs.home"))
            except AuthError as error:
                flash(str(error), "error")
        return render_template("login.html")

    @bp.route("/logout")
    def logout():
        auth.logout(session.pop("token", None))
        flash("You have been signed out.", "info")
        return redirect(url_for("prs.login"))

    @bp.route("/")
    @login_required
    def home():
        return render_template("home.html")

    @bp.route("/patients/search")
    @login_required
    def search():
        patient_id = request.args.get("patient_id", "").strip()
        if patient_id and patients.find(patient_id):
            return redirect(url_for("prs.patient_page",
                                    patient_id=patient_id))
        flash(f"No patient found for ID: {patient_id}", "error")
        return render_template("home.html")

    @bp.route("/patients/new", methods=["GET", "POST"])
    @login_required
    def register():
        if request.method == "POST":
            try:
                patient = patients.register(
                    request.form.get("name", ""),
                    request.form.get("date_of_birth", ""),
                    request.form.get("phone", ""),
                    request.form.get("address", ""),
                    request.form.get("emergency_contact", ""),
                    g.user.username)
                flash(f"Patient registered. Patient ID: {patient.patient_id}",
                      "info")
                return redirect(url_for("prs.patient_page",
                                        patient_id=patient.patient_id))
            except PatientError as error:
                flash(str(error), "error")
        return render_template("register.html")

    @bp.route("/patients/<patient_id>")
    @login_required
    def patient_page(patient_id):
        patient = patients.find(patient_id)
        if patient is None:
            flash(f"No patient found for ID: {patient_id}", "error")
            return render_template("home.html"), 404
        return render_template(
            "patient.html", patient=patient,
            notes=visits.history(patient_id),
            changes=patients.change_history(patient_id),
            today=date.today().isoformat())

    @bp.route("/patients/<patient_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit(patient_id):
        patient = patients.find(patient_id)
        if patient is None:
            flash(f"No patient found for ID: {patient_id}", "error")
            return render_template("home.html"), 404
        if request.method == "POST":
            try:
                patients.update(patient_id,
                                PatientUpdateSpec.from_form(request.form),
                                g.user.username)
                flash("Patient updated.", "info")
                return redirect(url_for("prs.patient_page",
                                        patient_id=patient_id))
            except PatientError as error:
                flash(str(error), "error")
        return render_template("edit.html", patient=patient)

    @bp.route("/patients/<patient_id>/notes", methods=["POST"])
    @login_required
    def add_note(patient_id):
        try:
            note = visits.add_note(
                patient_id, request.form.get("visit_date", ""),
                request.form.get("note_text", ""), g.user.username)
        except (PatientError, VisitError) as error:
            flash(str(error), "error")
            return redirect(url_for("prs.patient_page",
                                    patient_id=patient_id))
        flash("Note saved as Uncategorized.", "info")
        return redirect(url_for("prs.review", note_id=note.note_id))

    @bp.route("/notes/<int:note_id>/review", methods=["GET", "POST"])
    @login_required
    def review(note_id):
        try:
            note = visits.get_note(note_id)
        except VisitError as error:
            flash(str(error), "error")
            return redirect(url_for("prs.home"))
        if request.method == "POST":
            action = request.form.get("action")
            if action == "skip":
                flash("Note kept as Uncategorized.", "info")
                return redirect(url_for("prs.patient_page",
                                        patient_id=note.patient_id))
            category = request.form.get("category", "")
            source = ("ai-suggested" if action == "accept"
                      else "staff-chosen")
            try:
                visits.set_category(note_id, category, source,
                                    g.user.username)
                flash(f"Category saved: {category} ({source}).", "info")
                return redirect(url_for("prs.patient_page",
                                        patient_id=note.patient_id))
            except VisitError as error:
                flash(str(error), "error")
        suggestion = visits.suggest_category(note_id)
        return render_template(
            "review.html", note=note, suggestion=suggestion,
            categories=CATEGORIES, label=SUGGESTION_LABEL)

    @bp.route("/audit")
    @login_required
    def audit():
        try:
            entries = audit_service.recent_entries(g.user)
        except AuthError as error:
            flash(str(error), "error")
            return redirect(url_for("prs.home"))
        return render_template("audit.html", entries=entries)

    return bp
