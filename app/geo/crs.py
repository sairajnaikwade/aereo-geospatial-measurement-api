from typing import Any, Optional, Tuple
import pyproj
from pyproj import CRS, Transformer
import geopandas as gpd
from shapely.geometry import base
from app.core.logging import logger
from app.core.exceptions import ProcessingError

DEFAULT_GEOGRAPHIC_CRS = "EPSG:4326"


def parse_crs_to_string(crs_input: Any) -> str:
    """
    Safely convert various CRS representations (pyproj.CRS, dict, string, None) to an EPSG/WKT string.
    """
    if crs_input is None:
        return DEFAULT_GEOGRAPHIC_CRS
    
    try:
        if isinstance(crs_input, CRS):
            epsg = crs_input.to_epsg()
            if epsg:
                return f"EPSG:{epsg}"
            return crs_input.to_string()
        
        parsed = CRS.from_user_input(crs_input)
        epsg = parsed.to_epsg()
        if epsg:
            return f"EPSG:{epsg}"
        return parsed.name or str(crs_input)
    except Exception as e:
        logger.warning(f"Could not parse CRS input '{crs_input}': {e}. Defaulting to {DEFAULT_GEOGRAPHIC_CRS}")
        return DEFAULT_GEOGRAPHIC_CRS


def is_geographic_crs(crs_obj: CRS) -> bool:
    """
    Check if a CRS is geographic (angular units like degrees).
    """
    return crs_obj.is_geographic


def is_metric_projected_crs(crs_obj: CRS) -> bool:
    """
    Check if a CRS is projected and uses meters as its linear measurement unit.
    """
    if not crs_obj.is_projected:
        return False

    try:
        unit_name = crs_obj.axis_info[0].unit_name.lower()
        return "metre" in unit_name or "meter" in unit_name
    except Exception:
        return True


def determine_utm_crs_for_geometry(geom: base.BaseGeometry, source_crs: CRS) -> CRS:
    """
    Determine the optimal UTM projected CRS (in meters) for a given geometry.
    Calculates the centroid in EPSG:4326 coordinates to compute the UTM zone:
      zone = floor((lon + 180) / 6) + 1
      EPSG: 32600 + zone (North) or 32700 + zone (South)
    """
    # Transform geometry centroid to EPSG:4326 if not already in geographic coords
    if source_crs != CRS.from_epsg(4326):
        to_wgs84 = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
        # Compute centroid
        centroid = geom.centroid
        lon, lat = to_wgs84.transform(centroid.x, centroid.y)
    else:
        centroid = geom.centroid
        lon, lat = centroid.x, centroid.y

    # Clamp lat/lon within valid bounds
    lon = max(-180.0, min(180.0, lon))
    lat = max(-85.0, min(85.0, lat))

    # Calculate UTM Zone
    zone_number = int((lon + 180) // 6) + 1
    if zone_number > 60:
        zone_number = 60

    is_northern = lat >= 0
    epsg_code = 32600 + zone_number if is_northern else 32700 + zone_number
    return CRS.from_epsg(epsg_code)


def get_projected_crs_for_geometry(geom: base.BaseGeometry, source_crs_str: Optional[str]) -> Tuple[CRS, str]:
    """
    Determine the target projected metric CRS and return (target_crs_obj, crs_name_string).
    """
    try:
        source_crs = CRS.from_user_input(source_crs_str) if source_crs_str else CRS.from_epsg(4326)
    except Exception:
        logger.warning(f"Unrecognized source CRS '{source_crs_str}'. Assuming {DEFAULT_GEOGRAPHIC_CRS}.")
        source_crs = CRS.from_epsg(4326)

    # If the source CRS is already a projected metric CRS, we can use it directly
    if source_crs.is_projected and is_metric_projected_crs(source_crs):
        epsg = source_crs.to_epsg()
        name = f"EPSG:{epsg}" if epsg else source_crs.name
        return source_crs, name

    # Otherwise (e.g. EPSG:4326 or other geographic/non-metric), compute the optimal UTM projection
    target_crs = determine_utm_crs_for_geometry(geom, source_crs)
    return target_crs, f"EPSG:{target_crs.to_epsg()}"


def reproject_geometry(geom: base.BaseGeometry, source_crs_str: Optional[str], target_crs: CRS) -> base.BaseGeometry:
    """
    Reproject a Shapely geometry from source CRS to target projected CRS.
    """
    try:
        source_crs = CRS.from_user_input(source_crs_str) if source_crs_str else CRS.from_epsg(4326)
    except Exception:
        source_crs = CRS.from_epsg(4326)

    if source_crs == target_crs:
        return geom

    # PyProj Transformer with always_xy=True ensures (x/lon, y/lat) order
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    
    # Use shapely.ops.transform to reproject all coordinates in the geometry
    from shapely.ops import transform
    return transform(transformer.transform, geom)
