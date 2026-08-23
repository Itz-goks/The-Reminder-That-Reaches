# Decisions

## Project
**The Reminder That Reaches** — Brite Spark 2026, Problem 07

## Purpose
This file records important decisions made during development, including data findings, implementation decisions, rejected approaches, time cuts, limitations, and future improvements.

## 1. Initial Scope
Build a reminder orchestration system for existing appointments using the supplied appointment/contact data and the provided mock SMS, voice, and email channels.

## 2. Supplied Data Must Not Be Fabricated
Missing contact information is preserved. We do not randomly fill, delete, or ML-impute phone numbers, landlines, or email addresses.

## 3. Phase 0.2 — Data Findings
- 940 appointments
- 498 unique residents with appointments
- 620 residents in the contacts file
- 14 residents have no contact information
- 19 appointments have no contact method
- 27 shared mobile numbers affecting 61 residents
- 69 shared email addresses affecting 151 residents
- 283 residents have multiple appointments
- maximum observed appointments for one resident: 5
- languages recorded: en, es, vi, so, ru, zh
- supplied dataset currently contains zero SMS, voice, and email opt-outs

## 4. Contact Handling
Residents with no usable contact method remain in the system and receive an explicit `NO_USABLE_CONTACT` outcome.

Shared contact points are handled separately from the per-resident regulatory contact limit.

## 5. Language
Message selection is based on the resident's recorded language. Missing templates are handled through an explicit fallback rather than fabricated translations.

## 6. Verification Dates
`number_last_verified` is treated as a data-quality signal, not automatic invalidation because the supplied requirements do not define an invalidation threshold.

## 7. Definition of "Reached"
A delivery status alone is not treated as proof of human reach.

Current channel interpretation:
- voice + `answered` + `human` => `reached = True`
- voice + voicemail/no answer/failure => `reached = False`
- SMS delivery => delivery evidence, not confirmed human reach
- email delivery => delivery evidence, not confirmed human reach
- bounced/failed outcomes => not reached

This conservative definition is explicit and testable.

## 8. Central Contact Policy
Quiet hours, opt-outs, contact availability, and the regulatory contact limit are enforced centrally before an outbound attempt is sent.

## 9. Surprise Challenge — Rolling 7-Day Contact Limit
A resident may receive at most 2 outbound contacts in any rolling 7-day period.

Rules:
- every outbound attempt counts, including failed attempts
- count is per resident
- contacts across different appointments and channels count together
- historical contacts count
- the check occurs before every outbound contact
- blocked attempts are not added to the outbound ledger
- the decision and reason must be auditable

## 10. Channel Service
The supplied `channels.py` remains unchanged.

`ChannelService` acts as an adapter around the supplied SMS, voice, and email functions.

Responsibilities:
- select the correct contact point
- call the supplied channel
- interpret `status` and `detail`
- classify reach conservatively
- record every actual outbound attempt in the contact ledger

Permission decisions remain in `ContactPolicy`; channel execution remains in `ChannelService`.

## 11. Channel Results
The supplied mock channels intentionally produce misleading or ambiguous outcomes.

Example:
- SMS to a landline can return `delivered / accepted_by_carrier`.
- This is not treated as human reach.

Voice `answered / human` is currently the strongest available evidence of actual human reach.

## 12. Rejected Approaches
- random contact-data filling
- ML fabrication/imputation of contact values
- deleting residents with missing contact information
- treating delivery as human reach
- adding WhatsApp or Google Calendar to the core solution
- building a large frontend before the floor works

## 13. Scope Exclusions
Unless a later requirement changes the scope:
- appointment booking
- appointment rescheduling
- appointment cancellation workflow
- real SMS provider integration
- real voice provider integration
- real email provider integration
- WhatsApp
- Google Calendar
- production-scale infrastructure
- natural-language message generation

## 14. Development Checkpoints
Completed:
- data inspection scripts
- required project documents
- resident/appointment/contact-attempt models
- rolling 7-day contact ledger
- ledger tests
- central contact policy
- policy tests
- channel service
- channel outcome interpretation
- channel service tests

Current validated test suite: **59 tests passing**.

## 15. Git History
The repository is developed incrementally. Meaningful implementation and documentation changes are committed and pushed rather than accumulated into one final commit.

## 16. Next Development Step
Build the reminder orchestration flow on top of:
1. data models
2. contact ledger
3. central contact policy
4. channel service

The orchestrator must:
- consider only eligible appointments
- choose an allowed channel
- send through `ChannelService`
- record every actual attempt
- stop when reach is established
- perform controlled fallback when appropriate
- re-check the 2-in-7 limit before every fallback attempt
- produce auditable outcomes
