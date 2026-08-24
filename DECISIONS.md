# Decisions

## Project

**The Reminder That Reaches**  
Brite Spark 2026 — Problem 07

## Why this document exists

This file records the important decisions made during development, what we observed in the supplied data, how the surprise requirement changed the design, and what we intentionally left out.

---

## 1. Inspect the supplied data before building

### Decision

Profile the appointment and contact files before designing the reminder logic.

### Why

The data contains missing values, opt-outs, shared contact points, multiple appointments, and multiple languages. We did not want to build the system around assumptions that were not true in the data.

---

## 2. Do not fabricate missing contact information

### Decision

Do not randomly fill missing phone numbers or emails. Do not use ML to invent contact details.

### Why

A fabricated contact value is not evidence that it belongs to the resident. Missing information is therefore handled explicitly by the contact policy.

### Result

Residents with no usable contact method remain in the system and receive an auditable no-contact decision.

---

## 3. Data findings

The supplied data contains:

- 940 appointments
- 620 contact records
- 498 residents with appointments
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

The first inspection looked for `YES`, while the supplied data actually uses `Y/N`.

### Decision

Interpret:

```text
Y = opted out
N = not opted out
```

### Final counts

- SMS opt-out: 63
- Voice opt-out: 49
- Email opt-out: 40
- All-three opt-outs: 11

The inspection was corrected and rerun against the original data. The source files were not modified.

---

## 5. Centralize contact safety

### Decision

Use a central `ContactPolicy` for:

- quiet hours
- opt-outs
- usable contact methods
- rolling 2-in-7 enforcement

### Why

The supplied mock channels do not enforce these rules. A central policy makes the safety logic easier to test and harder to bypass.

---

## 6. Treat the surprise requirement as a core architectural rule

### Decision

When the surprise requirement introduced a maximum of two contacts in seven days, we integrated it into the main contact decision flow instead of adding a final after-the-fact check.

### Result

Every actual outbound attempt is checked against the resident's current rolling allowance.

---

## 7. Persistent per-resident 2-in-7 ledger

### Decision

Keep a structured outbound contact history.

Each attempt records:

- resident ID
- appointment ID
- timestamp
- channel
- contact point
- status
- detail
- reach result

Rules:

- maximum 2 outbound contacts in any rolling 7-day window
- every actual outbound attempt counts
- failed attempts count
- channels count together
- appointments count together
- historical attempts count
- a third outbound attempt is blocked

---

## 8. Historical contact persistence

### Decision

Persist application contact history in:

```text
data/contact_history.jsonl
```

### Why

A future run needs to remember contacts from earlier runs for the retrospective rule.

The history file is runtime-generated and is intentionally not tracked in Git.

---

## 9. Do not use outbox.jsonl as the regulatory source of truth

### Decision

Use the structured application contact history for the regulatory ledger.

### Why

The supplied channel outbox does not identify the resident in the way needed for a per-resident regulatory decision. Our contact history does.

---

## 10. Define "reached" conservatively

### Decision

Use:

```text
voice + answered + human -> confirmed human reach
```

Do not treat SMS or email delivery as proof of human reach.

### Why

The system should report only what the available channel evidence supports.

---

## 11. Channel fallback

### Decision

Default channel order:

```text
SMS -> Voice -> Email
```

Before every outbound attempt:

1. Contact Policy is checked.
2. Shared-contact deduplication is checked.
3. The selected channel is executed.
4. The attempt is recorded.
5. If human reach is not confirmed, the next permitted channel is considered.
6. The regulatory limit is checked again before another attempt.

### Stopping conditions

Stop when:

- human reach is confirmed
- the regulatory limit blocks the next attempt
- no permitted channel remains
- contact data is unavailable

---

## 12. Language-specific reminder messages

### Decision

Use the resident's recorded `language` field to select the reminder template.

Supported languages in the supplied dataset:

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

Missing or unknown language codes use English fallback:

```text
Unknown / missing
       ↓
English template
```

### Why

The requirement is to select the correct language for the resident. We chose deterministic templates rather than a translation API or generative translation service.

