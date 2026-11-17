"""Simulation-only Facebook connector stubs."""

from typing import Any

from pydantic import Field
from rich import print as rich_print

from agent.safety import SendOperation
from tools.base import RiskLevel, Tool, ToolContext, ToolInput


class CreateFacebookPostInput(ToolInput):
    message: str = Field(min_length=1, description="Full public post text.")


class ReplyFacebookCommentInput(ToolInput):
    comment_id: str = Field(min_length=1, description="Facebook comment identifier.")
    message: str = Field(min_length=1, description="Full public reply text.")


class CreateFacebookPost(Tool):
    name = "create_facebook_post"
    description = "Create a public post on the owner's Facebook page."
    input_model = CreateFacebookPostInput
    risk = RiskLevel.HIGH
    platform = "facebook"
    simulation_only = True

    def send_operations(self, arguments: dict[str, Any]) -> list[SendOperation]:
        data = self.input_model.model_validate(arguments)
        return [SendOperation(self.platform, "public", data.message)]

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        data = self.input_model.model_validate(arguments)
        rich_print("[yellow]SIMULATED: would create a Facebook post[/yellow]")
        # TODO: Replace simulation with the Facebook Graph API.
        return {"status": "simulated", "platform": self.platform, "message": data.message}


class ReplyFacebookComment(Tool):
    name = "reply_facebook_comment"
    description = "Reply publicly to a Facebook comment."
    input_model = ReplyFacebookCommentInput
    risk = RiskLevel.HIGH
    platform = "facebook"
    simulation_only = True

    def send_operations(self, arguments: dict[str, Any]) -> list[SendOperation]:
        data = self.input_model.model_validate(arguments)
        return [
            SendOperation(
                self.platform,
                f"comment:{data.comment_id}",
                data.message,
            )
        ]

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        data = self.input_model.model_validate(arguments)
        rich_print(
            f"[yellow]SIMULATED: would reply to Facebook comment {data.comment_id}[/yellow]"
        )
        # TODO: Replace simulation with the Facebook Graph API.
        return {
            "status": "simulated",
            "platform": self.platform,
            "comment_id": data.comment_id,
        }
