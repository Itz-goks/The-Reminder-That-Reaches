from datetime import datetime
import unittest

from src.channel_service import ChannelService
from src.contact_ledger import ContactLedger
from src.models import Resident


class TestChannelService(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = ContactLedger()

        self.service = ChannelService(
            ledger=self.ledger,
        )

        self.resident = Resident(
            resident_id="RS-4000",
            name="Test Resident",
            mobile="555-123-4567",
            landline="555-765-4321",
            email="test@example.com",
            language="en",
        )

        self.at = datetime(2026, 3, 10, 10, 0)

    def test_sms_uses_mobile_number(self) -> None:
        point = self.service.get_contact_point(
            self.resident,
            "sms",
        )

        self.assertEqual(point, "555-123-4567")

    def test_email_uses_email_address(self) -> None:
        point = self.service.get_contact_point(
            self.resident,
            "email",
        )

        self.assertEqual(point, "test@example.com")

    def test_voice_prefers_mobile_when_available(self) -> None:
        point = self.service.get_contact_point(
            self.resident,
            "voice",
        )

        self.assertEqual(point, "555-123-4567")

    def test_voice_uses_landline_when_mobile_missing(self) -> None:
        resident = Resident(
            resident_id="RS-4001",
            name="Landline Resident",
            mobile=None,
            landline="555-222-2222",
            email=None,
            language="en",
        )

        point = self.service.get_contact_point(
            resident,
            "voice",
        )

        self.assertEqual(point, "555-222-2222")

    def test_unknown_channel_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            self.service.get_contact_point(
                self.resident,
                "whatsapp",
            )

    def test_voice_human_is_reached(self) -> None:
        reached = self.service.interpret_reach(
            channel="voice",
            status="answered",
            detail="human",
        )

        self.assertTrue(reached)

    def test_voice_voicemail_is_not_confirmed_reach(self) -> None:
        reached = self.service.interpret_reach(
            channel="voice",
            status="answered",
            detail="voicemail_left",
        )

        self.assertFalse(reached)

    def test_voice_no_answer_is_not_reached(self) -> None:
        reached = self.service.interpret_reach(
            channel="voice",
            status="no_answer",
            detail="",
        )

        self.assertFalse(reached)

    def test_voice_failure_is_not_reached(self) -> None:
        reached = self.service.interpret_reach(
            channel="voice",
            status="failed",
            detail="busy",
        )

        self.assertFalse(reached)

    def test_sms_delivery_is_not_human_reach(self) -> None:
        reached = self.service.interpret_reach(
            channel="sms",
            status="delivered",
            detail="",
        )

        self.assertFalse(reached)

    def test_sms_landline_acceptance_is_not_human_reach(self) -> None:
        reached = self.service.interpret_reach(
            channel="sms",
            status="delivered",
            detail="accepted_by_carrier",
        )

        self.assertFalse(reached)

    def test_email_delivery_is_not_human_reach(self) -> None:
        reached = self.service.interpret_reach(
            channel="email",
            status="delivered",
            detail="",
        )

        self.assertFalse(reached)

    def test_email_spam_is_not_human_reach(self) -> None:
        reached = self.service.interpret_reach(
            channel="email",
            status="delivered",
            detail="placed_in_spam",
        )

        self.assertFalse(reached)

    def test_email_bounce_is_not_reach(self) -> None:
        reached = self.service.interpret_reach(
            channel="email",
            status="failed",
            detail="hard_bounce",
        )

        self.assertFalse(reached)

    def test_send_records_every_attempt(self) -> None:
        result = self.service.send(
            resident=self.resident,
            appointment_id="AP-001",
            channel="sms",
            body="Reminder: appointment tomorrow.",
            at=self.at,
            attempt_number=1,
        )

        self.assertEqual(result.channel, "sms")
        self.assertEqual(result.resident_id, "RS-4000")

        history = self.ledger.resident_attempt_history(
            "RS-4000"
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].channel, "sms")
        self.assertEqual(history[0].appointment_id, "AP-001")

    def test_failed_attempt_is_still_recorded(self) -> None:
        # Use an empty mobile to make the supplied channel return no_number.
        resident = Resident(
            resident_id="RS-4002",
            name="No Mobile",
            mobile=None,
            landline=None,
            email="test@example.com",
            language="en",
        )

        result = self.service.send(
            resident=resident,
            appointment_id="AP-002",
            channel="sms",
            body="Test reminder.",
            at=self.at,
            attempt_number=1,
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.detail, "no_number")
        self.assertFalse(result.reached)

        history = self.ledger.resident_attempt_history(
            "RS-4002"
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, "failed")

    def test_send_rejects_unsupported_channel(self) -> None:
        with self.assertRaises(ValueError):
            self.service.send(
                resident=self.resident,
                appointment_id="AP-003",
                channel="whatsapp",
                body="Test",
                at=self.at,
            )


if __name__ == "__main__":
    unittest.main()