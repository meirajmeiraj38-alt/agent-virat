"""Outbound-message policy checks, daily limits, and bulk-send pacing."""

from dataclasses import dataclass
import random
import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tools.base import Tool


class SafetyViolation(ValueError):
    """Raised when an action violates an outbound safety rule."""


@dataclass(frozen=True)
class SendOperation:
    """One outbound message to a single recipient."""

    platform: str
    recipient: str
    message: str


class SafetyLayer:
    """Validate sends before execution and pace multi-recipient operations."""

    _BLOCKED_CONTENT = re.compile(
        r"\b(?:spam|scam|phishing|blackmail|harass(?:ment)?|threaten|"
        r"porn(?:ography)?|explicit sexual|sexually explicit|"
        r"adult content|nudes?|guaranteed profit|send me your password|"
        r"steal (?:their|the) account)\b",
        re.IGNORECASE,
    )
    _SENSITIVE_CONTENT = re.compile(
        r"\b(?:password|passcode|one[- ]time password|otp|"
        r"bank account|bank details|credit card|debit card|"
        r"routing number|money transfers?|wire transfers?|send money)\b",
        re.IGNORECASE,
    )
    _LONG_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)")

    def __init__(
        self,
        memory: Any,
        action_logger: Any,
        daily_send_limit: int = 40,
        min_delay: float = 5,
        max_delay: float = 15,
        sleep: Any = time.sleep,
        uniform: Any = random.uniform,
    ) -> None:
        if daily_send_limit < 1 or min_delay < 0 or max_delay < min_delay:
            raise ValueError("Invalid safety limits or delay range.")
        self.memory = memory
        self.action_logger = action_logger
        self.daily_send_limit = daily_send_limit
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._sleep = sleep
        self._uniform = uniform

    def validate(self, tool: "Tool", arguments: dict[str, Any]) -> list[SendOperation]:
        """Check message content, DNC status, and platform daily limits."""
        operations = tool.send_operations(arguments)
        counts: dict[str, int] = {}
        for operation in operations:
            self._validate_message(operation.message)
            if self.memory.is_do_not_contact(operation.recipient):
                raise SafetyViolation(
                    f"{operation.recipient} is on the do-not-contact list."
                )
            counts[operation.platform] = counts.get(operation.platform, 0) + 1

        for platform, requested in counts.items():
            used = self.action_logger.count_actions_today(platform)
            if used + requested > self.daily_send_limit:
                raise SafetyViolation(
                    f"The {platform} daily send limit would be exceeded "
                    f"({used}/{self.daily_send_limit} already used)."
                )
        return operations

    @classmethod
    def _validate_message(cls, message: str) -> None:
        if cls._BLOCKED_CONTENT.search(message):
            raise SafetyViolation(
                "This message appears to request spam, scam, harassment, or adult content."
            )
        if cls._SENSITIVE_CONTENT.search(message) or cls._LONG_NUMBER.search(message):
            raise SafetyViolation(
                "Messages containing passwords, OTPs, bank details, card numbers, "
                "or money-transfer requests are not allowed."
            )

    def delay_between_sends(self) -> None:
        """Wait a random configured interval between recipients in a bulk send."""
        if self.max_delay > 0:
            self._sleep(self._uniform(self.min_delay, self.max_delay))
