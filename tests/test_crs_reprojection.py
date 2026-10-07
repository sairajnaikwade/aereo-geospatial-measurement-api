import pytest
from shapely.geometry import Polygon, Point
from pyproj import CRS
from app.geo.crs import (
    get_projected_crs_for_geometry,
    reproject_geometry,
    parse_crs_to_string,
    determine_utm_crs_for_geometry
)


def test_epsg4326_transforms_to_utm():
    """
    Test that a polygon defined in geographic EPSG:4326 (e.g. Bangalore, India: 77.59 E, 12.97 N)
    is dynamically assigned to the correct UTM projection (UTM Zone 43N -> EPSG:32643).
    """
    # Bangalore: lon=77.59, lat=12.97 -> Zone (77.59 + 180)//6 + 1 = 43. North -> EPSG:32643
    geom = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98), (77.59, 12.97)])
    
    target_crs, crs_name = get_projected_crs_for_geometry(geom, "EPSG:4326")
    assert crs_name == "EPSG:32643"
    assert target_crs.to_epsg() == 32643

    # Reproject geometry and ensure coordinates are now metric Cartesian (not degree angles)
    projected_geom = reproject_geometry(geom, "EPSG:4326", target_crs)
    assert projected_geom.area > 100000.0  # Area is in m² (> 1 km²)


def test_southern_hemisphere_utm():
    """
    Test that coordinates in the Southern Hemisphere (e.g. Sydney, Australia: 151.20 E, -33.86 S)
    are mapped to South UTM (UTM Zone 56S -> EPSG:32756).
    """
    # Sydney: lon=151.20, lat=-33.86 -> Zone (151.20 + 180)//6 + 1 = 56. South -> EPSG:32756
    geom = Point(151.20, -33.86)
    target_crs = determine_utm_crs_for_geometry(geom, CRS.from_epsg(4326))
    assert target_crs.to_epsg() == 32756


def test_already_projected_metric_crs_preserved():
    """
    Test that when source CRS is already a metric projected CRS (e.g. EPSG:3857 or EPSG:32643),
    it is preserved and not re-projected unnecessarily.
    """
    geom = Polygon([(1000, 1000), (2000, 1000), (2000, 2000), (1000, 2000), (1000, 1000)])
    target_crs, crs_name = get_projected_crs_for_geometry(geom, "EPSG:32643")
    assert crs_name == "EPSG:32643"
    assert target_crs.to_epsg() == 32643


def test_invalid_or_missing_crs_safe_fallback():
    """
    Test that unrecognized or None CRS input defaults safely without crashing.
    """
    geom = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98), (77.59, 12.97)])
    target_crs, crs_name = get_projected_crs_for_geometry(geom, None)
    assert crs_name == "EPSG:32643"

    target_crs2, crs_name2 = get_projected_crs_for_geometry(geom, "INVALID_NON_EXISTENT_CRS")
    assert crs_name2 == "EPSG:32643"
