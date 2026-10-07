import json
from typing import Dict, Any, Optional
from shapely.geometry import base, mapping
import shapely


def geometry_to_geojson_dict(geom: Optional[base.BaseGeometry]) -> Dict[str, Any]:
    """
    Convert a Shapely geometry object into a standardized GeoJSON dictionary.
    Handles None and empty geometries safely.
    """
    if geom is None or geom.is_empty:
        return {"type": "GeometryCollection", "geometries": []}

    try:
        # Shapely 2.0 mapping / to_geojson
        return mapping(geom)
    except Exception:
        # Fallback to json parsing from to_geojson string if mapping fails
        try:
            return json.loads(shapely.to_geojson(geom))
        except Exception:
            return {"type": "Unknown", "coordinates": []}
