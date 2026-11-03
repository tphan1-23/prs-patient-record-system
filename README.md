# prs-patient-record-system

CSCI 4490 Assignment 4 - Patient Record System (Python, OOP, Flask, SQLite), built with GenAI assistance.

| Folder | Contents |
|--------|----------|
| `v1/`  | Original, unedited AI-generated implementation. **Do not edit.** Audit only. |
| `v2/`  | Corrected and refactored version (Version 2). |
| `prompts_log.md` | The GenAI prompts used, in order. |

## Run a version

Requires Python 3.9 or newer.

```
cd v1                       # or v2
python -m venv venv
venv\Scripts\activate       # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 .

Demo logins (fake): `staff1` (regular staff) and `manager1` (clinic manager), password `password123`.

Set `GEMINI_API_KEY` to use a real AI model (Google Gemini) for note categorization. Without it, a clearly labeled temporary keyword fallback (not an AI) is used. Full details are in `v1/README.md`.

All patient data is synthetic.
