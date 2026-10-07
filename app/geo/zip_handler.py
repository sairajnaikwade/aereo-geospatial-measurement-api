import os
import zipfile
import tempfile
from typing import List, Tuple, Generator
from contextlib import contextmanager
from app.core.exceptions import InvalidFileError, SecurityViolationError
from app.core.logging import logger


REQUIRED_SHAPEFILE_EXTENSIONS = {".shp", ".shx", ".dbf"}


def validate_zip_members(zip_ref: zipfile.ZipFile, target_dir: str) -> List[zipfile.ZipInfo]:
    """
    Validate all members in a ZIP archive to prevent Zip Slip (Path Traversal)
    and ensure extracted files remain strictly within the target directory.
    """
    resolved_target_dir = os.path.abspath(target_dir)
    safe_members: List[zipfile.ZipInfo] = []

    for member in zip_ref.infolist():
        # Prevent absolute paths or suspicious prefixes
        filename = member.filename
        if filename.startswith("/") or filename.startswith("\\") or ".." in filename:
            raise SecurityViolationError(
                f"Suspicious path in ZIP archive: '{filename}'. Path traversal detected."
            )

        # Resolve destination path
        target_path = os.path.abspath(os.path.join(resolved_target_dir, filename))
        
        # Verify that target_path starts with target_dir
        if not target_path.startswith(resolved_target_dir + os.sep) and target_path != resolved_target_dir:
            raise SecurityViolationError(
                f"Directory traversal attack detected in ZIP archive: '{filename}'."
            )

        safe_members.append(member)

    return safe_members


def locate_shapefile_in_dir(extract_dir: str) -> str:
    """
    Scan the extracted directory to locate the primary .shp file and ensure
    that all mandatory Shapefile companion files (.shx, .dbf) exist.
    """
    shp_files = []
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.lower().endswith(".shp"):
                shp_files.append(os.path.join(root, file))

    if not shp_files:
        raise InvalidFileError(
            "No Shapefile (.shp) found in the uploaded ZIP archive."
        )

    if len(shp_files) > 1:
        logger.info(f"Multiple .shp files found in archive. Using primary: {shp_files[0]}")

    primary_shp = shp_files[0]
    base_name, _ = os.path.splitext(primary_shp)

    # Check required companion files
    missing_extensions = []
    for ext in REQUIRED_SHAPEFILE_EXTENSIONS:
        # Check both lower and upper case
        candidate_lower = base_name + ext.lower()
        candidate_upper = base_name + ext.upper()
        if not (os.path.isfile(candidate_lower) or os.path.isfile(candidate_upper)):
            missing_extensions.append(ext)

    if missing_extensions:
        raise InvalidFileError(
            f"Shapefile is incomplete. Missing mandatory companion file(s): {', '.join(sorted(missing_extensions))}."
        )

    return primary_shp


@contextmanager
def safe_extract_shapefile_zip(zip_path: str) -> Generator[str, None, None]:
    """
    Context manager that safely extracts a Shapefile ZIP into an isolated
    temporary directory, validates against Zip Slip, locates the primary .shp file,
    and guarantees cleanup on exit.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Validate members before extraction
                safe_members = validate_zip_members(zf, temp_dir)
                zf.extractall(path=temp_dir, members=safe_members)

            # Locate the valid .shp
            shp_path = locate_shapefile_in_dir(temp_dir)
            yield shp_path

        except zipfile.BadZipFile as e:
            raise InvalidFileError(f"Corrupted or invalid ZIP file: {str(e)}")
        finally:
            logger.debug(f"Temporary extraction directory cleaned up: {temp_dir}")
