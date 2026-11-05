import re
from typing import Tuple, List, Dict, Any
import numpy as np
import pandas as pd

def sanitize_column_name(col_name: str) -> str:
    # Convert to lowercase, replace non-alphanumeric characters with underscore
    name = str(col_name).strip().lower()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    if not name:
        name = "col"
    if name[0].isdigit():
        name = f"c_{name}"
    return name

def is_potential_date_column(series: pd.Series, col_name: str) -> bool:
    # 1. Never treat numeric columns as dates
    if pd.api.types.is_numeric_dtype(series):
        return False
    
    sample = series.dropna().head(15)
    if len(sample) == 0:
        return False

    # 2. Check if sample strings are plain numbers (e.g. "165349.2")
    numeric_like = 0
    for val in sample:
        s_val = str(val).strip().replace(',', '').replace('$', '')
        try:
            float(s_val)
            numeric_like += 1
        except ValueError:
            pass
    if numeric_like >= len(sample) * 0.7:
        return False

    # 3. Must match date patterns or have explicit date naming hints
    date_pattern = re.compile(r"(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})|(\d{4}-\d{2}-\d{2})|([a-zA-Z]{3,9}\s+\d{1,2})")
    has_date_pattern = sum(1 for v in sample if date_pattern.search(str(v))) >= len(sample) * 0.4
    
    date_hints = ["date", "time", "timestamp", "created", "updated", "day", "month"]
    has_date_hint = any(hint in col_name.lower() for hint in date_hints)
    
    if not (has_date_hint or has_date_pattern):
        return False

    parsed_count = 0
    for val in sample:
        try:
            dt = pd.to_datetime(val)
            if 1900 <= dt.year <= 2100:
                parsed_count += 1
        except Exception:
            pass
    return parsed_count >= len(sample) * 0.7

