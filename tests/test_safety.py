"""Tests for outbound safety checks and limits."""

from pathlib import Path
import tempfile
import unittest

from agent.logger import ActionLogger
from agent.memory import MemoryStore
from agent.safety import SafetyLayer, SafetyViolation
from tools.whatsapp import SendWhatsAppMessage


class SafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = str(Path(self.temp_dir.name) / "test.db")
        self.memory = MemoryStore(database)
        self.logger = ActionLogger(database)
        self.safety = SafetyLayer(
            self.memory, self.logger, daily_send_limit=2, min_delay=0, max_delay=0
        )
        self.tool = SendWhatsAppMessage()

    def tearDown(self) -> None:
        self.logger.close()
        self.memory.close()
        self.temp_dir.cleanup()

    def test_blocks_do_not_contact_recipient(self) -> None:
        self.memory.add_do_not_contact("+1 (555) 0100", "Opted out")
        with self.assertRaisesRegex(SafetyViolation, "do-not-contact"):
            self.safety.validate(
                self.tool,
                {"recipients": ["+15550100"], "message": "Happy birthday!"},
            )

    def test_do_not_contact_matches_contact_aliases(self) -> None:
        self.memory.add_contact("Ali", phone="+1 (555) 0100")
        self.memory.add_do_not_contact("Ali", "Opted out")
        with self.assertRaisesRegex(SafetyViolation, "do-not-contact"):
            self.safety.validate(
                self.tool,
                {"recipients": ["+15550100"], "message": "Happy birthday!"},
            )

    def test_blocks_passwords_and_scams(self) -> None:
        with self.assertRaisesRegex(SafetyViolation, "passwords"):
            self.safety.validate(
                self.tool,
                {"recipients": ["Ali"], "message": "Please send your OTP to me."},
            )
        with self.assertRaisesRegex(SafetyViolation, "spam, scam"):
            self.safety.validate(
                self.tool,
                {"recipients": ["Ali"], "message": "This is a phishing scam."},
            )

    def test_bulk_preflight_enforces_daily_limit(self) -> None:
        self.logger.log_action("whatsapp", "Already sent", "Hello", "SIMULATED")
        with self.assertRaisesRegex(SafetyViolation, "daily send limit"):
            self.safety.validate(
                self.tool,
                {
                    "recipients": ["Ali", "Sara"],
                    "message": "Have a wonderful day!",
                },
            )

    def test_safe_message_returns_all_send_operations(self) -> None:
        operations = self.safety.validate(
            self.tool,
            {"recipients": ["Ali", "Sara"], "message": "Happy birthday!"},
        )
        self.assertEqual([item.recipient for item in operations], ["Ali", "Sara"])


if __name__ == "__main__":
    unittest.main()
