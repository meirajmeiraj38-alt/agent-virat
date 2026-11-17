"""Human confirmation for medium- and high-risk tools."""

from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel

from tools.base import RiskLevel, Tool


class ApprovalManager:
    """Render action previews and require explicit owner approval."""

    def __init__(
        self,
        auto_approve_medium: bool = False,
        console: Console | None = None,
        input_fn: Callable[[str], str] = input,
    ) -> None:
        self.auto_approve_medium = auto_approve_medium
        self.console = console or Console()
        self.input_fn = input_fn

    def approve(self, tool: Tool, arguments: dict[str, Any]) -> bool:
        """Return whether the action is approved; LOW actions run automatically."""
        risk = tool.risk_for(arguments)
        if risk == RiskLevel.LOW:
            return True
        if risk == RiskLevel.MEDIUM and self.auto_approve_medium:
            return True

        self.console.print(
            Panel(
                tool.preview(arguments),
                title=f"Approval required - {risk.value} risk",
                border_style="yellow" if risk == RiskLevel.MEDIUM else "red",
            )
        )
        try:
            answer = self.input_fn('Type "yes" to continue: ')
        except (EOFError, KeyboardInterrupt):
            return False
        return answer.strip().casefold() == "yes"
