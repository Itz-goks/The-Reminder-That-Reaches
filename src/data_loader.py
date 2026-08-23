from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import Appointment, Resident


CONTACT_REQUIRED_FIELDS = (
    "resident_id",
    "name",
    "language",
    "sms_optout",
    "voice_optout",
    "email_optout",
)
APPOINTMENT_REQUIRED_FIELDS = (
    "appointment_id",
    "resident_id",
    "scheduled_at",
    "location",
    "service_type",
    "status",
)


def _read_rows(path: Path, required_fields: Iterable[str]) -> list[dict[str, str]]:
    """Read a CSV file and verify that its required columns are present."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        missing_fields = [field for field in required_fields if field not in fieldnames]

        if missing_fields:
            raise ValueError(
                f"{path}: missing required column(s): {', '.join(missing_fields)}"
            )

        return list(reader)


def _required_value(row: dict[str, str], field: str, row_number: int, path: Path) -> str:
    """Return a non-blank required CSV field."""
    value = (row.get(field) or "").strip()
    if not value:
        raise ValueError(f"{path}: row {row_number}: {field} is required.")
    return value


def _optional_value(row: dict[str, str], field: str) -> str | None:
    """Return a trimmed optional CSV field, or None when it is blank."""
    value = (row.get(field) or "").strip()
    return value or None


def _parse_optout(value: str, field: str, row_number: int, path: Path) -> bool:
    """Parse the supplied Y/N opt-out format."""
    normalized = value.upper()
    if normalized == "Y":
        return True
    if normalized == "N":
        return False
    raise ValueError(
        f"{path}: row {row_number}: {field} must be Y or N, got {value!r}."
    )


def _parse_datetime(value: str, field: str, row_number: int, path: Path) -> datetime:
    """Parse one required project timestamp in ISO format."""
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"{path}: row {row_number}: {field} is not a valid ISO timestamp: {value!r}."
        ) from error


def load_residents(path: Path) -> list[Resident]:
    """Load contacts.csv rows into Resident objects."""
    residents = []
    for row_number, row in enumerate(_read_rows(path, CONTACT_REQUIRED_FIELDS), start=2):
        verified_value = _optional_value(row, "number_last_verified")
        residents.append(
            Resident(
                resident_id=_required_value(row, "resident_id", row_number, path),
                name=_required_value(row, "name", row_number, path),
                mobile=_optional_value(row, "mobile"),
                landline=_optional_value(row, "landline"),
                email=_optional_value(row, "email"),
                language=_required_value(row, "language", row_number, path),
                sms_optout=_parse_optout(
                    _required_value(row, "sms_optout", row_number, path),
                    "sms_optout",
                    row_number,
                    path,
                ),
                voice_optout=_parse_optout(
                    _required_value(row, "voice_optout", row_number, path),
                    "voice_optout",
                    row_number,
                    path,
                ),
                email_optout=_parse_optout(
                    _required_value(row, "email_optout", row_number, path),
                    "email_optout",
                    row_number,
                    path,
                ),
                number_last_verified=(
                    _parse_datetime(
                        verified_value,
                        "number_last_verified",
                        row_number,
                        path,
                    )
                    if verified_value
                    else None
                ),
            )
        )
    return residents


def load_appointments(path: Path) -> list[Appointment]:
    """Load appointments.csv rows into Appointment objects."""
    appointments = []
    for row_number, row in enumerate(_read_rows(path, APPOINTMENT_REQUIRED_FIELDS), start=2):
        scheduled_at = _required_value(row, "scheduled_at", row_number, path)
        appointments.append(
            Appointment(
                appointment_id=_required_value(row, "appointment_id", row_number, path),
                resident_id=_required_value(row, "resident_id", row_number, path),
                scheduled_at=_parse_datetime(
                    scheduled_at, "scheduled_at", row_number, path
                ),
                location=_required_value(row, "location", row_number, path),
                service_type=_required_value(row, "service_type", row_number, path),
                status=_required_value(row, "status", row_number, path),
            )
        )
    return appointments
