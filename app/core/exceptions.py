from typing import Any, Optional, Dict
from fastapi import HTTPException, status


class GeoAppException(Exception):
    """Base exception for all application-level errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidFileError(GeoAppException):
    """Raised when an uploaded file format or content is invalid."""
    pass


class SecurityViolationError(GeoAppException):
    """Raised when security constraints (e.g. zip slip, oversized file) are breached."""
    pass


class ResourceNotFoundError(GeoAppException):
    """Raised when a requested database entity is not found."""
    pass


class ProcessingError(GeoAppException):
    """Raised when geospatial parsing or reprojection encounters an unrecoverable failure."""
    pass
