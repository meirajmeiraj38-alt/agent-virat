"""Simulation-only WhatsApp connector stubs."""

from typing import Any

from pydantic import Field
from rich import print as rich_print

from agent.safety import SendOperation
from tools.base import RiskLevel, Tool, ToolContext, ToolInput


class SendWhatsAppInput(ToolInput):
    recipients: list[str] = Field(min_length=1, description="Contact names or phone numbers.")
    message: str = Field(min_length=1, description="Full WhatsApp message text.")


class EmptyInput(ToolInput):
    pass


class SendWhatsAppMessage(Tool):
    name = "send_whatsapp_message"
    description = "Send a WhatsApp message to one or more listed recipients."
    input_model = SendWhatsAppInput
    risk = RiskLevel.MEDIUM
    platform = "whatsapp"
    simulation_only = True

    def send_operations(self, arguments: dict[str, Any]) -> list[SendOperation]:
        data = self.input_model.model_validate(arguments)
        return [
            SendOperation(self.platform, recipient, data.message)
            for recipient in data.recipients
        ]

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        data = self.input_model.model_validate(arguments)
        sent: list[str] = []
        for index, recipient in enumerate(data.recipients):
            if index:
                context.safety.delay_between_sends()
            rich_print(f"[yellow]SIMULATED: would send WhatsApp message to {recipient}[/yellow]")
            sent.append(recipient)
        # TODO: Replace simulation with the WhatsApp Cloud API.
        return {"status": "simulated", "platform": self.platform, "recipients": sent}


class GetContacts(Tool):
    name = "get_contacts"
    description = "List locally saved contacts; no external service is contacted."
    input_model = EmptyInput
    risk = RiskLevel.LOW
    platform = "whatsapp"
    simulation_only = True

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        self.input_model.model_validate(arguments)
        rich_print("[yellow]SIMULATED: would retrieve WhatsApp contacts[/yellow]")
        # TODO: Replace with the WhatsApp contacts API after integration.
        return {"status": "simulated", "contacts": []}
