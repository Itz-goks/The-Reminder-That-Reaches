from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import unittest

from src.channel_service import ChannelResult
from src.contact_ledger import ContactLedger
from src.contact_policy import ContactPolicy
from src.models import Appointment, Resident
from src.reminder_orchestrator import ReminderOrchestrator


@dataclass
class FakeChannelService:
    """
    Test double for ChannelService.

    The real ChannelService is already tested separately.
    These tests focus on orchestrator behaviour.
    """

    outcomes: list[ChannelResult]

    def __post_init__(self) -> None:
        self.calls: list[dict] = []

    def send(
        self,
        resident: Resident,
        appointment_id: str,
        channel: str,
        body: str,
        at: datetime,
        attempt_number: int = 1,
    ) -> ChannelResult:
        self.calls.append(
            {
                "resident_id": resident.resident_id,
                "appointment_id": appointment_id,
                "channel": channel,
                "body": body,
                "at": at,
                "attempt_number": attempt_number,
            }
        )

        result = self.outcomes.pop(0)

        # The real ChannelService records attempts in the ledger.
        # This fake must do the same so orchestrator tests reproduce
        # the real system's state transition.
        raise RuntimeError(
            "Use FakeChannelServiceWithLedger in these tests."
        )


class FakeChannelServiceWithLedger:
    def __init__(
        self,
        ledger: ContactLedger,
        outcomes: list[dict],
    ) -> None:
        self.ledger = ledger
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []


    def get_contact_point(
        self,
        resident: Resident,
        channel: str,
    ) -> str:
        """Mirror the real ChannelService contact-point selection."""

        channel = channel.lower().strip()

        if channel == "sms":
            return resident.mobile or ""

        if channel == "email":
            return resident.email or ""

        if channel == "voice":
            return resident.mobile or resident.landline or ""

        raise ValueError(
            f"Unsupported channel: {channel}"
    )

    def send(
        self,
        resident: Resident,
        appointment_id: str,
        channel: str,
        body: str,
        at: datetime,
        attempt_number: int = 1,
    ) -> ChannelResult:
        self.calls.append(
            {
                "resident_id": resident.resident_id,
                "appointment_id": appointment_id,
                "channel": channel,
                "body": body,
                "at": at,
                "attempt_number": attempt_number,
            }
        )

        outcome = self.outcomes.pop(0)

        from src.models import ContactAttempt

        attempt = ContactAttempt(
            resident_id=resident.resident_id,
            appointment_id=appointment_id,
            timestamp=at,
            channel=channel,
            contact_point=(
                resident.mobile
                if channel == "sms"
                else resident.email
                if channel == "email"
                else resident.mobile or resident.landline or ""
            ),
            status=outcome["status"],
            detail=outcome.get("detail", ""),
            reached=outcome.get("reached", False),
        )

        self.ledger.add_attempt(attempt)

        return ChannelResult(
            resident_id=resident.resident_id,
            appointment_id=appointment_id,
            channel=channel,
            contact_point=attempt.contact_point,
            status=attempt.status,
            detail=attempt.detail,
            reached=attempt.reached,
            attempt_number=attempt_number,
            timestamp=at,
        )


