# The Reminder That Reaches

**Brite Spark 2026 — Problem 07**

---

# 1. START HERE — Run the Program

This is a command-line Python project. There is no website or GUI to open.

## Step 1 — Clone the project

Open a terminal and run:

```bash
git clone https://github.com/Itz-goks/The-Reminder-That-Reaches.git
cd The-Reminder-That-Reaches
```

## Step 2 — Check Python

Run:

```bash
python --version
```

Python 3.10+ is recommended.

## Step 3 — Dependencies

No third-party Python packages are required.

The project uses Python's standard library only.

`requirements.txt` is intentionally empty.

## Step 4 — Run the tests

Run:

```bash
python -m unittest discover -s tests -v
```

A successful setup should end with:

```text
Ran 73 tests
OK
```

## Step 5 — Run the actual reminder program

Run:

```bash
python -m src.run_reminders
```

The program will:

1. Load the supplied appointments.
2. Load the supplied resident/contact data.
3. Load previous contact history.
4. Find appointments inside the reminder window.
5. Check contact rules.
6. Try SMS, voice, or email as permitted.
7. Fall back when the resident is not confirmed as reached.
8. Stop when human reach is confirmed or no further contact is allowed.
9. Record outbound attempts.
10. Print the results, metrics, and audit information.

You should see sections like:

```text
THE REMINDER THAT REACHES
REAL DATA END-TO-END RUN

--- RESULTS ---

--- SUMMARY ---

--- AUDIT ---
```

That terminal output is the running application.

---

# 2. ONE-MINUTE EXPLANATION

> **The Reminder That Reaches** is a policy-driven reminder system. Before contacting a resident, it checks opt-outs, quiet hours, available contact methods, shared-contact duplication, and the rolling two-contacts-in-seven-days limit. It then tries an allowed channel, falls back when necessary, records every actual attempt, and stops when human reach is confirmed or no further contact is allowed. The contact history is persistent, so the regulatory limit continues to work across separate runs.

# 4. AFTER THE PROGRAM RUNS — Understand the Output

Once the command works, the following sections explain what the output means and how the project works.

## Results

Each result represents one eligible appointment.

Example:

```text
AP-70514 | RS-4585 | attempted=True | channel=voice | reached=True | attempts=2 | ...
```

This means:

- `AP-70514` = appointment ID
- `RS-4585` = resident ID
- `attempted=True` = at least one outbound contact was made
- `channel=voice` = the final channel used was voice
- `reached=True` = the system confirmed human reach
- `attempts=2` = two outbound attempts were made
- the remaining text explains what happened

## Summary

The summary separates current-run activity from historical contact history.

```text
Processed
Outbound attempted
Reached
Not reached
Blocked
```

### Processed

Number of appointments that were inside the current reminder window.

### Outbound attempted

Number of appointments for which the system actually made at least one outbound contact.

### Reached

Number of appointments where confirmed human reach occurred.

### Not reached

A contact attempt happened, but confirmed human reach was not established.

### Blocked

No outbound attempt was allowed for the appointment.

---

# 4. The Reminder Decision Flow

The system follows:

```text
Appointment
    |
    v
Resident / Contact Data
    |
    v
Contact Policy
    |
    +--> Quiet hours
    +--> Opt-outs
    +--> Contact availability
    +--> Rolling 2-in-7 limit
    |
    v
Shared Contact Check
    |
    v
SMS / Voice / Email
    |
    v
Outcome Interpretation
    |
    v
Contact History + Audit
    |
    v
Metrics
```

The project is designed so that the system checks whether contact is appropriate before actually sending anything.

---

# 5. Channel Behaviour

Default order:

```text
SMS -> Voice -> Email
```

If a permitted channel does not establish confirmed human reach, the next permitted channel can be considered.

The sequence stops when:

- human reach is confirmed
- the rolling 2-in-7 limit blocks another contact
- no permitted channel remains
- contact information is unavailable
- all permitted channels have been exhausted

---

# 6. What Counts as "Reached"

The project deliberately uses a conservative definition.

```text
Voice + answered + human
    -> confirmed human reach
```

The following are not treated as confirmed human reach:

