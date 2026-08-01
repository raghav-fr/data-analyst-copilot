"""EDA route — automatic exploratory data analysis."""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from services.auth_service import get_current_user
from models.schemas import EDAResponse, EDAChart
from services.data_service import get_dataframe, get_df_info, get_dataset_meta
from services.chart_service import (
    generate_histogram, generate_boxplot, generate_correlation_heatmap,
    generate_countplot, generate_pairplot, generate_missing_heatmap
)
from services.ai_service import call_ai, extract_json
from prompts.system_prompts import EDA_SUMMARY_PROMPT, CHART_EXPLANATION_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_CHARTS_PER_TYPE = 5


@router.get("/{dataset_id}", response_model=EDAResponse)
async def run_eda(
    dataset_id: str,
    include_insights: bool = True,
    max_charts: int = 20,
    current_user = Depends(get_current_user)):
    """Run automatic EDA on a dataset. Returns charts with AI explanations."""
    df = get_dataframe(dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    meta = get_dataset_meta(dataset_id, current_user.uid) or {}
    df_info = get_df_info(df)
    charts = []

    # 1. Missing values heatmap
    try:
        missing_b64 = generate_missing_heatmap(df)
        if missing_b64:
            charts.append(EDAChart(
                chart_type="missing_heatmap",
                title="Missing Values Analysis",
                image_url=f"data:image/png;base64,{missing_b64}",
            ))
    except Exception as e:
        logger.warning(f"Missing heatmap error: {e}")

    # 2. Histograms for numeric columns
    numeric_cols = df_info["numeric_columns"][:MAX_CHARTS_PER_TYPE]
    for col in numeric_cols:
        try:
            b64 = generate_histogram(df, col)
            insight = None
            if include_insights:
                insight = await _get_chart_insight(df, col, "histogram", meta.get("filename", ""))
            charts.append(EDAChart(
                chart_type="histogram",
                title=f"Distribution: {col}",
                column=col,
                image_url=f"data:image/png;base64,{b64}",
                insight=insight,
            ))
        except Exception as e:
            logger.warning(f"Histogram error for {col}: {e}")

    # 3. Boxplots for numeric columns
    for col in numeric_cols[:MAX_CHARTS_PER_TYPE]:
        try:
            b64 = generate_boxplot(df, col)
            charts.append(EDAChart(
                chart_type="boxplot",
                title=f"Boxplot: {col}",
                column=col,
                image_url=f"data:image/png;base64,{b64}",
            ))
        except Exception as e:
            logger.warning(f"Boxplot error for {col}: {e}")

    # 4. Correlation heatmap
    if len(numeric_cols) >= 2:
        try:
            b64 = generate_correlation_heatmap(df)
            if b64:
                charts.append(EDAChart(
                    chart_type="correlation_heatmap",
                    title="Correlation Heatmap",
                    image_url=f"data:image/png;base64,{b64}",
                ))
        except Exception as e:
            logger.warning(f"Correlation heatmap error: {e}")

    # 5. Count plots for categorical columns
    cat_cols = df_info["categorical_columns"][:MAX_CHARTS_PER_TYPE]
    for col in cat_cols:
        if df[col].nunique() <= 30:  # Only reasonable cardinality
            try:
                b64 = generate_countplot(df, col)
                insight = None
                if include_insights:
                    insight = await _get_chart_insight(df, col, "countplot", meta.get("filename", ""))
                charts.append(EDAChart(
                    chart_type="countplot",
                    title=f"Category Distribution: {col}",
                    column=col,
                    image_url=f"data:image/png;base64,{b64}",
                    insight=insight,
                ))
            except Exception as e:
                logger.warning(f"Countplot error for {col}: {e}")

    # 6. Pairplot if we have multiple numeric columns
    if len(numeric_cols) >= 2:
        try:
            b64 = generate_pairplot(df, numeric_cols[:5])
            if b64:
                charts.append(EDAChart(
                    chart_type="pairplot",
                    title="Pair Plot (Numeric Columns)",
                    image_url=f"data:image/png;base64,{b64}",
                ))
        except Exception as e:
            logger.warning(f"Pairplot error: {e}")

    # Summary insight
    summary = None
    if include_insights:
        try:
            summary = await _get_eda_summary(df, df_info, meta.get("filename", ""))
        except Exception as e:
            logger.warning(f"EDA summary error: {e}")

    return EDAResponse(
        dataset_id=dataset_id,
        charts=charts[:max_charts],
        summary_insight=summary,
    )


async def _get_chart_insight(df, column, chart_type, dataset_name) -> str:
    """Get AI explanation for a chart."""
    import pandas as pd
    import numpy as np

    stats = {}
    if pd.api.types.is_numeric_dtype(df[column]):
        series = df[column].dropna()
        stats = {
            "mean": round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
            "std": round(float(series.std()), 2),
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
            "skewness": round(float(series.skew()), 2),
        }
    else:
        top = df[column].value_counts().head(3).to_dict()
        stats = {"top_values": {str(k): int(v) for k, v in top.items()}}

    prompt = CHART_EXPLANATION_PROMPT.format(
        chart_type=chart_type,
        columns=column,
        dataset_name=dataset_name,
        stats=str(stats),
    )
    try:
        response = await call_ai(prompt, temperature=0.3)
        return response.strip()[:500]
    except Exception:
        return None


async def _get_eda_summary(df, df_info, dataset_name) -> str:
    """Get AI summary of the entire EDA."""
    import pandas as pd
    numeric_cols = df_info["numeric_columns"]
    stats_summary = {}
    if numeric_cols:
        stats_summary = df[numeric_cols].describe().round(2).to_dict()

    col_summary = "\n".join([
        f"- {col}: {str(df[col].dtype)}, {int(df[col].isnull().sum())} missing, {int(df[col].nunique())} unique"
        for col in df.columns[:20]
    ])

    prompt = EDA_SUMMARY_PROMPT.format(
        dataset_name=dataset_name,
        rows=len(df),
        columns=len(df.columns),
        missing_pct=round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 1),
        duplicates=int(df.duplicated().sum()),
        column_summary=col_summary,
        numeric_stats=str(stats_summary)[:1000],
    )
    try:
        response = await call_ai(prompt, temperature=0.4)
        return response.strip()
    except Exception:
        return None
