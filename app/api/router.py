from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.files import router as files_router

api_router = APIRouter()

# Mount health routes at /api/health
api_router.include_router(health_router, prefix="", tags=["Health"])

# Mount file upload & measurement routes at /api/files
api_router.include_router(files_router, prefix="", tags=["Files & Measurements"])
