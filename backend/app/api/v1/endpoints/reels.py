from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.api.deps import get_supabase_client
from app.db.schemas.reel import ReelCreate, ReelResponse, ReelStatusResponse
from app.services.storage import StorageService
from app.services.ml_orchestrator import MLOrchestrator
from app.workers.tasks import process_reel_generation
from app.core.logging import logger

router = APIRouter()


@router.post("/generate", response_model=ReelResponse, status_code=status.HTTP_201_CREATED)
async def trigger_reel_generation(
    reel_in: ReelCreate,
    db: Client = Depends(get_supabase_client)
):
    """
    Submits a job to generate a cinematic reel.
    Creates a record in Supabase and dispatches the task to the Celery/Redis worker queue.
    """
    try:
        # 1. Verify Movie exists and is ready (processed)
        movie_res = db.table("movies").select("*").eq("id", str(reel_in.movie_id)).execute()
        if not movie_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found."
            )
        movie = movie_res.data[0]
        if movie["status"] != "processed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Movie upload must be confirmed. Current status is '{movie['status']}'."
            )
            
        # 2. Insert queued reel record
        data = {
            "project_id": str(reel_in.project_id),
            "movie_id": str(reel_in.movie_id),
            "soundtrack_id": str(reel_in.soundtrack_id) if reel_in.soundtrack_id else None,
            "name": reel_in.name,
            "selected_emotion": reel_in.selected_emotion,
            "target_duration_seconds": reel_in.target_duration_seconds,
            "status": "queued",
            "metadata": {}
        }
        res = db.table("reels").insert(data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create reel generation job."
            )
            
        reel = res.data[0]
        reel_id = reel["id"]
        
        # 3. TRIGGER CELERY TASK (Async Broker Queue)
        process_reel_generation.delay(str(reel_id))
        logger.info(f"Dispatched Celery task for reel composition job: {reel_id}")
        
        return reel
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate reel generation: {str(e)}"
        )


@router.get("/{reel_id}/status", response_model=ReelStatusResponse)
async def get_reel_generation_status(
    reel_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Retrieves the progress and download URL for a reel compilation job.
    Includes granular progress percentages mapping to processing state levels.
    """
    try:
        res = db.table("reels").select("*").eq("id", str(reel_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reel not found."
            )
        reel = res.data[0]
        status_val = reel["status"]
        
        # Map state levels to user-facing progress percentage
        progress_map = {
            "queued": 5,
            "processing_subtitles": 15,
            "analyzing_emotions": 35,
            "extracting_clips": 60,
            "matching_music": 80,
            "composing_reel": 90,
            "completed": 100,
            "failed": 100
        }
        progress = progress_map.get(status_val, 0)
        
        download_url = None
        # Generate presigned download link if completed
        if status_val == "completed" and reel.get("video_storage_path"):
            try:
                # signed download link valid for 2 hours (7200 seconds)
                download_url = StorageService.generate_presigned_download_url(
                    bucket_name="reels",
                    file_path=reel["video_storage_path"],
                    expires_in_seconds=7200
                )
            except Exception as se:
                logger.error(f"Failed to generate download url for completed reel: {str(se)}")
                
        return {
            "reel_id": reel["id"],
            "status": status_val,
            "progress_percentage": progress,
            "error_message": reel.get("error_message"),
            "download_url": download_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reel status: {str(e)}"
        )


@router.get("/project/{project_id}", response_model=List[ReelResponse])
async def list_reels_by_project(
    project_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Lists all reels generated under a specific Project.
    """
    try:
        res = db.table("reels").select("*").eq("project_id", str(project_id)).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reels: {str(e)}"
        )


@router.get("/{reel_id}", response_model=ReelResponse)
async def get_reel(
    reel_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Gets detailed metadata and properties of a specific Reel.
    """
    try:
        res = db.table("reels").select("*").eq("id", str(reel_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reel not found."
            )
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reel details: {str(e)}"
        )


@router.get("/search/recommendations", response_model=List[dict])
async def search_movie_recommendations(
    query: str,
    limit: Optional[int] = 5
):
    """
    API interface for 'semantic_recommender'.
    Passes a descriptive natural language query and fetches semantic Netflix suggestions.
    """
    try:
        recs = MLOrchestrator.recommend_movies(query, limit)
        return recs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommendations: {str(e)}"
        )
