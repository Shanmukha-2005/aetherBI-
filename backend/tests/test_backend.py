import os
import sys
import io
import pytest
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure test DB is used
os.environ["DATABASE_URL"] = "sqlite:///./test_bi_agent.db"

from app.main import app
from app.db.session import engine, Base

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_bi_agent.db"):
        try:
            os.remove("test_bi_agent.db")
        except Exception:
            pass

def test_auth_signup_and_login():
    # 1. Signup
    signup_res = client.post("/api/auth/signup", json={
        "name": "Alex Business",
        "email": "alex@company.com",
        "password": "SecurePassword123!"
    })
    assert signup_res.status_code == 200
    token_data = signup_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["email"] == "alex@company.com"

    # 2. Login
    login_res = client.post("/api/auth/login", json={
        "email": "alex@company.com",
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

def test_ingestion_and_remediation_audit():
    # Signup or login test user
    signup_res = client.post("/api/auth/signup", json={
        "name": "Data Scientist",
        "email": "scientist@company.com",
        "password": "SecurePassword123!"
    })
    if signup_res.status_code == 200:
        token = signup_res.json()["access_token"]
    else:
        login_res = client.post("/api/auth/login", json={
            "email": "scientist@company.com",
            "password": "SecurePassword123!"
        })
        token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}

    # Create synthetic dirty dataframe:
    # - irregular column headers
    # - missing values in numeric & categorical columns
    # - bad dates
    # - duplicate rows
    # - column with >70% nulls
    data = {
        " Order ID # ": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 110], # duplicate row
        "Customer Segment ": ["Enterprise", "SMB", None, "SMB", "Enterprise", "Enterprise", "SMB", "SMB", "Enterprise", "SMB", "SMB"],
        "Sales Amount": [1500.0, None, 2200.0, 180.0, 45000.0, 1300.0, 1450.0, None, 2100.0, 1900.0, 1900.0], # skewed + outlier + nulls
        "Order Date": ["2023-01-15", "01/16/2023", "2023-01-17", None, "2023-01-19", "2023-01-20", "2023-01-21", "2023-01-22", "2023-01-23", "2023-01-24", "2023-01-24"],
        "Sparse Notes": [None, None, "test", None, None, None, None, None, None, None, None] # >70% null -> should be dropped
    }
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # Upload file
    upload_res = client.post(
        "/api/datasets/upload",
        headers=headers,
        data={"name": "Q1 E-Commerce Sales"},
        files={"file": ("sales_dirty.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.status_code} - {upload_res.text}"
    dataset = upload_res.json()
    assert dataset["name"] == "Q1 E-Commerce Sales"
    dataset_id = dataset["id"]

    # Verify Detail & Audit Logs (Requirement 1)
    detail_res = client.get(f"/api/datasets/{dataset_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["sample_data"]) > 0
    assert len(detail["remediation_logs"]) > 0

    # Verify specific fixes logged
    strategies = [l["resolution_strategy"] for l in detail["remediation_logs"]]
    assert "SNAKE_CASE_NORMALIZATION" in strategies
    assert "DEDUPLICATION" in strategies
    assert "COLUMN_DROPPED" in strategies
    assert any("IMPUTATION" in s for s in strategies)

    # Verify Relationship & Facts Discovery (Requirement 2)
    facts_res = client.get(f"/api/datasets/{dataset_id}/facts", headers=headers)
    assert facts_res.status_code == 200
    facts = facts_res.json()
    assert len(facts) > 0

    # Verify Dashboard Pre-aggregation
    dash_res = client.get(f"/api/dashboard/{dataset_id}", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["kpis"]["total_rows"] == 10  # 11 - 1 duplicate = 10
    assert len(dash["charts"]) > 0

    # Verify NL-to-SQL Generator
    sql_res = client.post(
        "/api/sql-studio/generate",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "prompt": "Show top 3 customer segments by total sales amount"
        }
    )
    assert sql_res.status_code == 200
    sql_data = sql_res.json()
    assert "SELECT" in sql_data["generated_sql"].upper()
    assert detail["physical_table_name"] in sql_data["generated_sql"]
    assert len(sql_data["explanation"]) > 0

    # Verify NL-to-SQL for average query
    avg_res = client.post(
        "/api/sql-studio/generate",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "prompt": "the average of sales amount"
        }
    )
    assert avg_res.status_code == 200
    avg_sql = avg_res.json()["generated_sql"]
    assert "AVG" in avg_sql.upper()
    assert "sales_amount" in avg_sql

    # Verify NL-to-SQL for highest entity query
    highest_res = client.post(
        "/api/sql-studio/generate",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "prompt": "the customer segment with the highest sales amount"
        }
    )
    assert highest_res.status_code == 200
    highest_sql = highest_res.json()["generated_sql"]
    assert "ORDER BY" in highest_sql.upper()
    assert "DESC" in highest_sql.upper()
    assert "LIMIT 1" in highest_sql.upper()

    # Verify NL-to-SQL for entity with maximum metric (e.g. year/date with maximum sales)
    max_metric_res = client.post(
        "/api/sql-studio/generate",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "prompt": "output the order date with the maximum sales amount"
        }
    )
    assert max_metric_res.status_code == 200
    max_metric_sql = max_metric_res.json()["generated_sql"]
    assert "sales_amount" in max_metric_sql
    assert "order_date" in max_metric_sql
    assert "ORDER BY" in max_metric_sql.upper()
    assert "DESC" in max_metric_sql.upper()
    assert "LIMIT 1" in max_metric_sql.upper()
    # Confirm it does NOT generate SELECT MAX(order_date)
    assert "MAX(order_date)" not in max_metric_sql
