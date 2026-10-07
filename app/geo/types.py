from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List


class MeasurementType(str, Enum):
    AREA = "AREA"
    LENGTH = "LENGTH"
    NONE = "NONE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class MeasurementUnit(str, Enum):
    SQ_METERS = "sq_meters"
    METERS = "meters"


@dataclass
class FeatureMeasurementResult:
    """
    Standard domain result for an individual processed geospatial feature.
    """
    feature_index: int
    geometry_type: str
    geometry_geojson: Dict[str, Any]
    properties: Dict[str, Any]
    measurement_type: MeasurementType
    measurement_value: Optional[float]
    measurement_unit: Optional[MeasurementUnit]
    projected_crs: Optional[str]


@dataclass
class ParsedGeospatialData:
    """
    Domain container holding the complete parsed file metadata and features.
    """
    filename: str
    file_type: str
    file_size_bytes: int
    source_crs: str
    feature_count: int
    features: List[FeatureMeasurementResult] = field(default_factory=list)
