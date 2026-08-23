from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from src.channel_service import ChannelService
from src.contact_history import ContactHistoryStore
from src.contact_ledger import ContactLedger
from src.contact_policy import ContactPolicy
from src.data_loader import load_appointments, load_residents
from src.metrics import build_metrics
from src.reminder_orchestrator import ReminderOrchestrator


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

APPOINTMENTS_FILE = DATA_DIR / "appointments.csv"
CONTACTS_FILE = DATA_DIR / "contacts.csv"
HISTORY_FILE = DATA_DIR / "contact_history.jsonl"


def print_result(result) -> None:
    """Print one auditable reminder result."""
    print(
        f"{result.appointment_id} | "
        f"{result.resident_id} | "
        f"attempted={result.attempted} | "
        f"channel={result.channel} | "
        f"reached={result.reached} | "
        f"attempts={result.attempts_made} | "
        f"{result.reason}"
    )


def print_summary(metrics) -> None:
    """Print metrics for the current run only."""
    print("\n--- SUMMARY ---")

    print(f"Processed:            {metrics.processed}")
    print(f"Outbound attempted:   {metrics.attempted}")
    print(f"Reached:              {metrics.reached}")
    print(f"Not reached:          {metrics.not_reached}")
    print(f"Blocked:              {metrics.blocked}")

    print("\nCurrent-run channel attempts:")

    if metrics.channel_counts:
        for channel, count in sorted(
            metrics.channel_counts.items()
        ):
            print(f"  {channel}: {count}")
    else:
        print("  None")

    print("\nCurrent-run block reasons:")

    if metrics.block_reasons:
        for reason, count in sorted(
            metrics.block_reasons.items()
        ):
            print(f"  {reason}: {count}")
    else:
        print("  None")

    print(
        "\nCurrent-run outbound contact attempts: "
        f"{metrics.total_contact_attempts}"
    )


def main() -> None:
    print("=" * 70)
    print("THE REMINDER THAT REACHES")
    print("REAL DATA END-TO-END RUN")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Load supplied data
    # ---------------------------------------------------------

    appointments = load_appointments(
        APPOINTMENTS_FILE
    )

    residents = load_residents(
        CONTACTS_FILE
    )

    print(
        f"\nAppointments loaded: "
        f"{len(appointments)}"
    )

    print(
        f"Residents loaded:    "
        f"{len(residents)}"
    )

    # ---------------------------------------------------------
    # 2. Deterministic run time
    # ---------------------------------------------------------

    current_time = datetime(
        2026,
        3,
        1,
        10,
        0,
    )

    # ---------------------------------------------------------
    # 3. Load persistent regulatory history
    # ---------------------------------------------------------

    history_store = ContactHistoryStore(
        HISTORY_FILE
    )

    historical_attempts = history_store.load()

    print(
        "Historical contact attempts loaded: "
        f"{len(historical_attempts)}"
    )

    # ---------------------------------------------------------
    # 4. Build ledger + policies + services
    # ---------------------------------------------------------

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
        channel_order=(
            "sms",
            "voice",
            "email",
        ),
    )

    # ---------------------------------------------------------
    # 5. Remember where the current run starts
    #
    # Historical attempts must continue to affect the
    # regulatory 2-in-7 rule, but they must NOT be included
    # in the current-run metrics.
    # ---------------------------------------------------------

    attempts_before_run = len(
        ledger.all_attempts()
    )

    # ---------------------------------------------------------
    # 6. Process appointments
    # ---------------------------------------------------------

    results = orchestrator.process(
        appointments=appointments,
        residents=residents,
        current_time=current_time,
    )

    print(
        "\nEligible appointments processed: "
        f"{len(results)}"
    )

    # ---------------------------------------------------------
    # 7. Get only attempts created during THIS run
    # ---------------------------------------------------------

    all_attempts = ledger.all_attempts()

    current_run_attempts = all_attempts[
        attempts_before_run:
    ]

    # ---------------------------------------------------------
    # 8. No eligible appointments
    # ---------------------------------------------------------

    if not results:
        print(
            "No appointments were inside "
            "the configured reminder window."
        )

        print("\n--- AUDIT ---")
        print(
            "Historical + current ledger records: "
            f"{len(all_attempts)}"
        )
        print(
            "Current-run outbound attempts: "
            f"{len(current_run_attempts)}"
        )
        print(
            "Persistent history file:"
        )
        print(f"  {HISTORY_FILE}")

        print("\nRun completed.")
        print("=" * 70)
        return

    # ---------------------------------------------------------
    # 9. Print individual appointment results
    # ---------------------------------------------------------

    print("\n--- RESULTS ---")

    for result in results:
        print_result(result)

    # ---------------------------------------------------------
    # 10. Build current-run metrics ONLY
    # ---------------------------------------------------------

    metrics = build_metrics(
        results=results,
        attempts=current_run_attempts,
    )

    print_summary(metrics)

    # ---------------------------------------------------------
    # 11. Persistent audit information
    # ---------------------------------------------------------

    print("\n--- AUDIT ---")

    print(
        "Persistent history file:"
    )
    print(
        f"  {HISTORY_FILE}"
    )

    print(
        "Historical + current ledger records: "
        f"{len(all_attempts)}"
    )

    print(
        "Current-run outbound attempts: "
        f"{len(current_run_attempts)}"
    )

    print("\nRun completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()