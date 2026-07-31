"""Pydantic schemas for request/response validation."""
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Upload ────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    column_names: list[str]
    file_size: int
    message: str


# ─── Profile ───────────────────────────────────────────────────────────────────

class ColumnProfile(BaseModel):
    name: str
    dtype: str
    missing: int
    missing_pct: float
    unique: int
    unique_pct: float
    sample_values: list[Any]
    stats: Optional[dict[str, Any]] = None


class DatasetProfile(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    total_missing: int
    total_missing_pct: float
    duplicates: int
    memory_usage_mb: float
    column_profiles: list[ColumnProfile]
    numeric_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]


# ─── EDA ───────────────────────────────────────────────────────────────────────

class EDAChart(BaseModel):
    chart_type: str
    title: str
    column: Optional[str] = None
    image_url: str
    insight: Optional[str] = None


class EDAResponse(BaseModel):
    dataset_id: str
    charts: list[EDAChart]
    summary_insight: Optional[str] = None


# ─── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    dataset_id: str
    conversation_id: Optional[str] = None
    message: str
    model: str = "gemini"  # gemini | openai | ollama


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    role: str = "assistant"
    content: str
    code: Optional[str] = None
    chart_url: Optional[str] = None
    table_data: Optional[dict[str, Any]] = None
    intent: Optional[str] = None
    execution_time_ms: Optional[int] = None


# ─── Statistics ────────────────────────────────────────────────────────────────

class StatRequest(BaseModel):
    dataset_id: str
    analysis_type: str  # describe|correlation|anova|regression|distribution
    columns: Optional[list[str]] = None
    target_column: Optional[str] = None


class StatResponse(BaseModel):
    analysis_type: str
    result: dict[str, Any]
    chart_url: Optional[str] = None
    interpretation: Optional[str] = None


# ─── Cleaning ──────────────────────────────────────────────────────────────────

class CleaningRequest(BaseModel):
    dataset_id: str
    operation: str  # drop_duplicates|fill_missing|drop_columns|rename|normalize|encode
    params: dict[str, Any] = Field(default_factory=dict)


class CleaningResponse(BaseModel):
    dataset_id: str
    operation: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    message: str


# ─── SQL ───────────────────────────────────────────────────────────────────────

class SQLRequest(BaseModel):
    dataset_id: str
    query: str


class SQLResponse(BaseModel):
    query: str
    rows: int
    columns: list[str]
    data: list[dict[str, Any]]
    execution_time_ms: int


# ─── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    dataset_id: str
    format: str  # csv|excel|pdf|json
    include_profile: bool = True
    include_charts: bool = True
    conversation_id: Optional[str] = None


# ─── Suggestions ───────────────────────────────────────────────────────────────

class SuggestedQuestion(BaseModel):
    question: str
    category: str  # overview|statistics|visualization|cleaning|ml
    icon: str


class SuggestionsResponse(BaseModel):
    dataset_id: str
    questions: list[SuggestedQuestion]


# ─── Conversation ──────────────────────────────────────────────────────────────

class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
