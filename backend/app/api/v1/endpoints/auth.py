from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.api.deps import get_current_user, get_supabase_client
from app.core.config import settings
from jose import jwt

router = APIRouter()


@router.get("/config", response_model=dict)
async def get_auth_config():
    """
    Exposes the public Supabase URL and Anon Key required for client-side login/signup.
    """
    return {
        "supabase_url": settings.SUPABASE_URL,
        "supabase_anon_key": settings.SUPABASE_ANON_KEY
    }


@router.post("/bypass", response_model=dict)
async def bypass_auth():
    """
    Generates a mock valid signed JWT token for a local developer session.
    Bypasses manual authentication prompts in development.
    """
    try:
        payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "email": "local-developer@cinerec.ai",
            "role": "authenticated",
            # Expire in 10 years (far future)
            "exp": 2095192419
        }
        token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
        return {
            "access_token": token,
            "email": "local-developer@cinerec.ai"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate local developer bypass token: {str(e)}"
        )


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
