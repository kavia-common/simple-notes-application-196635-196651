"""
FastAPI backend for the Simple Notes App.

Exposes REST endpoints to create, list, retrieve, update, and delete notes stored in SQLite.
The backend is intended to be consumed by a React frontend running on http://localhost:3000.

Notes schema:
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- title (TEXT NOT NULL)
- content (TEXT NOT NULL)
- created_at (TEXT, ISO-8601)
- updated_at (TEXT, ISO-8601)
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Database lives in the dedicated database container folder.
# This path is stable in the provided workspace layout.
_DB_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "..",
        "simple-notes-application-196635-196652",
        "database",
        "myapp.db",
    )
)


def _utc_now_iso() -> str:
    """Return current time in UTC as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager yielding a SQLite connection with Row factory enabled.

    Ensures commits/rollback behavior is consistent and connections are closed.
    """
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_db() -> None:
    """Create notes table if it doesn't exist (lightweight migration on startup)."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


class Note(BaseModel):
    """A persisted note."""

    id: int = Field(..., description="Unique note identifier.")
    title: str = Field(..., description="Note title.")
    content: str = Field(..., description="Note content/body.")
    created_at: str = Field(..., description="ISO-8601 timestamp when created (UTC).")
    updated_at: str = Field(..., description="ISO-8601 timestamp when last updated (UTC).")


class NoteCreate(BaseModel):
    """Payload for creating a note."""

    title: str = Field(..., min_length=1, max_length=200, description="Note title.")
    content: str = Field(..., description="Note content/body.")


class NoteUpdate(BaseModel):
    """Payload for updating a note."""

    title: str = Field(..., min_length=1, max_length=200, description="Updated title.")
    content: str = Field(..., description="Updated content/body.")


openapi_tags = [
    {
        "name": "Health",
        "description": "Service health and metadata endpoints.",
    },
    {
        "name": "Notes",
        "description": "CRUD operations for notes stored in SQLite.",
    },
    {
        "name": "Docs",
        "description": "Human-readable help for API usage.",
    },
]

app = FastAPI(
    title="Simple Notes API",
    description="Backend API for a simple notes app (SQLite persistence).",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS for the React dev server on port 3000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    """Initialize SQLite schema on startup."""
    _init_db()


@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Returns a simple response indicating the service is running.",
    operation_id="health_check",
)
# PUBLIC_INTERFACE
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


@app.get(
    "/docs/help",
    tags=["Docs"],
    summary="API usage help",
    description="Human-readable notes on how to use the Notes endpoints.",
    operation_id="docs_help",
)
# PUBLIC_INTERFACE
def docs_help():
    """Return quick help text for using the API."""
    return {
        "db_path": _DB_PATH,
        "endpoints": {
            "list_notes": "GET /notes",
            "create_note": "POST /notes",
            "get_note": "GET /notes/{id}",
            "update_note": "PUT /notes/{id}",
            "delete_note": "DELETE /notes/{id}",
        },
    }


def _row_to_note(row: sqlite3.Row) -> Note:
    """Convert sqlite Row to Note model."""
    return Note(
        id=int(row["id"]),
        title=str(row["title"]),
        content=str(row["content"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@app.get(
    "/notes",
    response_model=List[Note],
    tags=["Notes"],
    summary="List notes",
    description="Returns notes ordered by last update time (descending).",
    operation_id="list_notes",
)
# PUBLIC_INTERFACE
def list_notes() -> List[Note]:
    """List all notes."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM notes ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return [_row_to_note(r) for r in rows]


@app.post(
    "/notes",
    response_model=Note,
    tags=["Notes"],
    summary="Create note",
    description="Creates a new note and returns it.",
    operation_id="create_note",
)
# PUBLIC_INTERFACE
def create_note(payload: NoteCreate) -> Note:
    """Create a new note."""
    now = _utc_now_iso()
    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notes (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (payload.title.strip(), payload.content, now, now),
        )
        note_id = int(cur.lastrowid)

        row = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to load created note")
    return _row_to_note(row)


@app.get(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Get note",
    description="Fetch a single note by id.",
    operation_id="get_note",
)
# PUBLIC_INTERFACE
def get_note(note_id: int) -> Note:
    """Get a note by id."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return _row_to_note(row)


@app.put(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Update note",
    description="Updates a note's title/content and returns the updated note.",
    operation_id="update_note",
)
# PUBLIC_INTERFACE
def update_note(note_id: int, payload: NoteUpdate) -> Note:
    """Update an existing note."""
    now = _utc_now_iso()
    with _get_conn() as conn:
        existing = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Note not found")

        conn.execute(
            "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?",
            (payload.title.strip(), payload.content, now, note_id),
        )

        row = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to load updated note")
    return _row_to_note(row)


@app.delete(
    "/notes/{note_id}",
    tags=["Notes"],
    summary="Delete note",
    description="Deletes a note by id.",
    operation_id="delete_note",
)
# PUBLIC_INTERFACE
def delete_note(note_id: int):
    """Delete a note by id."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted", "id": note_id}
