from contextlib import asynccontextmanager

from supabase import AsyncClient, acreate_client

from app.config import settings

key: str = settings.SUPABASE_KEY
url: str = settings.SUPABASE_URL

# Global reference
supabase_client: AsyncClient | None = None

async def init_supabase():
    """Initialize Supabase client on app startup"""
    global supabase_client
    supabase_client = await acreate_client(url, key)

async def close_supabase():
    """Close Supabase client on app shutdown"""
    global supabase_client
    if supabase_client:
        await supabase_client.close()
        supabase_client = None

@asynccontextmanager
async def database_session():
    """Async context manager for database session"""
    try:
        if supabase_client is None:
            raise RuntimeError("Supabase client not initialized")
        yield supabase_client
    except Exception as e:
        raise RuntimeError(f"Error in supabase context: {e}") from e
