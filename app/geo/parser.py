import os
from typing import List, Dict, Any, Optional
import pandas as pd
import geopandas as gpd
import fiona
from shapely.geometry import shape

from app.core.exceptions import InvalidFileError, ProcessingError
from app.core.logging import logger
from app.geo.crs import parse_crs_to_string, DEFAULT_GEOGRAPHIC_CRS
from app.geo.types import FeatureMeasurementResult, ParsedGeospatialData
from app.geo.measurements import calculate_feature_measurement
from app.geo.geojson import geometry_to_geojson_dict

# Enable KML drivers in Fiona
try:
    fiona.drvsupport.supported_drivers["KML"] = "rw"
    fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
except Exception as e:
    logger.warning(f"Could not register Fiona KML drivers: {e}")


def read_kml_file(kml_path: str) -> gpd.GeoDataFrame:
    """
    Read a KML file into a GeoPandas GeoDataFrame.
    Extracts all layers and standardizes the CRS to EPSG:4326.
    """
    if not os.path.exists(kml_path):
        raise InvalidFileError(f"KML file not found: {kml_path}")

    # Check for empty file
    if os.path.getsize(kml_path) == 0:
        raise InvalidFileError("KML file is empty (0 bytes).")

    try:
        layers = fiona.listlayers(kml_path)
    except Exception as e:
        raise InvalidFileError(f"Malformed or unreadable KML file: {str(e)}")

    if not layers:
        # Return empty GeoDataFrame
        return gpd.GeoDataFrame(columns=["geometry"], crs=DEFAULT_GEOGRAPHIC_CRS)

    gdf_list: List[gpd.GeoDataFrame] = []
    for layer in layers:
        try:
            gdf_layer = gpd.read_file(kml_path, layer=layer, driver="KML")
            if not gdf_layer.empty:
                gdf_list.append(gdf_layer)
        except Exception as e:
            logger.warning(f"Failed to read layer '{layer}' from KML {kml_path}: {e}")

    if not gdf_list:
        return gpd.GeoDataFrame(columns=["geometry"], crs=DEFAULT_GEOGRAPHIC_CRS)

    combined_gdf = pd.concat(gdf_list, ignore_index=True)
    gdf = gpd.GeoDataFrame(combined_gdf, crs=DEFAULT_GEOGRAPHIC_CRS)

    # If CRS is not explicitly set, assign default KML standard EPSG:4326
    if gdf.crs is None:
        gdf.set_crs(DEFAULT_GEOGRAPHIC_CRS, inplace=True)

    return gdf


def read_shapefile(shp_path: str) -> gpd.GeoDataFrame:
    """
    Read an extracted ESRI Shapefile (.shp) into a GeoPandas GeoDataFrame.
    Preserves attributes and detects CRS.
    """
    if not os.path.exists(shp_path):
        raise InvalidFileError(f"Shapefile not found: {shp_path}")

    try:
        gdf = gpd.read_file(shp_path)
    except Exception as e:
        raise InvalidFileError(f"Malformed or unreadable Shapefile: {str(e)}")

    # Detect and handle missing CRS
    if gdf.crs is None:
        logger.warning(
            f"Shapefile '{shp_path}' has no .prj file or defined CRS. Defaulting to {DEFAULT_GEOGRAPHIC_CRS}."
        )
        gdf.set_crs(DEFAULT_GEOGRAPHIC_CRS, inplace=True)

    return gdf


def sanitize_feature_properties(row_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize dataframe row properties into JSON-serializable types.
    Removes geometry column and handles NaN/Timestamp/bytes values.
    """
    clean_props: Dict[str, Any] = {}
    for key, val in row_dict.items():
        if key == "geometry":
            continue
        # Convert NaN / null to None
        if pd.isna(val):
            clean_props[key] = None
        elif isinstance(val, (int, float, str, bool)):
            clean_props[key] = val
        elif hasattr(val, "isoformat"):
            clean_props[key] = val.isoformat()
        else:
            clean_props[key] = str(val)
    return clean_props


def process_geodataframe(
    gdf: gpd.GeoDataFrame,
    filename: str,
    file_type: str,
    file_size_bytes: int
) -> ParsedGeospatialData:
    """
    Process a loaded GeoDataFrame into standard domain objects:
    Extracts features, calculates metric measurements, and converts geometries to GeoJSON.
    """
    source_crs_str = parse_crs_to_string(gdf.crs)
    feature_results: List[FeatureMeasurementResult] = []

    for idx, row in gdf.iterrows():
        geom = row.get("geometry")
        props = sanitize_feature_properties(row.to_dict())

        (
            geom_type,
            meas_type,
            meas_value,
            meas_unit,
            proj_crs
        ) = calculate_feature_measurement(geom, source_crs_str)

        geojson_geom = geometry_to_geojson_dict(geom)

        feature_results.append(
            FeatureMeasurementResult(
                feature_index=int(idx),
                geometry_type=geom_type,
                geometry_geojson=geojson_geom,
                properties=props,
                measurement_type=meas_type,
                measurement_value=meas_value,
                measurement_unit=meas_unit,
                projected_crs=proj_crs
            )
        )

    return ParsedGeospatialData(
        filename=filename,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        source_crs=source_crs_str,
        feature_count=len(feature_results),
        features=feature_results
    )
