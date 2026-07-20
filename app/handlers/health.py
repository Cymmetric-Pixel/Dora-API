"""Health and ping endpoints."""

async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


async def ping():
    """Simple liveness check."""
    return {"message": "pong"}
