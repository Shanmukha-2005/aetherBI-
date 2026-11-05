import json
import re
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import pandas as pd
from sqlalchemy.orm import Session
from app.db.session import get_db, engine
from app.models.user import User
from app.models.dataset import Dataset
from app.models.query import QueryHistory
from app.models.chat import ChatMessage
from app.schemas.query import (
    SQLGenerateRequest, SQLGenerateResponse, QueryHistoryOut,
    SQLExecuteRequest, SQLExecuteResponse,
    NLChartGenerateRequest, NLChartGenerateResponse
)
from app.schemas.chat import ChatPromptRequest, ChatMessageOut
from app.api.deps import get_current_user
from app.services.llm_service import generate_sqlite_sql
from app.services.relationship_service import discover_dataset_relationships
from app.services.privacy_service import generate_dp_micro_surrogate

router = APIRouter(prefix="/sql-studio", tags=["SQL Studio"])

@router.post("/generate", response_model=SQLGenerateResponse)
def generate_sql(
    payload: SQLGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == payload.dataset_id,
        Dataset.user_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    # Multi-dataset support if requested
    multi_tables_info = []
    detected_joins = []
    if payload.additional_dataset_ids:
        all_ds_ids = [payload.dataset_id] + payload.additional_dataset_ids
        datasets_list = db.query(Dataset).filter(
            Dataset.id.in_(all_ds_ids),
            Dataset.user_id == current_user.id
        ).all()
        for ds in datasets_list:
            multi_tables_info.append({
                "id": ds.id,
                "name": ds.name,
                "table_name": ds.physical_table_name,
                "columns": json.loads(ds.columns_meta or "[]")
            })
        all_rels = discover_dataset_relationships(current_user.id, db)
        detected_joins = [
            r for r in all_rels 
            if r["dataset_1_id"] in all_ds_ids and r["dataset_2_id"] in all_ds_ids
        ]

    # Fetch schema info, sample/full data, and distinct categorical values for deep dataset grounding
    columns_meta = json.loads(dataset.columns_meta or "[]")
    sample_rows = []
    distinct_categories = {}
    dataset_csv_str = ""
    is_full_dataset = False

    try:
        raw_df = pd.read_sql_query(f'SELECT * FROM "{dataset.physical_table_name}"', con=engine)
        # Synthesize Topologically Identical Micro-Surrogate under (ε=1.0, δ=1e-5)-Differential Privacy
        surrogate_df, privacy_meta = generate_dp_micro_surrogate(
            raw_df,
            epsilon=1.0,
            delta=1e-5,
            num_synthetic_rows=15
        )
        sample_rows = surrogate_df.to_dict(orient="records")
        dataset_csv_str = surrogate_df.to_csv(index=False)
        is_full_dataset = False
    except Exception:
        sample_rows = []
        dataset_csv_str = ""
        is_full_dataset = False

    for col in columns_meta:
        if col.get("type") == "categorical":
            try:
                col_name = col["name"]
                cat_df = pd.read_sql_query(
                    f'SELECT DISTINCT "{col_name}" FROM "{dataset.physical_table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 25',
                    con=engine
                )
                distinct_categories[col_name] = [str(val) for val in cat_df[col_name].dropna().tolist()]
            except Exception:
                pass

    # Retrieve conversational history context if provided, or pull recent turns from QueryHistory
    conv_history = payload.conversation_history
    if conv_history is None:
        prev_queries = db.query(QueryHistory).filter(
            QueryHistory.dataset_id == dataset.id,
            QueryHistory.user_id == current_user.id
        ).order_by(QueryHistory.created_at.desc()).limit(3).all()
        prev_queries.reverse()
        conv_history = [
            {"role": "user", "content": q.prompt, "generated_sql": q.generated_sql}
            for q in prev_queries
        ]

    # Call Gemini NL-to-SQL Generator (with full dataset when <= 500 rows, multi-table context, and conversational memory)
    gen_result = generate_sqlite_sql(
        prompt=payload.prompt,
        table_name=dataset.physical_table_name,
        schema_info=columns_meta,
        sample_rows=sample_rows,
        distinct_categories=distinct_categories,
        dataset_csv=dataset_csv_str,
        is_full_dataset=is_full_dataset,
        multi_tables_info=multi_tables_info,
        detected_joins=detected_joins,
        conversation_history=conv_history,
        api_key=payload.api_key
    )

    query_record = QueryHistory(
        dataset_id=dataset.id,
        user_id=current_user.id,
        prompt=payload.prompt.strip(),
        generated_sql=gen_result["sql"],
        explanation=gen_result["explanation"]
    )
    db.add(query_record)
    db.commit()
    db.refresh(query_record)

    return SQLGenerateResponse.model_validate(query_record)

@router.post("/execute", response_model=SQLExecuteResponse)
def execute_sql(
    payload: SQLExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a generated read-only SQLite SELECT query against the user's dataset,
    measures execution latency, and generates autonomous chart recommendations.
    """
    dataset = db.query(Dataset).filter(
        Dataset.id == payload.dataset_id,
        Dataset.user_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    raw_sql = payload.sql.strip().rstrip(";")
    if not raw_sql:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    lower_sql = raw_sql.lower()

    # Security check 1: Reject multiple semicolon statements
    if ";" in raw_sql:
        raise HTTPException(status_code=400, detail="Multiple SQL statements in a single execution are forbidden.")

    # Security check 2: Must be read-only (SELECT or WITH)
    if not (lower_sql.startswith("select") or lower_sql.startswith("with")):
        raise HTTPException(status_code=400, detail="Only read-only SELECT and WITH queries can be executed.")

    # Security check 3: Reject destructive DDL/DML keywords
    forbidden = ["drop", "delete", "insert", "update", "alter", "create", "replace", "attach", "detach", "vacuum", "reindex", "pragma"]
    for word in forbidden:
        if re.search(r'\b' + word + r'\b', lower_sql):
            raise HTTPException(status_code=400, detail=f"Operation '{word.upper()}' is not permitted for security reasons.")

    # Ensure query limits large scans to protect browser memory
    limited_sql = raw_sql
    if not re.search(r'\blimit\s+\d+\b', lower_sql):
        limited_sql = f"{raw_sql} LIMIT 500"

    start_time = time.perf_counter()
    try:
        res_df = pd.read_sql_query(limited_sql, con=engine)
        exec_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"SQLite execution failed: {str(err)}")

    # Clean NaNs for JSON compliance
    res_df = res_df.fillna("")
    columns = list(res_df.columns)
    total_returned = len(res_df)
    rows = res_df.to_dict(orient="records")

    # Autonomous dynamic chart suggestion based on output shape
    chart_suggestion = None
    if total_returned > 0 and len(columns) >= 2:
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(res_df[c])]
        non_numeric_cols = [c for c in columns if c not in numeric_cols]
        date_col = next((c for c in columns if any(kw in c.lower() for kw in ['date', 'year', 'month', 'time', 'period', 'quarter'])), None)

        if date_col and numeric_cols:
            target_num = next((c for c in numeric_cols if c != date_col), numeric_cols[0])
            chart_suggestion = {
                "chart_type": "line",
                "title": f"{target_num.replace('_', ' ').title()} across {date_col.replace('_', ' ').title()}",
                "x_key": date_col,
                "y_key": target_num,
                "data": rows[:50]
            }
        elif non_numeric_cols and numeric_cols:
            cat_col = non_numeric_cols[0]
            target_num = numeric_cols[0]
            chart_suggestion = {
                "chart_type": "bar",
                "title": f"{target_num.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                "x_key": cat_col,
                "y_key": target_num,
                "data": rows[:30]
            }
        elif len(numeric_cols) >= 2:
            chart_suggestion = {
                "chart_type": "scatter",
                "title": f"{numeric_cols[1].replace('_', ' ').title()} vs {numeric_cols[0].replace('_', ' ').title()}",
                "x_key": numeric_cols[0],
                "y_key": numeric_cols[1],
                "data": rows[:50]
            }

    return SQLExecuteResponse(
        columns=columns,
        rows=rows,
        total_rows=total_returned,
        execution_time_ms=exec_time_ms,
        chart_suggestion=chart_suggestion
    )

@router.post("/chat", response_model=ChatMessageOut)
def chat_with_data(
    payload: ChatPromptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Multi-turn Conversational Q&A turn with dataset context memory.
    """
    dataset = db.query(Dataset).filter(
        Dataset.id == payload.dataset_id,
        Dataset.user_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    # Fetch recent conversation history (last 6 messages)
    prev_messages = db.query(ChatMessage).filter(
        ChatMessage.dataset_id == dataset.id,
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(6).all()
    prev_messages.reverse()

    conv_history = [
        {
            "role": m.role,
            "content": m.content,
            "generated_sql": m.generated_sql or ""
        }
        for m in prev_messages
    ]

    # Save user message
    user_msg = ChatMessage(
        dataset_id=dataset.id,
        user_id=current_user.id,
        role="user",
        content=payload.prompt.strip()
    )
    db.add(user_msg)
    db.commit()

    # Load dataset schema, data, and distinct categories
    columns_meta = json.loads(dataset.columns_meta or "[]")
    sample_rows = []
    dataset_csv_str = ""
    is_full_dataset = False
    distinct_categories = {}

    try:
        raw_df = pd.read_sql_query(f'SELECT * FROM "{dataset.physical_table_name}"', con=engine)
        surrogate_df, privacy_meta = generate_dp_micro_surrogate(
            raw_df,
            epsilon=1.0,
            delta=1e-5,
            num_synthetic_rows=15
        )
        sample_rows = surrogate_df.to_dict(orient="records")
        dataset_csv_str = surrogate_df.to_csv(index=False)
        is_full_dataset = False
    except Exception:
        sample_rows = []
        dataset_csv_str = ""
        is_full_dataset = False

    for col in columns_meta:
        if col.get("type") == "categorical":
            try:
                col_name = col["name"]
                cat_df = pd.read_sql_query(
                    f'SELECT DISTINCT "{col_name}" FROM "{dataset.physical_table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 25',
                    con=engine
                )
                distinct_categories[col_name] = [str(val) for val in cat_df[col_name].dropna().tolist()]
            except Exception:
                pass

    # Generate SQL with conversational history context
    gen_result = generate_sqlite_sql(
        prompt=payload.prompt,
        table_name=dataset.physical_table_name,
        schema_info=columns_meta,
        sample_rows=sample_rows,
        distinct_categories=distinct_categories,
        dataset_csv=dataset_csv_str,
        is_full_dataset=is_full_dataset,
        conversation_history=conv_history,
        api_key=payload.api_key
    )

    # Save assistant message
    assistant_msg = ChatMessage(
        dataset_id=dataset.id,
        user_id=current_user.id,
        role="assistant",
        content=gen_result["explanation"],
        generated_sql=gen_result["sql"],
        explanation=gen_result["explanation"]
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatMessageOut.model_validate(assistant_msg)

@router.get("/chat/{dataset_id}", response_model=List[ChatMessageOut])
def get_chat_history(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    messages = db.query(ChatMessage).filter(
        ChatMessage.dataset_id == dataset.id,
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.asc()).limit(50).all()

    return [ChatMessageOut.model_validate(m) for m in messages]

@router.delete("/chat/{dataset_id}")
def clear_chat_history(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    db.query(ChatMessage).filter(
        ChatMessage.dataset_id == dataset.id,
        ChatMessage.user_id == current_user.id
    ).delete()
    db.commit()

    return {"message": "Chat conversation cleared successfully."}

@router.get("/history/{dataset_id}", response_model=List[QueryHistoryOut])
def get_query_history(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    records = db.query(QueryHistory).filter(
        QueryHistory.dataset_id == dataset.id
    ).order_by(QueryHistory.created_at.desc()).limit(20).all()

    return [QueryHistoryOut.model_validate(r) for r in records]

@router.post("/generate-chart", response_model=NLChartGenerateResponse)
def generate_chart_from_nl(
    payload: NLChartGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Translates a natural language visualization prompt into an optimized SQLite aggregation query,
    executes it in real-time, and formats the result coordinates for instant Recharts rendering.
    """
    dataset = db.query(Dataset).filter(
        Dataset.id == payload.dataset_id,
        Dataset.user_id == current_user.id
    ).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    columns_meta = json.loads(dataset.columns_meta or "[]")
    sample_rows = []
    distinct_categories = {}
    dataset_csv_str = ""
    is_full_dataset = False

    try:
        raw_df = pd.read_sql_query(f'SELECT * FROM "{dataset.physical_table_name}"', con=engine)
        surrogate_df, privacy_meta = generate_dp_micro_surrogate(
            raw_df,
            epsilon=1.0,
            delta=1e-5,
            num_synthetic_rows=15
        )
        sample_rows = surrogate_df.to_dict(orient="records")
        dataset_csv_str = surrogate_df.to_csv(index=False)
        is_full_dataset = False
    except Exception:
        sample_rows = []
        dataset_csv_str = ""
        is_full_dataset = False

    for col in columns_meta:
        if col.get("type") == "categorical":
            try:
                col_name = col["name"]
                cat_df = pd.read_sql_query(
                    f'SELECT DISTINCT "{col_name}" FROM "{dataset.physical_table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 25',
                    con=engine
                )
                distinct_categories[col_name] = [str(val) for val in cat_df[col_name].dropna().tolist()]
            except Exception:
                pass

    # Generate SQL query optimized for visualization
    gen_result = generate_sqlite_sql(
        prompt=payload.prompt,
        table_name=dataset.physical_table_name,
        schema_info=columns_meta,
        sample_rows=sample_rows,
        distinct_categories=distinct_categories,
        dataset_csv=dataset_csv_str,
        is_full_dataset=is_full_dataset,
        api_key=payload.api_key
    )

    generated_sql = gen_result["sql"]
    explanation = gen_result["explanation"]

    # Execute generated SQL to fetch live chart data points
    clean_sql = generated_sql.strip().rstrip(";")
    if ";" in clean_sql:
        raise HTTPException(status_code=400, detail="Multi-statement queries not permitted.")
    if not clean_sql.upper().startswith("SELECT") and not clean_sql.upper().startswith("WITH"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are permitted.")

    try:
        df = pd.read_sql_query(clean_sql, con=engine)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Chart query execution failed: {str(e)}")

    import numpy as np
    df = df.replace([np.nan, np.inf, -np.inf], None)
    rows = df.to_dict(orient="records")
    columns = list(df.columns)

    if not rows or not columns:
        raise HTTPException(status_code=400, detail="Query returned zero records for chart rendering.")

    # Determine chart type: user preference override or detect from prompt or column shape
    prompt_lower = payload.prompt.lower()
    selected_chart = payload.chart_type
    if not selected_chart:
        if "scatter" in prompt_lower or "correlation" in prompt_lower or "vs" in prompt_lower:
            selected_chart = "scatter"
        elif "line" in prompt_lower or "trend" in prompt_lower or "over time" in prompt_lower:
            selected_chart = "line"
        elif "pie" in prompt_lower or "donut" in prompt_lower or "share" in prompt_lower or "proportion" in prompt_lower:
            selected_chart = "pie"
        elif "area" in prompt_lower:
            selected_chart = "area"
        elif "bar" in prompt_lower or "column" in prompt_lower:
            selected_chart = "bar"
        else:
            # Fallback to column shape heuristic
            date_cols = [c for c in columns if any(kw in c.lower() for kw in ["date", "year", "month", "time", "day"])]
            num_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
            if date_cols and num_cols:
                selected_chart = "line"
            elif len(num_cols) >= 2:
                selected_chart = "scatter"
            else:
                selected_chart = "bar"

    # Identify X and Y keys
    x_key = columns[0]
    y_key = columns[1] if len(columns) > 1 else columns[0]
    num_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    non_num_cols = [c for c in columns if not pd.api.types.is_numeric_dtype(df[c])]

    if selected_chart in ["bar", "pie", "area"]:
        if non_num_cols:
            x_key = non_num_cols[0]
        if num_cols:
            y_key = num_cols[0]
        elif len(columns) > 1:
            y_key = columns[1]
    elif selected_chart == "line":
        date_cols = [c for c in columns if any(kw in c.lower() for kw in ["date", "year", "month", "time", "day"])]
        if date_cols:
            x_key = date_cols[0]
        elif non_num_cols:
            x_key = non_num_cols[0]
        if num_cols:
            y_key = num_cols[0]
    elif selected_chart == "scatter":
        if len(num_cols) >= 2:
            x_key = num_cols[0]
            y_key = num_cols[1]
        elif len(columns) >= 2:
            x_key = columns[0]
            y_key = columns[1]

    title = f"{y_key.replace('_', ' ').title()} by {x_key.replace('_', ' ').title()}"
    if selected_chart == "scatter":
        title = f"{y_key.replace('_', ' ').title()} vs {x_key.replace('_', ' ').title()}"

    return NLChartGenerateResponse(
        title=title,
        chart_type=selected_chart,
        x_key=x_key,
        y_key=y_key,
        data=rows[:60],
        explanation=explanation,
        generated_sql=clean_sql,
        total_data_points=len(rows)
    )