class TestReminderOrchestrator(unittest.TestCase):
    def setUp(self) -> None:
        self.current_time = datetime(2026, 3, 10, 10, 0)

        self.resident = Resident(
            resident_id="RS-4000",
            name="Test Resident",
            mobile="555-123-4567",
            landline="555-765-4321",
            email="test@example.com",
            language="en",
        )

        self.appointment = Appointment(
            appointment_id="AP-001",
            resident_id="RS-4000",
            scheduled_at=self.current_time + timedelta(hours=2),
            location="Calder Central",
            service_type="Benefits review",
            status="Booked",
        )

    def build_orchestrator(
        self,
        outcomes: list[dict],
        *,
        ledger: ContactLedger | None = None,
        channel_order=("sms", "voice", "email"),
    ):
        ledger = ledger or ContactLedger()
        policy = ContactPolicy(ledger=ledger)

        channel_service = FakeChannelServiceWithLedger(
            ledger=ledger,
            outcomes=outcomes,
        )

        orchestrator = ReminderOrchestrator(
            policy=policy,
            channel_service=channel_service,
            reminder_window=timedelta(days=1),
            channel_order=channel_order,
        )

        return orchestrator, ledger, channel_service

    def test_eligible_reminder_is_actually_executed(self) -> None:
        orchestrator, ledger, channel_service = self.build_orchestrator(
            [
                {
                    "status": "delivered",
                    "detail": "",
                    "reached": False,
                },
                {
                    "status": "answered",
                    "detail": "human",
                    "reached": True,
                },
            ]
        )

        results = orchestrator.process(
            [self.appointment],
            [self.resident],
            self.current_time,
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].attempted)

        # SMS did not establish human reach, so Voice was attempted.
        self.assertEqual(
            [call["channel"] for call in channel_service.calls],
            ["sms", "voice"],
        )

        self.assertTrue(results[0].reached)
        self.assertEqual(results[0].attempts_made, 2)

        self.assertEqual(
            len(ledger.resident_attempt_history("RS-4000")),
            2,
        )

    def test_voice_human_stops_fallback(self) -> None:
        orchestrator, ledger, channel_service = self.build_orchestrator(
            [
                {
                    "status": "answered",
                    "detail": "human",
                    "reached": True,
                },
            ]
        )

        results = orchestrator.process(
            [self.appointment],
            [self.resident],
            self.current_time,
        )

        self.assertTrue(results[0].reached)
        self.assertEqual(results[0].channel, "sms")

        # SMS is first in the default order, so this test only proves
        # that a confirmed reach stops immediately.
        self.assertEqual(len(channel_service.calls), 1)
        self.assertEqual(len(
            ledger.resident_attempt_history("RS-4000")
        ), 1)

    def test_sms_failure_falls_back_to_voice(self) -> None:
        orchestrator, ledger, channel_service = self.build_orchestrator(
            [
                {
                    "status": "failed",
                    "detail": "carrier_rejected",
                    "reached": False,
                },
                {
                    "status": "answered",
                    "detail": "human",
                    "reached": True,
                },
            ]
        )

        results = orchestrator.process(
            [self.appointment],
            [self.resident],
            self.current_time,
        )

        self.assertTrue(results[0].reached)
        self.assertEqual(
            [call["channel"] for call in channel_service.calls],
            ["sms", "voice"],
        )

        history = ledger.resident_attempt_history("RS-4000")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].status, "failed")
        self.assertEqual(history[1].reached, True)

    def test_voicemail_does_not_count_as_reached(self) -> None:
        orchestrator, ledger, channel_service = self.build_orchestrator(
            [
                {
                    "status": "failed",
                    "detail": "carrier_rejected",
                    "reached": False,
                },
                {
                    "status": "answered",
                    "detail": "voicemail_left",
                    "reached": False,
                },
            ]
        )

        results = orchestrator.process(
            [self.appointment],
            [self.resident],
            self.current_time,
        )

        self.assertFalse(results[0].reached)
        self.assertEqual(results[0].attempts_made, 2)

        self.assertEqual(
            [call["channel"] for call in channel_service.calls],
            ["sms", "voice"],
        )

        self.assertEqual(
            len(ledger.resident_attempt_history("RS-4000")),
            2,
        )

    def test_two_failed_attempts_block_third_attempt(self) -> None:
        orchestrator, ledger, channel_service = self.build_orchestrator(
            [
                {
                    "status": "failed",
                    "detail": "carrier_rejected",
                    "reached": False,
                },
                {
                    "status": "no_answer",
                    "detail": "",
                    "reached": False,
                },
                {
                    "status": "delivered",
                    "detail": "",
                    "reached": False,
                },
            ]
        )

        results = orchestrator.process(
            [self.appointment],
            [self.resident],
            self.current_time,
        )

        self.assertFalse(results[0].reached)
        self.assertEqual(results[0].attempts_made, 2)

        # The 3rd channel must never be called because the second
        # outbound attempt consumed the resident's 2-in-7 allowance.
        self.assertEqual(
            [call["channel"] for call in channel_service.calls],
            ["sms", "voice"],
        )

        self.assertEqual(
            len(ledger.resident_attempt_history("RS-4000")),
            2,
        )

        self.assertIn(
            "contact limit",
            results[0].reason.lower(),
        )

    def test_existing_recent_contact_can_block_before_sending(self) -> None:
        ledger = ContactLedger()

        from src.models import ContactAttempt

        ledger.add_attempt(
            ContactAttempt(
                resident_id="RS-4000",
                appointment_id="AP-OLD-1",
                timestamp=self.current_time - timedelta(days=2),
                channel="sms",
                contact_point="555-123-4567",
                status="failed",
                detail="carrier_rejected",
                reached=False,
            )
        )

        ledger.add_attempt(
            ContactAttempt(
                resident_id="RS-4000",
                appointment_id="AP-OLD-2",
                timestamp=self.current_time - timedelta(days=1),
                channel="email",
                contact_point="test@example.com",
                status="failed",
                detail="soft_bounce",
                reached=False,
            )
        )

        orchestrator, ledger, channel_service = self.build_orchestrator(
            [],
            ledger=ledger,
        )

        results = orchestrator.process(
            [self.appointment],
            [self.resident],
            self.current_time,
        )

        self.assertFalse(results[0].attempted)
        self.assertEqual(len(channel_service.calls), 0)

        # Existing history remains exactly two attempts.
        self.assertEqual(
            len(ledger.resident_attempt_history("RS-4000")),
            2,
        )

    def test_quiet_hours_block_without_outbound_attempt(self) -> None:
        ledger = ContactLedger()
        policy = ContactPolicy(ledger=ledger)

        channel_service = FakeChannelServiceWithLedger(
            ledger=ledger,
            outcomes=[],
    )

        orchestrator = ReminderOrchestrator(
            policy=policy,
            channel_service=channel_service,
    )

        quiet_time = datetime(2026, 3, 9, 22, 0)

        appointment = Appointment(
            appointment_id="AP-NIGHT",
            resident_id="RS-4000",
            scheduled_at=quiet_time + timedelta(hours=2),
            location="Calder Central",
            service_type="Benefits review",
            status="Booked",
    )

        results = orchestrator.process(
            [appointment],
            [self.resident],
            quiet_time,
    )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].attempted)
        self.assertEqual(channel_service.calls, [])
        self.assertEqual(
            ledger.resident_attempt_history("RS-4000"),
            [],
        )

    def test_not_upcoming_appointment_is_ignored(self) -> None:
        orchestrator, _, channel_service = self.build_orchestrator([])

        past_appointment = Appointment(
            appointment_id="AP-PAST",
            resident_id="RS-4000",
            scheduled_at=self.current_time - timedelta(hours=1),
            location="Calder Central",
            service_type="Benefits review",
            status="Booked",
        )

        results = orchestrator.process(
            [past_appointment],
            [self.resident],
            self.current_time,
        )

        self.assertEqual(results, [])
        self.assertEqual(channel_service.calls, [])

    def test_non_booked_appointment_is_ignored(self) -> None:
        orchestrator, _, channel_service = self.build_orchestrator([])

        appointment = Appointment(
            appointment_id="AP-CLOSED",
            resident_id="RS-4000",
            scheduled_at=self.current_time + timedelta(hours=2),
            location="Calder Central",
            service_type="Benefits review",
            status="Cancelled",
        )

        results = orchestrator.process(
            [appointment],
            [self.resident],
            self.current_time,
        )

        self.assertEqual(results, [])
        self.assertEqual(channel_service.calls, [])

    def test_multiple_appointments_are_processed_in_priority_order(self) -> None:
        second_appointment = Appointment(
            appointment_id="AP-002",
            resident_id="RS-4000",
            scheduled_at=self.current_time + timedelta(hours=4),
            location="Northgate",
            service_type="Housing options",
            status="Booked",
        )

        orchestrator, ledger, channel_service = self.build_orchestrator(
            [
                {
                    "status": "answered",
                    "detail": "human",
                    "reached": True,
                },
                {
                    "status": "answered",
                    "detail": "human",
                    "reached": True,
                },
            ]
        )

        results = orchestrator.process(
            [second_appointment, self.appointment],
            [self.resident],
            self.current_time,
        )

        self.assertEqual(
            [result.appointment_id for result in results],
            ["AP-001", "AP-002"],
        )

        self.assertEqual(
            [call["appointment_id"] for call in channel_service.calls],
            ["AP-001", "AP-002"],
        )

        self.assertEqual(
            len(ledger.resident_attempt_history("RS-4000")),
            2,
        )


if __name__ == "__main__":
    unittest.main()