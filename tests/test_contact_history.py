from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from src.contact_history import ContactHistoryStore
from src.models import ContactAttempt


class TestContactHistoryStore(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "history.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_and_load_attempt(self) -> None:
        store = ContactHistoryStore(self.path)

        attempt = ContactAttempt(
            resident_id="RS-4000",
            appointment_id="AP-001",
            timestamp=datetime(2026, 3, 1, 10, 0),
            channel="sms",
            contact_point="555-123-4567",
            status="failed",
            detail="carrier_rejected",
            reached=False,
        )

        store.append(attempt)

        loaded = store.load()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(
            loaded[0].resident_id,
            "RS-4000",
        )
        self.assertEqual(
            loaded[0].appointment_id,
            "AP-001",
        )
        self.assertEqual(
            loaded[0].channel,
            "sms",
        )
        self.assertFalse(loaded[0].reached)

    def test_historical_attempts_can_be_used_by_ledger(self) -> None:
        store = ContactHistoryStore(self.path)

        reference_time = datetime(
            2026,
            3,
            10,
            10,
            0,
        )

        for days_ago in (1, 2):
            store.append(
                ContactAttempt(
                    resident_id="RS-4000",
                    appointment_id=f"AP-{days_ago}",
                    timestamp=reference_time
                    - timedelta(days=days_ago),
                    channel="sms",
                    contact_point="555-123-4567",
                    status="failed",
                    detail="test",
                    reached=False,
                )
            )

        loaded = store.load()

        self.assertEqual(len(loaded), 2)


if __name__ == "__main__":
    unittest.main()