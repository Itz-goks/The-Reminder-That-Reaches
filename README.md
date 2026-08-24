# The Reminder That Reaches

**Brite Spark 2026 — Problem 07**

## 1. START HERE — Run the Program

This is a command-line Python project. There is no website or GUI to open.

### Step 1 — Clone the project

```bash
git clone https://github.com/Itz-goks/The-Reminder-That-Reaches.git
cd The-Reminder-That-Reaches
```

### Step 2 — Check Python

```bash
python --version
```

Python 3.10+ is recommended.

### Step 3 — Dependencies

No third-party Python packages are required.

The project uses Python's standard library only.

`requirements.txt` is intentionally empty except for comments documenting this.

### Step 4 — Run the tests

```bash
python -m unittest discover -s tests -v
```

Current verified result:

```text
Ran 75 tests
OK
```

### Step 5 — Run the program

```bash
python -m src.run_reminders
```

The program loads the supplied data, finds eligible appointments, checks contact rules, uses the available channels, performs controlled fallback, records the outcome, and prints metrics and audit information.

The terminal output is the running application.

---

## 2. ONE-MINUTE EXPLANATION

> **The Reminder That Reaches** is a policy-driven reminder system for existing service appointments. Before contacting a resident, it checks opt-outs, quiet hours, available contact methods, shared-contact duplication, the resident's recorded language, and the rolling two-contacts-in-seven-days limit. It then tries an allowed channel, falls back when necessary, records every actual outbound attempt, and stops when human reach is confirmed or no further contact is allowed. Contact history is persistent, so the regulatory limit continues to work across separate runs.

---

## 3. AFTER THE PROGRAM RUNS — Understand the Output

### Results

Each result represents one eligible appointment.

Example:

```text
AP-70514 | RS-4585 | attempted=True | channel=voice | reached=True | attempts=2 | ...
```

This means:

- `AP-70514` = appointment ID
- `RS-4585` = resident ID
- `attempted=True` = an outbound contact was made
- `channel=voice` = the final channel used was voice
- `reached=True` = confirmed human reach
- `attempts=2` = two outbound attempts were made

### Summary

The summary separates current-run activity from historical contact history:

```text
Processed
Outbound attempted
Reached
Not reached
Blocked
```

### Audit

The audit section shows the persistent history file and how many attempts are currently in the ledger.

---

## 4. Channel Behaviour

Default channel order:

```text
SMS -> Voice -> Email
```

If a permitted channel does not establish confirmed human reach, the next permitted channel can be considered.

The sequence stops when:

- human reach is confirmed
- the rolling 2-in-7 limit blocks another contact
- no permitted channel remains
- usable contact information is unavailable
- all permitted channels are exhausted

---

## 5. What Counts as "Reached"

The system uses a conservative definition.

```text
Voice + answered + human
    -> confirmed human reach
```

These are not treated as confirmed human reach:

```text
Voice voicemail
Voice no answer
Voice failure
SMS delivered
Email delivered
```

SMS/email delivery is recorded as delivery evidence, not proof that the resident saw the reminder.

---

## 6. Language Selection

Reminder messages use the resident's recorded `language` value.

The supplied dataset contains:

```text
en  English
es  Spanish
ru  Russian
so  Somali
vi  Vietnamese
zh  Chinese
```

Supported language templates are selected deterministically.

Missing or unknown language codes fall back to English.

The system does not claim universal language coverage; it supports the languages present in the supplied dataset.

---

## 7. Surprise Requirement — 2 Contacts in 7 Days

The system enforces:

> Maximum 2 outbound contacts per resident in any rolling 7-day window.

Rules:

- the limit is per resident
- different appointments count together
- different channels count together
- failed attempts count
- historical attempts count
- a third outbound contact is blocked
- the decision is auditable

Persistent history is stored locally in:

```text
data/contact_history.jsonl
```

This is runtime-generated and is intentionally not tracked in Git.

---

## 8. Optional Two-Run Demonstration

Use a separate history file for a clean demo.

### First run

