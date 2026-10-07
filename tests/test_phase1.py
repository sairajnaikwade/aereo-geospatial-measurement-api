import uuid
from unittest.mock import patch
from app.config import settings
from app.models.file import FileRecord
from app.models.feature import FeatureRecord
from app.db.base import Base


def test_app_config():
    """Verify application configuration loads default settings properly."""
    assert settings.APP_NAME == "Geospatial File Measurement API"
    assert settings.DATABASE_URL.startswith("postgresql")
    assert ".kml" in settings.allowed_extensions_list
    assert ".zip" in settings.allowed_extensions_list
    assert settings.MAX_UPLOAD_SIZE_BYTES > 0


def test_models_metadata():
    """Verify SQLAlchemy models and table schema definitions."""
    tables = Base.metadata.tables
    assert "files" in tables
    assert "features" in tables

    # Verify files columns
    files_cols = tables["files"].columns
    assert "id" in files_cols
    assert "filename" in files_cols
    assert "file_type" in files_cols
    assert "file_size_bytes" in files_cols
    assert "crs" in files_cols
    assert "feature_count" in files_cols
    assert "status" in files_cols
    assert "error_message" in files_cols

    # Verify features columns
    features_cols = tables["features"].columns
    assert "id" in features_cols
    assert "file_id" in features_cols
    assert "feature_index" in features_cols
    assert "geometry_type" in features_cols
    assert "geometry_geojson" in features_cols
    assert "properties" in features_cols
    assert "measurement_type" in features_cols
    assert "measurement_value" in features_cols
    assert "measurement_unit" in features_cols
    assert "projected_crs" in features_cols


def test_root_endpoint(client):
    """Test the root '/' endpoint returns expected service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == settings.APP_NAME
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/health"


def test_health_endpoint_when_db_connected(client):
    """Test health check returns 200 when database connection is simulated healthy."""
    with patch("app.api.v1.health.check_db_connection", return_value=True):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["app_name"] == settings.APP_NAME


def test_health_endpoint_when_db_disconnected(client):
    """Test health check returns 503 degraded when database connection fails."""
    with patch("app.api.v1.health.check_db_connection", return_value=False):
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
