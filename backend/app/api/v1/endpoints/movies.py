from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.api.deps import get_supabase_client
from app.db.schemas.movie import MovieCreate, MovieResponse, MovieUploadPresignedUrlsResponse
from app.services.storage import StorageService

router = APIRouter()


@router.post("/upload", response_model=MovieUploadPresignedUrlsResponse, status_code=status.HTTP_201_CREATED)
async def register_movie_and_get_upload_urls(
    movie_in: MovieCreate,
    db: Client = Depends(get_supabase_client)
):
    """
    Registers a new Movie record in PostgreSQL and generates pre-signed upload URLs 
    for the video and subtitle SRT files. The client will upload directly to these URLs,
    preventing large media files from bottlenecking the FastAPI server.
    """
    try:
        # Verify project exists and is owned by user
        proj_res = db.table("projects").select("id").eq("id", str(movie_in.project_id)).execute()
        if not proj_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target project not found or not owned by user."
            )
            
        # Create movie record
        data = {
            "project_id": str(movie_in.project_id),
            "name": movie_in.name,
            "status": "uploaded",
            "metadata": {}
        }
        res = db.table("movies").insert(data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not register movie."
            )
            
        movie = res.data[0]
        movie_id = movie["id"]
        
        # Structure paths
        video_path = f"{movie_in.project_id}/{movie_id}/movie.mp4"
        srt_path = f"{movie_in.project_id}/{movie_id}/subtitles.srt"
        
        # Update movie paths in database
        db.table("movies").update({
            "video_storage_path": video_path,
            "srt_storage_path": srt_path
        }).eq("id", movie_id).execute()
        
        # Generate presigned upload URLs
        # Expire in 1 hour (3600 seconds)
        video_upload_url = StorageService.generate_presigned_upload_url("movies", video_path)
        srt_upload_url = StorageService.generate_presigned_upload_url("movies", srt_path)
        
        return {
            "movie_id": movie_id,
            "video_upload_url": video_upload_url,
            "video_storage_path": video_path,
            "srt_upload_url": srt_upload_url,
            "srt_storage_path": srt_path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload flow: {str(e)}"
        )


@router.post("/{movie_id}/confirm-processed", response_model=MovieResponse)
async def confirm_upload_completed(
    movie_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Called by the client once they have uploaded files to the pre-signed URLs.
    Validates file sizes and presence in Supabase Storage, then flags status as 'processed'.
    """
    try:
        res = db.table("movies").select("*").eq("id", str(movie_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found."
            )
        movie = res.data[0]
        
        video_path = movie["video_storage_path"]
        srt_path = movie["srt_storage_path"]
        
        # Verify storage presence (Admin client verifies actual storage metadata)
        try:
            from app.core.supabase_client import supabase_admin_client
            # Verify video
            video_info = supabase_admin_client.storage.from_("movies").get_metadata(video_path)
            # Verify subtitles
            srt_info = supabase_admin_client.storage.from_("movies").get_metadata(srt_path)
        except Exception as se:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage validation failed. Please make sure both video and SRT files were fully uploaded. Error: {str(se)}"
            )
            
        # Update movie state
        update_data = {
            "status": "processed",
            "metadata": {
                "video_file_size": video_info.get("size"),
                "srt_file_size": srt_info.get("size"),
                "mime_type": video_info.get("mime_type")
            }
        }
        
        updated_res = db.table("movies").update(update_data).eq("id", str(movie_id)).execute()
        return updated_res.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process movie upload confirmation: {str(e)}"
        )


@router.get("/project/{project_id}", response_model=List[MovieResponse])
async def list_movies_by_project(
    project_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Lists all movies registered under a specific Project.
    """
    try:
        res = db.table("movies").select("*").eq("project_id", str(project_id)).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve movies: {str(e)}"
        )


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Gets detailed metadata for a specific Movie.
    """
    try:
        res = db.table("movies").select("*").eq("id", str(movie_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found."
            )
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve movie: {str(e)}"
        )


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Deletes a movie record and cleans up corresponding file objects inside Supabase Storage.
    """
    try:
        res = db.table("movies").select("*").eq("id", str(movie_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found."
            )
            
        movie = res.data[0]
        video_path = movie["video_storage_path"]
        srt_path = movie["srt_storage_path"]
        
        # Delete files from Supabase Storage bucket (using admin client to clear folder)
        from app.core.supabase_client import supabase_admin_client
        try:
            if video_path:
                supabase_admin_client.storage.from_("movies").remove([video_path])
            if srt_path:
                supabase_admin_client.storage.from_("movies").remove([srt_path])
        except Exception as se:
            # Non-blocking log, continue deleting DB row
            from app.core.logging import logger
            logger.warning(f"Failed to clean up files in storage during delete: {str(se)}")
            
        # Delete database row
        db.table("movies").delete().eq("id", str(movie_id)).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete movie: {str(e)}"
        )
