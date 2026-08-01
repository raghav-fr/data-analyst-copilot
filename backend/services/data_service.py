"""
Data Service — manages in-memory pandas DataFrames across requests.
Uses a session store keyed by dataset_id.
"""
import os
import uuid
import hashlib
import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# In-memory store: dataset_id -> DataFrame
_dataframe_store: dict[str, pd.DataFrame] = {}
_dataset_meta: dict[str, dict] = {}


def load_dataset(file_path: str, original_filename: str, dataset_id: str = None, user_id: str = None) -> tuple[str, pd.DataFrame]:
    """Load a dataset from file and store it. Returns (dataset_id, df)."""
    ext = os.path.splitext(original_filename)[1].lower()

    if ext == ".csv":
        df = pd.read_csv(file_path, low_memory=False)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    elif ext == ".json":
        try:
            df = pd.read_json(file_path)
        except Exception:
            import json
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and len(data) == 1:
                    first_key = list(data.keys())[0]
                    if isinstance(data[first_key], list):
                        data = data[first_key]
                df = pd.DataFrame(data)
            except json.JSONDecodeError:
                df = pd.read_json(file_path, lines=True)
    elif ext == ".parquet":
        df = pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if not dataset_id:
        dataset_id = str(uuid.uuid4())
    
    _dataframe_store[dataset_id] = df
    if user_id:
        _dataset_meta[dataset_id] = {
            "user_id": user_id,
            "filename": original_filename,
            "file_path": file_path,
            "rows": len(df),
            "columns": len(df.columns),
        }
    logger.info(f"Loaded dataset {dataset_id}: {len(df)} rows × {len(df.columns)} cols")
    return dataset_id, df


def register_dataset_meta(dataset_id: str, user_id: str, filename: str, file_path: str, rows: int, columns: int):
    """Register dataset metadata so it can be lazy-loaded later without DB access."""
    _dataset_meta[dataset_id] = {
        "user_id": user_id,
        "filename": filename,
        "file_path": file_path,
        "rows": rows,
        "columns": columns,
    }


def get_dataframe(dataset_id: str, user_id: str) -> Optional[pd.DataFrame]:
    """Get a DataFrame by dataset_id. Verifies user ownership. Tries disk reload if not in memory."""
    meta = _dataset_meta.get(dataset_id)
    if not meta or meta.get("user_id") != user_id:
        return None

    if dataset_id in _dataframe_store:
        return _dataframe_store[dataset_id]

    # Try to reload from disk
    _, df = load_dataset(meta["file_path"], meta["filename"], dataset_id=dataset_id, user_id=user_id)
    return df


def update_dataframe(dataset_id: str, df: pd.DataFrame):
    """Replace the DataFrame for a dataset (after cleaning ops)."""
    _dataframe_store[dataset_id] = df
    if dataset_id in _dataset_meta:
        _dataset_meta[dataset_id]["rows"] = len(df)
        _dataset_meta[dataset_id]["columns"] = len(df.columns)


def get_dataset_meta(dataset_id: str) -> Optional[dict]:
    return _dataset_meta.get(dataset_id)


def get_df_info(df: pd.DataFrame) -> dict:
    """Get comprehensive info about a DataFrame for prompt context."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    dt_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # Smart sample — include head and a few random rows
    sample_rows = min(5, len(df))
    sample = df.head(sample_rows).fillna("").to_dict("records")

    stats = {}
    if numeric_cols:
        stats = df[numeric_cols].describe().round(2).to_dict()

    return {
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "shape": {"rows": len(df), "cols": len(df.columns)},
        "numeric_columns": numeric_cols,
        "categorical_columns": cat_cols,
        "datetime_columns": dt_cols,
        "missing": df.isnull().sum().to_dict(),
        "sample_data": sample,
        "numeric_stats": stats,
    }


def build_profile(df: pd.DataFrame, dataset_id: str, filename: str) -> dict:
    """Build a comprehensive dataset profile."""
    total_cells = df.shape[0] * df.shape[1]
    total_missing = int(df.isnull().sum().sum())
    memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024

    column_profiles = []
    for col in df.columns:
        series = df[col]
        missing_count = int(series.isnull().sum())
        unique_count = int(series.nunique())
        dtype_str = str(series.dtype)

        # Sample values (non-null)
        sample_vals = series.dropna().head(5).tolist()
        sample_vals = [str(v) if not isinstance(v, (int, float, bool)) else v for v in sample_vals]

        col_stats = None
        if pd.api.types.is_numeric_dtype(series):
            col_stats = {
                "mean": round(float(series.mean()), 4) if not series.isna().all() else None,
                "median": round(float(series.median()), 4) if not series.isna().all() else None,
                "std": round(float(series.std()), 4) if not series.isna().all() else None,
                "min": round(float(series.min()), 4) if not series.isna().all() else None,
                "max": round(float(series.max()), 4) if not series.isna().all() else None,
                "q25": round(float(series.quantile(0.25)), 4) if not series.isna().all() else None,
                "q75": round(float(series.quantile(0.75)), 4) if not series.isna().all() else None,
                "skewness": round(float(series.skew()), 4) if not series.isna().all() else None,
                "kurtosis": round(float(series.kurtosis()), 4) if not series.isna().all() else None,
            }
        elif pd.api.types.is_object_dtype(series) or pd.api.types.is_categorical_dtype(series):
            top_vals = series.value_counts().head(5).to_dict()
            col_stats = {
                "top_values": {str(k): int(v) for k, v in top_vals.items()},
                "mode": str(series.mode().iloc[0]) if not series.mode().empty else None,
            }

        column_profiles.append({
            "name": col,
            "dtype": dtype_str,
            "missing": missing_count,
            "missing_pct": round(missing_count / len(df) * 100, 2),
            "unique": unique_count,
            "unique_pct": round(unique_count / len(df) * 100, 2),
            "sample_values": sample_vals,
            "stats": col_stats,
        })

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    dt_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "rows": len(df),
        "columns": len(df.columns),
        "total_missing": total_missing,
        "total_missing_pct": round(total_missing / total_cells * 100, 2) if total_cells > 0 else 0,
        "duplicates": int(df.duplicated().sum()),
        "memory_usage_mb": round(memory_mb, 3),
        "column_profiles": column_profiles,
        "numeric_columns": numeric_cols,
        "categorical_columns": cat_cols,
        "datetime_columns": dt_cols,
    }
