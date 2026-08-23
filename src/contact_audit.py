from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.contact_history import ContactHistoryStore
from src.contact_ledger import ContactLedger


ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = ROOT / "data" / "contact_history.jsonl"


def main() -> None:
    resident_id = input("Resident ID: ").strip()
    date_text = input(
        "Date/time (YYYY-MM-DD HH:MM): "
    ).strip()

    reference_time = datetime.fromisoformat(
        date_text
    )

    store = ContactHistoryStore(
        HISTORY_FILE
    )

    attempts = store.load()

    ledger = ContactLedger(
        attempts=attempts
    )

    recent = ledger.get_recent_attempts(
        resident_id=resident_id,
        reference_time=reference_time,
    )

    print("\n=== REGULATORY CONTACT EVIDENCE ===")
    print(f"Resident: {resident_id}")
    print(f"Reference time: {reference_time}")
    print(f"Contacts in preceding 7 days: {len(recent)}")

    for attempt in sorted(
        recent,
        key=lambda item: item.timestamp,
    ):
        print(
            f"- {attempt.timestamp.isoformat()} | "
            f"{attempt.channel} | "
            f"{attempt.status} | "
            f"{attempt.detail}"
        )

    decision = ledger.can_contact(
        resident_id=resident_id,
        reference_time=reference_time,
    )

    print("\nDecision:")
    print(f"Allowed: {decision.allowed}")
    print(f"Count: {decision.recent_count}")
    print(f"Remaining: {decision.remaining_contacts}")
    print(f"Reason: {decision.reason}")


if __name__ == "__main__":
    main()