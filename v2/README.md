# Patient Record System - Version 2

A small web app (Python, Flask, SQLite) for a clinic: register patients, add visit notes, and review AI-suggested note categories. **All data is fake.**

## File tree

```
v2/
  app.py                     entry point (wires everything together)
  requirements.txt
  README.md
  prs/
    ui/                      Flask routes + HTML templates
      __init__.py
      routes.py
      templates/  base, login, home, register, edit, patient, review, audit (.html)
    authentication/
      models.py              User, AuthError, roles
      service.py             login, roles, 15 minute timeout
      audit_service.py       manager-only access to the audit log
    patient/
      models.py              Patient (frozen, self-validating), PatientUpdateSpec
      interfaces.py          PatientLookup interface used by the visit package
      service.py             register, find, update, change history
    visit/
      models.py              VisitNote (frozen, self-validating)
      service.py             visit notes, category review
    ai_integration/suggester.py AI client + keyword fallback
    persistence/
      database.py            schema, Patient ID trigger, transactions
      user_repository.py     staff accounts
      patient_repository.py  patients + change history
      visit_repository.py    visit notes
      audit_repository.py    audit log
```

## Install and run (step by step)

1. Install Python 3.9 or newer from https://www.python.org/downloads/ .
2. Open a terminal in the `v2` folder:
   ```
   cd v2
   ```
3. (Recommended) create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS / Linux
   ```
4. Install the dependency:
   ```
   pip install -r requirements.txt
   ```
5. Start the app:
   ```
   python app.py
   ```
6. Open http://127.0.0.1:5000 in your browser.

The first run creates `prs.db` (SQLite) in the folder you ran the command from, plus three fake patients. Your data is still there after you stop and restart the app.

## Demo logins (fake)

| Username   | Password      | Role            | Notes                           |
|------------|---------------|-----------------|---------------------------------|
| `staff1`   | `password123` | regular staff   | patients, notes, categories     |
| `manager1` | `password123` | clinic manager  | the same, plus the **Audit log** page |

## Using the app

1. Sign in. Search a patient by ID (the three demo patients show up after the first run; open the audit log as the manager to see their IDs, or register a new patient).
2. **Register patient** creates a Patient ID automatically (`PRS-XXXXXXXX`).
3. On a patient page: update details, view the change history, add a visit note.
4. After you save a note (it starts as *Uncategorized*) the review screen shows **"Suggested category (not a diagnosis)"**. Accept it, choose a different category, or keep Uncategorized.
5. If the AI is unavailable, slow (over 5 seconds) or unsure, you see **"AI Suggestion Unavailable"** and can pick a category yourself.
6. You are signed out after 15 minutes of inactivity.

## AI categorization

- Easiest: create a file `v2/.env` containing one line, `GEMINI_API_KEY=your-key`. It is git-ignored, so it is never committed. The app reads it at startup.
- Or set `GEMINI_API_KEY` in the terminal (a free key from Google AI Studio) to use a real AI model, Google Gemini (5 second timeout). A terminal value wins over the file. Only the note text is sent. Never put the key in the code or commit it.
  ```
  set GEMINI_API_KEY=your-key             # Windows cmd
  $env:GEMINI_API_KEY = "your-key"        # PowerShell
  export GEMINI_API_KEY=your-key          # macOS / Linux
  ```
  The default model is `gemini-3.5-flash-lite`, chosen because it must answer within the 5 second limit; slower models time out and show "AI Suggestion Unavailable". Set `GEMINI_MODEL` to use a different Gemini model.
- With no key, a **temporary keyword fallback (not an AI)** is used and labeled as such on screen.

## Optional settings

- `PRS_SECRET_KEY`: secret for Flask session cookies (defaults to a development value).
