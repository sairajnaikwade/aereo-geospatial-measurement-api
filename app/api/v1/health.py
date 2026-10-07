from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.config import settings
from app.schemas.health import HealthResponse
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application and Database Health Check",
    description="Returns the operational status of the FastAPI service and PostgreSQL connectivity."
)
def get_health():
    """
    Check API health and database readiness.
    """
    is_db_connected = check_db_connection()
    db_status = "connected" if is_db_connected else "disconnected"
    overall_status = "healthy" if is_db_connected else "degraded"

    response_data = HealthResponse(
        status=overall_status,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV
    )

    status_code = status.HTTP_200_OK if is_db_connected else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=response_data.model_dump(mode="json"))
