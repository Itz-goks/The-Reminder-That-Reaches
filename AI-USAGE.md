# AI Usage

## Purpose
This file records AI assistance used during development of **The Reminder That Reaches**.

The project author remains responsible for understanding, reviewing, testing, and being able to explain all submitted code and decisions.

## Usage So Far

### Planning and requirements analysis
AI assistance was used to:
- interpret the Brite Spark guidelines and handbook
- interpret Problem 07 and the surprise challenge
- organize the project phases
- identify required documents, test checkpoints, and submission requirements

### Data inspection
AI assistance was used to help create:
- `src/inspect_data.py`
- `src/inspect_contact_cases.py`

These scripts were used to inspect missing contact information, contact combinations, shared contact points, languages, multiple appointments, and appointment-level contactability.

The supplied CSV files were not modified.

### Models and contact ledger
AI assistance was used to help scaffold:
- resident, appointment, and contact-attempt models
- the rolling 7-day contact ledger
- unit tests for the 2-in-7 surprise rule

The project author ran and verified the tests.

### Central contact policy
AI assistance was used to help scaffold the central policy and its tests for:
- quiet hours
- opt-outs
- channel availability
- rolling 2-in-7 enforcement

The project author ran and verified the tests.

### Channel service
AI assistance was used to help scaffold the adapter around the supplied mock SMS, voice, and email channels and the tests for:
- contact-point selection
- channel result interpretation
- conservative reach classification
- recording every actual outbound attempt
- rejecting unsupported channels

The project author ran the complete test suite and verified **59 tests passed**.

## Ongoing Use
AI assistance may continue to be used for:
- implementation scaffolding
- debugging
- test generation
- code review
- documentation

Any AI-suggested code will be reviewed, tested, and understood by the project author before inclusion.

This file will be updated whenever AI is used for a materially new purpose.