def clean_and_profile_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, float, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Auto-remediation engine for Requirement 1:
    - Normalizes column headers to snake_case
    - Profiles nulls, data types, and anomalies
    - Executes best-practice auto-fixes (median, mean, mode, unknown, date ISO parsing, deduplication)
    - Returns: (cleaned_df, health_score, remediation_logs, columns_meta)
    """
    total_original_rows = len(df)
    original_total_cells = df.size if df.size > 0 else 1
    total_missing_cells = int(df.isna().sum().sum())
    
    remediation_logs: List[Dict[str, Any]] = []
    
    # 1. Standardize column names
    renamed_cols = {}
    seen = set()
    for col in df.columns:
        clean_name = sanitize_column_name(col)
        # Ensure uniqueness
        base_name = clean_name
        counter = 1
        while clean_name in seen:
            clean_name = f"{base_name}_{counter}"
            counter += 1
        seen.add(clean_name)
        renamed_cols[col] = clean_name
    
    if renamed_cols != {c: c for c in df.columns}:
        df = df.rename(columns=renamed_cols)
        remediation_logs.append({
            "column_name": "All Columns",
            "issue_type": "SCHEMA_STANDARDIZATION",
            "issue_description": "Column headers contained irregular casing, whitespaces, or special characters.",
            "resolution_strategy": "SNAKE_CASE_NORMALIZATION",
            "resolution_details": "Sanitized all column headers into standardized SQLite-compliant snake_case identifiers."
        })

    # 2. Deduplication
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        df = df.drop_duplicates().reset_index(drop=True)
        remediation_logs.append({
            "column_name": "Full Table",
            "issue_type": "DUPLICATE_ROWS",
            "issue_description": f"Found {dup_count} exact duplicate rows ({dup_count / total_original_rows * 100:.1f}% of records).",
            "resolution_strategy": "DEDUPLICATION",
            "resolution_details": f"Removed {dup_count} duplicate rows to prevent false weighting and double-counting in aggregations."
        })

    # 3. Column-by-Column Profiling & Intelligent Remediation
    cols_to_drop = []
    columns_meta: List[Dict[str, Any]] = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
        
        # Severe missingness check (> 70%)
        if null_pct > 70.0 and len(df) >= 5:
            cols_to_drop.append(col)
            remediation_logs.append({
                "column_name": col,
                "issue_type": "HIGH_NULL_COLUMN",
                "issue_description": f"Column '{col}' has {null_pct:.1f}% missing values ({null_count}/{len(df)} rows).",
                "resolution_strategy": "COLUMN_DROPPED",
                "resolution_details": f"Dropped column '{col}' because sparse data (>70% null) introduces high distortion in analytical models."
            })
            continue

        # Check if object column contains stringified numbers (e.g. "$1,200.50" or "45000")
        if series.dtype == object:
            cleaned_num = series.dropna().astype(str).str.replace(r'[\$,]', '', regex=True).str.strip()
            converted_num = pd.to_numeric(cleaned_num, errors='coerce')
            if len(series.dropna()) > 0 and converted_num.notna().sum() >= len(series.dropna()) * 0.85:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[\$,]', '', regex=True).str.strip(), errors='coerce')
                series = df[col]

        # 1. Numeric Column Analysis & Imputation
        if pd.api.types.is_numeric_dtype(series):
            unique_count = int(series.nunique())
            if null_count > 0:
                clean_vals = series.dropna()
                skewness = float(clean_vals.skew()) if len(clean_vals) > 2 else 0.0
                
                # Check for outliers via IQR
                q25, q75 = clean_vals.quantile(0.25), clean_vals.quantile(0.75)
                iqr = q75 - q25
                outliers = clean_vals[(clean_vals < q25 - 1.5 * iqr) | (clean_vals > q75 + 1.5 * iqr)]
                has_outliers = len(outliers) > 0

                if abs(skewness) > 1.0 or has_outliers:
                    # Impute with median for resilience
                    impute_val = float(clean_vals.median())
                    df[col] = df[col].fillna(impute_val)
                    remediation_logs.append({
                        "column_name": col,
                        "issue_type": "SKEWED_MISSING_NUMERICS",
                        "issue_description": f"Found {null_count} missing values ({null_pct:.1f}%) in skewed numeric column (skewness: {skewness:.2f}, outliers: {len(outliers)}).",
                        "resolution_strategy": "MEDIAN_IMPUTATION",
                        "resolution_details": f"Imputed missing entries with median value ({impute_val:.2f}) to resist outlier bias and preserve distribution shape."
                    })
                else:
                    # Impute with mean for symmetric data
                    impute_val = float(clean_vals.mean())
                    df[col] = df[col].fillna(impute_val)
                    remediation_logs.append({
                        "column_name": col,
                        "issue_type": "SYMMETRIC_MISSING_NUMERICS",
                        "issue_description": f"Found {null_count} missing values ({null_pct:.1f}%) in balanced numeric column.",
                        "resolution_strategy": "MEAN_IMPUTATION",
                        "resolution_details": f"Imputed missing entries with mean value ({impute_val:.2f}) for balanced statistical representation."
                    })

            columns_meta.append({
                "name": col,
                "type": "numeric",
                "original_type": str(series.dtype),
                "null_count": 0,
                "unique_count": unique_count
            })
            continue

        # 2. Date Detection & Standardization
        if is_potential_date_column(series, col):
            try:
                converted_dates = pd.to_datetime(series, errors='coerce')
                valid_converted = converted_dates.notna().sum()
                if valid_converted > len(df) * 0.4:
                    df[col] = converted_dates.dt.strftime("%Y-%m-%d %H:%M:%S").replace({np.nan: None})
                    # If nulls exist in date, forward-fill or fill with earliest date
                    date_nulls = int(df[col].isna().sum())
                    if date_nulls > 0:
                        df[col] = df[col].ffill().bfill()
                        remediation_logs.append({
                            "column_name": col,
                            "issue_type": "MISSING_DATES",
                            "issue_description": f"Detected {date_nulls} missing timestamps in chronological column '{col}'.",
                            "resolution_strategy": "FORWARD_BACKWARD_FILL",
                            "resolution_details": "Applied forward/backward fill interpolation to preserve time-series continuity."
                        })
                    else:
                        remediation_logs.append({
                            "column_name": col,
                            "issue_type": "MIXED_DATE_FORMAT",
                            "issue_description": f"Column '{col}' contained non-standard or unformatted date strings.",
                            "resolution_strategy": "ISO_DATE_PARSING",
                            "resolution_details": "Standardized all timestamps into unified ISO-8601 strings (YYYY-MM-DD HH:MM:SS)."
                        })
                    
                    columns_meta.append({
                        "name": col,
                        "type": "datetime",
                        "original_type": str(series.dtype),
                        "null_count": 0,
                        "unique_count": int(df[col].nunique())
                    })
                    continue
            except Exception:
                pass

        # Categorical / String Column Analysis & Imputation
        unique_count = int(series.nunique())
        if null_count > 0:
            clean_str = series.dropna().astype(str).str.strip()
            mode_series = clean_str.mode()
            if not mode_series.empty and (clean_str == mode_series[0]).sum() / len(clean_str) > 0.4:
                dominant_val = str(mode_series[0])
                df[col] = df[col].fillna(dominant_val)
                remediation_logs.append({
                    "column_name": col,
                    "issue_type": "MISSING_CATEGORICAL",
                    "issue_description": f"Found {null_count} missing categorical entries ({null_pct:.1f}%).",
                    "resolution_strategy": "MODE_IMPUTATION",
                    "resolution_details": f"Imputed with dominant category mode '{dominant_val}'."
                })
            else:
                df[col] = df[col].fillna("Unknown")
                remediation_logs.append({
                    "column_name": col,
                    "issue_type": "MISSING_CATEGORICAL",
                    "issue_description": f"Found {null_count} missing categorical entries without a clear single majority class.",
                    "resolution_strategy": "UNKNOWN_LABELING",
                    "resolution_details": "Assigned explicit 'Unknown' category label to preserve group integrity without false imputation."
                })

        # Strip whitespace from text
        df[col] = df[col].astype(str).str.strip()

        columns_meta.append({
            "name": col,
            "type": "categorical",
            "original_type": str(series.dtype),
            "null_count": 0,
            "unique_count": unique_count
        })

    # Drop marked high-null columns
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # Compute overall health score: 100 - penalties for missing data, duplicates, and drops
    missing_ratio = total_missing_cells / original_total_cells
    duplicate_ratio = dup_count / total_original_rows if total_original_rows > 0 else 0
    penalty = (missing_ratio * 50.0) + (duplicate_ratio * 30.0) + (len(cols_to_drop) * 5.0)
    health_score = max(20.0, min(100.0, round(100.0 - penalty, 1)))

    return df, health_score, remediation_logs, columns_meta
