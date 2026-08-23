from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

APPOINTMENTS_FILE = DATA_DIR / "appointments.csv"
CONTACTS_FILE = DATA_DIR / "contacts.csv"


def load_csv(path: Path) -> list[dict[str, str]]:
    """Load a CSV file and return rows as dictionaries."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def is_missing(value: str | None) -> bool:
    """Return True if a field is blank or missing."""
    return value is None or value.strip() == ""


def get_contact_scenario(row: dict[str, str]) -> str:
    """Classify a resident by which contact methods are available."""
    available = []

    if not is_missing(row.get("mobile")):
        available.append("Mobile")

    if not is_missing(row.get("landline")):
        available.append("Landline")

    if not is_missing(row.get("email")):
        available.append("Email")

    if not available:
        return "No contact information"

    return " + ".join(available)


def inspect_contact_scenarios(
    contacts: list[dict[str, str]],
    appointments: list[dict[str, str]],
) -> None:
    print("\n=== CONTACT SCENARIOS ===")

    scenario_counts = Counter(
        get_contact_scenario(row)
        for row in contacts
    )

    scenario_order = [
        "Mobile + Landline + Email",
        "Mobile + Landline",
        "Mobile + Email",
        "Landline + Email",
        "Mobile",
        "Landline",
        "Email",
        "No contact information",
    ]

    for scenario in scenario_order:
        print(f"{scenario}: {scenario_counts.get(scenario, 0)}")

    print("\n=== SPECIAL CONTACT CASES ===")

    # Shared mobile numbers
    mobile_to_residents: defaultdict[str, list[str]] = defaultdict(list)

    for row in contacts:
        mobile = row.get("mobile", "").strip()
        resident_id = row.get("resident_id", "").strip()

        if mobile:
            mobile_to_residents[mobile].append(resident_id)

    shared_mobile = {
        mobile: residents
        for mobile, residents in mobile_to_residents.items()
        if len(residents) > 1
    }

    residents_with_shared_mobile = {
        resident
        for residents in shared_mobile.values()
        for resident in residents
    }

    print(f"Shared mobile numbers: {len(shared_mobile)}")
    print(
        f"Residents affected by shared mobile numbers: "
        f"{len(residents_with_shared_mobile)}"
    )

    # Shared email addresses
    email_to_residents: defaultdict[str, list[str]] = defaultdict(list)

    for row in contacts:
        email = row.get("email", "").strip().lower()
        resident_id = row.get("resident_id", "").strip()

        if email:
            email_to_residents[email].append(resident_id)

    shared_email = {
        email: residents
        for email, residents in email_to_residents.items()
        if len(residents) > 1
    }

    residents_with_shared_email = {
        resident
        for residents in shared_email.values()
        for resident in residents
    }

    print(f"Shared email addresses: {len(shared_email)}")
    print(
        f"Residents affected by shared email addresses: "
        f"{len(residents_with_shared_email)}"
    )

    # Residents with no contact
    no_contact_residents = [
        row["resident_id"]
        for row in contacts
        if get_contact_scenario(row) == "No contact information"
    ]

    print(f"Residents with no contact information: {len(no_contact_residents)}")

    # Multiple appointments
    appointments_per_resident = Counter(
        row["resident_id"]
        for row in appointments
        if row.get("resident_id")
    )

    multiple_appointments = {
        resident_id: count
        for resident_id, count in appointments_per_resident.items()
        if count > 1
    }

    print(f"Residents with multiple appointments: {len(multiple_appointments)}")

    if multiple_appointments:
        max_appointments = max(multiple_appointments.values())
        print(f"Maximum appointments for one resident: {max_appointments}")

    # Appointment-level contactability
    contact_by_resident = {
        row["resident_id"]: row
        for row in contacts
        if row.get("resident_id")
    }

    contactable_appointments = 0
    uncontactable_appointments = 0

    for appointment in appointments:
        resident_id = appointment.get("resident_id", "")
        contact = contact_by_resident.get(resident_id)

        if contact is None:
            uncontactable_appointments += 1
            continue

        if get_contact_scenario(contact) == "No contact information":
            uncontactable_appointments += 1
        else:
            contactable_appointments += 1

    print("\n=== APPOINTMENT CONTACTABILITY ===")
    print(
        f"Appointments with at least one contact method: "
        f"{contactable_appointments}"
    )
    print(
        f"Appointments with no contact method: "
        f"{uncontactable_appointments}"
    )

    # Detailed examples for inspection
    print("\n=== EXAMPLES ===")

    print("\nResidents with no contact information:")
    for resident_id in no_contact_residents[:10]:
        print(f"  {resident_id}")

    print("\nShared mobile examples:")
    for mobile, residents in list(shared_mobile.items())[:5]:
        print(f"  {mobile} -> {', '.join(residents)}")

    print("\nShared email examples:")
    for email, residents in list(shared_email.items())[:5]:
        print(f"  {email} -> {', '.join(residents)}")

    print("\nMultiple-appointment examples:")
    for resident_id, count in list(multiple_appointments.items())[:10]:
        print(f"  {resident_id} -> {count} appointments")


def main() -> None:
    contacts = load_csv(CONTACTS_FILE)
    appointments = load_csv(APPOINTMENTS_FILE)

    print("========================================")
    print("  THE REMINDER THAT REACHES")
    print("  CONTACT CASE INSPECTION")
    print("========================================")

    inspect_contact_scenarios(contacts, appointments)

    print("\n=== DONE ===")
    print("No source data was modified.")


if __name__ == "__main__":
    main()