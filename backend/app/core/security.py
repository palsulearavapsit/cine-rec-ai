from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger

ALGORITHM = "HS256"


def verify_supabase_jwt(token: str) -> dict:
    """
    Decodes and validates a Supabase Auth JWT token in FastAPI.
    Tokens are signed with HS256 using the Supabase JWT Secret.
    """
    try:
        # Decode and verify token signature and expiration
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False} # Supabase aud can vary (e.g. 'authenticated')
        )
        
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing user identification ('sub')"
            )
            
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Supabase JWT verification failed: Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again."
        )
    except JWTError as e:
        logger.error(f"Supabase JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )
