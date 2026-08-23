from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

APPOINTMENTS_FILE = DATA_DIR / "appointments.csv"
CONTACTS_FILE = DATA_DIR / "contacts.csv"


def load_csv(path: Path) -> list[dict[str, str]]:
    """Load a CSV file into a list of dictionaries."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def is_missing(value: str | None) -> bool:
    """Return True for blank or missing values."""
    return value is None or value.strip() == ""


def is_opted_out(row: dict[str, str], field: str) -> bool:
    """
    Interpret the supplied opt-out format.

    The supplied Problem 07 data uses:
        Y = opted out
        N = not opted out
    """
    return row.get(field, "").strip().upper() == "Y"


def profile_appointments(rows: list[dict[str, str]]) -> None:
    print("\n=== APPOINTMENTS ===")

    print(f"Total appointments: {len(rows)}")

    required_fields = [
        "appointment_id",
        "resident_id",
        "scheduled_at",
        "location",
        "service_type",
        "status",
    ]

    print("\nMissing values:")
    for field in required_fields:
        missing = sum(
            is_missing(row.get(field))
            for row in rows
        )
        print(f"  {field}: {missing}")

    appointment_ids = [
        row["appointment_id"]
        for row in rows
        if row.get("appointment_id")
    ]

    resident_ids = [
        row["resident_id"]
        for row in rows
        if row.get("resident_id")
    ]

    duplicate_appointments = {
        value: count
        for value, count in Counter(appointment_ids).items()
        if count > 1
    }

    print(
        f"\nUnique residents with appointments: "
        f"{len(set(resident_ids))}"
    )

    print(
        f"Duplicate appointment IDs: "
        f"{len(duplicate_appointments)}"
    )

    if duplicate_appointments:
        print(
            "  Examples:",
            list(duplicate_appointments.items())[:10],
        )

    service_counts = Counter(
        row["service_type"]
        for row in rows
    )

    location_counts = Counter(
        row["location"]
        for row in rows
    )

    status_counts = Counter(
        row["status"]
        for row in rows
    )

    print("\nService types:")
    for key, value in sorted(service_counts.items()):
        print(f"  {key}: {value}")

    print("\nLocations:")
    for key, value in sorted(location_counts.items()):
        print(f"  {key}: {value}")

    print("\nAppointment statuses:")
    for key, value in sorted(status_counts.items()):
        print(f"  {key}: {value}")

    dates = []

    for row in rows:
        value = row.get("scheduled_at", "").strip()

        if not value:
            continue

        try:
            dates.append(
                datetime.fromisoformat(value)
            )
        except ValueError:
            pass

    if dates:
        print("\nAppointment date range:")
        print(f"  Earliest: {min(dates)}")
        print(f"  Latest:   {max(dates)}")


def profile_contacts(rows: list[dict[str, str]]) -> None:
    print("\n=== CONTACTS ===")

    print(f"Total residents: {len(rows)}")

    contact_fields = [
        "mobile",
        "landline",
        "email",
    ]

    print("\nAvailable contact information:")

    for field in contact_fields:
        available = sum(
            not is_missing(row.get(field))
            for row in rows
        )

        missing = len(rows) - available

        print(
            f"  {field}: "
            f"{available} available, "
            f"{missing} missing"
        )

    no_contact = [
        row
        for row in rows
        if all(
            is_missing(row.get(field))
            for field in contact_fields
        )
    ]

    print(
        f"\nResidents with no contact information: "
        f"{len(no_contact)}"
    )

    # ---------------------------------------------------------
    # OPT-OUTS
    # ---------------------------------------------------------

    opt_out_fields = [
        "sms_optout",
        "voice_optout",
        "email_optout",
    ]

    print("\nOpt-out counts:")

    for field in opt_out_fields:
        count = sum(
            is_opted_out(row, field)
            for row in rows
        )

        print(f"  {field}: {count}")

    all_three_opted_out = [
        row
        for row in rows
        if all(
            is_opted_out(row, field)
            for field in opt_out_fields
        )
    ]

    print(
        "\nResidents opted out of all three channels: "
        f"{len(all_three_opted_out)}"
    )

    # Show all combinations so we understand the actual dataset.
    opt_out_combinations = Counter(
        (
            "Y" if is_opted_out(row, "sms_optout") else "N",
            "Y" if is_opted_out(row, "voice_optout") else "N",
            "Y" if is_opted_out(row, "email_optout") else "N",
        )
        for row in rows
    )

    print(
        "\nOpt-out combinations "
        "(SMS, Voice, Email):"
    )

    for combination, count in sorted(
        opt_out_combinations.items()
    ):
        print(
            f"  {combination}: {count}"
        )

    # ---------------------------------------------------------
    # LANGUAGES
    # ---------------------------------------------------------

    language_counts = Counter(
        row.get("language", "").strip()
        for row in rows
        if not is_missing(row.get("language"))
    )

    print("\nLanguages:")

    for language, count in sorted(
        language_counts.items()
    ):
        print(
            f"  {language}: {count}"
        )

    # ---------------------------------------------------------
    # SHARED MOBILE NUMBERS
    # ---------------------------------------------------------

    mobile_to_residents: defaultdict[
        str,
        list[str]
    ] = defaultdict(list)

    for row in rows:
        mobile = row.get("mobile", "").strip()
        resident_id = row.get("resident_id", "").strip()

        if mobile:
            mobile_to_residents[mobile].append(
                resident_id
            )

    shared_mobile = {
        mobile: residents
        for mobile, residents
        in mobile_to_residents.items()
        if len(residents) > 1
    }

    print(
        f"\nShared mobile numbers: "
        f"{len(shared_mobile)}"
    )

    if shared_mobile:
        print("  Examples:")

        for mobile, residents in list(
            shared_mobile.items()
        )[:10]:
            print(
                f"    {mobile}: "
                f"{residents}"
            )

    # ---------------------------------------------------------
    # SHARED EMAIL ADDRESSES
    # ---------------------------------------------------------

    email_to_residents: defaultdict[
        str,
        list[str]
    ] = defaultdict(list)

    for row in rows:
        email = row.get(
            "email",
            "",
        ).strip().lower()

        resident_id = row.get(
            "resident_id",
            "",
        ).strip()

        if email:
            email_to_residents[email].append(
                resident_id
            )

    shared_email = {
        email: residents
        for email, residents
        in email_to_residents.items()
        if len(residents) > 1
    }

    print(
        f"\nShared email addresses: "
        f"{len(shared_email)}"
    )

    if shared_email:
        print("  Examples:")

        for email, residents in list(
            shared_email.items()
        )[:10]:
            print(
                f"    {email}: "
                f"{residents}"
            )

    # ---------------------------------------------------------
    # VERIFICATION DATES
    # ---------------------------------------------------------

    verification_dates = []

    for row in rows:
        value = row.get(
            "number_last_verified",
            "",
        ).strip()

        if not value:
            continue

        try:
            verification_dates.append(
                datetime.fromisoformat(value)
            )
        except ValueError:
            pass

    print(
        f"\nValid verification dates: "
        f"{len(verification_dates)}"
    )

    if verification_dates:
        print(
            f"  Earliest verification: "
            f"{min(verification_dates)}"
        )

        print(
            f"  Latest verification: "
            f"{max(verification_dates)}"
        )


def cross_profile(
    appointments: list[dict[str, str]],
    contacts: list[dict[str, str]],
) -> None:
    print("\n=== CROSS-CHECK ===")

    contact_resident_ids = {
        row.get("resident_id", "").strip()
        for row in contacts
        if row.get("resident_id")
    }

    appointment_resident_ids = {
        row.get("resident_id", "").strip()
        for row in appointments
        if row.get("resident_id")
    }

    missing_contacts = (
        appointment_resident_ids
        - contact_resident_ids
    )

    print(
        "Appointment residents without a contact record: "
        f"{len(missing_contacts)}"
    )

    appointments_per_resident = Counter(
        row["resident_id"]
        for row in appointments
        if row.get("resident_id")
    )

    multiple_appointments = {
        resident: count
        for resident, count
        in appointments_per_resident.items()
        if count > 1
    }

    print(
        "Residents with multiple appointments: "
        f"{len(multiple_appointments)}"
    )

    if multiple_appointments:
        print("  Examples:")

        for resident, count in list(
            multiple_appointments.items()
        )[:10]:
            print(
                f"    {resident}: "
                f"{count} appointments"
            )


def main() -> None:
    appointments = load_csv(
        APPOINTMENTS_FILE
    )

    contacts = load_csv(
        CONTACTS_FILE
    )

    print("========================================")
    print("  THE REMINDER THAT REACHES")
    print("  DATA PROFILE")
    print("========================================")

    profile_appointments(
        appointments
    )

    profile_contacts(
        contacts
    )

    cross_profile(
        appointments,
        contacts,
    )

    print("\n=== DONE ===")
    print("No source data was modified.")


if __name__ == "__main__":
    main()