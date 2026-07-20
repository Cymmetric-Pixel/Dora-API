"""FastAPI application entry point."""
import app.database.client as db

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_supabase()
    yield
    await db.close_supabase()

app = FastAPI(
    title="Dora API",
    description="Serves Aquifer biblical content related to highlighted Bible text",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.ENVIRONMENT == "development",
    )
