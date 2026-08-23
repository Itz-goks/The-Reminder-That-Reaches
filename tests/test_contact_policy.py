from datetime import datetime, time, timedelta
import unittest

from src.contact_ledger import ContactLedger
from src.contact_policy import ContactPolicy
from src.models import ContactAttempt, Resident


class TestContactPolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = ContactLedger()

        self.policy = ContactPolicy(
            ledger=self.ledger,
            quiet_start=time(21, 0),
            quiet_end=time(8, 0),
        )

        self.resident = Resident(
            resident_id="RS-4000",
            name="Test Resident",
            mobile="555-123-4567",
            landline="555-765-4321",
            email="test@example.com",
            language="en",
            sms_optout=False,
            voice_optout=False,
            email_optout=False,
        )

        self.reference_time = datetime(2026, 3, 10, 10, 0)

    def add_attempt(
        self,
        *,
        resident_id: str = "RS-4000",
        timestamp: datetime,
        channel: str = "sms",
    ) -> None:
        attempt = ContactAttempt(
            resident_id=resident_id,
            appointment_id="AP-001",
            timestamp=timestamp,
            channel=channel,
            contact_point="555-123-4567",
            status="failed",
            detail="test",
            reached=False,
        )

        self.ledger.add_attempt(attempt)

    # ---------------------------------------------------------
    # Basic channel availability
    # ---------------------------------------------------------

    def test_valid_sms_is_allowed(self) -> None:
        decision = self.policy.evaluate(
            resident=self.resident,
            channel="sms",
            current_time=self.reference_time,
        )

        self.assertTrue(decision.allowed)
        self.assertIn("allowed", decision.reason.lower())

    def test_valid_email_is_allowed(self) -> None:
        decision = self.policy.evaluate(
            resident=self.resident,
            channel="email",
            current_time=self.reference_time,
        )

        self.assertTrue(decision.allowed)

    def test_valid_voice_is_allowed(self) -> None:
        decision = self.policy.evaluate(
            resident=self.resident,
            channel="voice",
            current_time=self.reference_time,
        )

        self.assertTrue(decision.allowed)

    # ---------------------------------------------------------
    # Missing contact information
    # ---------------------------------------------------------

    def test_sms_blocked_when_mobile_is_missing(self) -> None:
        resident = Resident(
            resident_id="RS-4001",
            name="No Mobile",
            mobile=None,
            landline="555-111-1111",
            email="nomobile@example.com",
            language="en",
        )

        decision = self.policy.evaluate(
            resident=resident,
            channel="sms",
            current_time=self.reference_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("no usable sms", decision.reason.lower())

    def test_voice_allowed_with_landline(self) -> None:
        resident = Resident(
            resident_id="RS-4002",
            name="Landline Only",
            mobile=None,
            landline="555-222-2222",
            email=None,
            language="en",
        )

        decision = self.policy.evaluate(
            resident=resident,
            channel="voice",
            current_time=self.reference_time,
        )

        self.assertTrue(decision.allowed)

    def test_email_blocked_when_email_is_missing(self) -> None:
        resident = Resident(
            resident_id="RS-4003",
            name="No Email",
            mobile="555-333-3333",
            landline=None,
            email=None,
            language="en",
        )

        decision = self.policy.evaluate(
            resident=resident,
            channel="email",
            current_time=self.reference_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("no usable email", decision.reason.lower())

    # ---------------------------------------------------------
    # Opt-outs
    # ---------------------------------------------------------

    def test_sms_blocked_when_resident_opted_out(self) -> None:
        resident = Resident(
            resident_id="RS-4004",
            name="SMS Opted Out",
            mobile="555-444-4444",
            landline=None,
            email="optout@example.com",
            language="en",
            sms_optout=True,
        )

        decision = self.policy.evaluate(
            resident=resident,
            channel="sms",
            current_time=self.reference_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("opted out of sms", decision.reason.lower())

    def test_voice_blocked_when_resident_opted_out(self) -> None:
        resident = Resident(
            resident_id="RS-4005",
            name="Voice Opted Out",
            mobile="555-555-5555",
            landline="555-555-5556",
            email=None,
            language="en",
            voice_optout=True,
        )

        decision = self.policy.evaluate(
            resident=resident,
            channel="voice",
            current_time=self.reference_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("opted out of voice", decision.reason.lower())

    def test_email_blocked_when_resident_opted_out(self) -> None:
        resident = Resident(
            resident_id="RS-4006",
            name="Email Opted Out",
            mobile="555-666-6666",
            landline=None,
            email="optout@example.com",
            language="en",
            email_optout=True,
        )

        decision = self.policy.evaluate(
            resident=resident,
            channel="email",
            current_time=self.reference_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("opted out of email", decision.reason.lower())

    # ---------------------------------------------------------
    # Quiet hours
    # ---------------------------------------------------------

    def test_contact_blocked_during_quiet_hours_at_night(self) -> None:
        night_time = datetime(2026, 3, 10, 22, 0)

        decision = self.policy.evaluate(
            resident=self.resident,
            channel="sms",
            current_time=night_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("quiet hours", decision.reason.lower())

    def test_contact_blocked_during_quiet_hours_early_morning(self) -> None:
        early_morning = datetime(2026, 3, 10, 7, 30)

        decision = self.policy.evaluate(
            resident=self.resident,
            channel="email",
            current_time=early_morning,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("quiet hours", decision.reason.lower())

    def test_contact_allowed_after_quiet_hours(self) -> None:
        daytime = datetime(2026, 3, 10, 10, 0)

        decision = self.policy.evaluate(
            resident=self.resident,
            channel="email",
            current_time=daytime,
        )

        self.assertTrue(decision.allowed)

    # ---------------------------------------------------------
    # Surprise: 2 contacts in rolling 7 days
    # ---------------------------------------------------------

    def test_two_recent_contacts_block_new_contact(self) -> None:
        self.add_attempt(
            timestamp=self.reference_time - timedelta(days=2)
        )

        self.add_attempt(
            timestamp=self.reference_time - timedelta(days=1)
        )

        decision = self.policy.evaluate(
            resident=self.resident,
            channel="email",
            current_time=self.reference_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("contact limit", decision.reason.lower())

    def test_one_recent_contact_still_allows_new_contact(self) -> None:
        self.add_attempt(
            timestamp=self.reference_time - timedelta(days=1)
        )

        decision = self.policy.evaluate(
            resident=self.resident,
            channel="email",
            current_time=self.reference_time,
        )

        self.assertTrue(decision.allowed)

    def test_contact_older_than_seven_days_does_not_block(self) -> None:
        self.add_attempt(
            timestamp=self.reference_time - timedelta(days=8)
        )

        self.add_attempt(
            timestamp=self.reference_time - timedelta(days=2)
        )

        decision = self.policy.evaluate(
            resident=self.resident,
            channel="email",
            current_time=self.reference_time,
        )

        self.assertTrue(decision.allowed)

    # ---------------------------------------------------------
    # Channel validation
    # ---------------------------------------------------------

    def test_unknown_channel_is_blocked(self) -> None:
        decision = self.policy.evaluate(
            resident=self.resident,
            channel="whatsapp",
            current_time=self.reference_time,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("unsupported channel", decision.reason.lower())

    # ---------------------------------------------------------
    # All contact methods absent
    # ---------------------------------------------------------

    def test_resident_with_no_contact_methods_is_blocked(self) -> None:
        resident = Resident(
            resident_id="RS-4007",
            name="No Contacts",
            mobile=None,
            landline=None,
            email=None,
            language="en",
        )

        for channel in ("sms", "voice", "email"):
            with self.subTest(channel=channel):
                decision = self.policy.evaluate(
                    resident=resident,
                    channel=channel,
                    current_time=self.reference_time,
                )

                self.assertFalse(decision.allowed)


if __name__ == "__main__":
    unittest.main()