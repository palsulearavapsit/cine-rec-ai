from fastapi import APIRouter
from app.api.v1.endpoints import auth, projects, movies, reels

api_router = APIRouter()

# Register sub-modules under standard V1 structures
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_router.include_router(reels.router, prefix="/reels", tags=["reels"])
