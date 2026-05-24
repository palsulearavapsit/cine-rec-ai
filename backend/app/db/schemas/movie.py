from typing import Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class MovieBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)


class MovieCreate(MovieBase):
    project_id: UUID


class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    video_storage_path: Optional[str] = None
    srt_storage_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: Optional[str] = Field(None, pattern="^(uploaded|processing_subtitles|processed|failed)$")
    metadata: Optional[Dict[str, Any]] = None


class MovieResponse(MovieBase):
    id: UUID
    project_id: UUID
    video_storage_path: Optional[str] = None
    srt_storage_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
        
class MovieUploadPresignedUrlsResponse(BaseModel):
    movie_id: UUID
    video_upload_url: str
    video_storage_path: str
    srt_upload_url: Optional[str] = None
    srt_storage_path: Optional[str] = None
