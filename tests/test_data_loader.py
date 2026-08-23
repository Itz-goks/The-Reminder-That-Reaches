from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.data_loader import load_appointments, load_residents


class TestDataLoader(unittest.TestCase):
    def write_csv(self, directory: Path, name: str, content: str) -> Path:
        path = directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_residents_parses_optional_contacts_optouts_and_timestamp(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = self.write_csv(
                directory,
                "contacts.csv",
                "resident_id,name,mobile,landline,email,language,sms_optout,voice_optout,email_optout,number_last_verified\n"
                "RS-1,Ada Lovelace,555-111-2222,,ada@example.com,en,Y,N,Y,2026-03-01 14:30\n",
            )

            residents = load_residents(path)

        self.assertEqual(len(residents), 1)
        resident = residents[0]
        self.assertEqual(resident.resident_id, "RS-1")
        self.assertIsNone(resident.landline)
        self.assertTrue(resident.sms_optout)
        self.assertFalse(resident.voice_optout)
        self.assertTrue(resident.email_optout)
        self.assertEqual(resident.number_last_verified, datetime(2026, 3, 1, 14, 30))

    def test_load_residents_allows_blank_optional_verification_timestamp(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = self.write_csv(
                directory,
                "contacts.csv",
                "resident_id,name,mobile,landline,email,language,sms_optout,voice_optout,email_optout,number_last_verified\n"
                "RS-2,Grace Hopper,,,,en,N,N,N,\n",
            )

            resident = load_residents(path)[0]

        self.assertIsNone(resident.number_last_verified)
        self.assertFalse(resident.sms_optout)

    def test_load_appointments_parses_valid_row_and_timestamp(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = self.write_csv(
                directory,
                "appointments.csv",
                "appointment_id,resident_id,scheduled_at,location,service_type,status\n"
                "AP-1,RS-1,2026-03-02 09:15,Central,Advice,Booked\n",
            )

            appointments = load_appointments(path)

        self.assertEqual(len(appointments), 1)
        appointment = appointments[0]
        self.assertEqual(appointment.appointment_id, "AP-1")
        self.assertEqual(appointment.scheduled_at, datetime(2026, 3, 2, 9, 15))

    def test_invalid_optout_value_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = self.write_csv(
                directory,
                "contacts.csv",
                "resident_id,name,mobile,landline,email,language,sms_optout,voice_optout,email_optout,number_last_verified\n"
                "RS-3,Invalid,,,,en,M,N,N,2026-03-01\n",
            )

            with self.assertRaisesRegex(ValueError, "sms_optout must be Y or N"):
                load_residents(path)

    def test_missing_required_appointment_value_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = self.write_csv(
                directory,
                "appointments.csv",
                "appointment_id,resident_id,scheduled_at,location,service_type,status\n"
                "AP-1,,2026-03-02 09:15,Central,Advice,Booked\n",
            )

            with self.assertRaisesRegex(ValueError, "resident_id is required"):
                load_appointments(path)

    def test_malformed_appointment_timestamp_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = self.write_csv(
                directory,
                "appointments.csv",
                "appointment_id,resident_id,scheduled_at,location,service_type,status\n"
                "AP-1,RS-1,not-a-date,Central,Advice,Booked\n",
            )

            with self.assertRaisesRegex(ValueError, "scheduled_at is not a valid ISO timestamp"):
                load_appointments(path)


if __name__ == "__main__":
    unittest.main()