```text
Voice voicemail
Voice no answer
Voice failure
SMS delivered
Email delivered
```

SMS and email delivery are recorded as delivery evidence, but the system does not claim that the resident actually saw or answered the reminder.

---

# 7. Surprise Requirement — 2 Contacts in 7 Days

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

Persistent contact history is stored locally in:

```text
data/contact_history.jsonl
```

This is what allows a later program run to remember previous contacts.

---

# 8. Optional Two-Run Demonstration

Use a separate history file so the demonstration starts clean.

## First run

```bash
rm -f data/demo_history.jsonl
CONTACT_HISTORY_PATH=data/demo_history.jsonl python -m src.run_reminders
```

The first run should show:

```text
Historical contact attempts loaded: 0
```

It demonstrates:

```text
Appointment
  -> policy checks
  -> SMS / Voice / Email
  -> fallback when needed
  -> reached / not reached
  -> history saved
```

## Second run

Run the same command again:

```bash
CONTACT_HISTORY_PATH=data/demo_history.jsonl python -m src.run_reminders
```

Now the previous attempts are loaded.

The system should demonstrate:

```text
History loaded
    ->
2-in-7 check
    ->
new contact blocked when the resident has already reached the limit
```

This is the easiest way to demonstrate the surprise requirement.

---

# 9. Regulatory Audit

Run:

```bash
python -m src.contact_audit
```

When prompted, enter a resident ID from the run.

For example:

```text
Resident ID: RS-4291
Date/time (YYYY-MM-DD HH:MM): 2026-03-01 10:00
```

The audit reports:

- the resident
- the reference time
- contacts in the preceding rolling seven-day window
- the contact count
- the remaining allowance
- whether another contact is allowed
- the reason for the decision

---

# 10. Data Profile

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

# 11. Shared Contact Handling

The supplied data contains residents who share phone numbers or email addresses.

A run-scoped deduplication layer prevents unnecessary reuse of the same channel/contact point during one processing run.

This is separate from the resident-level 2-in-7 rule.

---

# 12. Project Structure

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

# 13. Inspect the Data

To inspect the supplied data:

```bash
python src/inspect_data.py
```

To inspect contact edge cases:

```bash
python src/inspect_contact_cases.py
```

These scripts only inspect the supplied CSV files and do not modify them.

---

# 14. Test Suite

The automated test suite covers:

- data loading
- contact ledger
- rolling seven-day boundaries
- quiet hours
- opt-outs
- channel behaviour
- reach interpretation
- fallback
- persistent contact history
- shared-contact deduplication
- reminder orchestration
- metrics

Current verified result:

```text
Ran 73 tests
OK
```

---

# 15. Requirements

The project uses Python standard-library modules only.

No third-party packages are required.

Therefore the blank `requirements.txt` is intentional.

No database, web server, API key, or external messaging account is required.

---

# 16. Runtime Files

The program can create runtime/audit files such as:

```text
outbox.jsonl
data/contact_history.jsonl
data/demo_history.jsonl
```

These are runtime files and are not third-party dependencies.

---

# 17. Clean-Clone Verification

An evaluator can run:

```bash
git clone https://github.com/Itz-goks/The-Reminder-That-Reaches.git
cd The-Reminder-That-Reaches
python -m unittest discover -s tests -v
python -m src.run_reminders
```

Expected test result:

```text
Ran 73 tests
OK
```

No special IDE or service is required.

---

# 18. Documentation Files

### README.md

Explains how to clone, test, run, audit, and understand the project.

### DECISIONS.md

Records the important data findings, design choices, rejected approaches, and scope decisions.

### AI-USAGE.md

Records where AI assistance was used during development.

---

# 19. Scope

The core project does not include:

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

---

# 20. One-Minute Explanation

> **The Reminder That Reaches** is a policy-driven reminder system. Before contacting a resident, it checks opt-outs, quiet hours, available contact methods, shared-contact duplication, and the rolling two-contacts-in-seven-days limit. It then tries an allowed channel, falls back when necessary, records every actual attempt, and stops when human reach is confirmed or no further contact is allowed. The contact history is persistent, so the regulatory limit continues to work across separate runs.

