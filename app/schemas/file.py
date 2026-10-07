import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FileBase(BaseModel):
    """Base schema for file metadata."""
    filename: str = Field(..., example="survey_boundary.kml")
    file_type: str = Field(..., example="KML")
    file_size_bytes: int = Field(..., example=102400)
    crs: Optional[str] = Field(None, example="EPSG:4326")
    feature_count: int = Field(0, example=5)
    status: str = Field("COMPLETED", example="COMPLETED")
    error_message: Optional[str] = Field(None, example=None)


class FileUploadResponse(BaseModel):
    """
    Summary response returned upon successful file upload and processing.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., example="3fa85f64-5717-4562-b3fc-2c963f66afa6")
    filename: str = Field(..., example="survey_boundary.kml")
    feature_count: int = Field(..., example=5)
    crs: Optional[str] = Field(None, example="EPSG:4326")
    status: str = Field(..., example="COMPLETED")


class FileResponse(BaseModel):
    """
    Full file information response returned by GET /api/files/{id}/.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., example="3fa85f64-5717-4562-b3fc-2c963f66afa6")
    filename: str = Field(..., example="survey_boundary.kml")
    file_type: str = Field(..., example="KML")
    file_size_bytes: int = Field(..., example=102400)
    crs: Optional[str] = Field(None, example="EPSG:4326")
    feature_count: int = Field(..., example=5)
    status: str = Field(..., example="COMPLETED")
    error_message: Optional[str] = Field(None, example=None)
    created_at: datetime = Field(..., example="2026-10-07T12:00:00Z")
    updated_at: datetime = Field(..., example="2026-10-07T12:00:00Z")
