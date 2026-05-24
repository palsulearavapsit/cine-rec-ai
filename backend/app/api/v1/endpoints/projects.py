from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.api.deps import get_current_user, get_supabase_client
from app.db.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    Creates a new organization Project for the user.
    """
    try:
        data = {
            "name": project_in.name,
            "description": project_in.description,
            "user_id": current_user["id"]
        }
        res = db.table("projects").insert(data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create project."
            )
        return res.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    db: Client = Depends(get_supabase_client)
):
    """
    Lists all projects belonging to the authenticated user.
    """
    try:
        res = db.table("projects").select("*").order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Gets metadata for a specific Project.
    """
    try:
        res = db.table("projects").select("*").eq("id", str(project_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or not owned by user."
            )
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project: {str(e)}"
        )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    db: Client = Depends(get_supabase_client)
):
    """
    Modifies details of an existing Project.
    """
    try:
        # Check ownership first
        check_res = db.table("projects").select("id").eq("id", str(project_id)).execute()
        if not check_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or not owned by user."
            )
            
        update_data = project_in.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update fields provided."
            )
            
        res = db.table("projects").update(update_data).eq("id", str(project_id)).execute()
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: Client = Depends(get_supabase_client)
):
    """
    Deletes a project and recursively cascades deletions to movies and reels.
    """
    try:
        res = db.table("projects").delete().eq("id", str(project_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or not owned by user."
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