This makes the behaviour:

- predictable
- testable
- auditable
- independent of external services

We deliberately support the languages present in the supplied dataset rather than claiming universal language coverage.

### Testing

Language support is covered by automated tests for:

- supported-language selection
- unknown-language fallback

---

## 13. Shared contact points

### Decision

Use run-scoped deduplication for shared phone numbers and email addresses.

### Why

The supplied data contains shared contact points, so the same contact point should not be unnecessarily reused during one processing run.

### Important distinction

Deduplication is separate from the regulatory limit.

The 2-in-7 count remains per resident.

---

## 14. Multiple appointments

### Decision

A resident's appointments share the same resident-level 2-in-7 contact allowance.

### Priority

When eligible appointments compete, process them deterministically:

1. earliest scheduled appointment
2. appointment ID as tie-breaker

### Why

This is repeatable, operationally understandable, and does not use protected characteristics.

---

## 15. Current-run metrics vs historical ledger

### Decision

Metrics for a run include only attempts created during that run.

Historical ledger totals are displayed separately.

### Why

Mixing previous contacts into current-run metrics makes the run's performance misleading.

---

## 16. Contact edge cases and treatment

| Edge case | What we do |
|---|---|
| Missing mobile | SMS is blocked; other permitted channels may be considered |
| Missing landline | Voice can use mobile when available |
| Missing email | Email is blocked |
| No contact information | No outbound contact; explicit reason recorded |
| SMS opt-out | SMS blocked by policy |
| Voice opt-out | Voice blocked by policy |
| Email opt-out | Email blocked by policy |
| All three opt-outs | No permitted channel |
| Shared mobile | Run-scoped deduplication |
| Shared email | Run-scoped deduplication |
| Multiple appointments | Same resident-level 2-in-7 allowance |
| Failed outbound attempt | Counts toward 2-in-7 |
| Historical attempt | Loaded and counts toward 2-in-7 |
| Unknown language | English fallback |
| Missing language | English fallback |

---

## 17. Surprise retrofit — what changed

Before the surprise requirement, the core system focused on:

- channel selection
- policy checks
- fallback
- reach classification
- audit

The surprise required us to add retrospective regulatory control.

### What changed

- Added persistent contact history.
- Added rolling per-resident 2-in-7 enforcement.
- Made every actual outbound attempt count.
- Loaded previous contacts before each new run.
- Added deterministic appointment priority.
- Added audit evidence for the regulatory decision.
- Separated current-run metrics from historical ledger totals.

### What we would improve with more time

- richer language templates
- production-grade persistence
- real provider adapters
- stronger operational reporting

---

## 18. What we rejected

We deliberately did not use:

- random completion of missing contact information
- ML-imputed contact details
- deletion of residents with incomplete contact information
- delivery-as-human-reach semantics
- WhatsApp integration in the core build
- Google Calendar integration in the core build
- a large frontend/dashboard
- real provider APIs
- generative message creation

---

## 19. Time-cut policy

The floor requirements were prioritized before optional enhancements.

Completed priority order:

1. data inspection and validation
2. models
3. rolling contact ledger
4. central contact policy
5. channel service
6. reminder orchestration
7. fallback/stopping
8. reach classification
9. language selection
10. persistent history
11. surprise 2-in-7 rule
12. shared-contact deduplication
13. metrics
14. tests
15. real-data validation
16. documentation and clean-clone verification

---

## 20. Test status

Final validated automated suite:

```text
75 tests
OK
```

The suite covers data loading, ledger behaviour, policy, channels, history, deduplication, language selection, orchestration, and metrics.

---

## 21. Final project scope

The solution is a deterministic reminder orchestration system around the supplied appointment/contact data and supplied mock channels.

It does not claim to be a production messaging platform.

It does not include appointment booking, rescheduling, cancellation, real external provider integration, or a large frontend.

---

## 22. AI usage

AI was used as a development support tool for planning, implementation assistance, debugging, testing, and documentation.

See `AI-USAGE.md` for the project usage record.
