# AI Usage

## Purpose

This document records how AI assistance was used during the development of **The Reminder That Reaches**.

AI was used as a development support tool for planning, implementation assistance, debugging, testing, and documentation.

## Areas Where AI Assistance Was Used

### 1. Project Planning

AI was used to:

- break Problem 07 into development phases
- identify the main functional requirements
- plan Git checkpoints
- identify required project documentation
- plan the implementation around the surprise requirement

### 2. Data Inspection

AI assistance was used to create and refine scripts for inspecting:

- appointment completeness
- missing contact information
- contact combinations
- opt-out values
- languages
- shared phone numbers
- shared email addresses
- multiple appointments
- appointment-level contactability

The supplied CSV files were inspected without modifying the original data.

### 3. Implementation Assistance

AI assistance was used during implementation of:

- domain models
- data loading
- contact ledger
- contact policy
- channel service
- reminder orchestrator
- persistent contact history
- shared-contact deduplication
- metrics
- CLI/demo utilities

### 4. Testing Assistance

AI assistance was used to help create and expand automated tests covering:

- rolling 7-day boundaries
- the 2-contact limit
- failed contact attempts
- quiet hours
- opt-outs
- channel outcomes
- fallback behaviour
- persistent contact history
- shared-contact handling
- reminder orchestration
- metrics

### 5. Debugging Assistance

AI assistance was used to help interpret and resolve implementation issues discovered during development, including:

- test failures
- data-profile parsing issues
- missing contact-history persistence
- test-double/interface mismatches
- metrics mixing current-run and historical attempts
- generated runtime files being tracked by Git

### 6. Documentation Assistance

AI assistance was used to help draft and refine:

- `README.md`
- `DECISIONS.md`
- `AI-USAGE.md`

## Verification

AI suggestions were checked against the supplied requirements and the actual behaviour of the project.

The project was repeatedly run and tested locally during development.

Final automated test result:

```text
73 tests
OK