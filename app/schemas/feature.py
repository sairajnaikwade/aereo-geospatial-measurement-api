import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ConfigDict, Field


class FeatureMeasurementResponse(BaseModel):
    """
    Schema for an individual extracted feature and its measurement details.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., example="9a695e63-a550-4822-b06a-a2f026a27e74")
    feature_index: int = Field(..., example=0)
    geometry_type: str = Field(..., example="Polygon")
    geometry: Dict[str, Any] = Field(..., example={
        "type": "Polygon",
        "coordinates": [[[77.5946, 12.9716], [77.5956, 12.9716], [77.5956, 12.9726], [77.5946, 12.9726], [77.5946, 12.9716]]]
    })
    properties: Dict[str, Any] = Field(default_factory=dict, example={"name": "Zone A", "crop": "Wheat"})
    measurement_type: str = Field(..., example="AREA")  # AREA, LENGTH, NONE, UNSUPPORTED, INVALID_GEOMETRY
    measurement_value: Optional[float] = Field(None, example=12345.67)
    measurement_unit: Optional[str] = Field(None, example="sq_meters")  # sq_meters, meters, or null
    projected_crs: Optional[str] = Field(None, example="EPSG:32643")


class FileMeasurementsResponse(BaseModel):
    """
    Response schema containing file details along with all extracted feature measurements.
    """
    file_id: uuid.UUID = Field(..., example="3fa85f64-5717-4562-b3fc-2c963f66afa6")
    filename: str = Field(..., example="survey_boundary.kml")
    feature_count: int = Field(..., example=1)
    crs: Optional[str] = Field(None, example="EPSG:4326")
    status: str = Field(..., example="COMPLETED")
    features: List[FeatureMeasurementResponse] = Field(default_factory=list)
