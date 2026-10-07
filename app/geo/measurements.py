from typing import Optional, Tuple
from shapely.geometry import base
from shapely.geometry import (
    Polygon,
    MultiPolygon,
    LineString,
    MultiLineString,
    Point,
    MultiPoint,
    GeometryCollection
)
from app.geo.types import MeasurementType, MeasurementUnit
from app.geo.crs import get_projected_crs_for_geometry, reproject_geometry
from app.core.logging import logger


def calculate_feature_measurement(
    geom: Optional[base.BaseGeometry],
    source_crs_str: Optional[str]
) -> Tuple[str, MeasurementType, Optional[float], Optional[MeasurementUnit], Optional[str]]:
    """
    Calculate the metric measurement for a given geometry.
    
    Returns:
        Tuple of:
        - geometry_type (str)
        - measurement_type (MeasurementType)
        - measurement_value (float or None)
        - measurement_unit (MeasurementUnit or None)
        - projected_crs (str or None)
    """
    if geom is None or geom.is_empty:
        return (
            "None",
            MeasurementType.NONE,
            None,
            None,
            None
        )

    geom_type = geom.geom_type

    # Explicit check for geometric validity (DO NOT automatically make_valid)
    if not geom.is_valid:
        logger.warning(f"Invalid geometry detected (type={geom_type}): {geom.is_valid_reason if hasattr(geom, 'is_valid_reason') else 'topology error'}")
        return (
            geom_type,
            MeasurementType.INVALID_GEOMETRY,
            None,
            None,
            None
        )

    # 1. Point / MultiPoint -> No measurement required
    if isinstance(geom, (Point, MultiPoint)):
        return (
            geom_type,
            MeasurementType.NONE,
            None,
            None,
            None
        )

    # 2. Polygon / MultiPolygon -> Area in square meters (m²)
    elif isinstance(geom, (Polygon, MultiPolygon)):
        try:
            target_crs_obj, projected_crs_name = get_projected_crs_for_geometry(geom, source_crs_str)
            projected_geom = reproject_geometry(geom, source_crs_str, target_crs_obj)
            area_sq_meters = float(projected_geom.area)
            return (
                geom_type,
                MeasurementType.AREA,
                round(area_sq_meters, 4),
                MeasurementUnit.SQ_METERS,
                projected_crs_name
            )
        except Exception as e:
            logger.error(f"Error computing area for {geom_type}: {e}")
            return (
                geom_type,
                MeasurementType.UNSUPPORTED,
                None,
                None,
                None
            )

    # 3. LineString / MultiLineString -> Length in meters (m)
    elif isinstance(geom, (LineString, MultiLineString)):
        try:
            target_crs_obj, projected_crs_name = get_projected_crs_for_geometry(geom, source_crs_str)
            projected_geom = reproject_geometry(geom, source_crs_str, target_crs_obj)
            length_meters = float(projected_geom.length)
            return (
                geom_type,
                MeasurementType.LENGTH,
                round(length_meters, 4),
                MeasurementUnit.METERS,
                projected_crs_name
            )
        except Exception as e:
            logger.error(f"Error computing length for {geom_type}: {e}")
            return (
                geom_type,
                MeasurementType.UNSUPPORTED,
                None,
                None,
                None
            )

    # 4. GeometryCollection or other unhandled geometry types -> Gracefully return UNSUPPORTED
    else:
        logger.info(f"Unsupported geometry type encountered: {geom_type}")
        return (
            geom_type,
            MeasurementType.UNSUPPORTED,
            None,
            None,
            None
        )
