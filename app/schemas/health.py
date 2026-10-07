from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Health check status response schema.
    """
    status: str = Field(..., example="healthy")
    database: str = Field(..., example="connected")
    timestamp: datetime = Field(..., example="2026-10-07T12:00:00Z")
    app_name: str = Field(..., example="Geospatial File Measurement API")
    environment: str = Field(..., example="development")
