"""Load the maintained assistant instructions."""

from pathlib import Path


def load_system_prompt() -> str:
    """Read the system prompt relative to this source file."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"
    try:
        return prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to load system prompt at {prompt_path}.") from exc
