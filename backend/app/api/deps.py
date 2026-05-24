from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.core.security import verify_supabase_jwt
from app.core.supabase_client import get_supabase_user_client

security_scheme = HTTPBearer()


def get_token(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> str:
    """
    Extracts the raw Bearer JWT string from the request Authorization Header.
    """
    return credentials.credentials


def get_current_user(token: str = Depends(get_token)) -> dict:
    """
    Dependency that decodes the Supabase JWT and yields user properties.
    Validates signature, aud, and expiration times.
    """
    payload = verify_supabase_jwt(token)
    
    # Standard Supabase Auth JWT claims
    user_id = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role", "authenticated")
    
    return {
        "id": user_id,
        "email": email,
        "role": role,
        "token": token
    }


def get_supabase_client(current_user: dict = Depends(get_current_user)) -> Client:
    """
    Yields a Supabase client scoped to the authenticated user's privileges.
    Any database queries run through this client will trigger Row Level Security (RLS) policies
    evaluating auth.uid() = current_user.id.
    """
    return get_supabase_user_client(current_user["token"])
