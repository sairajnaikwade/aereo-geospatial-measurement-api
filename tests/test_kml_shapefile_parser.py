import os
import tempfile
import pytest
from app.geo.parser import read_kml_file, read_shapefile, process_geodataframe
from app.geo.zip_handler import safe_extract_shapefile_zip
from app.core.exceptions import InvalidFileError
from tests.test_helpers import create_sample_kml_content, create_sample_shapefile_zip_bytes


def test_read_valid_kml():
    """Test reading a valid KML file with Polygon and LineString placemarks."""
    kml_data = create_sample_kml_content("""
    <Placemark>
      <name>Test Polygon</name>
      <description>Sample area feature</description>
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
    <Placemark>
      <name>Test Line</name>
      <LineString>
        <coordinates>
          77.5946,12.9716,0
          77.6046,12.9716,0
        </coordinates>
      </LineString>
    </Placemark>
    """)

    with tempfile.NamedTemporaryFile(suffix=".kml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(kml_data)
        f_path = f.name

    try:
        gdf = read_kml_file(f_path)
        assert len(gdf) == 2
        assert "geometry" in gdf.columns
        assert gdf.crs is not None

        # Test process_geodataframe
        result = process_geodataframe(gdf, "sample.kml", "KML", len(kml_data))
        assert result.feature_count == 2
        assert result.source_crs == "EPSG:4326"
        assert result.features[0].geometry_type == "Polygon"
        assert result.features[0].measurement_type == "AREA"
        assert result.features[0].measurement_value > 0
        assert result.features[0].measurement_unit == "sq_meters"

        assert result.features[1].geometry_type == "LineString"
        assert result.features[1].measurement_type == "LENGTH"
        assert result.features[1].measurement_value > 0
        assert result.features[1].measurement_unit == "meters"
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_read_malformed_kml():
    """Test reading invalid / malformed XML in KML file raises InvalidFileError."""
    with tempfile.NamedTemporaryFile(suffix=".kml", mode="w", encoding="utf-8", delete=False) as f:
        f.write("<?xml version='1.0'?><kml><Document><Placemark><broken_tag>")
        f_path = f.name

    try:
        with pytest.raises(InvalidFileError, match="Malformed or unreadable KML"):
            read_kml_file(f_path)
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_read_empty_kml():
    """Test reading empty KML returns empty GeoDataFrame without error."""
    kml_data = create_sample_kml_content("")
    with tempfile.NamedTemporaryFile(suffix=".kml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(kml_data)
        f_path = f.name

    try:
        gdf = read_kml_file(f_path)
        assert len(gdf) == 0
        result = process_geodataframe(gdf, "empty.kml", "KML", len(kml_data))
        assert result.feature_count == 0
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_read_valid_shapefile_with_crs():
    """Test reading a valid Shapefile extracted from ZIP with CRS preserved."""
    zip_bytes = create_sample_shapefile_zip_bytes(crs="EPSG:4326", include_prj=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(zip_bytes)
        f_path = f.name

    try:
        with safe_extract_shapefile_zip(f_path) as shp_path:
            gdf = read_shapefile(shp_path)
            assert len(gdf) == 2
            assert "category" in gdf.columns
            result = process_geodataframe(gdf, "sample.zip", "SHAPEFILE_ZIP", len(zip_bytes))
            assert result.feature_count == 2
            assert result.source_crs == "EPSG:4326"
            assert result.features[0].measurement_value > 0
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_read_shapefile_missing_crs():
    """Test Shapefile missing .prj defaults safely to EPSG:4326."""
    zip_bytes = create_sample_shapefile_zip_bytes(include_prj=False)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(zip_bytes)
        f_path = f.name

    try:
        with safe_extract_shapefile_zip(f_path) as shp_path:
            gdf = read_shapefile(shp_path)
            assert gdf.crs is not None
            result = process_geodataframe(gdf, "no_prj.zip", "SHAPEFILE_ZIP", len(zip_bytes))
            assert result.source_crs == "EPSG:4326"
            assert result.feature_count == 2
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)
