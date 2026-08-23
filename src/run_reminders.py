from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from src.channel_service import ChannelService
from src.contact_history import ContactHistoryStore
from src.contact_ledger import ContactLedger
from src.contact_policy import ContactPolicy
from src.data_loader import load_appointments, load_residents
from src.reminder_orchestrator import ReminderOrchestrator


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

APPOINTMENTS_FILE = DATA_DIR / "appointments.csv"
CONTACTS_FILE = DATA_DIR / "contacts.csv"
HISTORY_FILE = DATA_DIR / "contact_history.jsonl"


def print_result(result) -> None:
    print(
        f"{result.appointment_id} | "
        f"{result.resident_id} | "
        f"attempted={result.attempted} | "
        f"channel={result.channel} | "
        f"reached={result.reached} | "
        f"attempts={result.attempts_made} | "
        f"{result.reason}"
    )


def main() -> None:
    print("=" * 70)
    print("THE REMINDER THAT REACHES")
    print("REAL DATA END-TO-END RUN")
    print("=" * 70)

    appointments = load_appointments(APPOINTMENTS_FILE)
    residents = load_residents(CONTACTS_FILE)

    print(f"\nAppointments loaded: {len(appointments)}")
    print(f"Residents loaded:    {len(residents)}")

    current_time = datetime(2026, 3, 1, 10, 0)

    # Load persistent historical contact attempts first.
    history_store = ContactHistoryStore(HISTORY_FILE)
    historical_attempts = history_store.load()

    print(
        f"Historical contact attempts loaded: "
        f"{len(historical_attempts)}"
    )

    ledger = ContactLedger(
        attempts=historical_attempts
    )

    policy = ContactPolicy(
        ledger=ledger
    )

    channel_service = ChannelService(
        ledger=ledger,
        history_store=history_store,
    )

    orchestrator = ReminderOrchestrator(
        policy=policy,
        channel_service=channel_service,
        reminder_window=timedelta(days=1),
        channel_order=("sms", "voice", "email"),
    )

    results = orchestrator.process(
        appointments=appointments,
        residents=residents,
        current_time=current_time,
    )

    print(
        f"\nEligible appointments processed: "
        f"{len(results)}"
    )

    if not results:
        print(
            "No appointments were inside the configured "
            "reminder window."
        )
        return

    print("\n--- RESULTS ---")

    reached = 0
    attempted = 0
    blocked = 0
    channel_counts: Counter[str] = Counter()

    for result in results:
        print_result(result)

        if result.attempted:
            attempted += 1

        if result.reached:
            reached += 1

        if not result.attempted:
            blocked += 1

        if result.channel:
            channel_counts[result.channel] += 1

    print("\n--- SUMMARY ---")

    print(f"Processed:  {len(results)}")
    print(f"Attempted:  {attempted}")
    print(f"Reached:    {reached}")
    print(f"Blocked:    {blocked}")

    print("\nChannel attempts:")
    for channel, count in sorted(channel_counts.items()):
        print(f"  {channel}: {count}")

    print("\nContact ledger:")
    print(
        "  Total recorded outbound attempts: "
        f"{len(ledger.all_attempts())}"
    )

    print(
        f"  Persistent history file: "
        f"{HISTORY_FILE}"
    )

    print("\nRun completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()