from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Sequence

from .channel_service import ChannelResult, ChannelService
from .contact_policy import ContactPolicy
from .models import Appointment, Resident


@dataclass(frozen=True)
class ReminderResult:
    """Auditable result of processing one appointment."""

    appointment_id: str
    resident_id: str
    attempted: bool
    channel: str | None
    reason: str
    reached: bool = False
    attempts_made: int = 0


class ReminderOrchestrator:
    """
    Coordinates reminder decisions and actual channel execution.

    Responsibilities:
    - identify eligible appointments
    - ask ContactPolicy whether a channel is permitted
    - execute the permitted channel through ChannelService
    - interpret the result through ChannelService
    - perform controlled fallback when the resident was not reached
    - re-check policy before every fallback attempt
    """

    DEFAULT_REMINDER_WINDOW = timedelta(days=1)
    DEFAULT_CHANNEL_ORDER = ("sms", "voice", "email")

    def __init__(
        self,
        policy: ContactPolicy,
        channel_service: ChannelService | None = None,
        reminder_window: timedelta = DEFAULT_REMINDER_WINDOW,
        channel_order: Sequence[str] = DEFAULT_CHANNEL_ORDER,
    ) -> None:
        if reminder_window <= timedelta(0):
            raise ValueError("reminder_window must be greater than zero.")

        if not channel_order:
            raise ValueError("channel_order cannot be empty.")

        self.policy = policy
        self.channel_service = channel_service or ChannelService(policy.ledger)
        self.reminder_window = reminder_window
        self.channel_order = tuple(
            channel.lower().strip()
            for channel in channel_order
        )

    def appointment_needs_reminder(
        self,
        appointment: Appointment,
        current_time: datetime,
    ) -> bool:
        """Return whether a booked appointment falls in the reminder window."""
        return (
            appointment.status.lower() == "booked"
            and current_time < appointment.scheduled_at
            <= current_time + self.reminder_window
        )

    def process(
        self,
        appointments: Iterable[Appointment],
        residents: Iterable[Resident],
        current_time: datetime,
    ) -> list[ReminderResult]:
        """
        Process all eligible appointments in deterministic priority order.

        Priority:
        1. earliest appointment time
        2. appointment ID
        """
        residents_by_id = {
            resident.resident_id: resident
            for resident in residents
        }

        upcoming = sorted(
            (
                appointment
                for appointment in appointments
                if self.appointment_needs_reminder(
                    appointment,
                    current_time,
                )
            ),
            key=lambda appointment: (
                appointment.scheduled_at,
                appointment.appointment_id,
            ),
        )

        return [
            self._process_appointment(
                appointment,
                residents_by_id,
                current_time,
            )
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

        rejected_reasons: list[str] = []
        attempts_made = 0

        for channel in self.channel_order:
            decision = self.policy.evaluate(
                resident,
                channel,
                current_time,
            )

            if not decision.allowed:
                rejected_reasons.append(
                    f"{channel}: {decision.reason}"
                )
                continue

            attempts_made += 1

            channel_result = self.channel_service.send(
                resident=resident,
                appointment_id=appointment.appointment_id,
                channel=channel,
                body=self._build_message(
                    resident=resident,
                    appointment=appointment,
                ),
                at=current_time,
                attempt_number=attempts_made,
            )

            if channel_result.reached:
                return ReminderResult(
                    appointment_id=appointment.appointment_id,
                    resident_id=appointment.resident_id,
                    attempted=True,
                    channel=channel,
                    reason=(
                        f"Resident reached via {channel}: "
                        f"{channel_result.status}"
                        f"{' / ' + channel_result.detail if channel_result.detail else ''}"
                    ),
                    reached=True,
                    attempts_made=attempts_made,
                )

            rejected_reasons.append(
                (
                    f"{channel}: not reached "
                    f"({channel_result.status}"
                    f"{' / ' + channel_result.detail if channel_result.detail else ''})"
                )
            )

            # The channel attempt has already been recorded by ChannelService.
            # On the next loop iteration, ContactPolicy checks the updated
            # rolling 2-in-7 ledger again before allowing another outbound attempt.

        return ReminderResult(
            appointment_id=appointment.appointment_id,
            resident_id=appointment.resident_id,
            attempted=attempts_made > 0,
            channel=None if attempts_made == 0 else self._last_attempt_channel(
                resident,
                appointment,
                current_time,
            ),
            reason=self._final_reason(rejected_reasons),
            reached=False,
            attempts_made=attempts_made,
        )

    @staticmethod
    def _build_message(
        resident: Resident,
        appointment: Appointment,
    ) -> str:
        """
        Build a deterministic reminder body.

        The message is intentionally simple at this stage.
        Language-specific templating will be separated into its own
        policy/template layer later.
        """
        return (
            f"Reminder: {resident.name} has an appointment on "
            f"{appointment.scheduled_at.isoformat()} for "
            f"{appointment.service_type} at {appointment.location}."
        )

    def _last_attempt_channel(
        self,
        resident: Resident,
        appointment: Appointment,
        current_time: datetime,
    ) -> str | None:
        """Return the last channel used for this appointment."""
        attempts = [
            attempt
            for attempt in self.policy.ledger.all_attempts()
            if (
                attempt.resident_id == resident.resident_id
                and attempt.appointment_id == appointment.appointment_id
                and attempt.timestamp == current_time
            )
        ]

        if not attempts:
            return None

        return attempts[-1].channel

    @staticmethod
    def _final_reason(rejected_reasons: list[str]) -> str:
        if not rejected_reasons:
            return "No permitted channel."

        return "Reminder processing completed. " + "; ".join(
            rejected_reasons
        )