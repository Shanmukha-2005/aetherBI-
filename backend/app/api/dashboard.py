from fastapi import APIRouter, Depends, HTTPException, status
import pandas as pd
from sqlalchemy.orm import Session
from app.db.session import get_db, engine
from app.models.user import User
from app.models.dataset import Dataset
from app.schemas.dashboard import DashboardResponse
from app.api.deps import get_current_user
from app.services.dashboard_service import generate_dashboard_payload

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/{dataset_id}", response_model=DashboardResponse)
def get_dataset_dashboard(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    try:
        df = pd.read_sql_table(dataset.physical_table_name, con=engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset table: {str(e)}")

    payload = generate_dashboard_payload(df, dataset.health_score)
    return payload
