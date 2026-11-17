"""SQLite-backed contacts, preferences, reminders, and do-not-contact memory."""

from datetime import date, datetime
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any


class MemoryStore:
    """Small persistent store shared by tools and the CLI."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS contacts (
                    name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    birthday TEXT,
                    language TEXT,
                    contact_group TEXT
                );
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS do_not_contact (
                    recipient TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    remind_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(character for character in value.casefold() if character.isalnum())

    def add_contact(
        self,
        name: str,
        phone: str | None = None,
        email: str | None = None,
        birthday: str | None = None,
        language: str | None = None,
        group: str | None = None,
    ) -> None:
        """Insert a contact. Birthday accepts ISO YYYY-MM-DD or MM-DD."""
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO contacts
                   (name, phone, email, birthday, language, contact_group)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, phone, email, birthday, language, group),
            )

    def search_contacts(self, query: str) -> list[dict[str, Any]]:
        """Find contacts by name, phone, email, group, or language."""
        pattern = f"%{query}%"
        with self._lock:
            rows = self._connection.execute(
                """SELECT name, phone, email, birthday, language,
                          contact_group AS 'group'
                   FROM contacts
                   WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                      OR contact_group LIKE ? OR language LIKE ?
                   ORDER BY name""",
                (pattern,) * 5,
            ).fetchall()
        return [dict(row) for row in rows]

    def all_contacts(self) -> list[dict[str, Any]]:
        """Return all contacts for the local contacts tool."""
        with self._lock:
            rows = self._connection.execute(
                """SELECT name, phone, email, birthday, language,
                          contact_group AS 'group'
                   FROM contacts ORDER BY name"""
            ).fetchall()
        return [dict(row) for row in rows]

    def contacts_with_birthday_today(
        self, today: date | None = None
    ) -> list[dict[str, Any]]:
        """Return contacts whose stored birthday matches today's month/day."""
        current = today or date.today()
        candidates = {
            current.strftime("%m-%d"),
            current.strftime("%Y-%m-%d"),
        }
        with self._lock:
            rows = self._connection.execute(
                """SELECT name, phone, email, birthday, language,
                          contact_group AS 'group'
                   FROM contacts WHERE birthday IS NOT NULL"""
            ).fetchall()
        return [
            dict(row)
            for row in rows
            if str(row["birthday"])[-5:] in candidates
            or str(row["birthday"]) in candidates
        ]

    def set_preference(self, key: str, value: str) -> None:
        """Create or replace a long-term preference."""
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO preferences(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_preferences(self) -> dict[str, str]:
        """Read all saved preferences."""
        with self._lock:
            rows = self._connection.execute(
                "SELECT key, value FROM preferences ORDER BY key"
            ).fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

    def add_do_not_contact(self, recipient: str, reason: str) -> None:
        """Add a recipient to the persistent do-not-contact list."""
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO do_not_contact(recipient, reason, created_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(recipient) DO UPDATE SET
                     reason = excluded.reason, created_at = excluded.created_at""",
                (recipient, reason, datetime.now().isoformat(timespec="seconds")),
            )

    def is_do_not_contact(self, recipient: str) -> bool:
        """Match a recipient against the DNC list, ignoring punctuation/case."""
        normalized_recipient = self._normalize(recipient)
        with self._lock:
            contacts = self._connection.execute(
                "SELECT name, phone, email FROM contacts"
            ).fetchall()
            blocked = self._connection.execute(
                "SELECT recipient FROM do_not_contact"
            ).fetchall()
        aliases = {normalized_recipient}
        for contact in contacts:
            contact_aliases = {
                self._normalize(str(contact[key]))
                for key in ("name", "phone", "email")
                if contact[key]
            }
            if normalized_recipient in contact_aliases:
                aliases.update(contact_aliases)
        blocked_aliases = {
            self._normalize(str(row["recipient"])) for row in blocked
        }
        return bool(aliases & blocked_aliases)

    def add_reminder(self, text: str, remind_at: datetime) -> int:
        """Persist a local reminder and return its database ID."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "INSERT INTO reminders(text, remind_at, created_at) VALUES (?, ?, ?)",
                (
                    text,
                    remind_at.isoformat(),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            return int(cursor.lastrowid)

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._connection.close()
