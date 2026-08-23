import unittest

from src.contact_dedup import ContactDeduplicator


class TestContactDeduplicator(unittest.TestCase):
    def setUp(self) -> None:
        self.dedup = ContactDeduplicator()

    def test_first_contact_point_is_allowed(self) -> None:
        result = self.dedup.check(
            "sms",
            "555-123-4567",
        )

        self.assertTrue(result.allowed)

    def test_same_sms_number_is_blocked_after_recording(self) -> None:
        self.dedup.record(
            "sms",
            "555-123-4567",
        )

        result = self.dedup.check(
            "sms",
            "555-123-4567",
        )

        self.assertFalse(result.allowed)

    def test_phone_formatting_is_normalized(self) -> None:
        self.dedup.record(
            "sms",
            "(555) 123-4567",
        )

        result = self.dedup.check(
            "sms",
            "555-123-4567",
        )

        self.assertFalse(result.allowed)

    def test_email_matching_is_case_insensitive(self) -> None:
        self.dedup.record(
            "email",
            "Test@example.com",
        )

        result = self.dedup.check(
            "email",
            "test@example.com",
        )

        self.assertFalse(result.allowed)

    def test_different_channels_are_tracked_separately(self) -> None:
        self.dedup.record(
            "sms",
            "555-123-4567",
        )

        result = self.dedup.check(
            "voice",
            "555-123-4567",
        )

        self.assertTrue(result.allowed)

    def test_different_contact_points_are_allowed(self) -> None:
        self.dedup.record(
            "sms",
            "555-123-4567",
        )

        result = self.dedup.check(
            "sms",
            "555-987-6543",
        )

        self.assertTrue(result.allowed)

    def test_clear_removes_current_run_state(self) -> None:
        self.dedup.record(
            "sms",
            "555-123-4567",
        )

        self.dedup.clear()

        result = self.dedup.check(
            "sms",
            "555-123-4567",
        )

        self.assertTrue(result.allowed)


if __name__ == "__main__":
    unittest.main()