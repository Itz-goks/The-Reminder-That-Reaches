from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

from .contact_ledger import ContactLedger
from .models import Resident


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class ContactPolicy:
    """
    Central policy gate for all outbound contact decisions.

    All future reminder attempts must pass through this class.
    """

    def __init__(
        self,
        ledger: ContactLedger,
        quiet_start: time = time(21, 0),
        quiet_end: time = time(8, 0),
    ) -> None:
        self.ledger = ledger
        self.quiet_start = quiet_start
        self.quiet_end = quiet_end

    def is_quiet_hours(self, current_time: datetime) -> bool:
        """Return True when current_time falls inside the quiet period."""
        current = current_time.time()

        # Quiet period crosses midnight, e.g. 21:00 -> 08:00.
        if self.quiet_start > self.quiet_end:
            return (
                current >= self.quiet_start
                or current < self.quiet_end
            )

        return self.quiet_start <= current < self.quiet_end

    def channel_has_contact(
        self,
        resident: Resident,
        channel: str,
    ) -> bool:
        """Check whether the resident has the requested contact method."""
        channel = channel.lower().strip()

        if channel == "sms":
            return resident.has_mobile()

        if channel == "voice":
            return resident.has_mobile() or resident.has_landline()

        if channel == "email":
            return resident.has_email()

        return False

    def channel_is_opted_out(
        self,
        resident: Resident,
        channel: str,
    ) -> bool:
        """Check whether the resident opted out of the requested channel."""
        channel = channel.lower().strip()

        if channel == "sms":
            return resident.sms_optout

        if channel == "voice":
            return resident.voice_optout

        if channel == "email":
            return resident.email_optout

        return True  # Unknown channels are denied by default.

    def evaluate(
        self,
        resident: Resident,
        channel: str,
        current_time: datetime,
    ) -> PolicyDecision:
        """
        Evaluate whether one outbound contact is permitted.

        This does not send anything and does not record a contact.
        """

        channel = channel.lower().strip()

        # 1. Known channel
        if channel not in {"sms", "voice", "email"}:
            return PolicyDecision(
                allowed=False,
                reason=f"Unsupported channel: {channel}",
            )

        # 2. Quiet hours
        if self.is_quiet_hours(current_time):
            return PolicyDecision(
                allowed=False,
                reason="Blocked by quiet hours.",
            )

        # 3. Contact availability
        if not self.channel_has_contact(resident, channel):
            return PolicyDecision(
                allowed=False,
                reason=f"No usable {channel} contact information.",
            )

        # 4. Opt-out
        if self.channel_is_opted_out(resident, channel):
            return PolicyDecision(
                allowed=False,
                reason=f"Resident opted out of {channel}.",
            )

        # 5. Regulatory 2-in-7 check
        contact_check = self.ledger.can_contact(
            resident_id=resident.resident_id,
            reference_time=current_time,
        )

        if not contact_check.allowed:
            return PolicyDecision(
                allowed=False,
                reason=contact_check.reason,
            )

        return PolicyDecision(
            allowed=True,
            reason=(
                f"Contact allowed via {channel}. "
                f"{contact_check.remaining_contacts} "
                "contact allowance remaining."
            ),
        )