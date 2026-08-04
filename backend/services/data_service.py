"""
Data Service — manages in-memory pandas DataFrames across requests.
Uses a session store keyed by dataset_id with LRU eviction to prevent OOM.
"""
import gc
import os
import uuid
import logging
import tempfile
from collections import OrderedDict
from typing import Optional
import pandas as pd
import numpy as np
from firebase_admin import firestore, storage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LRU DataFrame Store — evicts the oldest entry when limit is exceeded.
# Render free tier has 512MB RAM; each DataFrame can be 100–400MB, so
# keeping more than 3 simultaneous datasets risks OOM crashes.
# ---------------------------------------------------------------------------
MAX_CACHED_DATASETS = 3
MAX_ROWS = 500_000  # datasets larger than this are sampled down

_dataframe_store: OrderedDict[str, pd.DataFrame] = OrderedDict()


def _store_put(dataset_id: str, df: pd.DataFrame) -> None:
    """Insert/update a DataFrame in the LRU store, evicting the oldest if over limit."""
    if dataset_id in _dataframe_store:
        _dataframe_store.move_to_end(dataset_id)
    _dataframe_store[dataset_id] = df
    while len(_dataframe_store) > MAX_CACHED_DATASETS:
        evicted_id, evicted_df = _dataframe_store.popitem(last=False)
        del evicted_df
        gc.collect()
        logger.info(f"LRU evicted dataset {evicted_id} from memory store (limit={MAX_CACHED_DATASETS})")


def _store_get(dataset_id: str) -> Optional[pd.DataFrame]:
    """Retrieve a DataFrame and mark it as most-recently-used."""
    if dataset_id in _dataframe_store:
        _dataframe_store.move_to_end(dataset_id)
        return _dataframe_store[dataset_id]
    return None


def get_store_memory_mb() -> float:
    """Return total RAM used by all cached DataFrames (for health endpoint)."""
    try:
        return sum(
            df.memory_usage(deep=True).sum()
            for df in _dataframe_store.values()
        ) / 1024 / 1024
    except Exception:
        return 0.0


def _apply_row_cap(df: pd.DataFrame, dataset_id: str) -> pd.DataFrame:
    """If df has more than MAX_ROWS, sample it down with a warning."""
    if len(df) > MAX_ROWS:
        logger.warning(
            f"Dataset {dataset_id} has {len(df):,} rows — sampling down to {MAX_ROWS:,} to stay within memory limits."
        )
        df = df.sample(n=MAX_ROWS, random_state=42).reset_index(drop=True)
    return df


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

    # Apply row cap before storing to prevent large uploads from blowing memory
    df = _apply_row_cap(df, dataset_id)

    _store_put(dataset_id, df)
    mem_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
    logger.info(
        f"Loaded dataset {dataset_id}: {len(df):,} rows × {len(df.columns)} cols "
        f"({mem_mb:.1f} MB in-process). Store total: {get_store_memory_mb():.1f} MB"
    )
    return dataset_id, df


def get_dataframe(dataset_id: str, user_id: str) -> Optional[pd.DataFrame]:
    """Get a DataFrame by dataset_id. Verifies user ownership. Tries Firebase Storage download if not in memory."""
    cached = _store_get(dataset_id)
    if cached is not None:
        return cached

    db = firestore.client()
    doc_ref = db.collection('users').document(user_id).collection('datasets').document(dataset_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
        
    meta = doc.to_dict()
    file_path = meta.get("file_path")
    original_filename = meta.get("original_filename")
    if not file_path:
        return None

    bucket = storage.bucket()
    blob = bucket.blob(file_path)
    
    ext = os.path.splitext(original_filename)[1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        blob.download_to_filename(temp_file.name)
        temp_file_path = temp_file.name

    try:
        _, df = load_dataset(temp_file_path, original_filename, dataset_id=dataset_id, user_id=user_id)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    return df


def update_dataframe(dataset_id: str, df: pd.DataFrame, user_id: str):
    """Replace the DataFrame for a dataset (after cleaning ops). Updates Firestore."""
    _store_put(dataset_id, df)
    db = firestore.client()
    doc_ref = db.collection('users').document(user_id).collection('datasets').document(dataset_id)
    if doc_ref.get().exists:
        doc_ref.update({
            "rows": len(df),
            "columns": len(df.columns)
        })


def get_dataset_meta(dataset_id: str, user_id: str) -> Optional[dict]:
    db = firestore.client()
    doc_ref = db.collection('users').document(user_id).collection('datasets').document(dataset_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None


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
