from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    physical_table_name = Column(String, nullable=False, unique=True)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    health_score = Column(Float, default=100.0)
    columns_meta = Column(Text, default="[]")  # JSON string of column names and types
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="datasets")
    remediation_logs = relationship("RemediationLog", back_populates="dataset", cascade="all, delete-orphan")
    facts = relationship("DatasetFact", back_populates="dataset", cascade="all, delete-orphan")
    queries = relationship("QueryHistory", back_populates="dataset", cascade="all, delete-orphan")
