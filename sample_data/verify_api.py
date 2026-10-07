import os
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
base_dir = os.path.dirname(__file__)

print("--- Testing KML Polygons Upload ---")
kml_path = os.path.join(base_dir, "sample_polygons.kml")
with open(kml_path, "rb") as f:
    res = client.post("/api/files/", files={"file": ("sample_polygons.kml", f, "application/vnd.google-earth.kml+xml")})
print("Upload Response:", res.status_code, json.dumps(res.json(), indent=2))
file_id = res.json()["id"]

meas = client.get(f"/api/files/{file_id}/measurements/")
print("Measurements Response:", meas.status_code, json.dumps(meas.json(), indent=2))

print("\n--- Testing Shapefile ZIP Upload ---")
zip_path = os.path.join(base_dir, "sample_shapefile.zip")
with open(zip_path, "rb") as f:
    res2 = client.post("/api/files/", files={"file": ("sample_shapefile.zip", f, "application/zip")})
print("Upload Response:", res2.status_code, json.dumps(res2.json(), indent=2))
file_id2 = res2.json()["id"]

meas2 = client.get(f"/api/files/{file_id2}/measurements/")
print("Measurements Response:", meas2.status_code, json.dumps(meas2.json(), indent=2))
