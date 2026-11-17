"""Environment-backed application settings."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be a boolean value.")
    return normalized in {"true", "1", "yes"}


@dataclass(frozen=True)
class Settings:
    """Validated runtime settings loaded from environment variables."""

    anthropic_api_key: str
    anthropic_model: str
    daily_send_limit: int
    min_delay: float
    max_delay: float
    dry_run: bool
    auto_approve_medium: bool
    database_path: str
    log_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Load .env and validate configuration values."""
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        model = os.getenv("ANTHROPIC_MODEL", "").strip()
        if not api_key:
            raise ValueError("Set ANTHROPIC_API_KEY in your .env file.")
        if not model:
            raise ValueError("Set ANTHROPIC_MODEL in your .env file.")

        try:
            daily_limit = int(os.getenv("DAILY_SEND_LIMIT", "40"))
            min_delay = float(os.getenv("MIN_DELAY", "5"))
            max_delay = float(os.getenv("MAX_DELAY", "15"))
        except ValueError as exc:
            raise ValueError("DAILY_SEND_LIMIT and delay settings must be numeric.") from exc
        if daily_limit < 1:
            raise ValueError("DAILY_SEND_LIMIT must be at least 1.")
        if min_delay < 0 or max_delay < min_delay:
            raise ValueError("Delays must satisfy 0 <= MIN_DELAY <= MAX_DELAY.")

        return cls(
            anthropic_api_key=api_key,
            anthropic_model=model,
            daily_send_limit=daily_limit,
            min_delay=min_delay,
            max_delay=max_delay,
            dry_run=_read_bool("DRY_RUN", True),
            auto_approve_medium=_read_bool("AUTO_APPROVE_MEDIUM", False),
            database_path=os.getenv("DATABASE_PATH", "agent_virat.db"),
            log_path=os.getenv("LOG_PATH", "agent_virat.log"),
        )
