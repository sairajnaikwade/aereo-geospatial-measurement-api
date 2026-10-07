import io
import os
import zipfile
import tempfile
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, MultiLineString


def create_sample_kml_content(placemarks: str) -> str:
    """Generate a standard KML document string."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample Data</name>
    {placemarks}
  </Document>
</kml>
"""


def create_sample_shapefile_zip_bytes(
    crs: str = "EPSG:4326",
    include_shp: bool = True,
    include_shx: bool = True,
    include_dbf: bool = True,
    include_prj: bool = True
) -> bytes:
    """
    Generate an in-memory ZIP containing a valid or intentionally broken ESRI Shapefile.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        shp_path = os.path.join(temp_dir, "test_layer.shp")
        
        # Create a simple GeoDataFrame with valid polygons (Shapefiles require single geometry type per layer)
        gdf = gpd.GeoDataFrame({
            "name": ["Zone A", "Zone B"],
            "category": ["Alpha", "Beta"],
            "geometry": [
                Polygon([(77.5946, 12.9716), (77.5956, 12.9716), (77.5956, 12.9726), (77.5946, 12.9726), (77.5946, 12.9716)]),
                Polygon([(77.5960, 12.9716), (77.5970, 12.9716), (77.5970, 12.9726), (77.5960, 12.9726), (77.5960, 12.9716)])
            ]
        }, crs=crs if include_prj else None)

        gdf.to_file(shp_path)

        # Build ZIP archive
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            base_name = os.path.splitext(shp_path)[0]
            if include_shp and os.path.exists(base_name + ".shp"):
                zf.write(base_name + ".shp", "test_layer.shp")
            if include_shx and os.path.exists(base_name + ".shx"):
                zf.write(base_name + ".shx", "test_layer.shx")
            if include_dbf and os.path.exists(base_name + ".dbf"):
                zf.write(base_name + ".dbf", "test_layer.dbf")
            if include_prj and os.path.exists(base_name + ".prj"):
                zf.write(base_name + ".prj", "test_layer.prj")

        zip_buf.seek(0)
        return zip_buf.getvalue()


def create_zip_slip_archive_bytes() -> bytes:
    """Generate a malicious ZIP archive with path traversal (Zip Slip)."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("../../evil.txt", "Malicious content escaping sandbox")
    zip_buf.seek(0)
    return zip_buf.getvalue()
