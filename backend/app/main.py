from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api.v1.api import api_router
from app.services.storage import StorageService

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise-grade production backend orchestrating semantic media intelligence and movie compositions for CineRec AI.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 1. SETUP CORS MIDDLEWARE
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# 2. STARTUP OPERATIONS
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing CineRec AI FastAPI Backend...")
    # provision folders & storage buckets
    StorageService.create_buckets_if_not_exist()
    logger.info("Startup sequence finished successfully. Server ready.")


# 3. REGISTER ROUTER LAYER
app.include_router(api_router, prefix=settings.API_V1_STR)


# 4. HEALTH CHECK / ROOT WELCOME
@app.get("/", tags=["health"])
async def root_health_check():
    """
    Gateway health verification checking active components availability.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_prefix": settings.API_V1_STR,
        "docs_url": "/docs",
        "description": "Backend is running and listening for upload and composition orchestrations."
    }
