"""Statistics route — descriptive stats, correlation, ANOVA, regression."""
import logging
import json
from fastapi import APIRouter, HTTPException
from models.schemas import StatRequest, StatResponse
from services.data_service import get_dataframe
from services.chart_service import generate_correlation_heatmap, generate_histogram
from services.ai_service import call_ai

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=StatResponse)
async def analyze_statistics(request: StatRequest):
    """Run statistical analysis on the dataset."""
    df = get_dataframe(request.dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    import pandas as pd
    import numpy as np

    analysis_type = request.analysis_type
    columns = request.columns or []

    try:
        if analysis_type == "describe":
            result = _describe(df, columns)
            chart_url = None

        elif analysis_type == "correlation":
            result, chart_b64 = _correlation(df, columns)
            chart_url = f"data:image/png;base64,{chart_b64}" if chart_b64 else None

        elif analysis_type == "distribution":
            col = columns[0] if columns else df.select_dtypes(include=[np.number]).columns[0]
            result = _distribution(df, col)
            b64 = generate_histogram(df, col)
            chart_url = f"data:image/png;base64,{b64}" if b64 else None

        elif analysis_type == "anova":
            result = _anova(df, columns, request.target_column)
            chart_url = None

        elif analysis_type == "regression":
            result = _regression(df, columns, request.target_column)
            chart_url = None

        elif analysis_type == "outliers":
            result = _outlier_analysis(df, columns)
            chart_url = None

        else:
            result = {"error": f"Unknown analysis type: {analysis_type}"}
            chart_url = None

        # AI interpretation
        interpretation = await _interpret_stats(analysis_type, result)

        return StatResponse(
            analysis_type=analysis_type,
            result=result,
            chart_url=chart_url,
            interpretation=interpretation,
        )

    except Exception as e:
        logger.error(f"Stats analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _describe(df, columns):
    import numpy as np
    cols = [c for c in columns if c in df.columns] if columns else df.select_dtypes(include=[np.number]).columns.tolist()
    if not cols:
        cols = df.columns.tolist()

    desc = df[cols].describe(include="all").round(4)
    return {
        "summary": desc.to_dict(),
        "missing": df[cols].isnull().sum().to_dict(),
        "skewness": {col: round(float(df[col].skew()), 4) for col in cols if hasattr(df[col], 'skew')},
        "kurtosis": {col: round(float(df[col].kurtosis()), 4) for col in cols if hasattr(df[col], 'kurtosis')},
    }


def _correlation(df, columns):
    import numpy as np
    numeric_df = df.select_dtypes(include=[np.number])
    if columns:
        numeric_df = numeric_df[[c for c in columns if c in numeric_df.columns]]
    if len(numeric_df.columns) < 2:
        return {"error": "Need at least 2 numeric columns"}, None

    corr = numeric_df.corr().round(4)
    b64 = generate_correlation_heatmap(numeric_df)
    return {"correlation_matrix": corr.to_dict()}, b64


def _distribution(df, column):
    import numpy as np
    series = df[column].dropna()
    try:
        from scipy import stats
        stat, pvalue = stats.normaltest(series)
        is_normal = pvalue > 0.05
    except Exception:
        is_normal = None
        pvalue = None

    return {
        "column": column,
        "count": int(len(series)),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std()),
        "min": float(series.min()),
        "max": float(series.max()),
        "q1": float(series.quantile(0.25)),
        "q3": float(series.quantile(0.75)),
        "skewness": float(series.skew()),
        "kurtosis": float(series.kurtosis()),
        "is_normal": is_normal,
        "normality_p_value": float(pvalue) if pvalue is not None else None,
        "percentiles": {
            "p5": float(series.quantile(0.05)),
            "p10": float(series.quantile(0.10)),
            "p25": float(series.quantile(0.25)),
            "p50": float(series.quantile(0.50)),
            "p75": float(series.quantile(0.75)),
            "p90": float(series.quantile(0.90)),
            "p95": float(series.quantile(0.95)),
        }
    }


def _anova(df, columns, target):
    try:
        from scipy import stats as scipy_stats
        import numpy as np

        if not target or target not in df.columns:
            return {"error": "Target column required for ANOVA"}
        if not columns or columns[0] not in df.columns:
            return {"error": "Group column required for ANOVA"}

        group_col = columns[0]
        groups = [group[target].dropna().values
                  for name, group in df.groupby(group_col)
                  if len(group[target].dropna()) > 1]

        if len(groups) < 2:
            return {"error": "Need at least 2 groups for ANOVA"}

        f_stat, p_value = scipy_stats.f_oneway(*groups)
        return {
            "test": "One-way ANOVA",
            "group_column": group_col,
            "target_column": target,
            "f_statistic": round(float(f_stat), 4),
            "p_value": round(float(p_value), 6),
            "significant": bool(p_value < 0.05),
            "interpretation": f"{'Significant' if p_value < 0.05 else 'Not significant'} difference (p={p_value:.4f})",
            "group_means": df.groupby(group_col)[target].mean().round(4).to_dict(),
        }
    except Exception as e:
        return {"error": str(e)}


def _regression(df, columns, target):
    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import r2_score, mean_squared_error

        if not target or target not in df.columns:
            return {"error": "Target column required for regression"}

        features = [c for c in (columns or []) if c in df.columns and c != target]
        if not features:
            features = df.select_dtypes(include=[np.number]).columns.tolist()
            features = [f for f in features if f != target][:5]

        subset = df[features + [target]].dropna()
        X = subset[features]
        y = subset[target]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        coefficients = dict(zip(features, [round(float(c), 4) for c in model.coef_]))

        return {
            "model": "Linear Regression",
            "target": target,
            "features": features,
            "r2_score": round(float(r2_score(y_test, y_pred)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
            "intercept": round(float(model.intercept_), 4),
            "coefficients": coefficients,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
        }
    except Exception as e:
        return {"error": str(e)}


def _outlier_analysis(df, columns):
    import numpy as np
    numeric_cols = [c for c in (columns or df.select_dtypes(include=[np.number]).columns.tolist())]
    results = {}
    for col in numeric_cols[:10]:
        series = df[col].dropna()
        Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers = series[(series < lower) | (series > upper)]
        z_scores = abs((series - series.mean()) / series.std())
        results[col] = {
            "iqr_outliers": int(len(outliers)),
            "iqr_outlier_pct": round(len(outliers) / len(series) * 100, 2),
            "lower_bound": round(float(lower), 4),
            "upper_bound": round(float(upper), 4),
            "z_score_outliers": int((z_scores > 3).sum()),
        }
    return results


async def _interpret_stats(analysis_type: str, result: dict) -> str:
    """Get AI interpretation of statistical results."""
    prompt = f"""Interpret these {analysis_type} statistical results for a business user:

{json.dumps(result, default=str)[:2000]}

Give a concise (3-4 sentences) interpretation focusing on what this means for the data and any actionable insights."""
    try:
        return await call_ai(prompt, temperature=0.3)
    except Exception:
        return None
