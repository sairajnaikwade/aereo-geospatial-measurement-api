import os
import tempfile
import pytest
from app.geo.validator import validate_file_metadata, inspect_file_content
from app.geo.zip_handler import safe_extract_shapefile_zip
from app.core.exceptions import InvalidFileError, SecurityViolationError
from tests.test_helpers import (
    create_sample_shapefile_zip_bytes,
    create_zip_slip_archive_bytes,
    create_sample_kml_content
)


def test_validate_file_metadata_valid():
    """Test valid filenames and sizes pass validation."""
    name, ext = validate_file_metadata("survey_data.kml", 1024)
    assert name == "survey_data.kml"
    assert ext == ".kml"

    name, ext = validate_file_metadata("boundary.ZIP", 2048)
    assert name == "boundary.ZIP"
    assert ext == ".zip"


def test_validate_file_metadata_unsupported_extension():
    """Test unsupported extensions are rejected."""
    with pytest.raises(InvalidFileError, match="Unsupported file extension"):
        validate_file_metadata("data.geojson", 1024)

    with pytest.raises(InvalidFileError, match="Unsupported file extension"):
        validate_file_metadata("script.py", 1024)


def test_validate_file_metadata_oversized():
    """Test files exceeding MAX_UPLOAD_SIZE_BYTES are rejected."""
    oversized = 30 * 1024 * 1024  # 30 MB
    with pytest.raises(SecurityViolationError, match="exceeds the maximum allowed limit"):
        validate_file_metadata("large.zip", oversized)


def test_validate_file_metadata_empty():
    """Test zero-byte files are rejected."""
    with pytest.raises(InvalidFileError, match="Uploaded file is empty"):
        validate_file_metadata("empty.kml", 0)


def test_inspect_file_content_fake_extension():
    """Test file content inspection rejects non-ZIP files disguised as .zip."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(b"This is just plain text, not a zip file.")
        f_path = f.name

    try:
        with pytest.raises(InvalidFileError, match="Invalid ZIP archive"):
            inspect_file_content(f_path, ".zip")
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_inspect_file_content_fake_kml():
    """Test file content inspection rejects non-XML files disguised as .kml."""
    with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as f:
        f.write(b"random binary data without xml tags")
        f_path = f.name

    try:
        with pytest.raises(InvalidFileError, match="Invalid KML file"):
            inspect_file_content(f_path, ".kml")
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_safe_zip_extraction_valid():
    """Test valid shapefile ZIP extracts and locates .shp."""
    zip_bytes = create_sample_shapefile_zip_bytes()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(zip_bytes)
        f_path = f.name

    try:
        with safe_extract_shapefile_zip(f_path) as shp_path:
            assert os.path.exists(shp_path)
            assert shp_path.endswith(".shp")
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_safe_zip_extraction_missing_shx():
    """Test ZIP missing .shx is rejected."""
    zip_bytes = create_sample_shapefile_zip_bytes(include_shx=False)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(zip_bytes)
        f_path = f.name

    try:
        with pytest.raises(InvalidFileError, match="Missing mandatory companion file.*.shx"):
            with safe_extract_shapefile_zip(f_path):
                pass
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_safe_zip_extraction_missing_dbf():
    """Test ZIP missing .dbf is rejected."""
    zip_bytes = create_sample_shapefile_zip_bytes(include_dbf=False)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(zip_bytes)
        f_path = f.name

    try:
        with pytest.raises(InvalidFileError, match="Missing mandatory companion file.*.dbf"):
            with safe_extract_shapefile_zip(f_path):
                pass
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_safe_zip_extraction_missing_shp():
    """Test ZIP missing .shp is rejected."""
    zip_bytes = create_sample_shapefile_zip_bytes(include_shp=False)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(zip_bytes)
        f_path = f.name

    try:
        with pytest.raises(InvalidFileError, match="No Shapefile .* found in the uploaded ZIP archive"):
            with safe_extract_shapefile_zip(f_path):
                pass
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_safe_zip_extraction_zip_slip():
    """Test Zip Slip path traversal archive is detected and rejected."""
    malicious_bytes = create_zip_slip_archive_bytes()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(malicious_bytes)
        f_path = f.name

    try:
        with pytest.raises(SecurityViolationError, match="Path traversal detected|Directory traversal attack"):
            with safe_extract_shapefile_zip(f_path):
                pass
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)
