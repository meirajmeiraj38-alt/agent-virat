# Agent Virat

Agent Virat is a CLI personal task-execution assistant for Meiraj Atif. It uses
Anthropic tool use, SQLite for contacts/preferences/action logs, and replaceable
simulation-only WhatsApp, email, and Facebook connectors.

## Setup

1. Install Python 3.11 or newer.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. Choose the model
   available to your Anthropic account in `ANTHROPIC_MODEL`.
5. Start the chat:

   ```powershell
   python main.py
   ```

Type `exit` or `quit` to end the session. The default database and log files are
created in the project directory.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Anthropic API credential | Required |
| `ANTHROPIC_MODEL` | Model used for tool planning and replies | Required |
| `DAILY_SEND_LIMIT` | Maximum logged sends per platform per day | `40` |
| `MIN_DELAY` / `MAX_DELAY` | Random delay in seconds between bulk sends | `5` / `15` |
| `DRY_RUN` | Keep connector actions simulated | `true` |
| `AUTO_APPROVE_MEDIUM` | Skip confirmation for medium-risk actions | `false` |
| `DATABASE_PATH` | SQLite database location | `agent_virat.db` |
| `LOG_PATH` | Application log location | `agent_virat.log` |

High-risk actions always require approval. `DRY_RUN=false` does not activate a
real integration: all included platform connectors are stubs and always
simulate actions. Reminders are saved locally; no notification scheduler is
included yet.

## Project structure

```text
agent-virat/
  agent/       Agent loop, approval, memory, logging, safety, configuration
  prompts/     System prompt
  tools/       Typed tools and simulated platform connectors
  tests/       Focused safety and approval tests
  main.py      Rich CLI
```

## Adding a tool

Create a class extending `Tool` in `tools/`. Give it a unique `name`,
`description`, Pydantic `input_model`, `risk` level, and `execute()` method.
Register an instance in `tools/registry.py`. Return JSON-serializable results.
For outbound messages, also implement `send_operations()` so the safety layer
can validate every recipient, message, do-not-contact entry, and daily limit
before execution.

## Replacing a connector stub

Implement the relevant platform API inside the existing connector's
`execute()` method (for example WhatsApp Cloud API, Gmail API, or Facebook
Graph API). Keep credentials in environment variables, never in source code.
Preserve the tool schema and route outbound sends through the safety layer.
Use the shared `ToolContext` logger for per-recipient outcomes. Do not remove
the approval step, do-not-contact checks, content screening, or daily limits.
Real integrations should only be enabled after their API credentials, scopes,
recipient consent, and platform-specific policies have been reviewed.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```
