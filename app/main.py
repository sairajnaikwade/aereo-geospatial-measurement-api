from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logging import setup_logging, logger
from app.core.exceptions import GeoAppException
from app.api.router import api_router
from app.api.v1.health import router as health_router
from app.db.base import Base
from app.db.session import engine, check_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: initialize logging and database tables on startup.
    """
    setup_logging()
    logger.info(f"Starting up {settings.APP_NAME} in [{settings.APP_ENV}] mode...")

    # Attempt to initialize PostgreSQL tables if database is reachable
    try:
        if check_db_connection():
            logger.info("Database reachable. Ensuring tables are created...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully.")
        else:
            logger.warning("Database not immediately reachable during startup. Tables will be verified on request.")
    except Exception as e:
        logger.error(f"Error during startup table initialization: {e}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


# Initialize FastAPI Application
app = FastAPI(
    title=settings.APP_NAME,
    description="A production-ready REST API for uploading geospatial files (KML, Shapefile ZIP), reprojecting to metric CRS, and computing measurements.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler for custom domain exceptions
@app.exception_handler(GeoAppException)
async def geo_app_exception_handler(request: Request, exc: GeoAppException):
    from app.core.exceptions import ResourceNotFoundError
    status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, ResourceNotFoundError) else status.HTTP_400_BAD_REQUEST
    logger.warning(f"Domain error processing {request.method} {request.url.path}: {exc.message} (HTTP {status_code})")
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )


# Mount Health Router directly for root /health probes
app.include_router(health_router, prefix="", tags=["Health"])

# Mount Main Versioned API Router at /api
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint returning service metadata and documentation links.
    """
    return {
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health",
        "api_v1_prefix": settings.API_V1_STR
    }
