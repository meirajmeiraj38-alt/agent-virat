"""Typed tool contract, tool context, and risk classification."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from agent.logger import ActionLogger
    from agent.memory import MemoryStore
    from agent.safety import SafetyLayer, SendOperation


class RiskLevel(str, Enum):
    """Approval categories for tool actions."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ToolInput(BaseModel):
    """Strict base for tool argument schemas."""

    model_config = ConfigDict(extra="forbid")


class ToolContext:
    """Shared runtime services passed to every tool."""

    def __init__(
        self,
        memory: "MemoryStore",
        action_logger: "ActionLogger",
        safety: "SafetyLayer",
        dry_run: bool,
    ) -> None:
        self.memory = memory
        self.action_logger = action_logger
        self.safety = safety
        self.dry_run = dry_run


class Tool(ABC):
    """Abstract callable exposed to Claude as a JSON-schema tool."""

    name: str
    description: str
    input_model: type[ToolInput]
    risk: RiskLevel = RiskLevel.LOW
    platform: str = "local"
    simulation_only: bool = False

    def anthropic_schema(self) -> dict[str, Any]:
        """Build the Anthropic tool-use schema from the Pydantic model."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }

    def risk_for(self, arguments: dict[str, Any]) -> RiskLevel:
        """Allow a tool to elevate risk for a bulk request."""
        if self.risk == RiskLevel.MEDIUM and len(self.send_operations(arguments)) > 1:
            return RiskLevel.HIGH
        return self.risk

    def send_operations(self, arguments: dict[str, Any]) -> list["SendOperation"]:
        """Return outbound messages for safety preflight, if applicable."""
        return []

    def preview(self, arguments: dict[str, Any]) -> str:
        """Create a concise human-readable preview of the requested action."""
        operations = self.send_operations(arguments)
        if operations:
            return "\n\n".join(
                f"Platform: {operation.platform}\n"
                f"Recipient: {operation.recipient}\n"
                f"Message:\n{operation.message}"
                for operation in operations
            )
        return f"Tool: {self.name}\nArguments:\n{arguments}"

    @abstractmethod
    def execute(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        """Validate and execute tool arguments."""
