# Decisions

## Project

**The Reminder That Reaches**  
Brite Spark 2026 — Problem 07

## Why this document exists

We used this file as a running record of the important decisions made during the project.

It is intentionally not just a technical specification. It records what we noticed, what we chose, what we rejected, and what changed when the requirements changed.

---

## 1. Start with the supplied data

### Decision

Inspect the appointment and contact files before designing the reminder engine.

### Why

The contact data contains missing values, opt-outs, shared contact points, multiple appointments, and different languages. Designing first and inspecting later would have caused the system to make assumptions about the data.

---

## 2. Do not fabricate missing contact information

### Decision

Do not randomly fill missing mobile, landline, or email values. Do not use ML to invent contact details.

### Why

A predicted contact value is not proof that it belongs to the resident. The safer and more defensible behaviour is to keep the missing value and let the policy decide what can still be done.

### Result

Residents with no usable contact method remain in the system and receive an explicit `NO_USABLE_CONTACT` outcome.

---

## 3. Actual data findings

The inspection found:

- 940 appointments
- 620 residents
- 498 unique residents with appointments
- 14 residents with no contact information
- 19 appointments with no contact method
- 27 shared mobile numbers affecting 61 residents
- 69 shared email addresses affecting 151 residents
- 283 residents with multiple appointments
- maximum observed appointments for one resident: 5

Contact combinations:

- Mobile + Landline + Email: 95
- Mobile + Landline: 70
- Mobile + Email: 236
- Landline + Email: 31
- Mobile only: 157
- Landline only: 17
- Email only: 0
- No contact information: 14

---

## 4. Opt-out parsing correction

### What happened

The first profiling version looked for `YES`.

The supplied data actually uses `Y/N`.

### Decision

Correct the inspection logic to use:

```text
Y = opted out
N = not opted out
```

### Final observed values

- SMS opt-out: 63
- Voice opt-out: 49
- Email opt-out: 40
- All three: 11

This was rerun against the original data. The source CSV was not changed.

---

## 5. Centralize contact safety

### Decision

Create a central `ContactPolicy`.

The policy is responsible for:

- quiet hours
- opt-outs
- usable contact methods
- rolling regulatory contact allowance

### Why

The supplied mock channels do not enforce safety rules themselves. Having a central gate makes it harder for future code to bypass an important restriction.

---

## 6. Treat the surprise requirement as architecture, not a patch

### Decision

When the surprise requirement introduced the rolling two-contacts-in-seven-days rule, we made it a central part of the contact decision flow instead of adding a special case at the end.

### Result

Every outbound attempt passes through the regulatory check.

---

## 7. Per-resident rolling 7-day ledger

### Decision

Track contact history by resident and timestamp.

The ledger stores:

- resident ID
- appointment ID
- timestamp
- channel
- contact point
- status
- detail
- reach result

### Rules

- maximum 2 outbound contacts
- rolling seven-day window
- per resident
- different appointments count together
- different channels count together
- failed attempts still count
- historical attempts count

---

## 8. Keep persistent history

### Decision

Persist outbound attempts in:

```text
data/contact_history.jsonl
```

### Why

The surprise requirement applies retrospectively. A purely in-memory ledger would forget yesterday's contacts after the application stopped.

---

## 9. Do not use outbox.jsonl as the regulatory source of truth

### Decision

Use our own structured contact history for regulatory counting.

### Why

The supplied `outbox.jsonl` contains channel-level information but does not identify the resident. Because the regulatory limit is per resident, our application must retain the resident ID with each attempt.

---

## 10. Define "reached" conservatively

### Decision

A successful delivery status is not automatically a human reach.

Current rule:

```text
voice + answered + human -> reached
voice + voicemail/no-answer/failure -> not confirmed
SMS delivery -> delivery evidence only
Email delivery -> delivery evidence only
```

### Why

We do not want the metrics to claim that somebody was reached when the channel only confirms delivery.

---

## 11. Channel fallback

### Decision

Use a controlled fallback sequence:

```text
SMS -> Voice -> Email
```

When the first channel does not establish confirmed human reach, the next permitted channel is considered.

### Stopping conditions

Stop when:

- human reach is confirmed
- the regulatory limit blocks the next attempt
- no permitted channel remains
- contact data is unavailable
- all allowed channels have been exhausted


---

## 11A. Language-specific reminder messages

### Decision

Use the resident's recorded `language` field to select the reminder message template.

The supplied dataset contains these language codes:

- `en` — English
- `es` — Spanish
- `ru` — Russian
- `so` — Somali
- `vi` — Vietnamese
- `zh` — Chinese

### Behaviour

```text
Resident language
       ↓
Supported template
       ↓
Reminder message
```

If the language is missing or not supported:

```text
Unknown / missing language
       ↓
English fallback
```

### Why

The requirement is to select the correct language for the resident. We chose a deterministic template approach rather than adding a translation service or generative translation layer.

This keeps the behaviour predictable, testable, auditable, and independent of external APIs.

We deliberately support the languages present in the supplied dataset rather than claiming universal language coverage.

### Testing

Language selection is covered by automated tests for:

- supported-language selection
- unknown-language fallback to English

---

## 12. Shared contact points

### Decision

Add a run-scoped deduplicator for shared phone numbers and email addresses.

### Why

The supplied data contains shared contact points, so the same channel/contact point should not be unnecessarily reused within one processing run.

### Important distinction

Deduplication does not replace the regulatory ledger.

The 2-in-7 rule is still counted per resident.

---

## 13. Multiple appointments

### Decision

A resident's appointments share the same regulatory contact allowance.

### Priority

When eligible appointments compete, process them deterministically:

1. earliest appointment time
2. appointment ID as tie-breaker

### Why

This is simple, repeatable, based on operational appointment information, and does not rely on protected characteristics.

---

## 14. Keep current-run metrics separate from history

### Decision

Metrics for a run use only contacts created during that run.

The persistent ledger total is shown separately.

### Why

Otherwise a second run could appear to have sent messages that were actually sent yesterday.

---

## 15. Do not overbuild the project

### Rejected or deliberately excluded

- random/ML completion of missing contact data
- WhatsApp integration
- Google Calendar integration
- real provider APIs
- large UI/dashboard
- appointment booking
- rescheduling/cancellation
- production infrastructure
- generative message creation

### Why

The priority was to solve the scored reminder problem reliably and make the surprise requirement auditable.

---

## 16. Test-first checkpoints

We added tests alongside the main components rather than waiting until the end.

The final suite covers:

- data loading
- contact ledger
- contact policy
- channel service
- contact history
- shared-contact deduplication
- orchestrator
- metrics

Final validated result:

```text
75 tests
OK
```

---

## 17. What changed during development

The project was deliberately built in small stages.

Major milestones:

1. data inspection
2. models
3. rolling contact ledger
4. central policy
5. channel integration
6. reminder orchestration
7. persistent history
8. shared-contact deduplication
9. metrics
10. real-data validation
11. documentation and cleanup

Each milestone was tested before moving to the next major component.

---

## 18. What the final system does not claim

The system does not claim to guarantee that an SMS or email was read.

It reports what the available channel evidence actually supports.

It also does not claim to be a production messaging platform. It is a deterministic reminder decision/orchestration solution built around the supplied mock channels.

---

## 19. Future improvement

After the required floor, the next improvements would be:

1. broader language coverage beyond the languages present in the supplied dataset
2. stronger operational reporting
3. production-grade persistence
4. real messaging provider adapters

Those are deliberately outside the core submission scope.
