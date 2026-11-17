"""SQLite action history and ordinary application log setup."""

from datetime import date, datetime
import logging
from pathlib import Path
import sqlite3
from threading import RLock


def configure_file_logging(log_path: str) -> None:
    """Configure a file logger without replacing other application handlers."""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


class ActionLogger:
    """Persist completed or failed tool actions in SQLite."""

    def __init__(self, database_path: str) -> None:
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._lock, self._connection:
            self._connection.execute(
                """CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    recipient TEXT,
                    message TEXT,
                    status TEXT NOT NULL
                )"""
            )

    def log_action(
        self,
        platform: str,
        recipient: str | None,
        message: str | None,
        status: str,
    ) -> None:
        """Write one action record and a corresponding application log entry."""
        timestamp = datetime.now().isoformat(timespec="seconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO action_log(timestamp, platform, recipient, message, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (timestamp, platform, recipient, message, status),
            )
        logging.getLogger("agent.actions").info(
            "%s platform=%s recipient=%s", status, platform, recipient or "-"
        )

    def count_actions_today(self, platform: str, today: date | None = None) -> int:
        """Count successful sends for a platform on the local calendar day."""
        day = (today or date.today()).isoformat()
        with self._lock:
            row = self._connection.execute(
                """SELECT COUNT(*) AS total FROM action_log
                   WHERE platform = ? AND timestamp LIKE ?
                     AND status IN ('SENT', 'SIMULATED')""",
                (platform, f"{day}%"),
            ).fetchone()
        return int(row["total"])

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._connection.close()
