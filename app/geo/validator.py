import os
import zipfile
from typing import Tuple
from app.config import settings
from app.core.exceptions import InvalidFileError, SecurityViolationError


def validate_file_metadata(filename: str, file_size: int) -> Tuple[str, str]:
    """
    Validate filename extension and file size constraints.
    Returns normalized (clean_filename, extension).
    """
    if not filename or not filename.strip():
        raise InvalidFileError("Filename cannot be empty.")

    clean_filename = os.path.basename(filename.strip())
    _, ext = os.path.splitext(clean_filename)
    ext = ext.lower()

    allowed = settings.allowed_extensions_list
    if ext not in allowed:
        raise InvalidFileError(
            f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(allowed)}."
        )

    if file_size <= 0:
        raise InvalidFileError("Uploaded file is empty (0 bytes).")

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise SecurityViolationError(
            f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds the maximum allowed limit of {max_mb:.2f} MB."
        )

    return clean_filename, ext


def inspect_file_content(file_path: str, expected_ext: str) -> str:
    """
    Inspect the actual file header / binary content to verify file type authenticity.
    Does not rely on file extension alone.
    Returns normalized file_type: 'KML' or 'SHAPEFILE_ZIP'.
    """
    if not os.path.isfile(file_path):
        raise InvalidFileError(f"File not found at path: {file_path}")

    # Read first 1024 bytes to check magic headers
    with open(file_path, "rb") as f:
        header = f.read(1024)

    if expected_ext == ".zip":
        # Standard PKZIP magic header check: PK\x03\x04 or PK\x05\x06 (empty zip) or PK\x07\x08 (spanned)
        if not (header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06")):
            raise InvalidFileError("Invalid ZIP archive: File does not contain a valid ZIP header.")
        
        # Test ZIP readability
        if not zipfile.is_zipfile(file_path):
            raise InvalidFileError("Corrupted ZIP file: Cannot be opened as a valid ZIP archive.")
            
        return "SHAPEFILE_ZIP"

    elif expected_ext == ".kml":
        # Check if header contains XML / KML indicators
        header_str = header.decode("utf-8", errors="ignore").lower()
        if "<kml" not in header_str and "<?xml" not in header_str:
            raise InvalidFileError(
                "Invalid KML file: File content does not contain valid XML/KML markup header."
            )
        return "KML"

    else:
        raise InvalidFileError(f"Unsupported file extension: {expected_ext}")
