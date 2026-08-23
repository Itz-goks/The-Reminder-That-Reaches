from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Sequence

from .contact_policy import ContactPolicy
from .models import Appointment, ContactAttempt, Resident


@dataclass(frozen=True)
class ReminderResult:
    """The auditable result of considering one appointment for a reminder."""

    appointment_id: str
    resident_id: str
    attempted: bool
    channel: str | None
    reason: str


class ReminderOrchestrator:
    """Create safe, deterministic reminder attempts for upcoming appointments."""

    DEFAULT_REMINDER_WINDOW = timedelta(days=1)
    DEFAULT_CHANNEL_ORDER = ("sms", "voice", "email")

    def __init__(
        self,
        policy: ContactPolicy,
        reminder_window: timedelta = DEFAULT_REMINDER_WINDOW,
        channel_order: Sequence[str] = DEFAULT_CHANNEL_ORDER,
    ) -> None:
        if reminder_window <= timedelta(0):
            raise ValueError("reminder_window must be greater than zero.")
        if not channel_order:
            raise ValueError("channel_order cannot be empty.")

        self.policy = policy
        self.reminder_window = reminder_window
        self.channel_order = tuple(channel.lower().strip() for channel in channel_order)

    def appointment_needs_reminder(
        self,
        appointment: Appointment,
        current_time: datetime,
    ) -> bool:
        """Return whether a booked appointment falls in the reminder window."""
        return (
            appointment.status.lower() == "booked"
            and current_time < appointment.scheduled_at <= current_time + self.reminder_window
        )

    def process(
        self,
        appointments: Iterable[Appointment],
        residents: Iterable[Resident],
        current_time: datetime,
    ) -> list[ReminderResult]:
        """
        Consider upcoming appointments and record exactly one permitted attempt each.

        The policy remains the sole authority for quiet hours, opt-outs, contact
        availability, and the rolling contact limit.
        """
        residents_by_id = {resident.resident_id: resident for resident in residents}
        upcoming = sorted(
            (
                appointment
                for appointment in appointments
                if self.appointment_needs_reminder(appointment, current_time)
            ),
            key=lambda appointment: (appointment.scheduled_at, appointment.appointment_id),
        )

        return [
            self._process_appointment(appointment, residents_by_id, current_time)
            for appointment in upcoming
        ]

    def _process_appointment(
        self,
        appointment: Appointment,
        residents_by_id: dict[str, Resident],
        current_time: datetime,
    ) -> ReminderResult:
        resident = residents_by_id.get(appointment.resident_id)
        if resident is None:
            return ReminderResult(
                appointment_id=appointment.appointment_id,
                resident_id=appointment.resident_id,
                attempted=False,
                channel=None,
                reason="No resident record found for appointment.",
            )

        rejected_reasons = []
        for channel in self.channel_order:
            decision = self.policy.evaluate(resident, channel, current_time)
            if not decision.allowed:
                rejected_reasons.append(f"{channel}: {decision.reason}")
                continue

            attempt = ContactAttempt(
                resident_id=resident.resident_id,
                appointment_id=appointment.appointment_id,
                timestamp=current_time,
                channel=channel,
                contact_point=self._contact_point(resident, channel),
                status="attempted",
                detail="permitted_by_contact_policy",
                reached=False,
            )
            self.policy.ledger.add_attempt(attempt)
            return ReminderResult(
                appointment_id=appointment.appointment_id,
                resident_id=resident.resident_id,
                attempted=True,
                channel=channel,
                reason=decision.reason,
            )

        return ReminderResult(
            appointment_id=appointment.appointment_id,
            resident_id=resident.resident_id,
            attempted=False,
            channel=None,
            reason="No permitted channel. " + "; ".join(rejected_reasons),
        )

    @staticmethod
    def _contact_point(resident: Resident, channel: str) -> str:
        """Select the concrete contact point for a policy-approved channel."""
        if channel == "sms":
            return resident.mobile or ""
        if channel == "voice":
            return resident.mobile or resident.landline or ""
        if channel == "email":
            return resident.email or ""
        return ""
