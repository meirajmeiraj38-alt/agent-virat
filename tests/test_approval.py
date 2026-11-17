"""Tests for risk-based approval behavior."""

import unittest

from agent.approval import ApprovalManager
from tools.base import RiskLevel, Tool, ToolContext, ToolInput
from tools.facebook import CreateFacebookPost
from tools.whatsapp import SendWhatsAppMessage


class LowRiskTool(Tool):
    name = "read_only"
    description = "Read-only test tool."
    input_model = ToolInput
    risk = RiskLevel.LOW

    def execute(self, arguments: dict, context: ToolContext) -> dict:
        return {}


class ApprovalTests(unittest.TestCase):
    def test_low_risk_runs_without_prompt(self) -> None:
        manager = ApprovalManager(input_fn=lambda _: self.fail("unexpected prompt"))
        self.assertTrue(manager.approve(LowRiskTool(), {}))

    def test_medium_requires_exact_yes_by_default(self) -> None:
        tool = SendWhatsAppMessage()
        arguments = {"recipients": ["Ali"], "message": "Hello."}
        self.assertTrue(
            ApprovalManager(input_fn=lambda _: "yes").approve(tool, arguments)
        )
        self.assertFalse(
            ApprovalManager(input_fn=lambda _: "y").approve(tool, arguments)
        )

    def test_medium_auto_approval_does_not_approve_bulk_high_risk(self) -> None:
        tool = SendWhatsAppMessage()
        arguments = {"recipients": ["Ali", "Sara"], "message": "Hello."}
        manager = ApprovalManager(
            auto_approve_medium=True,
            input_fn=lambda _: "no",
        )
        self.assertFalse(manager.approve(tool, arguments))

    def test_high_risk_never_uses_medium_auto_approval(self) -> None:
        manager = ApprovalManager(
            auto_approve_medium=True,
            input_fn=lambda _: "no",
        )
        self.assertFalse(
            manager.approve(
                CreateFacebookPost(),
                {"message": "A public announcement."},
            )
        )


if __name__ == "__main__":
    unittest.main()
