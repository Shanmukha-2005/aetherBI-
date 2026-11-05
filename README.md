# AetherBI — Autonomous AI Business Intelligence Agent (SQLite Edition)

A modern, interactive, and autonomous Business Intelligence platform powered by **FastAPI**, **SQLite**, and **React + Vite with Framer Motion**.

---

## 🌟 Key Features

1. **Automated Data Health & Smart Remediation (Requirement 1)**:
   - Ingests `.csv` and `.xlsx` files.
   - Detects null/empty fields, mixed data types, malformed dates, extreme statistical outliers, and exact duplicate rows.
   - Automatically resolves issues using best-practice statistics:
     - **Median Imputation** for skewed numeric distributions or outlier-heavy columns.
     - **Mean Imputation** for balanced/symmetric numeric data.
     - **Mode Imputation** or **"Unknown"** classification for categorical values.
     - **ISO-8601 Standardization** for timestamps (`YYYY-MM-DD HH:MM:SS`).
     - **Column Dropping** for severe missingness (>70% nulls).
     - **Deduplication** to eliminate double-counting.
   - Generates a **transparent remediation audit log** explaining *what problem was detected*, *the strategy used*, and *why it was chosen*.
   - Stores the cleaned dataset as a dedicated physical table in **SQLite** (`user_{id}_ds_{id}`).

2. **Relationship Discovery & Unique Facts Engine (Requirement 2)**:
   - Computes the **Pearson & Spearman correlation matrix** to discover how variables interact.
   - Uncovers **Pareto 80/20 power laws** (e.g., top 15% of products driving 80% of revenue).
   - Identifies **categorical dominance** (single categories controlling >50-70% of dataset activity).
   - Detects high-volatility variables with heavy tails.
   - Translates findings into **plain-English executive takeaways** via **Google Gemini** (with built-in offline heuristic fallback).

3. **Auto-Generated Dashboards & Reactive Visualizations**:
   - Animated KPI metric counters (Total Records, Active Attributes, Health Score %, Date Timeline).
   - Server-side pre-aggregated charts using **Recharts**:
     - Distribution histograms for numerical columns.
     - Top category frequency bar charts.
     - Category aggregation donut charts.
     - Monthly average time-series trend lines.

4. **Natural Language to SQLite Generator**:
   - Contextualizes queries using the active dataset's SQLite table name, schema, and sample records.
   - Translates plain-English requests into clean, optimized, read-only SQLite `SELECT` queries.
   - Provides a clear **Query Logic Breakdown** explaining the joins, filters, and aggregations.
   - One-click **Copy SQL** with clipboard feedback.
   - Maintains a searchable query history drawer.

5. **Single-Tier Member Workspace**:
   - Simplified user access: upload datasets, review automated cleaning logs, explore dashboards, read facts, and generate queries without complicated multi-tier administrative permissions.

---

## 🚀 Quickstart

### 1. Launch Everything in One Click
Double click `run_dev.bat` or run:
```cmd
run_dev.bat
```

### 2. Manual Startup

**Terminal 1 — Backend (FastAPI):**
```powershell
.\venv\Scripts\uvicorn app.main:app --app-dir backend --reload --port 8000
```

**Terminal 2 — Frontend (React + Vite):**
```powershell
cd frontend
npm run dev
```

- **Frontend App**: `http://localhost:5173`
- **Backend API Docs (Swagger)**: `http://localhost:8000/docs`

---

## 🧪 Testing

Run backend tests verifying user auth, data ingestion, auto-remediation, correlation discovery, and SQL generation:
```powershell
.\venv\Scripts\pytest backend\tests\test_backend.py -v
```

---

## 📊 Sample Data Included

A sample dirty business dataset is provided at [`sample_business_data.csv`](sample_business_data.csv). You can also click **"Load Sample Dirty Dataset"** directly in the upload page UI to test the entire pipeline with one click.
