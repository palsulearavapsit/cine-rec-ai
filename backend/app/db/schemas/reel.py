from typing import Optional, Any, Dict, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

EmotionType = Literal['action', 'suspense', 'emotional', 'comedy', 'dark', 'motivational']
ReelStatusType = Literal[
    'queued', 
    'processing_subtitles', 
    'analyzing_emotions', 
    'extracting_clips', 
    'matching_music', 
    'composing_reel', 
    'completed', 
    'failed'
]


class ReelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    selected_emotion: EmotionType
    target_duration_seconds: int = Field(60, ge=5, le=180)


class ReelCreate(ReelBase):
    project_id: UUID
    movie_id: UUID
    soundtrack_id: Optional[UUID] = None


class ReelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    soundtrack_id: Optional[UUID] = None
    status: Optional[ReelStatusType] = None
    error_message: Optional[str] = None
    video_storage_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReelResponse(ReelBase):
    id: UUID
    project_id: UUID
    movie_id: UUID
    soundtrack_id: Optional[UUID] = None
    status: str
    error_message: Optional[str] = None
    video_storage_path: Optional[str] = None
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReelStatusResponse(BaseModel):
    reel_id: UUID
    status: str
    progress_percentage: int
    error_message: Optional[str] = None
    download_url: Optional[str] = None
