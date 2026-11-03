# GenAI Prompt Log

Rule: GenAI is used for **code only**. All written analysis is done by the group.

## Prompt 1 - Version 1 generation (Person 1)

Tool: Claude
Target: `v1/`

Prompt (exact text as sent):

> Hi! I'm working on a school project and I need you to build a Patient Record System in Python using object-oriented programming. Please give me a full working app that I can run on my computer.
>
> Here's what I want:
>
> Use Python, Flask for a simple web interface, and SQLite to store the data. Only use fake patient data. Please add a few fake patients and two demo logins, one for a regular staff member and one for a clinic manager.
>
> Organize the code into these six packages: ui, patient, visit, authentication, ai_integration, and persistence. The ui package talks to authentication, patient, and visit. The visit package uses patient to check that a patient exists, and it's the only package that uses ai_integration. All database work goes through persistence. The ai_integration package shouldn't depend on any of the others.
>
> Here's what the app should do:
>
> 1. Staff can register a new patient. The name can't be blank. The app creates the Patient ID automatically and staff can't choose or change it. No two patients should ever get the same ID.
> 2. Staff can search for a patient by ID. If the ID doesn't exist, show "No patient found for ID: <id>" and no patient data.
> 3. Staff can update a patient's name, date of birth, phone number, address, and emergency contact, but nothing else, and never the Patient ID. Every change should be saved in a change history with the old value, the new value, who changed it, and when.
> 4. Staff can add a visit note, but only for a patient that exists. The visit date can't be in the future, and the note must be 1 to 2,000 characters and not blank. Save who wrote it and when.
> 5. The note gets saved first, with no category (it shows as "Uncategorized"). After that, the app asks the AI to suggest a category based only on the note text, not any patient info. The four categories are Respiratory, Digestive, Musculoskeletal, and General/Other.
> 6. The suggestion appears on screen labeled "Suggested category (not a diagnosis)". Staff can accept it, reject it, or pick a different category from the same four. The category only gets saved after staff accept or choose it, and it should be marked as either AI-suggested or staff-chosen.
> 7. If the AI is down, takes more than 5 seconds, or isn't sure, the note stays saved anyway. Show a warning that says "AI Suggestion Unavailable" and let staff pick a category by hand.
> 8. Show a patient's visit history with the newest visit date first, including the date, text, staff member, and category. Never show another patient's notes.
> 9. Users have to log in. If they're not logged in, they can't see any patient data. Log them out after 15 minutes of no activity. Keep a log of who created, updated, or added what, and when.
> 10. All data has to still be there after I close and restart the app.
>
> For the AI part, write a class that calls an outside AI API with a 5 second timeout, and read the API key from an environment variable. Also add a simple keyword-based backup that's clearly labeled as a temporary fallback and not a real AI, and use it only when there's no API key.
>
> Please give me the file tree first, then the full code for every file, then a requirements.txt, and a README with step by step instructions for installing and running it, including the demo logins. Add docstrings and basic error handling.

## Prompts for Version 2 (collected from Person 3)
Tool: Claude
Target: `v2/`

Prompt (exact text as sent):
Hi! I'm working on a group school project. My teammate already generated Version 1 (v1) of our Patient Record System using Python, Flask, and SQLite. My task is to create Version 2 (v2) by improving the existing code based on our code review.
I have attached v1 source code and the five weaknesses our group identified.
Please refactor v1 to address these weaknesses:
Weakness 1: Weak Encapsulation of Patient ID (OOP / Encapsulation)
Location: Patient dataclass (prs/patient/service.py).
Analysis: Unfrozen dataclasses allow callers to assign patient._patient_id directly, and SQLite lacks schema triggers blocking patient_id updates.   
Action: Freeze the Patient dataclass or add a __setattr__ guard on _patient_id. And also add a SQLite trigger: CREATE TRIGGER block_patient_id_update BEFORE UPDATE OF patient_id ON patients BEGIN SELECT RAISE(ABORT, 'Patient ID is immutable'); END;.   

Weakness 2: Anemic Domain Model (OOP Design)
Location: Patient, VisitNote, PatientService._check_dob(), VisitService.add_note().   
Analysis: Domain entities act as passive data containers while service classes handle validation rules (blank names, date checks, text limits). Update methods use generic untyped dictionaries.   
Action: Move field validations directly into Patient and VisitNote constructors, and pass structured PatientUpdateSpec objects to updates.  

Weakness 3: Tight Coupling and Layer Leakage (OOP / File Structure)
Location: VisitService (prs/visit/service.py), routes.py (prs/ui/routes.py), prs/persistence/.   
Analysis: VisitService directly imports concrete PatientService instead of an interface. routes.py executes AuditRepository.recent() directly, bypassing the service layer. Monolithic files combine entities, services, and repositories.   
Action: Decouple VisitService via a PatientLookup interface, create an AuditService for web routes, and split code into distinct models.py, service.py, and repository.py files.

Weakness 4: Database Operations (Efficiency and Optimization)
Location: VisitService.set_category() (prs/visit/service.py).
Analysis: VisitService calls get_note() twice. First time, before updating the visit note category and then after saving the updated category to the database. Additional database query may not be necessary.
Action: Modify the set_category() method to return the updated visit note directly. So that the VisitService.set_category() can use updated visit notes without calling get_note() again.

Weakness 5: Separate Database Operations (Requirements/Architecture Alignment)
Location: VisitService.add_note() (prs/visit/service.py), (prs/persistence/).
Analysis: VisitService.add_note() saves new visit notes through the visit repository and then calls self._audit.log() to record the action. Those operations are saved separately, so if self._audit.log() fails, the visit may be saved without an audit record. 
Action: Modify VisitService.add_note() so the visit repository saves the new note and self._audit.log() records the action together. If one of them fails, no changes should be made.

Important Requirements!

* Use the existing v1 code as the starting point. Do not create a completely new application.
* Keep all ten functional requirements from v1.
*  Preserve the six main packages: ui, patient, visit, authentication, ai_integration, and persistence.
* Keep the existing Flask interface, SQLite database, authentication, and AI category suggestion functionality.
* All changes should be made in a separate v2 folder.
* Generate the complete updated code for every changed file, including any necessary imports.
* Make only the changes necessary to address the five identified weaknesses while preserving existing functionality.


Please first inspect the existing code and identify what need changes. Then provide the updated v2 implementation.
