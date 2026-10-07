import uuid
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class FeatureRecord(Base, TimestampMixin):
    """
    SQLAlchemy model representing an individual extracted geospatial feature and its calculated measurements.
    """
    __tablename__ = "features"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    feature_index: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Polygon, LineString, Point, etc.
    geometry_geojson: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Measurement details
    measurement_type: Mapped[str] = mapped_column(String(30), nullable=False)  # AREA, LENGTH, NONE, UNSUPPORTED, INVALID_GEOMETRY
    measurement_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in m² or m
    measurement_unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # sq_meters, meters, or null
    projected_crs: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Projected CRS used for metric calculation

    # Back relationship to the parent file
    file: Mapped["FileRecord"] = relationship("FileRecord", back_populates="features")

    def __repr__(self) -> str:
        return f"<FeatureRecord(id={self.id}, file_id={self.file_id}, index={self.feature_index}, type='{self.geometry_type}', measurement={self.measurement_value} {self.measurement_unit})>"
