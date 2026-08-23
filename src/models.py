from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Resident:
    """Resident/contact information loaded from contacts.csv."""

    resident_id: str
    name: str
    mobile: Optional[str]
    landline: Optional[str]
    email: Optional[str]
    language: str
    sms_optout: bool = False
    voice_optout: bool = False
    email_optout: bool = False
    number_last_verified: Optional[datetime] = None

    def has_mobile(self) -> bool:
        return bool(self.mobile and self.mobile.strip())

    def has_landline(self) -> bool:
        return bool(self.landline and self.landline.strip())

    def has_email(self) -> bool:
        return bool(self.email and self.email.strip())

    def has_any_contact(self) -> bool:
        return self.has_mobile() or self.has_landline() or self.has_email()


@dataclass(frozen=True)
class Appointment:
    """Appointment information loaded from appointments.csv."""

    appointment_id: str
    resident_id: str
    scheduled_at: datetime
    location: str
    service_type: str
    status: str


@dataclass(frozen=True)
class ContactAttempt:
    """
    A single outbound contact attempt.

    Every outbound attempt counts toward the surprise
    2-contacts-in-7-days rule, regardless of its result.
    """

    resident_id: str
    appointment_id: str
    timestamp: datetime
    channel: str
    contact_point: str
    status: str
    detail: str
    reached: bool = False

    def is_in_window(
        self,
        reference_time: datetime,
        window_days: int = 7,
    ) -> bool:
        """Return True when this attempt falls inside the rolling window."""
        age_seconds = (reference_time - self.timestamp).total_seconds()

        return 0 <= age_seconds < window_days * 24 * 60 * 60