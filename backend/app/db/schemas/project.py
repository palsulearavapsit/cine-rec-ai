from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# Shared properties
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


# Properties to receive on project creation
class ProjectCreate(ProjectBase):
    pass


# Properties to receive on project update
class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


# Properties returned to client
class ProjectResponse(ProjectBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
