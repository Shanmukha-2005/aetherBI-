from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class DatasetFact(Base):
    __tablename__ = "dataset_facts"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    fact_type = Column(String, nullable=False)  # CORRELATION, PARETO_80_20, DOMINANCE, QUIRK
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    metric_value = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset", back_populates="facts")
