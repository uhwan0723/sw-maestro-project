from pathlib import Path
import json
import sqlite3
from typing import Any

from app.db.connection import connect_sqlite


class SQLiteRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS raw_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'manual',
                    source_url TEXT NOT NULL DEFAULT '',
                    external_id TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS raw_document_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    source_document_id INTEGER NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
                    target_document_id INTEGER NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
                    relation_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(workspace_id, source_document_id, target_document_id, relation_type)
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    token_estimate INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS knowledge_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    source_document_id INTEGER NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
                    source_chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
                    card_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_quote TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    source_card_id INTEGER NOT NULL REFERENCES knowledge_cards(id) ON DELETE CASCADE,
                    target_card_id INTEGER NOT NULL REFERENCES knowledge_cards(id) ON DELETE CASCADE,
                    relation_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    referenced_card_ids TEXT NOT NULL,
                    referenced_chunk_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_raw_document_source_columns(connection)

    def create_workspace(self, name: str, description: str = "") -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO workspaces (name, description) VALUES (?, ?)",
                (name, description),
            )
            return self.get_workspace(cursor.lastrowid, connection=connection)

    def list_workspaces(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM workspaces ORDER BY id").fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_workspace(self, workspace_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            row = connection.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
            if row is None:
                raise KeyError(f"Workspace {workspace_id} not found")
            return self._row_to_dict(row)
        finally:
            if owns_connection:
                connection.close()

    def create_raw_document(
        self,
        workspace_id: int,
        filename: str,
        document_type: str,
        content: str,
        source_type: str = "manual",
        source_url: str = "",
        external_id: str = "",
    ) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO raw_documents (
                    workspace_id, filename, document_type, source_type, source_url, external_id, content
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, filename, document_type, source_type, source_url, external_id, content),
            )
            return self.get_raw_document(cursor.lastrowid, connection=connection)

    def get_raw_document(self, document_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            row = connection.execute("SELECT * FROM raw_documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                raise KeyError(f"Document {document_id} not found")
            return self._row_to_dict(row)
        finally:
            if owns_connection:
                connection.close()

    def list_raw_documents(self, workspace_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM raw_documents WHERE workspace_id = ? ORDER BY id",
                (workspace_id,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def create_raw_document_link(
        self,
        workspace_id: int,
        source_document_id: int,
        target_document_id: int,
        relation_type: str,
        reason: str,
        confidence: str,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id FROM raw_document_links
                WHERE workspace_id = ?
                  AND source_document_id = ?
                  AND target_document_id = ?
                  AND relation_type = ?
                """,
                (workspace_id, source_document_id, target_document_id, relation_type),
            ).fetchone()
            if existing:
                return self.get_raw_document_link(existing["id"], connection=connection)

            cursor = connection.execute(
                """
                INSERT INTO raw_document_links (
                    workspace_id, source_document_id, target_document_id, relation_type, reason, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, source_document_id, target_document_id, relation_type, reason, confidence),
            )
            return self.get_raw_document_link(cursor.lastrowid, connection=connection)

    def get_raw_document_link(self, link_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            row = connection.execute("SELECT * FROM raw_document_links WHERE id = ?", (link_id,)).fetchone()
            if row is None:
                raise KeyError(f"Raw document link {link_id} not found")
            return self._row_to_dict(row)
        finally:
            if owns_connection:
                connection.close()

    def list_raw_document_links(self, workspace_id: int, document_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM raw_document_links WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if document_id is not None:
            query += " AND (source_document_id = ? OR target_document_id = ?)"
            params.extend([document_id, document_id])
        query += " ORDER BY id"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def create_chunks(self, document_id: int, workspace_id: int, contents: list[str]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        with self._connect() as connection:
            for index, content in enumerate(contents):
                cursor = connection.execute(
                    """
                    INSERT INTO chunks (document_id, workspace_id, chunk_index, content, token_estimate)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (document_id, workspace_id, index, content, len(content.split())),
                )
                chunks.append(self.get_chunk(cursor.lastrowid, connection=connection))
        return chunks

    def get_chunk(self, chunk_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            row = connection.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
            if row is None:
                raise KeyError(f"Chunk {chunk_id} not found")
            return self._row_to_dict(row)
        finally:
            if owns_connection:
                connection.close()

    def list_chunks(self, workspace_id: int, document_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM chunks WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if document_id is not None:
            query += " AND document_id = ?"
            params.append(document_id)
        query += " ORDER BY document_id, chunk_index"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def create_knowledge_card(
        self,
        workspace_id: int,
        source_document_id: int,
        source_chunk_id: int,
        card_type: str,
        title: str,
        summary: str,
        evidence_quote: str,
        keywords: list[str],
        tags: list[str],
        status: str,
        confidence: str,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO knowledge_cards (
                    workspace_id, source_document_id, source_chunk_id, card_type, title, summary,
                    evidence_quote, keywords, tags, status, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    source_document_id,
                    source_chunk_id,
                    card_type,
                    title,
                    summary,
                    evidence_quote,
                    json.dumps(keywords, ensure_ascii=False),
                    json.dumps(tags, ensure_ascii=False),
                    status,
                    confidence,
                ),
            )
            return self.get_card(cursor.lastrowid, connection=connection)

    def get_card(self, card_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            row = connection.execute("SELECT * FROM knowledge_cards WHERE id = ?", (card_id,)).fetchone()
            if row is None:
                raise KeyError(f"Card {card_id} not found")
            return self._decode_card(row)
        finally:
            if owns_connection:
                connection.close()

    def list_cards(
        self,
        workspace_id: int,
        card_type: str | None = None,
        status: str | None = None,
        confidence: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM knowledge_cards WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if card_type:
            query += " AND card_type = ?"
            params.append(card_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        if confidence:
            query += " AND confidence = ?"
            params.append(confidence)
        query += " ORDER BY id"
        with self._connect() as connection:
            cards = [self._decode_card(row) for row in connection.execute(query, params).fetchall()]
        if keyword:
            cards = [card for card in cards if keyword in card["keywords"] or keyword in card["title"] or keyword in card["summary"]]
        if tag:
            cards = [card for card in cards if tag in card["tags"]]
        return cards

    def update_card(self, card_id: int, status: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
        card = self.get_card(card_id)
        next_status = status or card["status"]
        next_tags = tags if tags is not None else card["tags"]
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE knowledge_cards
                SET status = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (next_status, json.dumps(next_tags, ensure_ascii=False), card_id),
            )
            return self.get_card(card_id, connection=connection)

    def create_relation(
        self,
        workspace_id: int,
        source_card_id: int,
        target_card_id: int,
        relation_type: str,
        reason: str,
        confidence: str,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id FROM relations 
                WHERE workspace_id = ? AND source_card_id = ? AND target_card_id = ? AND relation_type = ?
                """,
                (workspace_id, source_card_id, target_card_id, relation_type)
            ).fetchone()
            
            if existing:
                return self.get_relation(existing["id"], connection=connection)

            cursor = connection.execute(
                """
                INSERT INTO relations (workspace_id, source_card_id, target_card_id, relation_type, reason, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, source_card_id, target_card_id, relation_type, reason, confidence),
            )
            return self.get_relation(cursor.lastrowid, connection=connection)

    def get_relation(self, relation_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            row = connection.execute("SELECT * FROM relations WHERE id = ?", (relation_id,)).fetchone()
            if row is None:
                raise KeyError(f"Relation {relation_id} not found")
            return self._row_to_dict(row)
        finally:
            if owns_connection:
                connection.close()

    def list_relations(self, workspace_id: int, card_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM relations WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if card_id is not None:
            query += " AND (source_card_id = ? OR target_card_id = ?)"
            params.extend([card_id, card_id])
        query += " ORDER BY id"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def create_chat_history(
        self,
        workspace_id: int,
        question: str,
        answer: str,
        referenced_card_ids: list[int],
        referenced_chunk_ids: list[int],
    ) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO chat_history (workspace_id, question, answer, referenced_card_ids, referenced_chunk_ids)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    question,
                    answer,
                    json.dumps(referenced_card_ids),
                    json.dumps(referenced_chunk_ids),
                ),
            )
            return self.get_chat_history(cursor.lastrowid, connection=connection)

    def get_chat_history(self, chat_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            row = connection.execute("SELECT * FROM chat_history WHERE id = ?", (chat_id,)).fetchone()
            if row is None:
                raise KeyError(f"Chat history {chat_id} not found")
            return self._decode_chat(row)
        finally:
            if owns_connection:
                connection.close()

    def list_chat_history(self, workspace_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM chat_history WHERE workspace_id = ? ORDER BY id",
                (workspace_id,),
            ).fetchall()
            return [self._decode_chat(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self.path)

    @staticmethod
    def _ensure_raw_document_source_columns(connection: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(raw_documents)").fetchall()
        }
        migrations = {
            "source_type": "ALTER TABLE raw_documents ADD COLUMN source_type TEXT NOT NULL DEFAULT 'manual'",
            "source_url": "ALTER TABLE raw_documents ADD COLUMN source_url TEXT NOT NULL DEFAULT ''",
            "external_id": "ALTER TABLE raw_documents ADD COLUMN external_id TEXT NOT NULL DEFAULT ''",
        }
        for column, statement in migrations.items():
            if column not in existing_columns:
                try:
                    connection.execute(statement)
                except sqlite3.OperationalError as error:
                    if "duplicate column name" not in str(error).lower():
                        raise

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def _decode_card(self, row: sqlite3.Row) -> dict[str, Any]:
        card = self._row_to_dict(row)
        card["keywords"] = json.loads(card["keywords"])
        card["tags"] = json.loads(card["tags"])
        return card

    def _decode_chat(self, row: sqlite3.Row) -> dict[str, Any]:
        chat = self._row_to_dict(row)
        chat["referenced_card_ids"] = json.loads(chat["referenced_card_ids"])
        chat["referenced_chunk_ids"] = json.loads(chat["referenced_chunk_ids"])
        return chat
