import uuid
from typing import List, Optional
from sqlalchemy import String, BigInteger, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class FileRecord(Base, TimestampMixin):
    """
    SQLAlchemy model representing an uploaded geospatial file and its processing status.
    """
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # KML or SHAPEFILE_ZIP
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    crs: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g. "EPSG:4326"
    feature_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PROCESSING", nullable=False)  # PROCESSING, COMPLETED, FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # One-to-many relationship to extracted features
    features: Mapped[List["FeatureRecord"]] = relationship(
        "FeatureRecord",
        back_populates="file",
        cascade="all, delete-orphan",
        order_by="FeatureRecord.feature_index"
    )

    def __repr__(self) -> str:
        return f"<FileRecord(id={self.id}, filename='{self.filename}', status='{self.status}', count={self.feature_count})>"
