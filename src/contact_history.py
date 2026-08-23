from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import ContactAttempt


class ContactHistoryStore:
    """
    Persistent audit store for outbound contact attempts.

    Every actual outbound attempt is written as one JSONL record.
    This allows the regulatory 2-in-7 rule to survive between runs
    and provides evidence for historical/retrospective counting.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, attempt: ContactAttempt) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "resident_id": attempt.resident_id,
            "appointment_id": attempt.appointment_id,
            "timestamp": attempt.timestamp.isoformat(),
            "channel": attempt.channel,
            "contact_point": attempt.contact_point,
            "status": attempt.status,
            "detail": attempt.detail,
            "reached": attempt.reached,
        }

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    record,
                    sort_keys=True,
                )
                + "\n"
            )

    def load(self) -> list[ContactAttempt]:
        """Load all historical outbound attempts."""
        if not self.path.exists():
            return []

        attempts: list[ContactAttempt] = []

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()

                if not line:
                    continue

                try:
                    record = json.loads(line)

                    attempts.append(
                        ContactAttempt(
                            resident_id=record["resident_id"],
                            appointment_id=record["appointment_id"],
                            timestamp=datetime.fromisoformat(
                                record["timestamp"]
                            ),
                            channel=record["channel"],
                            contact_point=record["contact_point"],
                            status=record["status"],
                            detail=record.get("detail", ""),
                            reached=bool(
                                record.get("reached", False)
                            ),
                        )
                    )

                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(
                        f"Invalid contact-history record "
                        f"at line {line_number}: {error}"
                    ) from error

        return attempts