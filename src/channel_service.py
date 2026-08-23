from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from channels.channels import send_email, send_sms, send_voice

from .contact_ledger import ContactLedger
from .models import ContactAttempt, Resident


@dataclass(frozen=True)
class ChannelResult:
    """Normalized result of one outbound channel attempt."""

    resident_id: str
    appointment_id: str
    channel: str
    contact_point: str
    status: str
    detail: str
    reached: bool
    attempt_number: int
    timestamp: datetime


class ChannelService:
    """
    Adapter around the supplied mock SMS, voice and email channels.

    Responsibilities:
    - choose the correct contact point
    - call the supplied channel implementation
    - interpret status + detail
    - record every outbound attempt in the ContactLedger

    This class does NOT decide whether a contact is allowed.
    ContactPolicy remains responsible for permission/safety checks.
    """

    SUPPORTED_CHANNELS = {"sms", "voice", "email"}

    def __init__(self, ledger: ContactLedger) -> None:
        self.ledger = ledger

    def get_contact_point(
    self,
    resident: Resident,
    channel: str,
    ) -> str:
        """Return the contact value to use for a supported channel."""

        channel = channel.lower().strip()

        if channel not in self.SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported channel: {channel}")

        if channel == "sms":
            return (resident.mobile or "").strip()

        if channel == "email":
            return (resident.email or "").strip()

        # voice
        if resident.mobile:
            return resident.mobile.strip()

        return (resident.landline or "").strip()

    def interpret_reach(
        self,
        channel: str,
        status: str,
        detail: str,
    ) -> bool:
        """
        Decide whether the channel result provides evidence
        that a human resident was reached.

        Conservative rule:
        - Voice answered/human => reached
        - Everything else => not confirmed as human reach

        SMS/email delivery is recorded as delivery evidence,
        but not as confirmed human reach.
        """

        channel = channel.lower().strip()
        status = status.lower().strip()
        detail = detail.lower().strip()

        if channel == "voice":
            return status == "answered" and detail == "human"

        return False

    def send(
        self,
        resident: Resident,
        appointment_id: str,
        channel: str,
        body: str,
        at: datetime,
        attempt_number: int = 1,
    ) -> ChannelResult:
        """
        Send one outbound contact through the supplied mock channel.

        The caller is expected to run ContactPolicy before calling this method.
        """

        channel = channel.lower().strip()

        if channel not in self.SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported channel: {channel}")

        contact_point = self.get_contact_point(
            resident=resident,
            channel=channel,
        )

        if channel == "sms":
            result = send_sms(
                to=contact_point,
                body=body,
                at=at,
                attempt=attempt_number,
            )

        elif channel == "voice":
            result = send_voice(
                to=contact_point,
                body=body,
                at=at,
                attempt=attempt_number,
            )

        else:
            result = send_email(
                to=contact_point,
                body=body,
                at=at,
                attempt=attempt_number,
            )

        status = str(result.get("status", "unknown"))
        detail = str(result.get("detail", ""))

        reached = self.interpret_reach(
            channel=channel,
            status=status,
            detail=detail,
        )

        attempt = ContactAttempt(
            resident_id=resident.resident_id,
            appointment_id=appointment_id,
            timestamp=at,
            channel=channel,
            contact_point=contact_point,
            status=status,
            detail=detail,
            reached=reached,
        )

        # IMPORTANT:
        # Every outbound attempt counts, including failures.
        self.ledger.add_attempt(attempt)

        return ChannelResult(
            resident_id=resident.resident_id,
            appointment_id=appointment_id,
            channel=channel,
            contact_point=contact_point,
            status=status,
            detail=detail,
            reached=reached,
            attempt_number=attempt_number,
            timestamp=at,
        )