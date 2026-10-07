import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db, SessionLocal
from app.models.file import FileRecord
from app.models.feature import FeatureRecord
from tests.test_helpers import (
    create_sample_kml_content,
    create_sample_shapefile_zip_bytes,
    create_zip_slip_archive_bytes
)


@pytest.fixture
def db_session():
    """Database session fixture that provides a clean session per test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_post_valid_kml(client: TestClient, db_session: Session):
    """Test successful upload and processing of a valid KML file."""
    kml_content = create_sample_kml_content("""
    <Placemark>
      <name>Survey Zone</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5946,12.9716,0
              77.5956,12.9716,0
              77.5956,12.9726,0
              77.5946,12.9726,0
              77.5946,12.9716,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    """)

    files = {"file": ("survey_zone.kml", io.BytesIO(kml_content.encode("utf-8")), "application/vnd.google-earth.kml+xml")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "survey_zone.kml"
    assert data["feature_count"] == 1
    assert data["crs"] == "EPSG:4326"
    assert data["status"] == "COMPLETED"

    # Verify database persistence
    file_id = uuid.UUID(data["id"])
    file_record = db_session.query(FileRecord).filter(FileRecord.id == file_id).first()
    assert file_record is not None
    assert len(file_record.features) == 1
    assert file_record.features[0].geometry_type == "Polygon"
    assert file_record.features[0].measurement_type == "AREA"
    assert file_record.features[0].measurement_value > 0
    assert file_record.features[0].measurement_unit == "sq_meters"


def test_post_valid_shapefile_zip(client: TestClient, db_session: Session):
    """Test successful upload and processing of a Shapefile ZIP archive."""
    zip_bytes = create_sample_shapefile_zip_bytes(crs="EPSG:4326")
    files = {"file": ("cadastral_plots.zip", io.BytesIO(zip_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "cadastral_plots.zip"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"

    file_id = uuid.UUID(data["id"])
    file_record = db_session.query(FileRecord).filter(FileRecord.id == file_id).first()
    assert file_record is not None
    assert file_record.file_type == "SHAPEFILE_ZIP"
    assert len(file_record.features) == 2


def test_post_unsupported_file_extension(client: TestClient):
    """Test uploading an unsupported extension returns 400 Bad Request."""
    files = {"file": ("dataset.csv", io.BytesIO(b"id,val\n1,10"), "text/csv")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file extension" in data["message"]


def test_post_malformed_kml(client: TestClient):
    """Test uploading malformed/broken KML XML returns 400 Bad Request."""
    files = {"file": ("broken.kml", io.BytesIO(b"<?xml><kml><Placemark><unclosed>"), "application/xml")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "Malformed or unreadable KML" in data["message"] or "Invalid KML file" in data["message"]


def test_post_invalid_zip_missing_components(client: TestClient):
    """Test Shapefile ZIP missing .shx companion returns 400 Bad Request."""
    zip_bytes = create_sample_shapefile_zip_bytes(include_shx=False)
    files = {"file": ("missing_shx.zip", io.BytesIO(zip_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "Missing mandatory companion file" in data["message"]


def test_post_malicious_zip_slip(client: TestClient):
    """Test Zip Slip path traversal archive returns 400 Bad Request."""
    malicious_bytes = create_zip_slip_archive_bytes()
    files = {"file": ("malicious.zip", io.BytesIO(malicious_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "Path traversal detected" in data["message"] or "Directory traversal attack" in data["message"]


def test_get_existing_file_info(client: TestClient):
    """Test GET /api/files/{id}/ returns complete file metadata."""
    # First upload a file
    kml_content = create_sample_kml_content("<Placemark><Point><coordinates>77.59,12.97,0</coordinates></Point></Placemark>")
    files = {"file": ("point_survey.kml", io.BytesIO(kml_content.encode("utf-8")), "application/vnd.google-earth.kml+xml")}
    upload_res = client.post("/api/files/", files=files)
    file_id = upload_res.json()["id"]

    # Now query metadata
    response = client.get(f"/api/files/{file_id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == file_id
    assert data["filename"] == "point_survey.kml"
    assert data["file_type"] == "KML"
    assert data["feature_count"] == 1
    assert data["status"] == "COMPLETED"
    assert "created_at" in data


def test_get_nonexistent_file_returns_404(client: TestClient):
    """Test GET /api/files/{id}/ with non-existent ID returns 404 Not Found."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/files/{random_id}/")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["message"].lower()


