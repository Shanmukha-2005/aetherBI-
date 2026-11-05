from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class RemediationLog(Base):
    __tablename__ = "remediation_logs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    column_name = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)
    issue_description = Column(Text, nullable=False)
    resolution_strategy = Column(String, nullable=False)
    resolution_details = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset", back_populates="remediation_logs")
