# The Reminder That Reaches

**Brite Spark 2026 — Problem 07**

## Overview
The Reminder That Reaches is a reminder orchestration system for existing service appointments.

The system does more than send messages. It checks whether a resident may be contacted, selects an appropriate permitted channel, handles controlled fallback, interprets channel outcomes, records every actual outbound attempt, and stops when appropriate.

## Core Requirements
- channel fallback with a stopping rule
- quiet-hour enforcement
- opt-out enforcement
- language-aware message selection
- duplicate protection for shared contact points
- measurable definition of "reached"
- auditable decisions
- surprise requirement: at most 2 outbound contacts per resident in a rolling 7-day period

## Supplied Components
- `data/appointments.csv`
- `data/contacts.csv`
- `channels/channels.py`
- `channels/demo.py`

The supplied CSV files and mock channels are kept as provided.

## Current Data Profile
- 940 appointments
- 498 unique residents with appointments
- 620 contact records
- 14 residents with no contact information
- 19 appointments with no contact method
- 27 shared mobile numbers affecting 61 residents
- 69 shared email addresses affecting 151 residents
- 283 residents with multiple appointments
- languages: en, es, vi, so, ru, zh
- 0 opt-outs in the supplied dataset; opt-out behavior is still covered by tests

## Architecture

```text
Appointment
    |
    v
Resident / Contact Resolution
    |
    v
Regulatory Contact Guard
(2 contacts in rolling 7 days)
    |
    v
Central Contact Policy
(quiet hours / opt-outs / usable channels)
    |
    v
Channel Selection
    |
    v
Channel Service
(SMS / Voice / Email)
    |
    v
Outcome Interpretation
    |
    v
Contact Ledger + Audit Result
    |
    v
Metrics
```

## Implemented Components

### Data and models
- resident model
- appointment model
- contact-attempt model

### Contact ledger
Tracks every actual outbound attempt and enforces the rolling 2-in-7 resident contact limit.

### Central contact policy
Checks channel availability, quiet hours, opt-outs, and the regulatory contact limit before allowing an outbound contact.

### Channel service
Wraps the supplied mock SMS, voice, and email channels and interprets their `status` and `detail` values.

### Reach definition
Current conservative rule:
- voice `answered / human` is confirmed human reach
- voicemail, no answer, and failures are not confirmed human reach
- SMS/email delivery is recorded as delivery evidence, not confirmed human reach

## Data Inspection
Run from the repository root:

```bash
python src/inspect_data.py
```

and:

```bash
python src/inspect_contact_cases.py
```

These scripts only inspect data and do not modify the supplied CSV files.

## Tests

Run the full test suite:

```bash
python -m unittest discover -s tests -v
```

Current validated suite:

```text
59 tests
PASS
```

## Running the Application
The final reminder-orchestration entry point will be documented here after the orchestrator is implemented.

## Known Scope Limits
The core solution does not currently include:
- appointment booking
- appointment rescheduling
- appointment cancellation
- real external messaging providers
- WhatsApp
- Google Calendar
- production-scale infrastructure
- natural-language message generation

Optional enhancements only come after all floor requirements are working and tested.

## Documentation
- `README.md` — setup, usage, architecture, testing
- `DECISIONS.md` — decisions, edge cases, rejected approaches, and scope
- `AI-USAGE.md` — disclosure of AI assistance

These documents are maintained throughout development.
