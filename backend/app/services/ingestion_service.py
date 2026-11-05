import io
import json
import time
from typing import Tuple
from fastapi import UploadFile, HTTPException
import pandas as pd
from sqlalchemy.orm import Session
from app.db.session import engine
from app.models.dataset import Dataset
from app.models.audit import RemediationLog
from app.models.facts import DatasetFact
from app.services.cleaner_service import clean_and_profile_dataset
from app.services.discovery_service import discover_dataset_facts

async def process_and_ingest_dataset(file: UploadFile, name: str, user_id: int, db: Session) -> Dataset:
    filename = file.filename or "dataset.csv"
    contents = await file.read()
    
    # 1. Parse File
    try:
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            raw_df = pd.read_excel(io.BytesIO(contents))
        else:
            try:
                raw_df = pd.read_csv(io.BytesIO(contents), encoding="utf-8")
            except UnicodeDecodeError:
                raw_df = pd.read_csv(io.BytesIO(contents), encoding="latin1")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    if raw_df.empty:
        raise HTTPException(status_code=400, detail="Uploaded dataset contains no data.")

    # 2. Run Auto-Remediation & Profiling (Requirement 1)
    cleaned_df, health_score, remediation_logs, columns_meta = clean_and_profile_dataset(raw_df)

    # 3. Create Dataset Record in App Metadata
    safe_ts = int(time.time())
    physical_table_name = f"user_{user_id}_ds_{safe_ts}"

    dataset = Dataset(
        user_id=user_id,
        name=name.strip() if name else filename.split(".")[0],
        original_filename=filename,
        physical_table_name=physical_table_name,
        row_count=len(cleaned_df),
        column_count=len(cleaned_df.columns),
        health_score=health_score,
        columns_meta=json.dumps(columns_meta)
    )
    db.add(dataset)
    db.flush()  # Populates dataset.id

    # 4. Save Cleaned Physical Table to SQLite using current session connection
    try:
        cleaned_df.to_sql(physical_table_name, con=db.connection(), if_exists="replace", index=False)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to write physical SQLite table: {str(e)}")

    # 5. Persist Remediation Audit Logs
    for log_entry in remediation_logs:
        audit_row = RemediationLog(
            dataset_id=dataset.id,
            column_name=log_entry["column_name"],
            issue_type=log_entry["issue_type"],
            issue_description=log_entry["issue_description"],
            resolution_strategy=log_entry["resolution_strategy"],
            resolution_details=log_entry["resolution_details"]
        )
        db.add(audit_row)

    # 6. Discover Statistical Relationships & Facts (Requirement 2)
    facts = discover_dataset_facts(cleaned_df, dataset.name)
    for fact in facts:
        fact_row = DatasetFact(
            dataset_id=dataset.id,
            fact_type=fact["fact_type"],
            title=fact["title"],
            description=fact["description"],
            metric_value=fact.get("metric_value")
        )
        db.add(fact_row)

    db.commit()
    db.refresh(dataset)
    return dataset
