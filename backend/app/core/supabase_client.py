from supabase import create_client, Client
from app.core.config import settings

# Initialize public anonymous client
supabase_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

# Initialize administrative client (Service Role Key)
# WARNING: Bypasses RLS. Use ONLY in background workers or highly controlled backend services.
supabase_admin_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)


def get_supabase_user_client(access_token: str) -> Client:
    """
    Creates a new Supabase client acting on behalf of a specific user.
    Uses the user's personal JWT access token.
    """
    # Create a fresh client and set the authorization header
    client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY
    )
    # Set session token for RLS to identify the active user
    client.postgrest.auth(access_token)
    return client
