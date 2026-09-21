"""SQLite-backed conversation memory for Telegram users."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Iterator, Literal


Role = Literal["user", "assistant"]
MAX_STORED_MESSAGES = 200


@dataclass(frozen=True)
class ConversationMessage:
    role: Role
    content: str


class ConversationStore:
    """Persist messages separately for each Telegram user."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the database schema and indexes if they do not exist."""
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_messages_user_id_id
                ON conversation_messages (telegram_user_id, id)
                """
            )

    def add_message(self, telegram_user_id: int, role: Role, content: str) -> None:
        """Save one user or assistant message."""
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO conversation_messages (telegram_user_id, role, content)
                VALUES (?, ?, ?)
                """,
                (telegram_user_id, role, content),
            )
            connection.execute(
                """
                DELETE FROM conversation_messages
                WHERE telegram_user_id = ?
                  AND id NOT IN (
                      SELECT id
                      FROM conversation_messages
                      WHERE telegram_user_id = ?
                      ORDER BY id DESC
                      LIMIT ?
                  )
                """,
                (telegram_user_id, telegram_user_id, MAX_STORED_MESSAGES),
            )

    def recent_messages(
        self,
        telegram_user_id: int,
        *,
        limit: int = 20,
        max_chars: int = 12_000,
    ) -> list[ConversationMessage]:
        """Return recent messages in chronological order within the context budget."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM conversation_messages
                WHERE telegram_user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (telegram_user_id, limit),
            ).fetchall()

        selected: list[ConversationMessage] = []
        characters = 0
        for row in reversed(rows):
            message = ConversationMessage(role=row[0], content=row[1])
            if selected and characters + len(message.content) > max_chars:
                break
            selected.append(message)
            characters += len(message.content)
        return selected

    def count_messages(self, telegram_user_id: int) -> int:
        """Return the number of saved messages for one Telegram user."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM conversation_messages
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            ).fetchone()
        return int(row[0])

    def clear_user_history(self, telegram_user_id: int) -> int:
        """Delete only one user's saved conversation and return deleted row count."""
        with self._connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM conversation_messages
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            )
        return cursor.rowcount