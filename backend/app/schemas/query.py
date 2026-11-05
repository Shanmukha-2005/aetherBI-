from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class SQLGenerateRequest(BaseModel):
    dataset_id: int
    prompt: str
    additional_dataset_ids: Optional[List[int]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    api_key: Optional[str] = None

class SQLGenerateResponse(BaseModel):
    id: int
    dataset_id: int
    prompt: str
    generated_sql: str
    explanation: str
    created_at: datetime

    class Config:
        from_attributes = True

class QueryHistoryOut(BaseModel):
    id: int
    dataset_id: int
    prompt: str
    generated_sql: str
    explanation: str
    created_at: datetime

    class Config:
        from_attributes = True

class SQLExecuteRequest(BaseModel):
    dataset_id: int
    sql: str

class SQLExecuteResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    execution_time_ms: float
    chart_suggestion: Optional[Dict[str, Any]] = None

class NLChartGenerateRequest(BaseModel):
    dataset_id: int
    prompt: str
    chart_type: Optional[str] = None
    api_key: Optional[str] = None

class NLChartGenerateResponse(BaseModel):
    title: str
    chart_type: str
    x_key: str
    y_key: str
    data: List[Dict[str, Any]]
    explanation: str
    generated_sql: str
    total_data_points: int

