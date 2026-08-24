# AI Usage

## Purpose

This document records where and how AI assistance was used during development of **The Reminder That Reaches**.

AI was used as a development support tool for planning, implementation, testing, debugging, and documentation.

## 1. Planning and Requirement Breakdown

AI assistance was used to:

- break Problem 07 into implementation phases
- turn the handbook requirements into development checkpoints
- plan the reminder flow
- plan the surprise 2-in-7 retrofit
- identify required documentation and validation steps

## 2. Data Inspection

AI assistance was used to help create and refine:

- `src/inspect_data.py`
- `src/inspect_contact_cases.py`

These scripts were used to inspect:

- appointment completeness
- missing contact information
- contact combinations
- opt-outs
- languages
- shared phone numbers
- shared email addresses
- multiple appointments
- appointment-level contactability
- verification dates

The supplied CSV files were inspected without modifying the source data.

## 3. Core Implementation Assistance

AI assistance was used while developing and revising:

- `models.py`
- `data_loader.py`
- `contact_ledger.py`
- `contact_policy.py`
- `channel_service.py`
- `reminder_orchestrator.py`
- `contact_history.py`
- `contact_dedup.py`
- `metrics.py`
- `contact_audit.py`
- `run_reminders.py`

## 4. Language Support

AI assistance was used to implement and test deterministic reminder templates for the languages present in the supplied dataset:

- English
- Spanish
- Russian
- Somali
- Vietnamese
- Chinese

AI assistance also helped add the English fallback for unknown or missing language codes.

## 5. Surprise Requirement

AI assistance was used to help implement the retrospective rolling 2-in-7 rule through:

- persistent contact history
- per-resident contact counting
- historical loading
- deterministic priority
- audit evidence
- current-run vs historical metric separation

## 6. Testing Assistance

AI assistance was used to help create and expand automated tests covering:

- data loading
- rolling seven-day boundaries
- failed contact attempts
- quiet hours
- opt-outs
- channel outcomes
- fallback
- persistent history
- shared contacts
- language selection
- unknown-language fallback
- reminder orchestration
- metrics

Final locally verified result:

```text
75 tests
OK
```

## 7. Debugging Assistance

AI assistance was used to help interpret and resolve issues discovered during development, including:

- incorrect Y/N opt-out inspection
- missing persistent contact-history integration
- fake channel service interface mismatch
- current-run vs historical metrics mixing
- generated runtime files being tracked by Git
- import-order syntax errors
- language-template implementation/indentation issues
- repository clean-clone verification issues

The fixes were executed and verified locally.

## 8. Documentation Assistance

AI assistance was used to help draft and refine:

- `README.md`
- `DECISIONS.md`
- `AI-USAGE.md`

## 9. Development Workflow

The AI-assisted development workflow was:

```text
Requirement / project idea
        ↓
Planning / design discussion
        ↓
AI-assisted implementation or revision
        ↓
Run code locally
        ↓
Inspect actual behaviour
        ↓
Fix / refine
        ↓
Run tests
        ↓
Commit and push
```

The final repository was also tested from a fresh Git clone.

## 10. Final Responsibility

AI assistance was not treated as an automatic source of correctness.

The project author reviewed changes, ran the code, inspected outputs, made project-level decisions, and validated the final implementation against the project requirements.