def test_get_measurements_endpoint(client: TestClient):
    """Test GET /api/files/{id}/measurements/ returns features and calculated metric measurements."""
    kml_content = create_sample_kml_content("""
    <Placemark>
      <name>Road Corridor</name>
      <LineString>
        <coordinates>
          77.5946,12.9716,0
          77.6046,12.9716,0
        </coordinates>
      </LineString>
    </Placemark>
    """)
    files = {"file": ("road.kml", io.BytesIO(kml_content.encode("utf-8")), "application/vnd.google-earth.kml+xml")}
    upload_res = client.post("/api/files/", files=files)
    file_id = upload_res.json()["id"]

    # Query measurements
    response = client.get(f"/api/files/{file_id}/measurements/")
    assert response.status_code == 200
    data = response.json()

    assert data["file_id"] == file_id
    assert data["filename"] == "road.kml"
    assert data["feature_count"] == 1
    assert len(data["features"]) == 1

    feature = data["features"][0]
    assert feature["feature_index"] == 0
    assert feature["geometry_type"] == "LineString"
    assert feature["measurement_type"] == "LENGTH"
    assert feature["measurement_value"] > 0
    assert feature["measurement_unit"] == "meters"
    assert feature["projected_crs"].startswith("EPSG:")
    assert feature["geometry"]["type"] == "LineString"
    assert feature["properties"].get("Name") == "Road Corridor" or feature["properties"].get("name") == "Road Corridor"


def test_get_measurements_nonexistent_file_returns_404(client: TestClient):
    """Test GET /api/files/{id}/measurements/ for missing file returns 404."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/files/{random_id}/measurements/")

    assert response.status_code == 404


def test_transaction_rollback_on_persistence_failure(client: TestClient, db_session: Session):
    """
    Explicit test to verify transaction rollback:
    If a database error occurs during feature persistence or commit, the transaction
    is rolled back, leaving zero orphan FileRecord or FeatureRecord in PostgreSQL.
    """
    from unittest.mock import patch
    from sqlalchemy.orm import Session

    kml_content = create_sample_kml_content("""
    <Placemark>
      <name>Rollback Zone</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5946,12.9716,0
              77.5956,12.9716,0
              77.5956,12.9726,0
              77.5946,12.9726,0
              77.5946,12.9716,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    """)

    # Count initial records
    initial_file_count = db_session.query(FileRecord).count()
    initial_feature_count = db_session.query(FeatureRecord).count()

    files = {"file": ("rollback_test.kml", io.BytesIO(kml_content.encode("utf-8")), "application/vnd.google-earth.kml+xml")}

    # Simulate database commit failure
    with patch.object(Session, "commit", side_effect=Exception("Simulated Database I/O Disk Error")):
        response = client.post("/api/files/", files=files)

    # 1. Confirm the request failed gracefully with 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Database transaction failed" in data["message"]

    # 2. Confirm no partial FileRecord exists in PostgreSQL
    after_file_count = db_session.query(FileRecord).count()
    assert after_file_count == initial_file_count
    assert db_session.query(FileRecord).filter(FileRecord.filename == "rollback_test.kml").first() is None

    # 3. Confirm no orphan FeatureRecord exists in PostgreSQL
    after_feature_count = db_session.query(FeatureRecord).count()
    assert after_feature_count == initial_feature_count
