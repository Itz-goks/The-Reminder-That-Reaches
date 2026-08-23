from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import Iterable

from .models import ContactAttempt
from .reminder_orchestrator import ReminderResult


@dataclass(frozen=True)
class ReminderMetrics:
    processed: int
    attempted: int
    reached: int
    not_reached: int
    blocked: int
    channel_counts: dict[str, int]
    block_reasons: dict[str, int]
    total_contact_attempts: int


def build_metrics(
    results: Iterable[ReminderResult],
    attempts: Iterable[ContactAttempt],
) -> ReminderMetrics:
    results = list(results)
    attempts = list(attempts)

    channel_counts = Counter(
        attempt.channel
        for attempt in attempts
    )

    block_reasons = Counter()

    for result in results:
        if result.attempted:
            continue

        reason = result.reason.lower()

        if "rolling 7-day contact limit" in reason:
            block_reasons["2-in-7 limit"] += 1
        elif "opted out" in reason:
            block_reasons["opt-out"] += 1
        elif "quiet hours" in reason:
            block_reasons["quiet hours"] += 1
        elif "no usable" in reason:
            block_reasons["no usable contact"] += 1
        elif "duplicate contact" in reason:
            block_reasons["duplicate contact"] += 1
        else:
            block_reasons["other"] += 1

    attempted = sum(
        result.attempted
        for result in results
    )

    reached = sum(
        result.reached
        for result in results
    )

    return ReminderMetrics(
        processed=len(results),
        attempted=attempted,
        reached=reached,
        not_reached=sum(
            result.attempted and not result.reached
            for result in results
        ),
        blocked=sum(
            not result.attempted
            for result in results
        ),
        channel_counts=dict(channel_counts),
        block_reasons=dict(block_reasons),
        total_contact_attempts=len(attempts),
    )