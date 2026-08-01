"""Cleaning route — data cleaning operations."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from services.auth_service import get_current_user
from models.schemas import CleaningRequest, CleaningResponse
from services.data_service import get_dataframe, update_dataframe

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=CleaningResponse)
async def clean_data(request: CleaningRequest):
    """Apply a cleaning operation to the dataset."""
    df = get_dataframe(request.dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    import pandas as pd
    import numpy as np

    rows_before = len(df)
    cols_before = len(df.columns)
    op = request.operation
    params = request.params

    try:
        if op == "drop_duplicates":
            subset = params.get("subset")
            keep = params.get("keep", "first")
            df = df.drop_duplicates(subset=subset, keep=keep)

        elif op == "fill_missing":
            strategy = params.get("strategy", "mean")
            columns = params.get("columns", df.columns.tolist())

            for col in columns:
                if col not in df.columns:
                    continue
                if strategy == "mean" and pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].mean())
                elif strategy == "median" and pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].median())
                elif strategy == "mode":
                    df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else "Unknown")
                elif strategy == "ffill":
                    df[col] = df[col].ffill()
                elif strategy == "bfill":
                    df[col] = df[col].bfill()
                elif strategy == "drop":
                    df = df.dropna(subset=[col])
                elif strategy == "value":
                    df[col] = df[col].fillna(params.get("value", 0))

        elif op == "drop_columns":
            columns = params.get("columns", [])
            df = df.drop(columns=[c for c in columns if c in df.columns])

        elif op == "rename_columns":
            mapping = params.get("mapping", {})
            df = df.rename(columns=mapping)

        elif op == "normalize":
            columns = params.get("columns", df.select_dtypes(include=[np.number]).columns.tolist())
            method = params.get("method", "minmax")
            for col in columns:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    if method == "minmax":
                        min_val, max_val = df[col].min(), df[col].max()
                        if max_val != min_val:
                            df[col] = (df[col] - min_val) / (max_val - min_val)
                    elif method == "zscore":
                        df[col] = (df[col] - df[col].mean()) / df[col].std()

        elif op == "encode_categories":
            columns = params.get("columns", df.select_dtypes(include=["object", "category"]).columns.tolist())
            method = params.get("method", "label")
            for col in columns:
                if col not in df.columns:
                    continue
                if method == "label":
                    df[col] = pd.Categorical(df[col]).codes
                elif method == "onehot":
                    dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                    df = pd.concat([df.drop(col, axis=1), dummies], axis=1)

        elif op == "drop_rows_with_missing":
            threshold = params.get("threshold", 0)  # 0 = any missing
            if threshold == 0:
                df = df.dropna()
            else:
                df = df.dropna(thresh=int(len(df.columns) * (1 - threshold)))

        elif op == "convert_dtype":
            column = params.get("column")
            dtype = params.get("dtype")
            if column and dtype and column in df.columns:
                df[column] = df[column].astype(dtype)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {op}")

        # Update in-memory store
        update_dataframe(request.dataset_id, df, current_user.uid)

        return CleaningResponse(
            dataset_id=request.dataset_id,
            operation=op,
            rows_before=rows_before,
            rows_after=len(df),
            columns_before=cols_before,
            columns_after=len(df.columns),
            message=f"Operation '{op}' completed. Rows: {rows_before} → {len(df)}, Columns: {cols_before} → {len(df.columns)}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleaning error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{dataset_id}")
async def get_cleaning_suggestions(dataset_id: str, current_user = Depends(get_current_user)):
    """Get AI-powered cleaning recommendations."""
    df = get_dataframe(dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    import numpy as np
    from services.ai_service import call_ai
    from prompts.system_prompts import CLEANING_RECOMMENDATION_PROMPT

    missing_cols = {col: int(df[col].isnull().sum()) for col in df.columns if df[col].isnull().sum() > 0}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Outlier detection
    outlier_cols = []
    for col in numeric_cols:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df[(df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)]
        if len(outliers) / len(df) > 0.05:  # >5% are outliers
            outlier_cols.append(col)

    prompt = CLEANING_RECOMMENDATION_PROMPT.format(
        dataset_name="dataset",
        missing_columns=str(missing_cols),
        duplicates=int(df.duplicated().sum()),
        dtypes=str({col: str(dtype) for col, dtype in df.dtypes.items()}),
        outlier_columns=str(outlier_cols),
    )

    try:
        response = await call_ai(prompt, temperature=0.3)
        from services.ai_service import extract_json
        suggestions = extract_json(response)
        return {"dataset_id": dataset_id, "suggestions": suggestions}
    except Exception as e:
        logger.warning(f"Could not get cleaning suggestions: {e}")
        # Return basic suggestions
        suggestions = []
        if missing_cols:
            suggestions.append({
                "operation": "fill_missing",
                "description": f"Fill missing values in {list(missing_cols.keys())}",
                "params": {"strategy": "mean", "columns": list(missing_cols.keys())}
            })
        if int(df.duplicated().sum()) > 0:
            suggestions.append({
                "operation": "drop_duplicates",
                "description": f"Remove {int(df.duplicated().sum())} duplicate rows",
                "params": {}
            })
        return {"dataset_id": dataset_id, "suggestions": suggestions}
