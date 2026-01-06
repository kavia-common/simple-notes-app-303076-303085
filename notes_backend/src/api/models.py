from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Short title for the note.")
    content: str = Field(..., min_length=1, description="Full note content.")


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    # Allow partial update via PATCH semantics.
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated title.")
    content: Optional[str] = Field(None, min_length=1, description="Updated content.")


class NoteOut(NoteBase):
    id: int = Field(..., description="Note primary key.")
    created_at: datetime = Field(..., description="When the note was created.")
    updated_at: datetime = Field(..., description="When the note was last updated.")

    class Config:
        from_attributes = True
