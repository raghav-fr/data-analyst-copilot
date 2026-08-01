"""Profile route — dataset profiling endpoint."""
import logging
from fastapi import APIRouter, HTTPException, Depends
from models.schemas import DatasetProfile
from services.data_service import get_dataframe, build_profile, get_dataset_meta
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{dataset_id}", response_model=DatasetProfile)
async def get_profile(dataset_id: str, current_user = Depends(get_current_user)):
    """Get comprehensive dataset profile."""
    df = get_dataframe(dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    meta = get_dataset_meta(dataset_id, current_user.uid) or {}
    filename = meta.get("filename", "Unknown")

    profile = build_profile(df, dataset_id, filename)
    return DatasetProfile(**profile)


@router.get("/{dataset_id}/preview")
async def get_preview(dataset_id: str, rows: int = 50, page: int = 1, current_user = Depends(get_current_user)):
    """Get paginated data preview."""
    df = get_dataframe(dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    start = (page - 1) * rows
    end = start + rows
    preview_df = df.iloc[start:end]

    return {
        "dataset_id": dataset_id,
        "total_rows": len(df),
        "total_pages": (len(df) + rows - 1) // rows,
        "current_page": page,
        "rows": rows,
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "data": preview_df.fillna("").to_dict("records"),
    }


@router.get("/{dataset_id}/schema")
async def get_schema(dataset_id: str, current_user = Depends(get_current_user)):
    """Get dataset schema (column names and types)."""
    df = get_dataframe(dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    import numpy as np
    return {
        "dataset_id": dataset_id,
        "columns": [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "category": (
                    "numeric" if hasattr(df[col], 'dtype') and (
                        str(df[col].dtype).startswith('int') or
                        str(df[col].dtype).startswith('float')
                    ) else
                    "datetime" if str(df[col].dtype).startswith('datetime') else
                    "categorical"
                ),
                "missing_count": int(df[col].isnull().sum()),
                "unique_count": int(df[col].nunique()),
            }
            for col in df.columns
        ],
        "total_rows": len(df),
        "total_columns": len(df.columns),
    }
