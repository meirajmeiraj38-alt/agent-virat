"""Claude tool-use loop and per-session conversation management."""

import json
import logging
from typing import Any

from anthropic import Anthropic

from agent.approval import ApprovalManager
from agent.safety import SafetyLayer, SafetyViolation
from agent.system_prompt import load_system_prompt
from tools.base import Tool, ToolContext

logger = logging.getLogger(__name__)


class AgentCore:
    """Run a bounded tool-use conversation for each CLI session."""

    def __init__(
        self,
        client: Anthropic,
        model: str,
        tools: list[Tool],
        context: ToolContext,
        approval: ApprovalManager,
        safety: SafetyLayer,
        max_tool_rounds: int = 8,
    ) -> None:
        self.client = client
        self.model = model
        self.tools = {tool.name: tool for tool in tools}
        self.context = context
        self.approval = approval
        self.safety = safety
        self.max_tool_rounds = max_tool_rounds
        self.system_prompt = load_system_prompt()
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def run_turn(self, session_id: str, user_text: str) -> str:
        """Process one owner message, executing approved tool calls as needed."""
        history = self._sessions.setdefault(session_id, [])
        history.append({"role": "user", "content": user_text})
        for _ in range(self.max_tool_rounds):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1200,
                    system=self.system_prompt,
                    tools=[tool.anthropic_schema() for tool in self.tools.values()],
                    messages=history,
                )
            except Exception as exc:
                logger.exception("Anthropic request failed")
                return self._failure_reply(history, f"Claude request failed: {exc}")

            tool_uses = [
                block for block in response.content if getattr(block, "type", None) == "tool_use"
            ]
            if not tool_uses:
                answer = self._text_content(response.content)
                history.append({"role": "assistant", "content": answer})
                return answer

            history.append({"role": "assistant", "content": response.content})
            results: list[dict[str, Any]] = []
            for index, call in enumerate(tool_uses):
                tool = self.tools.get(call.name)
                arguments = call.input if isinstance(call.input, dict) else {}
                if tool is None:
                    error = f"Unknown tool requested: {call.name}."
                else:
                    error = ""
                try:
                    if not error and tool is not None:
                        approved = self.approval.approve(tool, arguments)
                        if not approved:
                            error = f"Action {call.name} was not approved; nothing was executed."
                        else:
                            self.safety.validate(tool, arguments)
                            result = tool.execute(arguments, self.context)
                            self._log_success(tool, arguments)
                            results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": call.id,
                                    "content": json.dumps(
                                        result, ensure_ascii=False, default=str
                                    ),
                                }
                            )
                except SafetyViolation as exc:
                    logger.warning("Tool %s was blocked: %s", call.name, exc)
                    error = f"Action blocked: {exc}"
                    self._log_blocked(tool, arguments)
                except ValueError as exc:
                    logger.warning("Invalid arguments for tool %s: %s", call.name, exc)
                    error = f"Invalid arguments for {call.name}: {exc}"
                except Exception as exc:
                    logger.exception("Tool %s failed", call.name)
                    error = f"Tool {call.name} failed: {exc}"
                    if tool is not None:
                        self._log_failed(tool, arguments)

                if error:
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "content": error,
                            "is_error": True,
                        }
                    )
                    for remaining in tool_uses[index + 1 :]:
                        results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": remaining.id,
                                "content": "Stopped; no additional tools were executed.",
                                "is_error": True,
                            }
                        )
                    history.append({"role": "user", "content": results})
                    return self._failure_reply(history, error, add_instruction=False)
            history.append({"role": "user", "content": results})

        logger.error("Maximum tool rounds reached for session %s", session_id)
        answer = "I stopped because this task required too many tool rounds."
        history.append({"role": "assistant", "content": answer})
        return answer

    @staticmethod
    def _text_content(content: list[Any]) -> str:
        texts = [
            block.text
            for block in content
            if getattr(block, "type", None) == "text" and getattr(block, "text", "")
        ]
        return "\n".join(texts).strip() or "I couldn't produce a response."

    def _failure_reply(
        self,
        history: list[dict[str, Any]],
        error: str,
        add_instruction: bool = True,
    ) -> str:
        """Ask Claude to explain a stopped action without making further tool calls."""
        messages = list(history)
        if add_instruction:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The task has stopped and no more actions may be taken. "
                        f"Explain this clearly and briefly in the same language as the owner: {error}"
                    ),
                }
            )
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=self.system_prompt,
                messages=messages,
            )
            answer = self._text_content(response.content)
            history.append({"role": "assistant", "content": answer})
            return answer
        except Exception:
            logger.exception("Could not request a localized failure reply")
            history.append({"role": "assistant", "content": error})
            return error

    def _log_success(self, tool: Tool, arguments: dict[str, Any]) -> None:
        operations = tool.send_operations(arguments)
        if operations:
            status = (
                "SIMULATED"
                if self.context.dry_run or tool.simulation_only
                else "SENT"
            )
            for operation in operations:
                self.context.action_logger.log_action(
                    operation.platform,
                    operation.recipient,
                    operation.message,
                    status,
                )
        else:
            self.context.action_logger.log_action(
                tool.platform,
                None,
                tool.name,
                "SIMULATED"
                if self.context.dry_run or tool.simulation_only
                else "COMPLETED",
            )

    def _log_failed(self, tool: Tool, arguments: dict[str, Any]) -> None:
        operations = tool.send_operations(arguments)
        if operations:
            for operation in operations:
                self.context.action_logger.log_action(
                    operation.platform, operation.recipient, operation.message, "FAILED"
                )
        else:
            self.context.action_logger.log_action(tool.platform, None, tool.name, "FAILED")

    def _log_blocked(self, tool: Tool | None, arguments: dict[str, Any]) -> None:
        if tool is None:
            return
        operations = tool.send_operations(arguments)
        if operations:
            for operation in operations:
                self.context.action_logger.log_action(
                    operation.platform,
                    operation.recipient,
                    operation.message,
                    "BLOCKED",
                )
        else:
            self.context.action_logger.log_action(tool.platform, None, tool.name, "BLOCKED")
