from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Sequence

from .channel_service import ChannelService
from .contact_dedup import ContactDeduplicator
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
    - prevent duplicate use of the same contact point in one run
    - execute the permitted channel through ChannelService
    - interpret the result through ChannelService
    - perform controlled fallback when the resident is not reached
    - re-check policy before every fallback attempt
    - generate a reminder using the resident's recorded language
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
            raise ValueError(
                "reminder_window must be greater than zero."
            )

        if not channel_order:
            raise ValueError(
                "channel_order cannot be empty."
            )

        self.policy = policy

        self.channel_service = (
            channel_service
            if channel_service is not None
            else ChannelService(policy.ledger)
        )

        self.reminder_window = reminder_window

        self.channel_order = tuple(
            channel.lower().strip()
            for channel in channel_order
        )

        self.deduplicator = ContactDeduplicator()

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

        # Deduplication applies only to this processing run.
        # The regulatory 2-in-7 ledger remains persistent separately.
        self.deduplicator.clear()

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
                appointment=appointment,
                residents_by_id=residents_by_id,
                current_time=current_time,
            )
            for appointment in upcoming
        ]

    def _process_appointment(
        self,
        appointment: Appointment,
        residents_by_id: dict[str, Resident],
        current_time: datetime,
    ) -> ReminderResult:
        resident = residents_by_id.get(
            appointment.resident_id
        )

        if resident is None:
            return ReminderResult(
                appointment_id=appointment.appointment_id,
                resident_id=appointment.resident_id,
                attempted=False,
                channel=None,
                reason=(
                    "No resident record found for appointment."
                ),
            )

        rejected_reasons: list[str] = []
        attempts_made = 0
        last_channel: str | None = None

        for channel in self.channel_order:
            # -------------------------------------------------
            # 1. Central contact policy
            # -------------------------------------------------
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

            # -------------------------------------------------
            # 2. Resolve concrete contact point
            # -------------------------------------------------
            contact_point = (
                self.channel_service.get_contact_point(
                    resident=resident,
                    channel=channel,
                )
            )

            # -------------------------------------------------
            # 3. Protect against duplicate contact points
            # -------------------------------------------------
            dedup_decision = self.deduplicator.check(
                channel=channel,
                contact_point=contact_point,
            )

            if not dedup_decision.allowed:
                rejected_reasons.append(
                    f"{channel}: {dedup_decision.reason}"
                )
                continue

            # -------------------------------------------------
            # 4. Actual outbound attempt
            # -------------------------------------------------
            attempts_made += 1
            last_channel = channel

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

            # Record the contact point only after an actual
            # outbound attempt has happened.
            self.deduplicator.record(
                channel=channel,
                contact_point=contact_point,
            )

            # -------------------------------------------------
            # 5. Confirmed human reach -> STOP
            # -------------------------------------------------
            if channel_result.reached:
                return ReminderResult(
                    appointment_id=appointment.appointment_id,
                    resident_id=appointment.resident_id,
                    attempted=True,
                    channel=channel,
                    reason=(
                        f"Resident reached via {channel}: "
                        f"{channel_result.status}"
                        + (
                            f" / {channel_result.detail}"
                            if channel_result.detail
                            else ""
                        )
                    ),
                    reached=True,
                    attempts_made=attempts_made,
                )

            # -------------------------------------------------
            # 6. Not reached -> controlled fallback
            # -------------------------------------------------
            rejected_reasons.append(
                (
                    f"{channel}: not reached "
                    f"({channel_result.status}"
                    + (
                        f" / {channel_result.detail}"
                        if channel_result.detail
                        else ""
                    )
                    + ")"
                )
            )

            # On the next iteration ContactPolicy is checked
            # again, including the rolling 2-in-7 limit.

        # -----------------------------------------------------
        # No channel resulted in confirmed human reach
        # -----------------------------------------------------
        return ReminderResult(
            appointment_id=appointment.appointment_id,
            resident_id=appointment.resident_id,
            attempted=attempts_made > 0,
            channel=last_channel,
            reason=self._final_reason(
                rejected_reasons
            ),
            reached=False,
            attempts_made=attempts_made,
        )

    @staticmethod
    def _build_message(
        resident: Resident,
        appointment: Appointment,
    ) -> str:
        """
        Build a reminder message using the resident's language.

        Supported language codes in the supplied data:
        en, es, ru, so, vi, zh

        Missing or unknown language codes fall back to English.
        """

        language = (
            resident.language or "en"
        ).strip().lower()

        templates = {
            "en": (
                "Reminder: {name} has an appointment on "
                "{date} for {service} at {location}."
            ),
            "es": (
                "Recordatorio: {name} tiene una cita el "
                "{date} para {service} en {location}."
            ),
            "ru": (
                "Напоминание: у {name} назначена встреча "
                "{date} по услуге «{service}» в {location}."
            ),
            "so": (
                "Xusuusin: {name} wuxuu leeyahay ballan "
                "{date} oo ah {service} goobta {location}."
            ),
            "vi": (
                "Nhắc nhở: {name} có lịch hẹn vào "
                "{date} cho dịch vụ {service} tại {location}."
            ),
            "zh": (
                "提醒：{name} 于 {date} 在 {location} "
                "有一个 {service} 预约。"
            ),
        }

        template = templates.get(
            language,
            templates["en"],
        )

        return template.format(
            name=resident.name,
            date=appointment.scheduled_at.isoformat(),
            service=appointment.service_type,
            location=appointment.location,
        )

    @staticmethod
    def _final_reason(
        rejected_reasons: list[str],
    ) -> str:
        if not rejected_reasons:
            return "No permitted channel."

        return (
            "Reminder processing completed. "
            + "; ".join(rejected_reasons)
        )