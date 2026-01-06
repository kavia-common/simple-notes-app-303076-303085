import os
from typing import Any, Dict, List, Optional, Tuple

import pymysql
from pymysql.connections import Connection


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer for env var {name}: {value}") from exc


# PUBLIC_INTERFACE
def get_connection() -> Connection:
    """Create and return a new MySQL connection.

    Uses environment variables (preferred) and falls back to defaults derived from
    `database/db_connection.txt` per project instructions.

    Env vars used (database container provides these names):
      - MYSQL_URL (optional host override)
      - MYSQL_USER
      - MYSQL_PASSWORD
      - MYSQL_DB
      - MYSQL_PORT

    Returns:
        pymysql Connection: A new connection with dict cursor enabled.

    Raises:
        RuntimeError: If connection cannot be established.
    """
    # Prefer MYSQL_URL if present; otherwise use localhost.
    host = os.getenv("MYSQL_URL") or os.getenv("MYSQL_HOST") or "localhost"
    user = os.getenv("MYSQL_USER") or "appuser"
    password = os.getenv("MYSQL_PASSWORD") or "dbuser123"
    db_name = os.getenv("MYSQL_DB") or "myapp"
    port = _env_int("MYSQL_PORT", 5000)

    try:
        return pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db_name,
            port=port,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
            charset="utf8mb4",
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to connect to MySQL. Ensure MYSQL_* env vars are set correctly "
            "and that the database container is reachable."
        ) from exc


def _execute_one(
    query: str, params: Optional[Tuple[Any, ...]] = None
) -> Tuple[List[Dict[str, Any]], int, Optional[int]]:
    """Execute a single query and return (rows, affected_rows, lastrowid)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall() if cur.description is not None else []
            affected = cur.rowcount
            lastrowid = cur.lastrowid
        return rows, affected, lastrowid
    finally:
        conn.close()


# PUBLIC_INTERFACE
def fetch_all_notes() -> List[Dict[str, Any]]:
    """Fetch all notes ordered by most recently updated/created."""
    rows, _, _ = _execute_one(
        """
        SELECT id, title, content, created_at, updated_at
        FROM notes
        ORDER BY updated_at DESC, created_at DESC, id DESC
        """.strip()
    )
    return rows


# PUBLIC_INTERFACE
def fetch_note_by_id(note_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single note by id or return None."""
    rows, _, _ = _execute_one(
        """
        SELECT id, title, content, created_at, updated_at
        FROM notes
        WHERE id = %s
        """.strip(),
        (note_id,),
    )
    return rows[0] if rows else None


# PUBLIC_INTERFACE
def create_note(title: str, content: str) -> Dict[str, Any]:
    """Create a note and return the inserted record."""
    _, affected, last_id = _execute_one(
        "INSERT INTO notes (title, content) VALUES (%s, %s)",
        (title, content),
    )
    if affected != 1 or last_id is None:
        raise RuntimeError("Failed to create note.")
    created = fetch_note_by_id(int(last_id))
    if created is None:
        raise RuntimeError("Note created but could not be retrieved.")
    return created


# PUBLIC_INTERFACE
def update_note(note_id: int, title: Optional[str], content: Optional[str]) -> Optional[Dict[str, Any]]:
    """Update a note (partial update) and return updated record; None if not found."""
    existing = fetch_note_by_id(note_id)
    if existing is None:
        return None

    new_title = title if title is not None else existing["title"]
    new_content = content if content is not None else existing["content"]

    _, affected, _ = _execute_one(
        "UPDATE notes SET title = %s, content = %s WHERE id = %s",
        (new_title, new_content, note_id),
    )
    # affected can be 0 if values didn't change; still return current row.
    if affected < 0:
        raise RuntimeError("Failed to update note.")
    return fetch_note_by_id(note_id)


# PUBLIC_INTERFACE
def delete_note(note_id: int) -> bool:
    """Delete a note by id. Returns True if deleted, False if not found."""
    _, affected, _ = _execute_one("DELETE FROM notes WHERE id = %s", (note_id,))
    return affected == 1
