from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.api.deps import get_current_user, get_supabase_client

router = APIRouter()


@router.get("/me", response_model=dict)
async def read_user_me(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    Retrieves the active user profile details from Supabase user_profiles.
    """
    try:
        # Fetch profile
        res = db.table("user_profiles").select("*").eq("id", current_user["id"]).single().execute()
        if not res.data:
            # Fallback if profile trigger delayed
            return {
                "id": current_user["id"],
                "email": current_user["email"],
                "full_name": "New User",
                "avatar_url": None
            }
        return {
            "id": res.data["id"],
            "email": current_user["email"],
            "full_name": res.data.get("full_name"),
            "avatar_url": res.data.get("avatar_url"),
            "created_at": res.data.get("created_at")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading user profile: {str(e)}"
        )
