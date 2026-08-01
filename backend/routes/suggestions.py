"""Suggestions route — AI-generated questions after dataset upload."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from services.auth_service import get_current_user
from models.schemas import SuggestionsResponse, SuggestedQuestion
from services.data_service import get_dataframe, get_df_info, get_dataset_meta
from services.ai_service import call_ai, extract_json
from prompts.system_prompts import SUGGESTED_QUESTIONS_PROMPT
import json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{dataset_id}", response_model=SuggestionsResponse)
async def get_suggested_questions(dataset_id: str, model: str = "gemini", current_user = Depends(get_current_user)):
    """Generate AI-powered suggested questions for a dataset."""
    df = get_dataframe(dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    meta = get_dataset_meta(dataset_id, current_user.uid) or {}
    df_info = get_df_info(df)

    import pandas as pd
    import numpy as np

    # Build quick stats summary
    numeric_cols = df_info["numeric_columns"]
    quick_stats = {}
    if numeric_cols:
        for col in numeric_cols[:3]:
            quick_stats[col] = {
                "mean": round(float(df[col].mean()), 2) if not df[col].isna().all() else None,
                "max": round(float(df[col].max()), 2) if not df[col].isna().all() else None,
            }

    prompt = SUGGESTED_QUESTIONS_PROMPT.format(
        dataset_name=meta.get("filename", "dataset"),
        columns=json.dumps(df_info["columns"]),
        sample_data=json.dumps(df_info["sample_data"][:3], default=str),
        dtypes=json.dumps(df_info["dtypes"]),
        quick_stats=json.dumps(quick_stats, default=str),
    )

    try:
        response = await call_ai(prompt, temperature=0.5, model=model)
        questions_data = extract_json(response)

        if not isinstance(questions_data, list):
            questions_data = questions_data.get("questions", []) if isinstance(questions_data, dict) else []

        questions = [
            SuggestedQuestion(
                question=q.get("question", ""),
                category=q.get("category", "overview"),
                icon=q.get("icon", "📊"),
            )
            for q in questions_data[:12]
            if q.get("question")
        ]

        return SuggestionsResponse(dataset_id=dataset_id, questions=questions)

    except Exception as e:
        logger.warning(f"Suggestion generation failed: {e}")
        # Return fallback suggestions based on column names
        return _fallback_suggestions(dataset_id, df_info)


def _fallback_suggestions(dataset_id: str, df_info: dict) -> SuggestionsResponse:
    """Generate basic suggestions without AI when API is unavailable."""
    cols = df_info["columns"]
    numeric_cols = df_info["numeric_columns"]
    cat_cols = df_info["categorical_columns"]

    questions = [
        SuggestedQuestion(question="What is the shape and structure of this dataset?", category="overview", icon="📋"),
        SuggestedQuestion(question="How many missing values does this dataset have?", category="overview", icon="❓"),
        SuggestedQuestion(question="Are there any duplicate rows?", category="overview", icon="🔍"),
    ]

    if numeric_cols:
        questions.extend([
            SuggestedQuestion(question=f"What is the average {numeric_cols[0]}?", category="statistics", icon="📊"),
            SuggestedQuestion(question=f"Show the distribution of {numeric_cols[0]}", category="visualization", icon="📈"),
        ])
        if len(numeric_cols) >= 2:
            questions.append(SuggestedQuestion(
                question=f"What is the correlation between {numeric_cols[0]} and {numeric_cols[1]}?",
                category="statistics", icon="🔗"
            ))

    if cat_cols:
        questions.append(SuggestedQuestion(
            question=f"What are the most common values in {cat_cols[0]}?",
            category="statistics", icon="🏆"
        ))
        questions.append(SuggestedQuestion(
            question=f"Show a bar chart of {cat_cols[0]}",
            category="visualization", icon="📊"
        ))

    if numeric_cols and cat_cols:
        questions.append(SuggestedQuestion(
            question=f"What is the average {numeric_cols[0]} by {cat_cols[0]}?",
            category="statistics", icon="📉"
        ))

    questions.append(SuggestedQuestion(question="Identify any outliers in the data", category="statistics", icon="⚠️"))
    questions.append(SuggestedQuestion(question="Show me the top 10 rows with highest values", category="overview", icon="🔝"))

    return SuggestionsResponse(dataset_id=dataset_id, questions=questions[:10])
