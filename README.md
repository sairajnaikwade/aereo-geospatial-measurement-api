# Geospatial File Measurement API

A robust, production-grade backend REST API built with **FastAPI**, **PostgreSQL**, and **GeoPandas** that accepts geospatial files (KML and Shapefile ZIP archives), safely parses and reprojects features to optimal metric coordinate reference systems (UTM), calculates geometric measurements (Polygon area and LineString length), and persists results with full transaction safety.

Developed as a technical assignment for the **Software Development Engineer (SDE) Intern** position at **AEREO**.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [Technology Stack](#technology-stack)
4. [Architecture & Project Structure](#architecture--project-structure)
5. [File Processing Flow](#file-processing-flow)
6. [CRS Strategy & Metric Measurements](#crs-strategy--metric-measurements)
7. [Security & Robustness](#security--robustness)
8. [API Documentation & Examples](#api-documentation--examples)
9. [Running Locally](#running-locally)
10. [Docker & Containerized Setup](#docker--containerized-setup)
11. [Automated Testing](#automated-testing)
12. [Sample Data & Verification Script](#sample-data--verification-script)
13. [Design Decisions & Trade-Offs](#design-decisions--trade-offs)
14. [Limitations & Future Scope](#limitations--future-scope)
15. [AEREO Assignment Alignment Matrix](#aereo-assignment-alignment-matrix)

---

## Project Overview

Geospatial data ingested from drone surveys, satellite imagery, and GIS tools comes in varying formats and coordinate systems. The **Geospatial File Measurement API** provides a backend service to:
1. Ingest **KML** (`.kml`) and **ESRI Shapefile ZIP archives** (`.zip`).
2. Safely parse and extract feature records, geometries, and attribute properties.
3. Automatically determine the optimal local **Universal Transverse Mercator (UTM)** projection for geographic datasets (such as standard `EPSG:4326` WGS84).
4. Perform accurate metric measurements:
   - **Polygon / MultiPolygon** $\rightarrow$ Area in square meters ($m^2$)
   - **LineString / MultiLineString** $\rightarrow$ Length in meters ($m$)
   - **Point / MultiPoint** $\rightarrow$ No measurement required (`measurement_type: NONE`, `value: null`)
5. Handle invalid geometries (e.g. self-intersecting polygons) and unsupported types (e.g. `GeometryCollection`) explicitly without crashing or silently altering input coordinates.
6. Persist file metadata and feature records into a relational **PostgreSQL** database with rollback guarantees on any failure.

---

## Key Features

- **FastAPI Framework**: High performance, automatic OpenAPI / Swagger documentation, and strict Pydantic v2 data validation.
- **Relational PostgreSQL Persistence**: SQLAlchemy 2.0 ORM with 1-to-many relationship mapping (`files` $\rightarrow$ `features`).
- **CRS-Aware Measurement Engine**: Avoids invalid degree-based distance/area calculations by reprojecting geographic coordinates to local metric UTM projections.
- **Strict Security Protections**: Defends against **Zip Slip / Path Traversal** vulnerabilities, restricts file extensions, enforces strict upload size quotas, and inspects file headers/magic bytes.
- **Zero Disk Residue**: Temporary uploads and extracted shapefile directories are managed using Python context managers (`tempfile.TemporaryDirectory`) ensuring immediate cleanup.
- **Full Transaction Safety**: Atomic database transactions guarantee zero orphan files or partial feature records if processing or database persistence fails.
- **100% Automated Test Coverage**: 44 automated pytest unit and integration tests covering security, parsing, reprojection, measurements, and HTTP APIs.
- **Docker Compose Ready**: One-command startup deploying PostgreSQL alongside the FastAPI backend service.

---

## Technology Stack

| Technology | Purpose | Justification |
| :--- | :--- | :--- |
| **Python 3.11+ / 3.13** | Core Language | Industry standard for geospatial data processing and backend development. |
| **FastAPI** | Web Framework | High throughput, asynchronous/synchronous support, automatic OpenAPI/Swagger docs, and native Pydantic validation. |
| **PostgreSQL** | Relational Database | Reliable, ACID-compliant database for storing file metadata, features, and JSON attributes. |
| **SQLAlchemy 2.0** | ORM & DB Access | Type-safe declarative database models, relationship cascades, and connection pooling. |
| **GeoPandas & Fiona** | Geospatial Data Parsing | Standard Python geospatial library for reading Shapefile layers and KML placemarks. |
| **Shapely 2.0** | Geometric Analysis | High-performance computational geometry for topological validity checks and planar measurements. |
| **PyProj** | Geodetic Transformations | Cartographic projections and coordinate transformations based on the PROJ engine. |
| **Pydantic V2** | Schema Validation | Robust serialization, deserialization, and request/response contracts. |
| **Pytest & HTTPX** | Automated Testing | Unit tests and end-to-end integration tests for APIs, security boundaries, and geospatial logic. |
| **Docker & Compose** | Containerization | Reproducible environments packaging GDAL/PROJ C-libraries and PostgreSQL. |

---

## Architecture & Project Structure

The project follows a clean **Layered Architecture** ensuring clear separation of concerns between HTTP routing, business orchestration, pure geospatial domain logic, and database persistence.

```mermaid
flowchart TD
    Client([HTTP Client / Postman / Swagger]) -->|Multipart Upload / Queries| APILayer[API Layer - app/api/]
    APILayer --> ServiceLayer[Service Layer - app/services/]
    
    subgraph GeoEngine [Geospatial Processing Engine - app/geo/]
        Validator[Validator & Security - validator.py / zip_handler.py]
        Parser[KML & Shapefile Parser - parser.py]
        CRSManager[CRS & Reprojection Engine - crs.py]
        MeasEngine[Measurement Engine - measurements.py]
    end

    ServiceLayer --> Validator
    ServiceLayer --> Parser
    Parser --> CRSManager
    CRSManager --> MeasEngine
    
    ServiceLayer -->|Atomic Transaction| DBLayer[(PostgreSQL Database)]
```

### Folder Structure

```
aereo-geospatial-measurement-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI entrypoint, lifespan manager, CORS, global exception handlers
│   ├── config.py                # Pydantic Settings (ENV variables, upload limits, Postgres URL)
│   │
│   ├── api/                     # HTTP API Routing
│   │   ├── __init__.py
│   │   ├── router.py            # Aggregated API router mounted at /api
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py        # Health probe endpoint (/health & /api/health)
│   │       └── files.py         # POST /api/files/, GET /api/files/{id}/, GET /api/files/{id}/measurements/
│   │
│   ├── core/                    # Cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── exceptions.py        # Domain exceptions (InvalidFileError, SecurityViolationError, etc.)
│   │   └── logging.py           # Structured application logging
│   │
│   ├── db/                      # Database connection & session lifecycle
│   │   ├── __init__.py
│   │   ├── base.py              # SQLAlchemy 2.0 DeclarativeBase & TimestampMixin
│   │   └── session.py           # Engine connection pool, sessionmaker, get_db dependency
│   │
│   ├── models/                  # SQLAlchemy ORM Database Models
│   │   ├── __init__.py
│   │   ├── file.py              # FileRecord model (files table)
│   │   └── feature.py           # FeatureRecord model (features table)
│   │
│   ├── schemas/                 # Pydantic Request/Response DTOs
│   │   ├── __init__.py
│   │   ├── health.py            # HealthResponse schema
│   │   ├── file.py              # FileResponse, FileUploadResponse schemas
│   │   └── feature.py           # FeatureMeasurementResponse, FileMeasurementsResponse schemas
│   │
│   ├── geo/                     # Geospatial Domain Logic (Pure & Decoupled)
│   │   ├── __init__.py
│   │   ├── types.py             # Dataclasses & Enums (MeasurementType, MeasurementUnit, etc.)
│   │   ├── validator.py         # File metadata & binary content inspection
│   │   ├── zip_handler.py       # Safe ZIP extraction with Zip Slip protection
│   │   ├── crs.py               # Dynamic UTM determination & metric reprojection
│   │   ├── measurements.py      # Area ($m^2$) and Length ($m$) calculator
│   │   ├── geojson.py           # Shapely to GeoJSON dictionary serializer
│   │   └── parser.py            # KML & Shapefile GeoDataFrame parser
│   │
│   └── services/                # Business Workflow Orchestration
│       ├── __init__.py
│       └── file_service.py      # Pipeline orchestration and atomic DB transactions
│
├── tests/                       # Automated Pytest Suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest TestClient fixture
│   ├── test_helpers.py          # Synthetic Shapefile & malicious ZIP fixture generators
│   ├── test_phase1.py           # Infrastructure & config tests
│   ├── test_validation_and_security.py # File validation, magic header & Zip Slip tests
│   ├── test_kml_shapefile_parser.py    # KML & Shapefile parsing tests
│   ├── test_crs_reprojection.py        # Dynamic UTM zone calculation tests
│   ├── test_measurements.py            # Area, Length, Point, and invalid geometry tests
│   └── test_api_endpoints.py           # End-to-end API upload, query, & rollback tests
│
├── sample_data/                 # Deterministic sample datasets
│   ├── sample_polygons.kml      # Sample KML with Polygon placemark
│   ├── sample_lines.kml         # Sample KML with LineString placemark
│   ├── sample_shapefile.zip     # Sample ESRI Shapefile archive (.shp, .shx, .dbf, .prj)
│   ├── generate_samples.py      # Script to rebuild sample files
│   └── verify_api.py            # End-to-end verification script
│
├── Dockerfile                   # Multi-stage image with GDAL/GEOS/PROJ system libraries
├── docker-compose.yml           # Multi-container setup (PostgreSQL 15 + FastAPI app)
├── requirements.txt             # Project Python dependencies
├── pytest.ini                   # Pytest configuration
├── .env.example                 # Environment variable template
└── .gitignore                   # Git exclusion rules
```

---

## File Processing Flow

```
1. Client POSTs multipart/form-data to /api/files/
   │
2. Filename & Size Validation (app/geo/validator.py)
   ├── Check extension against allowed list (.kml, .zip)
   └── Verify size does not exceed MAX_UPLOAD_SIZE_BYTES (25 MB)
   │
3. Secure Isolated Temporary Directory (tempfile.TemporaryDirectory)
   └── Stream upload to temporary disk file
   │
4. Content & Header Verification
   ├── Check magic bytes: PK\x03\x04 for ZIP archives, XML/KML markup for KML files
   └── Reject disguised or corrupted files
   │
5. Extraction & Geospatial Reading (app/geo/zip_handler.py, app/geo/parser.py)
   ├── If .kml: Read placemark layers using Fiona KML driver (assign default EPSG:4326)
   └── If .zip: Validate ZIP entries against Zip Slip, extract safely, locate .shp + .shx + .dbf, read via GeoPandas
   │
6. Feature Extraction & Measurement Engine (app/geo/measurements.py)
   For each feature in the GeoDataFrame:
   ├── Extract properties/attributes dictionary
   ├── Explicitly verify validity (geom.is_valid):
   │     └── If self-intersecting/invalid: Mark INVALID_GEOMETRY, set value = null (preserve original geom)
   ├── Determine geometry type:
   │     ├── Point / MultiPoint ─────────► MeasurementType.NONE, value = null
   │     ├── Polygon / MultiPolygon ─────► Reproject to dynamic UTM ──► Area in m² (sq_meters)
   │     ├── LineString / MultiLineString ► Reproject to dynamic UTM ──► Length in m (meters)
   │     └── GeometryCollection / Other ──► MeasurementType.UNSUPPORTED, value = null
   └── Convert geometry to standard GeoJSON dictionary
   │
7. Atomic Database Transaction (app/services/file_service.py)
   ├── INSERT FileRecord (status='COMPLETED', crs, feature_count)
   ├── Bulk INSERT FeatureRecords (geometry, properties, measurement_value, unit, projected_crs)
   └── COMMIT transaction (automatic ROLLBACK on any database error)
   │
8. Temporary Directory Cleanup
   └── Python context manager automatically deletes all temporary files
   │
9. Return HTTP 201 Created with FileUploadResponse summary
```

---

## CRS Strategy & Metric Measurements

### Why Geographic Coordinates Cannot Be Used Directly
Geographic Coordinate Systems (such as standard GPS / WGS84 `EPSG:4326`) represent points using **angular degrees** (latitude $\phi$, longitude $\lambda$) on an ellipsoidal Earth model.
- 1 degree of longitude spans $\approx 111.32\text{ km}$ at the equator, but shrinks to $\approx 55.66\text{ km}$ at $60^\circ$ latitude, and converges to $0\text{ km}$ at the poles.
- Directly computing $\text{base} \times \text{height}$ or Euclidean distance on degree coordinates produces meaningless "square degrees" and severe geometric distortion.

### Dynamic UTM Projection Strategy
To calculate accurate metric planar measurements without hardcoding regional projections, the service implements a **Dynamic Universal Transverse Mercator (UTM)** selection strategy:

```mermaid
flowchart LR
    SourceGeom["Input Geometry (Degrees: EPSG:4326)"] --> CalcCentroid["Compute Geographic Centroid (lon, lat)"]
    CalcCentroid --> CalcZone["Calculate UTM Zone = floor((lon + 180)/6) + 1"]
    CalcZone --> CheckHemi{"Is Latitude >= 0?"}
    CheckHemi -->|Yes| NorthEPSG["EPSG: 32600 + Zone (UTM North)"]
    CheckHemi -->|No| SouthEPSG["EPSG: 32700 + Zone (UTM South)"]
    NorthEPSG --> Transform["pyproj.Transformer(source -> UTM, always_xy=True)"]
    SouthEPSG --> Transform
    Transform --> MetricGeom["Projected Geometry (Meters)"]
    MetricGeom --> PlanarCalc["Shapely Planar .area (m²) / .length (m)"]
```

1. **Source CRS Resolution**:
   - For **KML**: Standard KML coordinates are defined in WGS84 geographic coordinates (`EPSG:4326`).
   - For **Shapefiles**: Native CRS is detected from the companion `.prj` file. If the `.prj` file is missing, the system safely defaults to `EPSG:4326` with explicit logging.
2. **Projected CRS Verification**:
   - If the input dataset is already in a valid projected coordinate system with linear units in **meters** (e.g. pre-projected UTM), it is preserved and used directly.
3. **Dynamic Zone Calculation**:
   - If the dataset is in geographic degrees, the geometric centroid $(\text{lon}, \text{lat})$ is computed.
   - The UTM longitudinal zone is determined using:
     $$\text{Zone Number} = \left\lfloor\frac{\text{Longitude} + 180^\circ}{6^\circ}\right\rfloor + 1 \quad (1 \le \text{Zone} \le 60)$$
   - The appropriate EPSG code is assigned:
     - **Northern Hemisphere** ($\text{lat} \ge 0^\circ$): `EPSG: 32600 + Zone` (e.g., Bangalore, India at $77.59^\circ\text{E}, 12.97^\circ\text{N} \rightarrow \text{UTM Zone 43N} \rightarrow \text{EPSG:32643}$).
     - **Southern Hemisphere** ($\text{lat} < 0^\circ$): `EPSG: 32700 + Zone` (e.g., Sydney, Australia at $151.20^\circ\text{E}, -33.86^\circ\text{S} \rightarrow \text{UTM Zone 56S} \rightarrow \text{EPSG:32756}$).
4. **Reprojection & Planar Calculation**:
   - Coordinates are transformed using `pyproj.Transformer(always_xy=True)` and `shapely.ops.transform`.
   - Polygon area is computed via `.area` in square meters ($m^2$).
   - LineString length is computed via `.length` in meters ($m$).
   - The exact `projected_crs` identifier is stored with each feature in the database.

> **Note on Accuracy**: Planar UTM transformations provide high metric accuracy for local and regional geospatial files. The API does not claim centimeter-level geodetic survey-grade accuracy for continental-scale geometries spanning multiple UTM zones.

---

## Security & Robustness

1. **Zip Slip (Path Traversal) Protection**: 
   ZIP entries are validated before extraction. Any archive entry containing `..`, absolute paths, or trying to escape the target directory is rejected with a `SecurityViolationError`.
2. **File Size Quota & Stream Limits**: 
   Upload streams enforce a maximum file size limit (default `25 MB`, configurable via `MAX_UPLOAD_SIZE_BYTES`).
3. **Content Verification (Non-Trust of Extension Alone)**: 
   The service inspects binary headers (PKZIP `PK\x03\x04` for ZIPs, XML/KML declarations for KML) to prevent malicious files disguised with valid extensions.
4. **Mandatory Shapefile Component Checks**: 
   ZIP archives are scanned to ensure all 3 essential ESRI Shapefile files (`.shp`, `.shx`, `.dbf`) exist before parsing. Missing components return a clean `400 Bad Request`.
5. **Safe Temporary Directory Lifecycle**: 
   All upload staging and decompression take place inside isolated `tempfile.TemporaryDirectory` blocks, ensuring 100% cleanup even if an unexpected exception occurs.
6. **Explicit Invalid Geometry Handling**: 
   Geometries are checked for topological validity via `geom.is_valid`. Invalid or self-intersecting geometries are marked `INVALID_GEOMETRY` with `measurement_value: null`—the API **does not silently alter** or mutate the user's coordinates with `make_valid()`.
7. **Graceful Unsupported Geometry Handling**: 
   Unrecognized geometry types (e.g. `GeometryCollection`) are categorized as `UNSUPPORTED` without crashing the service or failing other valid features in the file.
8. **Transaction Atomicity & Rollback**: 
   Database insertions occur inside an atomic transaction. If any database write or commit fails, `db.rollback()` executes immediately, leaving zero partial or orphan records.
9. **No Sensitive Leaks**: 
   Global exception handlers convert domain exceptions into structured JSON responses (`400 Bad Request`, `404 Not Found`) without exposing server paths or raw stack traces.

---

## API Documentation & Examples

Interactive OpenAPI/Swagger documentation is automatically available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Endpoints Overview

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/files/` | Upload and process a geospatial file (`.kml` or `.zip`). | `201`, `400`, `500` |
| `GET` | `/api/files/{id}/` | Get metadata and status for an uploaded file. | `200`, `404` |
| `GET` | `/api/files/{id}/measurements/` | Get all extracted feature measurements for a file. | `200`, `404` |
| `GET` | `/health` / `/api/health` | Health probe checking service and PostgreSQL connection. | `200`, `503` |

---

### 1. Upload & Process File (`POST /api/files/`)

Accepts a `multipart/form-data` file upload.

#### Example Request (`curl`):
```bash
curl -X POST "http://localhost:8000/api/files/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_data/sample_polygons.kml"
```

#### Example Response (`201 Created`):
```json
{
  "id": "5422bf62-6307-4180-9e68-a7d66b04c1af",
  "filename": "sample_polygons.kml",
  "feature_count": 1,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

---

### 2. Get File Information (`GET /api/files/{id}/`)

#### Example Request (`curl`):
```bash
curl -X GET "http://localhost:8000/api/files/5422bf62-6307-4180-9e68-a7d66b04c1af/" \
  -H "accept: application/json"
```

#### Example Response (`200 OK`):
```json
{
  "id": "5422bf62-6307-4180-9e68-a7d66b04c1af",
  "filename": "sample_polygons.kml",
  "file_type": "KML",
  "file_size_bytes": 482,
  "crs": "EPSG:4326",
  "feature_count": 1,
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-07T12:19:17.000000Z",
  "updated_at": "2026-10-07T12:19:17.000000Z"
}
```

---

### 3. Get Feature Measurements (`GET /api/files/{id}/measurements/`)

#### Example Request (`curl`):
```bash
curl -X GET "http://localhost:8000/api/files/5422bf62-6307-4180-9e68-a7d66b04c1af/measurements/" \
  -H "accept: application/json"
```

#### Example Response (`200 OK`):
```json
{
  "file_id": "5422bf62-6307-4180-9e68-a7d66b04c1af",
  "filename": "sample_polygons.kml",
  "feature_count": 1,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "features": [
    {
      "id": "74167da8-6737-45a9-afd4-8b8286e6599c",
      "feature_index": 0,
      "geometry_type": "Polygon",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [77.5946, 12.9716, 0.0],
            [77.5976, 12.9716, 0.0],
            [77.5976, 12.9746, 0.0],
            [77.5946, 12.9746, 0.0],
            [77.5946, 12.9716, 0.0]
          ]
        ]
      },
      "properties": {
        "Name": "Survey Zone Alpha",
        "description": "Agricultural survey plot 1"
      },
      "measurement_type": "AREA",
      "measurement_value": 108152.5411,
      "measurement_unit": "sq_meters",
      "projected_crs": "EPSG:32643"
    }
  ]
}
```

---

### 4. Health Check (`GET /health`)

#### Example Response (`200 OK`):
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-10-07T12:00:00.000000Z",
  "app_name": "Geospatial File Measurement API",
  "environment": "development"
}
```

---

## Running Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.11 and 3.13)
- PostgreSQL (running locally on port `5432` or via Docker)
- GDAL/GEOS/PROJ libraries (installed automatically with Python wheels on Windows/Linux)

### Step-by-Step Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/aereo-geospatial-measurement-api.git
cd aereo-geospatial-measurement-api
```

#### 2. Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Ensure `DATABASE_URL` matches your local PostgreSQL configuration:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geomeasurement_db
```

#### 5. Create PostgreSQL Database
Ensure the `geomeasurement_db` database exists in your PostgreSQL server:
```sql
CREATE DATABASE geomeasurement_db;
```

#### 6. Run the Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will start at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

---

## Docker & Containerized Setup

You can run the entire application and PostgreSQL database with a single Docker Compose command:

```bash
docker compose up --build
```

This will:
1. Spin up `postgres:15-alpine` container on port `5432` with healthcheck.
2. Build the FastAPI image with system GDAL/PROJ dependencies.
3. Automatically connect the app to PostgreSQL once the database is healthy.
4. Expose the API on `http://localhost:8000`.

To stop the containers:
```bash
docker compose down
```

---

## Automated Testing

The project includes an automated test suite with **44 tests** covering all layers of the application.

### Run All Tests
```bash
python -m pytest -v
```

### Test Suite Breakdown (44 Passed Tests)

| Test Module | Coverage Area | Tests Count | Status |
| :--- | :--- | :--- | :--- |
| `tests/test_api_endpoints.py` | API Uploads, Metadata, Measurements, 404s, Rollback | 11 | **PASSED** |
| `tests/test_crs_reprojection.py` | EPSG:4326 to UTM, Southern Hemisphere, Metric Preserved | 4 | **PASSED** |
| `tests/test_kml_shapefile_parser.py` | Valid/Empty/Malformed KML, Shapefile with/without `.prj` | 5 | **PASSED** |
| `tests/test_measurements.py` | Polygon/MultiPolygon Area, LineString Length, Point, Invalid Geom | 8 | **PASSED** |
| `tests/test_validation_and_security.py` | Size Quota, Extensions, Content Headers, Zip Slip, Missing Files | 11 | **PASSED** |
| `tests/test_phase1.py` | Pydantic Settings, Model Schemas, Root & Health Probes | 5 | **PASSED** |
| **Total** | | **44** | **100% Passed** |

---

## Sample Data & Verification Script

The repository includes deterministic sample files in `sample_data/`:
- `sample_data/sample_polygons.kml`: Valid KML with Polygon placemark.
- `sample_data/sample_lines.kml`: Valid KML with LineString placemark.
- `sample_data/sample_shapefile.zip`: Valid ESRI Shapefile archive with `.shp`, `.shx`, `.dbf`, and `.prj`.

### Run the End-to-End Verification Script
```bash
python -m sample_data.verify_api
```
This script uploads the sample KML and Shapefile ZIP files and queries their measurements, verifying end-to-end functionality.

---

## Design Decisions & Trade-Offs

1. **FastAPI over Django / Flask**:
   - Chosen for modern async/sync support, native Pydantic V2 type validation, and automatic OpenAPI schema generation.
2. **PostgreSQL Relational Schema (without PostGIS dependency)**:
   - For an intern assignment, standard PostgreSQL with `JSONB` for GeoJSON geometries is simpler, easier to run locally, and avoids requiring custom PostGIS extensions on the host machine. Geometric calculations are performed via Shapely and PyProj in Python.
3. **Synchronous Request Processing over Celery / Background Workers**:
   - In accordance with engineering principles, keeping file processing synchronous avoids unnecessary complexity (Redis/Celery infrastructure). Files are validated and processed in-memory/temp storage immediately.
4. **Temporary Directory Sandboxing (`tempfile.TemporaryDirectory`)**:
   - Eliminates persistent local file storage. Files are parsed into database entities and the host disk is cleaned up immediately.
5. **No Blind `make_valid()` Mutation**:
   - Invalid geometries are flagged explicitly as `INVALID_GEOMETRY` rather than automatically altered. This preserves the user's raw survey coordinates without unexpected geometric distortions.

---

## Limitations & Future Scope

While the API satisfies all assignment requirements, production systems could incorporate:
- **Asynchronous Task Queue (Celery / ARQ)**: For processing large multi-gigabyte point clouds or shapefiles asynchronously with job status polling.
- **Object Storage Integration (AWS S3 / MinIO)**: For archival of original raw survey uploads.
- **PostGIS Spatial Indexing**: For server-side spatial queries (e.g. bounding box intersection, spatial join).
- **Pagination**: For files containing tens of thousands of individual feature records.
- **Authentication & Authorization**: JWT or API-Key based access control.

---

## AEREO Assignment Alignment Matrix

| Requirement | Implementation Details | Status |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI with Pydantic V2 and SQLAlchemy 2.0 | Completed |
| **Supported File Types** | `.kml` and `.zip` (containing ESRI Shapefile) | Completed |
| **Feature Extraction** | Feature index, geometry type, GeoJSON geometry, source CRS, properties | Completed |
| **Measurements** | Polygon area ($m^2$), LineString length ($m$), Point (None) | Completed |
| **Unsupported Geometries** | Handled gracefully without crashing (`UNSUPPORTED` status) | Completed |
| **Invalid Geometries** | Explicitly identified (`INVALID_GEOMETRY`) without altering coords | Completed |
| **Geographic CRS Handling** | Never computes degrees directly; dynamically reprojects to local UTM | Completed |
| **API: POST /api/files/** | Uploads, validates, parses, reprojects, and persists file & features | Completed |
| **API: GET /api/files/{id}/** | Returns uploaded file metadata, feature count, CRS, and status | Completed |
| **API: GET /api/files/{id}/measurements/** | Returns all features with calculated metric measurements and units | Completed |
| **Security** | Extension check, max file size, content verification, Zip Slip protection | Completed |
| **Database** | PostgreSQL with `files` and `features` tables and rollback safety | Completed |
| **Docker** | Dockerfile with GDAL/PROJ dependencies + `docker-compose.yml` | Completed |
| **Testing** | 44 automated pytest unit, integration, and security tests | Completed |
