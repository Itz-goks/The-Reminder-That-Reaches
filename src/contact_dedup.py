from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeduplicationDecision:
    allowed: bool
    reason: str


class ContactDeduplicator:
    """
    Prevents duplicate outbound contact to the same contact point
    during one reminder-processing run.

    Important:
    - Deduplication is scoped to the current run.
    - Regulatory 2-in-7 counting remains per resident.
    - The deduplicator does not replace the contact ledger.
    """

    def __init__(self) -> None:
        self._sent: set[tuple[str, str]] = set()

    @staticmethod
    def _normalize_contact(
        channel: str,
        contact_point: str,
    ) -> str:
        channel = channel.strip().lower()
        contact_point = contact_point.strip().lower()

        if channel in {"sms", "voice"}:
            # Remove common formatting characters for stable comparison.
            return (
                contact_point
                .replace(" ", "")
                .replace("-", "")
                .replace("(", "")
                .replace(")", "")
                .replace("+", "")
            )

        if channel == "email":
            return contact_point

        return contact_point

    def check(
        self,
        channel: str,
        contact_point: str,
    ) -> DeduplicationDecision:
        """Check whether this contact point has already been used."""
        key = (
            channel.strip().lower(),
            self._normalize_contact(
                channel,
                contact_point,
            ),
        )

        if key in self._sent:
            return DeduplicationDecision(
                allowed=False,
                reason=(
                    "Duplicate contact point already used "
                    "for this channel in the current run."
                ),
            )

        return DeduplicationDecision(
            allowed=True,
            reason="Contact point has not been used in this run.",
        )

    def record(
        self,
        channel: str,
        contact_point: str,
    ) -> None:
        """Record a successful outbound attempt against the run."""
        key = (
            channel.strip().lower(),
            self._normalize_contact(
                channel,
                contact_point,
            ),
        )

        self._sent.add(key)

    def clear(self) -> None:
        """Clear the current-run deduplication state."""
        self._sent.clear()