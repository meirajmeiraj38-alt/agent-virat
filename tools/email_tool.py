"""Simulation-only email connector stubs."""

from typing import Any

from pydantic import Field
from rich import print as rich_print

from agent.safety import SendOperation
from tools.base import RiskLevel, Tool, ToolContext, ToolInput


class SendEmailInput(ToolInput):
    recipients: list[str] = Field(min_length=1, description="Email addresses or contact names.")
    subject: str = Field(min_length=1, description="Email subject.")
    message: str = Field(min_length=1, description="Full email body.")


class ReadRecentEmailsInput(ToolInput):
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of messages.")


class SendEmail(Tool):
    name = "send_email"
    description = "Send an email to one or more recipients."
    input_model = SendEmailInput
    risk = RiskLevel.MEDIUM
    platform = "email"
    simulation_only = True

    def send_operations(self, arguments: dict[str, Any]) -> list[SendOperation]:
        data = self.input_model.model_validate(arguments)
        body = f"Subject: {data.subject}\n\n{data.message}"
        return [
            SendOperation(self.platform, recipient, body)
            for recipient in data.recipients
        ]

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        data = self.input_model.model_validate(arguments)
        sent: list[str] = []
        for index, recipient in enumerate(data.recipients):
            if index:
                context.safety.delay_between_sends()
            rich_print(f"[yellow]SIMULATED: would send email to {recipient}[/yellow]")
            sent.append(recipient)
        # TODO: Replace simulation with the Gmail API.
        return {"status": "simulated", "platform": self.platform, "recipients": sent}


class ReadRecentEmails(Tool):
    name = "read_recent_emails"
    description = "Read recent email headers and snippets."
    input_model = ReadRecentEmailsInput
    risk = RiskLevel.LOW
    platform = "email"
    simulation_only = True

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        data = self.input_model.model_validate(arguments)
        rich_print("[yellow]SIMULATED: would read recent emails[/yellow]")
        # TODO: Replace with Gmail API access and appropriate read scopes.
        return {"emails": [], "limit": data.limit, "status": "simulated"}