```bash
rm -f data/demo_history.jsonl
CONTACT_HISTORY_PATH=data/demo_history.jsonl python -m src.run_reminders
```

This should start with:

```text
Historical contact attempts loaded: 0
```

It demonstrates reminder attempts, fallback, reach classification, and persistence.

### Second run

```bash
CONTACT_HISTORY_PATH=data/demo_history.jsonl python -m src.run_reminders
```

The previous attempts are now loaded and the rolling 2-in-7 rule can block new outbound contacts.

---

## 9. Regulatory Audit

Run:

```bash
python -m src.contact_audit
```

Enter a resident ID from the run and a reference date/time, for example:

```text
Resident ID: RS-4291
Date/time (YYYY-MM-DD HH:MM): 2026-03-02 10:00
```

The audit shows:

- contacts in the preceding rolling seven-day window
- contact count
- remaining allowance
- whether another contact is allowed
- reason for the decision

---

## 10. Data Profile

The supplied data was inspected before implementation.

Observed:

- 940 appointments
- 620 residents
- 498 residents with appointments
- 14 residents with no contact information
- 19 appointments with no contact method
- 27 shared mobile numbers affecting 61 residents
- 69 shared email addresses affecting 151 residents
- 283 residents with multiple appointments
- 63 SMS opt-outs
- 49 voice opt-outs
- 40 email opt-outs
- 11 residents opted out of all three channels

The original CSV files are not modified.

---

## 11. Project Structure

```text
The-Reminder-That-Reaches/
|
├── data/
|   ├── appointments.csv
|   └── contacts.csv
|
├── channels/
|   └── channels.py
|
├── src/
|   ├── models.py
|   ├── data_loader.py
|   ├── contact_ledger.py
|   ├── contact_policy.py
|   ├── contact_history.py
|   ├── contact_dedup.py
|   ├── channel_service.py
|   ├── reminder_orchestrator.py
|   ├── metrics.py
|   ├── contact_audit.py
|   ├── inspect_data.py
|   ├── inspect_contact_cases.py
|   └── run_reminders.py
|
├── tests/
|
├── README.md
├── DECISIONS.md
├── AI-USAGE.md
└── requirements.txt
```

---

## 12. Data Inspection

```bash
python src/inspect_data.py
python src/inspect_contact_cases.py
```

These scripts only inspect the supplied CSV data.

---

## 13. Testing

The automated test suite covers:

- data loading
- contact ledger
- rolling 7-day boundaries
- quiet hours
- opt-outs
- channel behaviour
- reach interpretation
- fallback
- persistent history
- shared-contact deduplication
- language selection and fallback
- reminder orchestration
- metrics

Current verified result:

```text
Ran 75 tests
OK
```

---

## 14. Requirements

The project uses Python standard-library modules only.

No third-party packages are required.

Therefore `requirements.txt` contains no installable dependencies.

---

## 15. Runtime Files

The application can create:

```text
outbox.jsonl
data/contact_history.jsonl
data/demo_history.jsonl
```

These are runtime/audit files, not source dependencies.

---

## 16. Clean-Clone Verification

An evaluator can run:

```bash
git clone https://github.com/Itz-goks/The-Reminder-That-Reaches.git
cd The-Reminder-That-Reaches
python -m unittest discover -s tests -v
python -m src.run_reminders
```

Expected test result:

```text
Ran 75 tests
OK
```

No IDE, database, web server, API key, or external messaging account is required.

---

## 17. Documentation

- `README.md` — setup, run instructions, output explanation, architecture, scope
- `DECISIONS.md` — data findings, design decisions, edge cases, surprise retrofit
- `AI-USAGE.md` — record of AI assistance used during development

---

## 18. Scope

The core solution does not include:

- appointment booking
- appointment rescheduling
- appointment cancellation workflow
- real external messaging providers
- WhatsApp integration
- Google Calendar integration
- a large frontend/dashboard
- production-scale infrastructure
- generative message creation

The scope was intentionally kept focused on Problem 07 and the surprise requirement.
