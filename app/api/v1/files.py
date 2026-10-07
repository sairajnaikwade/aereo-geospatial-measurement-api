import uuid
from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.file_service import FileService
from app.schemas.file import FileResponse, FileUploadResponse
from app.schemas.feature import FileMeasurementsResponse

router = APIRouter(prefix="/files", tags=["Files & Measurements"])


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Process Geospatial File",
    description="Accepts a KML (.kml) or Shapefile ZIP archive (.zip), extracts features, calculates metric measurements (Polygon area / LineString length), and persists metadata to the database."
)
def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.kml or .zip containing Shapefile)"),
    db: Session = Depends(get_db)
):
    """
    Upload and process a geospatial file.
    """
    file_record = FileService.process_upload(upload_file=file, db=db)
    return file_record


@router.get(
    "/{id}/",
    response_model=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Uploaded File Information",
    description="Returns metadata and processing status for an uploaded file by its UUID."
)
def get_file_info(
    id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve file metadata and processing summary.
    """
    return FileService.get_file_by_id(file_id=id, db=db)


@router.get(
    "/{id}/measurements/",
    response_model=FileMeasurementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Feature Measurements for Uploaded File",
    description="Returns all extracted features with their calculated metric measurements (area in m² or length in meters), GeoJSON geometries, and properties."
)
def get_file_measurements(
    id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve measurements for features in the specified file.
    """
    return FileService.get_measurements_by_file_id(file_id=id, db=db)
