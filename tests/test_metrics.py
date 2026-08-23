import unittest
from datetime import datetime

from src.metrics import build_metrics
from src.models import ContactAttempt
from src.reminder_orchestrator import ReminderResult


class TestMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.attempt = ContactAttempt(
            resident_id="RS-4000",
            appointment_id="AP-001",
            timestamp=datetime(2026, 3, 1, 10, 0),
            channel="sms",
            contact_point="555-123-4567",
            status="failed",
            detail="carrier_rejected",
            reached=False,
        )

    def test_separates_not_reached_from_blocked(self) -> None:
        results = [
            ReminderResult(
                appointment_id="AP-001",
                resident_id="RS-4000",
                attempted=True,
                channel="sms",
                reason="SMS not reached",
                reached=False,
                attempts_made=1,
            ),
            ReminderResult(
                appointment_id="AP-002",
                resident_id="RS-4001",
                attempted=False,
                channel=None,
                reason="Rolling 7-day contact limit reached (2/2)",
                reached=False,
                attempts_made=0,
            ),
        ]

        metrics = build_metrics(
            results=results,
            attempts=[self.attempt],
        )

        self.assertEqual(metrics.processed, 2)
        self.assertEqual(metrics.attempted, 1)
        self.assertEqual(metrics.reached, 0)
        self.assertEqual(metrics.not_reached, 1)
        self.assertEqual(metrics.blocked, 1)
        self.assertEqual(
            metrics.block_reasons["2-in-7 limit"],
            1,
        )

    def test_reached_is_counted(self) -> None:
        result = ReminderResult(
            appointment_id="AP-001",
            resident_id="RS-4000",
            attempted=True,
            channel="voice",
            reason="Resident reached via voice",
            reached=True,
            attempts_made=2,
        )

        metrics = build_metrics(
            results=[result],
            attempts=[self.attempt],
        )

        self.assertEqual(metrics.reached, 1)
        self.assertEqual(metrics.not_reached, 0)

    def test_channel_counts_are_reported(self) -> None:
        email_attempt = ContactAttempt(
            resident_id="RS-4001",
            appointment_id="AP-002",
            timestamp=datetime(2026, 3, 1, 10, 0),
            channel="email",
            contact_point="test@example.com",
            status="delivered",
            detail="",
            reached=False,
        )

        result = ReminderResult(
            appointment_id="AP-002",
            resident_id="RS-4001",
            attempted=True,
            channel="email",
            reason="Email sent",
            reached=False,
            attempts_made=1,
        )

        metrics = build_metrics(
            results=[result],
            attempts=[email_attempt],
        )

        self.assertEqual(
            metrics.channel_counts["email"],
            1,
        )


if __name__ == "__main__":
    unittest.main()