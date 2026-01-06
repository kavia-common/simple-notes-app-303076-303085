from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.api import db
from src.api.models import NoteCreate, NoteOut, NoteUpdate

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics."},
    {"name": "notes", "description": "CRUD operations for notes."},
]

app = FastAPI(
    title="Simple Notes API",
    description=(
        "Backend API for the Simple Notes App. Provides CRUD endpoints for notes stored in MySQL.\n\n"
        "MySQL connection is configured via environment variables (preferred): MYSQL_URL, MYSQL_USER, "
        "MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS: allow the React dev server (port 3000).
# NOTE: If deployed elsewhere, add the production origin via an env var and include it here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(_: Request, exc: RuntimeError) -> JSONResponse:
    """Convert internal RuntimeError into a consistent JSON 500 response."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# PUBLIC_INTERFACE
@app.get(
    "/",
    tags=["health"],
    summary="Health check",
    description="Returns a simple health payload to verify the API is running.",
)
def health_check():
    """API health check endpoint.

    Returns:
        dict: A small JSON object indicating the service is healthy.
    """
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[NoteOut],
    tags=["notes"],
    summary="List notes",
    description="Return all notes ordered by last updated (descending).",
)
def list_notes():
    """List notes.

    Returns:
        List[NoteOut]: All notes in the database ordered by updated_at desc.
    """
    return db.fetch_all_notes()


# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=NoteOut,
    status_code=201,
    tags=["notes"],
    summary="Create note",
    description="Create a new note with a title and content.",
)
def create_note(payload: NoteCreate):
    """Create a note.

    Args:
        payload (NoteCreate): Note fields.

    Returns:
        NoteOut: Created note row.

    Raises:
        HTTPException: For validation-related failures (should be rare due to Pydantic validation).
    """
    created = db.create_note(title=payload.title, content=payload.content)
    return created


# PUBLIC_INTERFACE
@app.patch(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Update note (partial)",
    description="Partially update a note. Provide title and/or content.",
)
def patch_note(note_id: int, payload: NoteUpdate):
    """Partially update a note by id.

    Args:
        note_id (int): Note id.
        payload (NoteUpdate): Optional fields to update.

    Returns:
        NoteOut: Updated note.

    Raises:
        HTTPException: 404 if not found; 400 if no fields provided.
    """
    if payload.title is None and payload.content is None:
        raise HTTPException(status_code=400, detail="At least one field (title/content) must be provided.")

    updated = db.update_note(note_id=note_id, title=payload.title, content=payload.content)
    if updated is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return updated


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Update note (full)",
    description="Fully replace a note's title and content.",
)
def put_note(note_id: int, payload: NoteCreate):
    """Fully update a note by id (PUT semantics).

    Args:
        note_id (int): Note id.
        payload (NoteCreate): Full note payload (title and content required).

    Returns:
        NoteOut: Updated note.

    Raises:
        HTTPException: 404 if not found.
    """
    updated = db.update_note(note_id=note_id, title=payload.title, content=payload.content)
    if updated is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return updated


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    tags=["notes"],
    summary="Delete note",
    description="Delete a note by id.",
)
def delete_note(note_id: int):
    """Delete a note by id.

    Args:
        note_id (int): Note id.

    Returns:
        dict: JSON indicating deletion.

    Raises:
        HTTPException: 404 if not found.
    """
    deleted = db.delete_note(note_id=note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found.")
    return {"deleted": True, "id": note_id}
