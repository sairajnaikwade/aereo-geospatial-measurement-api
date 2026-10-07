import os
import uuid
import tempfile
from typing import Tuple, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    InvalidFileError,
    SecurityViolationError,
    ResourceNotFoundError,
    ProcessingError
)
from app.models.file import FileRecord
from app.models.feature import FeatureRecord
from app.schemas.feature import FeatureMeasurementResponse, FileMeasurementsResponse
from app.geo import (
    validate_file_metadata,
    inspect_file_content,
    safe_extract_shapefile_zip,
    read_kml_file,
    read_shapefile,
    process_geodataframe,
    ParsedGeospatialData
)


def save_upload_to_temp(upload_file: UploadFile, target_dir: str) -> Tuple[str, int]:
    """
    Stream and save an uploaded file to a temporary file while enforcing max upload size.
    Returns (saved_file_path, total_bytes_written).
    """
    filename = upload_file.filename or "uploaded_file"
    clean_name, _ = validate_file_metadata(filename, 1)  # Preliminary name check

    temp_file_path = os.path.join(target_dir, clean_name)
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1 MB chunk

    try:
        with open(temp_file_path, "wb") as f:
            while chunk := upload_file.file.read(chunk_size):
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    raise SecurityViolationError(
                        f"Uploaded file exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.2f} MB."
                    )
                f.write(chunk)
    finally:
        upload_file.file.seek(0)

    if total_bytes == 0:
        raise InvalidFileError("Uploaded file is empty (0 bytes).")

    return temp_file_path, total_bytes


def parse_and_extract_features(file_path: str, ext: str, original_filename: str, file_size: int) -> ParsedGeospatialData:
    """
    Extract geospatial data and measurements from a validated temporary file.
    """
    if ext == ".kml":
        gdf = read_kml_file(file_path)
        return process_geodataframe(
            gdf=gdf,
            filename=original_filename,
            file_type="KML",
            file_size_bytes=file_size
        )
    elif ext == ".zip":
        with safe_extract_shapefile_zip(file_path) as shp_path:
            gdf = read_shapefile(shp_path)
            return process_geodataframe(
                gdf=gdf,
                filename=original_filename,
                file_type="SHAPEFILE_ZIP",
                file_size_bytes=file_size
            )
    else:
        raise InvalidFileError(f"Unsupported file format: {ext}")


class FileService:
    """
    Service layer orchestrating file upload validation, parsing, calculation, and database persistence.
    """

    @staticmethod
    def process_upload(upload_file: UploadFile, db: Session) -> FileRecord:
        """
        Full orchestration pipeline for file upload and measurement persistence:
        1. Validate filename & extension
        2. Stream to isolated temp directory while checking size limit
        3. Verify magic bytes / file content authenticity
        4. Parse KML or Shapefile into GeoDataFrame
        5. Execute CRS reprojection & calculate metric measurements
        6. Persist FileRecord and FeatureRecord entities in atomic DB transaction
        7. Guarantee cleanup of all temporary files
        """
        raw_filename = upload_file.filename or ""
        clean_filename, ext = validate_file_metadata(raw_filename, 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path, file_size = save_upload_to_temp(upload_file, temp_dir)

            # Validate binary content headers (do not trust extension alone)
            file_type = inspect_file_content(temp_file_path, ext)

            # Parse dataset and compute measurements
            parsed_data = parse_and_extract_features(temp_file_path, ext, clean_filename, file_size)

            # Persist to database in atomic transaction
            file_record = FileRecord(
                id=uuid.uuid4(),
                filename=clean_filename,
                file_type=parsed_data.file_type,
                file_size_bytes=parsed_data.file_size_bytes,
                crs=parsed_data.source_crs,
                feature_count=parsed_data.feature_count,
                status="COMPLETED",
                error_message=None
            )

            try:
                db.add(file_record)
                db.flush()  # Flush to generate/bind file_record.id

                # Create feature records
                for feat in parsed_data.features:
                    feature_record = FeatureRecord(
                        id=uuid.uuid4(),
                        file_id=file_record.id,
                        feature_index=feat.feature_index,
                        geometry_type=feat.geometry_type,
                        geometry_geojson=feat.geometry_geojson,
                        properties=feat.properties,
                        measurement_type=feat.measurement_type.value,
                        measurement_value=feat.measurement_value,
                        measurement_unit=feat.measurement_unit.value if feat.measurement_unit else None,
                        projected_crs=feat.projected_crs
                    )
                    db.add(feature_record)

                db.commit()
                db.refresh(file_record)
                logger.info(
                    f"Successfully processed and stored file '{clean_filename}' (ID: {file_record.id}) with {file_record.feature_count} features."
                )
                return file_record

            except Exception as e:
                db.rollback()
                logger.error(f"Failed to persist file processing results: {e}")
                raise ProcessingError(f"Database transaction failed while saving processed data: {str(e)}")

    @staticmethod
    def get_file_by_id(file_id: uuid.UUID, db: Session) -> FileRecord:
        """
        Fetch a FileRecord by its UUID or raise ResourceNotFoundError.
        """
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not file_record:
            raise ResourceNotFoundError(f"File with ID '{file_id}' was not found.")
        return file_record

    @staticmethod
    def get_measurements_by_file_id(file_id: uuid.UUID, db: Session) -> FileMeasurementsResponse:
        """
        Fetch all feature measurements for a given file ID.
        """
        file_record = FileService.get_file_by_id(file_id, db)
        
        feature_responses = [
            FeatureMeasurementResponse(
                id=feat.id,
                feature_index=feat.feature_index,
                geometry_type=feat.geometry_type,
                geometry=feat.geometry_geojson,
                properties=feat.properties,
                measurement_type=feat.measurement_type,
                measurement_value=feat.measurement_value,
                measurement_unit=feat.measurement_unit,
                projected_crs=feat.projected_crs
            )
            for feat in file_record.features
        ]

        return FileMeasurementsResponse(
            file_id=file_record.id,
            filename=file_record.filename,
            feature_count=file_record.feature_count,
            crs=file_record.crs,
            status=file_record.status,
            features=feature_responses
        )
