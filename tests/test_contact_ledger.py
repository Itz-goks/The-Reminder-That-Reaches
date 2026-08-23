from datetime import datetime, timedelta
import unittest

from src.contact_ledger import ContactLedger
from src.models import ContactAttempt


class TestContactLedger(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = ContactLedger()

        self.resident_id = "RS-4000"
        self.appointment_id = "AP-001"
        self.reference_time = datetime(2026, 3, 10, 10, 0)

    def make_attempt(
        self,
        timestamp: datetime,
        channel: str = "sms",
        status: str = "delivered",
        detail: str = "test",
        reached: bool = False,
    ) -> ContactAttempt:
        return ContactAttempt(
            resident_id=self.resident_id,
            appointment_id=self.appointment_id,
            timestamp=timestamp,
            channel=channel,
            contact_point="555-123-4567",
            status=status,
            detail=detail,
            reached=reached,
        )

    def test_zero_contacts_are_allowed(self) -> None:
        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.recent_count, 0)
        self.assertEqual(result.remaining_contacts, 2)

    def test_one_recent_contact_is_allowed(self) -> None:
        self.ledger.add_attempt(
            self.make_attempt(
                self.reference_time - timedelta(days=1)
            )
        )

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.recent_count, 1)
        self.assertEqual(result.remaining_contacts, 1)

    def test_two_recent_contacts_are_blocked(self) -> None:
        self.ledger.add_attempt(
            self.make_attempt(
                self.reference_time - timedelta(days=2)
            )
        )

        self.ledger.add_attempt(
            self.make_attempt(
                self.reference_time - timedelta(days=1)
            )
        )

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.recent_count, 2)
        self.assertEqual(result.remaining_contacts, 0)

    def test_failed_attempt_still_counts(self) -> None:
        self.ledger.add_attempt(
            self.make_attempt(
                self.reference_time - timedelta(days=1),
                channel="sms",
                status="failed",
                detail="carrier_rejected",
                reached=False,
            )
        )

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertEqual(result.recent_count, 1)
        self.assertTrue(result.allowed)

    def test_contacts_from_different_channels_count_together(self) -> None:
        self.ledger.add_attempt(
            self.make_attempt(
                self.reference_time - timedelta(days=2),
                channel="sms",
            )
        )

        self.ledger.add_attempt(
            self.make_attempt(
                self.reference_time - timedelta(days=1),
                channel="voice",
            )
        )

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.recent_count, 2)

    def test_contacts_from_different_appointments_count_together(self) -> None:
        first = self.make_attempt(
            self.reference_time - timedelta(days=2)
        )

        second = ContactAttempt(
            resident_id=self.resident_id,
            appointment_id="AP-999",
            timestamp=self.reference_time - timedelta(days=1),
            channel="email",
            contact_point="test@example.com",
            status="delivered",
            detail="test",
            reached=False,
        )

        self.ledger.add_attempt(first)
        self.ledger.add_attempt(second)

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.recent_count, 2)

    def test_attempt_exactly_seven_days_old_is_outside_window(self) -> None:
        old_attempt = self.make_attempt(
            self.reference_time - timedelta(days=7)
        )

        self.ledger.add_attempt(old_attempt)

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.recent_count, 0)
        self.assertEqual(result.remaining_contacts, 2)

    def test_future_attempt_is_not_counted(self) -> None:
        future_attempt = self.make_attempt(
            self.reference_time + timedelta(hours=1)
        )

        self.ledger.add_attempt(future_attempt)

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.recent_count, 0)

    def test_other_residents_do_not_count_against_this_resident(self) -> None:
        other_resident_attempt = ContactAttempt(
            resident_id="RS-9999",
            appointment_id="AP-002",
            timestamp=self.reference_time - timedelta(days=1),
            channel="sms",
            contact_point="555-999-9999",
            status="delivered",
            detail="test",
            reached=False,
        )

        self.ledger.add_attempt(other_resident_attempt)

        result = self.ledger.can_contact(
            self.resident_id,
            self.reference_time,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.recent_count, 0)

    def test_all_historical_attempts_are_kept(self) -> None:
        old_attempt = self.make_attempt(
            self.reference_time - timedelta(days=10)
        )

        recent_attempt = self.make_attempt(
            self.reference_time - timedelta(days=1)
        )

        self.ledger.add_attempt(old_attempt)
        self.ledger.add_attempt(recent_attempt)

        history = self.ledger.resident_attempt_history(
            self.resident_id
        )

        self.assertEqual(len(history), 2)

    def test_record_attempt_and_check_records_failed_attempt(self) -> None:
        failed_attempt = self.make_attempt(
            self.reference_time,
            status="failed",
            detail="accepted_by_carrier",
            reached=False,
        )

        result = self.ledger.record_attempt_and_check(
            failed_attempt
        )

        self.assertEqual(
            self.ledger.count_recent_contacts(
                self.resident_id,
                self.reference_time,
            ),
            1,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.recent_count, 1)
        self.assertEqual(result.remaining_contacts, 1)


if __name__ == "__main__":
    unittest.main()