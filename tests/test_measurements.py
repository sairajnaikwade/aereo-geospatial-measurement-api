import pytest
from shapely.geometry import (
    Polygon,
    MultiPolygon,
    LineString,
    MultiLineString,
    Point,
    MultiPoint,
    GeometryCollection
)
from app.geo.measurements import calculate_feature_measurement
from app.geo.types import MeasurementType, MeasurementUnit
from app.geo.geojson import geometry_to_geojson_dict


def test_polygon_area_measurement():
    """
    Test Polygon area calculation in square meters.
    A ~100m x 100m box in projected coords or known lat/lon.
    """
    # 100m x 100m square in EPSG:32643
    poly = Polygon([(500000, 1000000), (500100, 1000000), (500100, 100100), (500000, 100100), (500000, 1000000)])
    # Make a valid 100m x 100m
    poly_box = Polygon([(500000, 1000000), (500100, 1000000), (500100, 1000100), (500000, 1000100), (500000, 1000000)])

    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(poly_box, "EPSG:32643")
    assert geom_type == "Polygon"
    assert meas_type == MeasurementType.AREA
    assert pytest.approx(val, rel=1e-2) == 10000.0  # 100m * 100m = 10,000 m²
    assert unit == MeasurementUnit.SQ_METERS


def test_multipolygon_area_measurement():
    """Test MultiPolygon area calculation aggregates all parts."""
    poly1 = Polygon([(500000, 1000000), (500100, 1000000), (500100, 1000100), (500000, 1000100), (500000, 1000000)])
    poly2 = Polygon([(500200, 1000000), (500300, 1000000), (500300, 1000100), (500200, 1000100), (500200, 1000000)])
    multipoly = MultiPolygon([poly1, poly2])

    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(multipoly, "EPSG:32643")
    assert geom_type == "MultiPolygon"
    assert meas_type == MeasurementType.AREA
    assert pytest.approx(val, rel=1e-2) == 20000.0  # 2 * 10,000 m² = 20,000 m²
    assert unit == MeasurementUnit.SQ_METERS


def test_linestring_length_measurement():
    """Test LineString length calculation in meters."""
    line = LineString([(500000, 1000000), (500500, 1000000)])  # 500 meters long
    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(line, "EPSG:32643")
    assert geom_type == "LineString"
    assert meas_type == MeasurementType.LENGTH
    assert pytest.approx(val, rel=1e-2) == 500.0
    assert unit == MeasurementUnit.METERS


def test_multilinestring_length_measurement():
    """Test MultiLineString length calculation aggregates segments."""
    line1 = LineString([(500000, 1000000), (500500, 1000000)])  # 500m
    line2 = LineString([(500000, 1000100), (500250, 1000100)])  # 250m
    multiline = MultiLineString([line1, line2])

    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(multiline, "EPSG:32643")
    assert geom_type == "MultiLineString"
    assert meas_type == MeasurementType.LENGTH
    assert pytest.approx(val, rel=1e-2) == 750.0  # 500 + 250 = 750m
    assert unit == MeasurementUnit.METERS


def test_point_no_measurement():
    """Test Point returns NONE measurement type and null value."""
    pt = Point(77.5946, 12.9716)
    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(pt, "EPSG:4326")
    assert geom_type == "Point"
    assert meas_type == MeasurementType.NONE
    assert val is None
    assert unit is None


def test_multipoint_no_measurement():
    """Test MultiPoint returns NONE measurement type and null value."""
    mpt = MultiPoint([(77.5946, 12.9716), (77.5956, 12.9726)])
    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(mpt, "EPSG:4326")
    assert geom_type == "MultiPoint"
    assert meas_type == MeasurementType.NONE
    assert val is None
    assert unit is None


def test_unsupported_geometry_collection():
    """Test GeometryCollection is handled gracefully without crashing."""
    pt = Point(77.5946, 12.9716)
    line = LineString([(77.5946, 12.9716), (77.6046, 12.9716)])
    gc = GeometryCollection([pt, line])

    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(gc, "EPSG:4326")
    assert geom_type == "GeometryCollection"
    assert meas_type == MeasurementType.UNSUPPORTED
    assert val is None
    assert unit is None


def test_invalid_geometry_explicit_handling():
    """
    Test that self-intersecting / invalid geometry is explicitly identified as
    INVALID_GEOMETRY without being altered by make_valid().
    """
    # Self-intersecting 'Bowtie' polygon: (0,0)-(2,2)-(2,0)-(0,2)-(0,0)
    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
    assert not bowtie.is_valid  # Verify it is geometrically invalid

    geom_type, meas_type, val, unit, proj_crs = calculate_feature_measurement(bowtie, "EPSG:4326")
    assert geom_type == "Polygon"
    assert meas_type == MeasurementType.INVALID_GEOMETRY
    assert val is None
    assert unit is None

    # Verify original geometry is preserved in GeoJSON conversion
    geojson = geometry_to_geojson_dict(bowtie)
    assert geojson["type"] == "Polygon"
    assert len(geojson["coordinates"][0]) == 5
