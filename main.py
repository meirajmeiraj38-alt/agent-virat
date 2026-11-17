"""Interactive Rich CLI for Agent Virat."""

import logging
import uuid

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel

from agent.approval import ApprovalManager
from agent.config import Settings
from agent.core import AgentCore
from agent.logger import ActionLogger, configure_file_logging
from agent.memory import MemoryStore
from agent.safety import SafetyLayer
from tools.base import ToolContext
from tools.registry import build_tools


def main() -> None:
    """Configure dependencies and run the owner chat loop."""
    console = Console()
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        return

    configure_file_logging(settings.log_path)
    memory: MemoryStore | None = None
    action_logger: ActionLogger | None = None
    try:
        memory = MemoryStore(settings.database_path)
        action_logger = ActionLogger(settings.database_path)
        safety = SafetyLayer(
            memory,
            action_logger,
            settings.daily_send_limit,
            settings.min_delay,
            settings.max_delay,
        )
        context = ToolContext(memory, action_logger, safety, settings.dry_run)
        core = AgentCore(
            Anthropic(api_key=settings.anthropic_api_key),
            settings.anthropic_model,
            build_tools(),
            context,
            ApprovalManager(settings.auto_approve_medium, console),
            safety,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("Could not initialize Agent Virat")
        console.print(f"[red]Startup failed: {exc}[/red]")
        if action_logger:
            action_logger.close()
        if memory:
            memory.close()
        return

    session_id = str(uuid.uuid4())
    console.print(
        Panel(
            "Your personal task assistant is ready. Type [bold]exit[/bold] or "
            "[bold]quit[/bold] to leave.",
            title="Agent Virat",
            border_style="cyan",
        )
    )
    try:
        while True:
            try:
                user_text = console.input("[bold cyan]Meiraj Bhai[/bold cyan] > ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye, Meiraj Bhai.[/dim]")
                break
            if user_text.casefold() in {"exit", "quit"}:
                console.print("[dim]Goodbye, Meiraj Bhai.[/dim]")
                break
            if not user_text:
                continue
            try:
                answer = core.run_turn(session_id, user_text)
                console.print(f"[bold green]Agent Virat[/bold green] > {answer}")
            except Exception as exc:
                logging.getLogger(__name__).exception("Unexpected turn failure")
                console.print(f"[red]This turn failed: {exc}[/red]")
    finally:
        action_logger.close()
        memory.close()


if __name__ == "__main__":
    main()
