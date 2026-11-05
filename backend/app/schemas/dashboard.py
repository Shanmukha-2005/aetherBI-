from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class NumericSummary(BaseModel):
    column: str
    min_val: float
    max_val: float
    avg_val: float
    sum_val: float

class KPICards(BaseModel):
    total_rows: int
    total_cols: int
    health_score: float
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    numeric_summaries: List[NumericSummary] = []

class ChartData(BaseModel):
    id: str
    title: str
    chart_type: str  # "bar", "line", "pie", "histogram"
    x_key: str
    y_key: str
    data: List[Dict[str, Any]]

class DashboardResponse(BaseModel):
    kpis: KPICards
    charts: List[ChartData]
