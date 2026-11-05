from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel

class RemediationLogOut(BaseModel):
    id: int
    column_name: str
    issue_type: str
    issue_description: str
    resolution_strategy: str
    resolution_details: str
    created_at: datetime

    class Config:
        from_attributes = True

class DatasetFactOut(BaseModel):
    id: int
    fact_type: str
    title: str
    description: str
    metric_value: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ColumnMeta(BaseModel):
    name: str
    type: str  # numeric, categorical, datetime, boolean
    original_type: str
    null_count: int
    unique_count: int

class DatasetSummary(BaseModel):
    id: int
    name: str
    original_filename: str
    physical_table_name: str
    row_count: int
    column_count: int
    health_score: float
    created_at: datetime

    class Config:
        from_attributes = True

class DatasetDetail(BaseModel):
    id: int
    name: str
    original_filename: str
    physical_table_name: str
    row_count: int
    column_count: int
    health_score: float
    columns_meta: List[ColumnMeta]
    created_at: datetime
    remediation_logs: List[RemediationLogOut]
    facts: List[DatasetFactOut]
    sample_data: List[dict] = []

    class Config:
        from_attributes = True
