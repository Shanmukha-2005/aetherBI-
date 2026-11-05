import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db, engine
from app.models.user import User
from app.models.dataset import Dataset
from app.models.audit import RemediationLog
from app.models.facts import DatasetFact
from app.schemas.dataset import (
    DatasetSummary,
    DatasetDetail,
    RemediationLogOut,
    DatasetFactOut,
    ColumnMeta
)
from app.api.deps import get_current_user
from app.services.ingestion_service import process_and_ingest_dataset
from app.services.report_service import generate_executive_pdf_report
from app.services.relationship_service import discover_dataset_relationships
from app.services.privacy_service import generate_dp_micro_surrogate

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.get("/relationships")
def get_dataset_relationships(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns discovered foreign-key relationships and join candidates across
    all datasets belonging to the current user.
    """
    return discover_dataset_relationships(current_user.id, db)

@router.post("/upload", response_model=DatasetSummary)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset_name = name or (file.filename.rsplit(".", 1)[0] if file.filename else "Dataset")
    dataset = await process_and_ingest_dataset(file, dataset_name, current_user.id, db)
    return DatasetSummary.model_validate(dataset)

@router.get("", response_model=List[DatasetSummary])
def list_datasets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).order_by(Dataset.created_at.desc()).all()
    return [DatasetSummary.model_validate(d) for d in datasets]

@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset_detail(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    # Read sample rows from physical SQLite table
    sample_data = []
    try:
        sample_df = pd.read_sql_query(f"SELECT * FROM {dataset.physical_table_name} LIMIT 10", con=engine)
        sample_data = sample_df.to_dict(orient="records")
    except Exception:
        sample_data = []

    columns_meta_raw = json.loads(dataset.columns_meta or "[]")
    columns_meta = [ColumnMeta(**c) for c in columns_meta_raw]

    return DatasetDetail(
        id=dataset.id,
        name=dataset.name,
        original_filename=dataset.original_filename,
        physical_table_name=dataset.physical_table_name,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        health_score=dataset.health_score,
        columns_meta=columns_meta,
        created_at=dataset.created_at,
        remediation_logs=[RemediationLogOut.model_validate(l) for l in dataset.remediation_logs],
        facts=[DatasetFactOut.model_validate(f) for f in dataset.facts],
        sample_data=sample_data
    )

@router.get("/{dataset_id}/audit-logs", response_model=List[RemediationLogOut])
def get_remediation_logs(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    logs = db.query(RemediationLog).filter(RemediationLog.dataset_id == dataset.id).order_by(RemediationLog.id.asc()).all()
    return [RemediationLogOut.model_validate(l) for l in logs]

@router.get("/{dataset_id}/facts", response_model=List[DatasetFactOut])
def get_dataset_facts(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    facts = db.query(DatasetFact).filter(DatasetFact.dataset_id == dataset.id).order_by(DatasetFact.id.asc()).all()
    return [DatasetFactOut.model_validate(f) for f in facts]

@router.get("/{dataset_id}/report/pdf")
def download_executive_report_pdf(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates and returns an executive PDF intelligence dossier for the given dataset.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    pdf_stream = generate_executive_pdf_report(dataset, current_user.name)
    filename = f"{dataset.name.replace(' ', '_')}_Executive_Dossier.pdf"

    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@router.get("/{dataset_id}/privacy-audit")
def get_dataset_privacy_audit(
    dataset_id: int,
    epsilon: float = 1.0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns mathematical Differential Privacy metrics and a preview of the
    Topologically Identical Micro-Surrogate dataset used for LLM grounding.
    Zero raw enterprise rows or PII are exposed.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    try:
        raw_df = pd.read_sql_query(f'SELECT * FROM "{dataset.physical_table_name}"', con=engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read physical table: {e}")

    surrogate_df, audit_meta = generate_dp_micro_surrogate(
        raw_df,
        epsilon=epsilon,
        delta=1e-5,
        num_synthetic_rows=15
    )

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "physical_table_name": dataset.physical_table_name,
        "real_rows_count": dataset.row_count,
        "synthetic_rows_count": audit_meta["synthetic_rows_count"],
        "epsilon": audit_meta["epsilon"],
        "delta": audit_meta["delta"],
        "pii_columns_scrubbed": audit_meta["pii_columns_scrubbed"],
        "topological_fidelity_score": audit_meta["topological_fidelity_score"],
        "privacy_guarantee": audit_meta["privacy_guarantee"],
        "surrogate_preview": surrogate_df.head(10).to_dict(orient="records"),
        "surrogate_columns": list(surrogate_df.columns)
    }

@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    # Drop physical SQLite table
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {dataset.physical_table_name}"))
            conn.commit()
    except Exception:
        pass

    db.delete(dataset)
    db.commit()
    return {"message": "Dataset and physical SQLite table deleted successfully."}
