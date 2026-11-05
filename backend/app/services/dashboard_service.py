from typing import Dict, Any, List
import numpy as np
import pandas as pd
from app.schemas.dashboard import DashboardResponse, KPICards, ChartData, NumericSummary

def generate_dashboard_payload(df: pd.DataFrame, health_score: float) -> DashboardResponse:
    total_rows = len(df)
    total_cols = len(df.columns)
    
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c])]
    date_cols = [c for c in df.columns if "date" in c or "time" in c or pd.api.types.is_datetime64_any_dtype(df[c])]

    # Date range
    date_min = None
    date_max = None
    active_date_col = None
    if date_cols:
        for dc in date_cols:
            try:
                dt_series = pd.to_datetime(df[dc], errors='coerce').dropna()
                if not dt_series.empty:
                    date_min = dt_series.min().strftime("%b %d, %Y")
                    date_max = dt_series.max().strftime("%b %d, %Y")
                    active_date_col = dc
                    break
            except Exception:
                pass

    # Numeric summaries
    num_summaries: List[NumericSummary] = []
    for col in numeric_cols[:4]:
        series = df[col].dropna()
        if not series.empty:
            num_summaries.append(NumericSummary(
                column=col.replace("_", " ").title(),
                min_val=float(round(series.min(), 2)),
                max_val=float(round(series.max(), 2)),
                avg_val=float(round(series.mean(), 2)),
                sum_val=float(round(series.sum(), 2))
            ))

    kpis = KPICards(
        total_rows=total_rows,
        total_cols=total_cols,
        health_score=health_score,
        date_min=date_min,
        date_max=date_max,
        numeric_summaries=num_summaries
    )

    charts: List[ChartData] = []

    # Chart 1: Categorical Breakdown (Bar / Pie)
    if categorical_cols:
        primary_cat = categorical_cols[0]
        top_cats = df[primary_cat].value_counts().head(7).reset_index()
        top_cats.columns = ["name", "count"]
        chart_data = [{"name": str(row["name"])[:20], "value": int(row["count"])} for _, row in top_cats.iterrows()]
        charts.append(ChartData(
            id=f"cat_{primary_cat}",
            title=f"Top {primary_cat.replace('_', ' ').title()} Distribution",
            chart_type="bar",
            x_key="name",
            y_key="value",
            data=chart_data
        ))

    # Chart 2: Numerical Distribution (Histogram)
    if numeric_cols:
        primary_num = numeric_cols[0]
        clean_num = df[primary_num].dropna()
        if not clean_num.empty:
            counts, bin_edges = np.histogram(clean_num, bins=8)
            hist_data = []
            for i in range(len(counts)):
                bin_label = f"{bin_edges[i]:.0f}-{bin_edges[i+1]:.0f}"
                hist_data.append({"range": bin_label, "frequency": int(counts[i])})
            charts.append(ChartData(
                id=f"hist_{primary_num}",
                title=f"{primary_num.replace('_', ' ').title()} Range Distribution",
                chart_type="histogram",
                x_key="range",
                y_key="frequency",
                data=hist_data
            ))

    # Chart 3: Time Series (if date column exists)
    if active_date_col and numeric_cols:
        trend_num = numeric_cols[0]
        try:
            temp_df = df.copy()
            temp_df["_dt"] = pd.to_datetime(temp_df[active_date_col], errors='coerce')
            temp_df = temp_df.dropna(subset=["_dt"])
            # Resample by month or day depending on range
            temp_df["period"] = temp_df["_dt"].dt.strftime("%Y-%m")
            grouped = temp_df.groupby("period")[trend_num].mean().reset_index()
            trend_data = [{"date": str(row["period"]), "metric": round(float(row[trend_num]), 2)} for _, row in grouped.iterrows()]
            if len(trend_data) > 1:
                charts.append(ChartData(
                    id="timeseries_trend",
                    title=f"Monthly Average {trend_num.replace('_', ' ').title()} Trend",
                    chart_type="line",
                    x_key="date",
                    y_key="metric",
                    data=trend_data
                ))
        except Exception:
            pass

    # Chart 4: Secondary Categorical or Metric comparison if available
    if len(categorical_cols) > 1 and numeric_cols:
        sec_cat = categorical_cols[1]
        agg_metric = numeric_cols[0]
        grouped_cat = df.groupby(sec_cat)[agg_metric].sum().sort_values(ascending=False).head(6).reset_index()
        grouped_data = [{"name": str(row[sec_cat])[:20], "total": round(float(row[agg_metric]), 2)} for _, row in grouped_cat.iterrows()]
        charts.append(ChartData(
            id=f"agg_{sec_cat}",
            title=f"Total {agg_metric.replace('_', ' ').title()} by {sec_cat.replace('_', ' ').title()}",
            chart_type="pie",
            x_key="name",
            y_key="total",
            data=grouped_data
        ))

    return DashboardResponse(kpis=kpis, charts=charts)
