import os
from tests.test_helpers import create_sample_shapefile_zip_bytes

output_path = os.path.join(os.path.dirname(__file__), "sample_shapefile.zip")
zip_bytes = create_sample_shapefile_zip_bytes(crs="EPSG:4326")

with open(output_path, "wb") as f:
    f.write(zip_bytes)

print(f"Created {output_path} ({len(zip_bytes)} bytes)")
