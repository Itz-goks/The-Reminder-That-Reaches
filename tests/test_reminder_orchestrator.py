from datetime import datetime, time, timedelta
import unittest

from src.contact_ledger import ContactLedger
from src.contact_policy import ContactPolicy
from src.models import Appointment, ContactAttempt, Resident
from src.reminder_orchestrator import ReminderOrchestrator


class TestReminderOrchestrator(unittest.TestCase):
    def setUp(self) -> None:
        self.current_time = datetime(2026, 3, 10, 10, 0)
        self.ledger = ContactLedger()
        self.policy = ContactPolicy(
            ledger=self.ledger,
            quiet_start=time(21, 0),
            quiet_end=time(8, 0),
        )
        self.orchestrator = ReminderOrchestrator(self.policy)
        self.resident = self.make_resident("RS-1")

    def make_resident(self, resident_id: str, **changes: object) -> Resident:
        values: dict[str, object] = {
            "resident_id": resident_id,
            "name": "Test Resident",
            "mobile": "555-111-2222",
            "landline": None,
            "email": "resident@example.com",
            "language": "en",
        }
        values.update(changes)
        return Resident(**values)  # type: ignore[arg-type]

    def make_appointment(self, appointment_id: str, resident_id: str) -> Appointment:
        return Appointment(
            appointment_id=appointment_id,
            resident_id=resident_id,
            scheduled_at=self.current_time + timedelta(hours=2),
            location="Central",
            service_type="Advice",
            status="Booked",
        )

    def add_previous_attempt(self, resident_id: str, hours_ago: int) -> None:
        self.ledger.add_attempt(
            ContactAttempt(
                resident_id=resident_id,
                appointment_id="AP-OLD",
                timestamp=self.current_time - timedelta(hours=hours_ago),
                channel="sms",
                contact_point="555-111-2222",
                status="failed",
                detail="test",
            )
        )

    def test_eligible_reminder_is_attempted_and_recorded(self) -> None:
        results = self.orchestrator.process(
            [self.make_appointment("AP-1", self.resident.resident_id)],
            [self.resident],
            self.current_time,
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].attempted)
        self.assertEqual(results[0].channel, "sms")
        attempts = self.ledger.all_attempts()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].appointment_id, "AP-1")
        self.assertEqual(attempts[0].status, "attempted")

    def test_quiet_hours_blocks_reminder_without_recording_attempt(self) -> None:
        quiet_time = datetime(2026, 3, 10, 22, 0)
        appointment = Appointment(
            appointment_id="AP-1",
            resident_id=self.resident.resident_id,
            scheduled_at=quiet_time + timedelta(hours=2),
            location="Central",
            service_type="Advice",
            status="Booked",
        )

        results = self.orchestrator.process(
            [appointment],
            [self.resident],
            quiet_time,
        )

        self.assertFalse(results[0].attempted)
        self.assertIn("quiet hours", results[0].reason.lower())
        self.assertEqual(self.ledger.all_attempts(), [])

    def test_opted_out_resident_is_blocked_without_recording_attempt(self) -> None:
        resident = self.make_resident(
            "RS-1",
            sms_optout=True,
            voice_optout=True,
            email_optout=True,
        )

        results = self.orchestrator.process(
            [self.make_appointment("AP-1", resident.resident_id)],
            [resident],
            self.current_time,
        )

        self.assertFalse(results[0].attempted)
        self.assertIn("opted out", results[0].reason.lower())
        self.assertEqual(self.ledger.all_attempts(), [])

    def test_unavailable_channels_are_rejected_by_existing_policy(self) -> None:
        resident = self.make_resident("RS-1", mobile=None, email=None)

        results = self.orchestrator.process(
            [self.make_appointment("AP-1", resident.resident_id)],
            [resident],
            self.current_time,
        )

        self.assertFalse(results[0].attempted)
        self.assertIn("no usable sms", results[0].reason.lower())
        self.assertEqual(self.ledger.all_attempts(), [])

    def test_contact_limit_blocks_reminder_without_a_duplicate_attempt(self) -> None:
        self.add_previous_attempt(self.resident.resident_id, hours_ago=48)
        self.add_previous_attempt(self.resident.resident_id, hours_ago=24)

        results = self.orchestrator.process(
            [self.make_appointment("AP-1", self.resident.resident_id)],
            [self.resident],
            self.current_time,
        )

        self.assertFalse(results[0].attempted)
        self.assertIn("contact limit", results[0].reason.lower())
        self.assertEqual(len(self.ledger.all_attempts()), 2)

    def test_multiple_appointments_and_residents_are_processed_in_priority_order(self) -> None:
        second_resident = self.make_resident("RS-2", mobile="555-333-4444")
        later = self.make_appointment("AP-LATER", self.resident.resident_id)
        earlier = Appointment(
            appointment_id="AP-EARLIER",
            resident_id=second_resident.resident_id,
            scheduled_at=self.current_time + timedelta(hours=1),
            location="Central",
            service_type="Advice",
            status="Booked",
        )

        results = self.orchestrator.process(
            [later, earlier],
            [self.resident, second_resident],
            self.current_time,
        )

        self.assertEqual([result.appointment_id for result in results], ["AP-EARLIER", "AP-LATER"])
        self.assertTrue(all(result.attempted for result in results))
        self.assertEqual(
            [attempt.resident_id for attempt in self.ledger.all_attempts()],
            ["RS-2", "RS-1"],
        )

    def test_third_competing_appointment_is_rejected_after_two_attempts(self) -> None:
        appointments = [
            Appointment(
                appointment_id=f"AP-{index}",
                resident_id=self.resident.resident_id,
                scheduled_at=self.current_time + timedelta(hours=index),
                location="Central",
                service_type="Advice",
                status="Booked",
            )
            for index in (1, 2, 3)
        ]

        results = self.orchestrator.process(appointments, [self.resident], self.current_time)

        self.assertEqual([result.attempted for result in results], [True, True, False])
        self.assertEqual(len(self.ledger.all_attempts()), 2)

    def test_non_upcoming_or_non_booked_appointments_are_not_considered(self) -> None:
        past = Appointment(
            appointment_id="AP-PAST",
            resident_id=self.resident.resident_id,
            scheduled_at=self.current_time - timedelta(minutes=1),
            location="Central",
            service_type="Advice",
            status="Booked",
        )
        cancelled = Appointment(
            appointment_id="AP-CANCELLED",
            resident_id=self.resident.resident_id,
            scheduled_at=self.current_time + timedelta(hours=1),
            location="Central",
            service_type="Advice",
            status="Cancelled",
        )

        results = self.orchestrator.process([past, cancelled], [self.resident], self.current_time)

        self.assertEqual(results, [])
        self.assertEqual(self.ledger.all_attempts(), [])


if __name__ == "__main__":
    unittest.main()
