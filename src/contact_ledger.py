from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

try:
    from .models import ContactAttempt
except ImportError:
    from models import ContactAttempt


@dataclass(frozen=True)
class ContactCheckResult:
    """Result of checking whether another contact is allowed."""

    allowed: bool
    recent_count: int
    remaining_contacts: int
    reason: str


class ContactLedger:
    """
    Stores outbound contact attempts and enforces the surprise rule:

    A resident may receive at most 2 outbound contacts
    in any rolling 7-day period.

    Important:
    - Count is per resident.
    - Every outbound attempt counts.
    - Failed attempts still count.
    - Contacts from different appointments count together.
    - Historical attempts can be loaded into the ledger.
    """

    DEFAULT_MAX_CONTACTS = 2
    DEFAULT_WINDOW_DAYS = 7

    def __init__(
        self,
        attempts: Iterable[ContactAttempt] | None = None,
        max_contacts: int = DEFAULT_MAX_CONTACTS,
        window_days: int = DEFAULT_WINDOW_DAYS,
    ) -> None:
        if max_contacts < 0:
            raise ValueError("max_contacts cannot be negative.")

        if window_days <= 0:
            raise ValueError("window_days must be greater than zero.")

        self.max_contacts = max_contacts
        self.window_days = window_days
        self._attempts: list[ContactAttempt] = []

        if attempts:
            self.add_attempts(attempts)

    def add_attempt(self, attempt: ContactAttempt) -> None:
        """Add one outbound attempt to the ledger."""
        self._attempts.append(attempt)

    def add_attempts(self, attempts: Iterable[ContactAttempt]) -> None:
        """Add multiple outbound attempts to the ledger."""
        for attempt in attempts:
            self.add_attempt(attempt)

    def all_attempts(self) -> list[ContactAttempt]:
        """Return a copy of all stored attempts."""
        return list(self._attempts)

    def get_recent_attempts(
        self,
        resident_id: str,
        reference_time: datetime,
    ) -> list[ContactAttempt]:
        """
        Return this resident's attempts inside the rolling 7-day window.

        Boundary rule:
        - exactly 7 days old is outside the window
        - future-dated attempts are ignored
        """
        window_start = reference_time - timedelta(days=self.window_days)

        return [
            attempt
            for attempt in self._attempts
            if (
                attempt.resident_id == resident_id
                and window_start < attempt.timestamp <= reference_time
            )
        ]

    def load_history(
        self,
        attempts: Iterable[ContactAttempt],
    ) -> None:
        """
        Load historical contact attempts into the ledger.

        Historical attempts count immediately toward the rolling
            7-day regulatory limit.
    """
        self.add_attempts(attempts)

    def count_recent_contacts(
        self,
        resident_id: str,
        reference_time: datetime,
    ) -> int:
        """Count this resident's outbound attempts in the rolling window."""
        return len(
            self.get_recent_attempts(
                resident_id=resident_id,
                reference_time=reference_time,
            )
        )

    def remaining_contacts(
        self,
        resident_id: str,
        reference_time: datetime,
    ) -> int:
        """Return how many contacts remain available."""
        count = self.count_recent_contacts(
            resident_id=resident_id,
            reference_time=reference_time,
        )

        return max(self.max_contacts - count, 0)

    def can_contact(
        self,
        resident_id: str,
        reference_time: datetime,
    ) -> ContactCheckResult:
        """
        Check whether another outbound contact is permitted.

        This method does not record a contact.

        The actual attempt must be recorded after the system
        makes the outbound attempt.
        """
        recent_count = self.count_recent_contacts(
            resident_id=resident_id,
            reference_time=reference_time,
        )

        remaining = max(self.max_contacts - recent_count, 0)

        if recent_count >= self.max_contacts:
            return ContactCheckResult(
                allowed=False,
                recent_count=recent_count,
                remaining_contacts=0,
                reason=(
                    f"Rolling {self.window_days}-day contact limit reached "
                    f"({recent_count}/{self.max_contacts})."
                ),
            )

        return ContactCheckResult(
            allowed=True,
            recent_count=recent_count,
            remaining_contacts=remaining,
            reason=(
                f"Contact allowed: {recent_count}/{self.max_contacts} "
                f"contacts used in rolling {self.window_days}-day window."
            ),
        )

    def record_attempt_and_check(
        self,
        attempt: ContactAttempt,
    ) -> ContactCheckResult:
        """
        Record an outbound attempt and return the resident's
        contact status immediately after that attempt.

        This is useful because every attempt counts, including failures.
        """
        self.add_attempt(attempt)

        return self.can_contact(
            resident_id=attempt.resident_id,
            reference_time=attempt.timestamp,
        )

    def resident_attempt_history(
        self,
        resident_id: str,
    ) -> list[ContactAttempt]:
        """Return all historical attempts for a resident."""
        return [
            attempt
            for attempt in self._attempts
            if attempt.resident_id == resident_id
        ]

    def clear(self) -> None:
        """Clear all attempts. Mainly useful for controlled tests."""
        self._attempts.clear()