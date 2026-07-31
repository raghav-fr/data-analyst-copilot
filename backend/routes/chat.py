"""
Chat route — AI-powered natural language data analysis.
Uses LangGraph intent detection → code generation → safe execution → AI explanation.
"""
import uuid
import time
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from models.schemas import ChatRequest, ChatResponse
from services.data_service import get_dataframe, get_df_info, get_dataset_meta
from services.ai_service import call_ai, extract_json
from services.executor import execute_code
from services.memory_service import (
    get_or_create_conversation,
    save_message,
    get_conversation_history,
    update_conversation_title,
)
from prompts.system_prompts import (
    SYSTEM_PROMPT,
    INTENT_DETECTION_PROMPT,
    NL_TO_PANDAS_PROMPT,
    INSIGHT_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Main chat endpoint — processes natural language questions about datasets."""
    start_time = time.time()

    # Get dataset
    df = get_dataframe(request.dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload a dataset first.")

    meta = get_dataset_meta(request.dataset_id) or {}
    df_info = get_df_info(df)

    # Get/create conversation
    conv_id = await get_or_create_conversation(db, request.dataset_id, request.conversation_id)

    # Save user message
    await save_message(db, conv_id, "user", request.message)
    await update_conversation_title(db, conv_id, request.message)

    # Get conversation history for context
    history = await get_conversation_history(db, conv_id, limit=8)

    # Step 1: Detect intent
    intent_data = await _detect_intent(request.message, df_info)
    intent = intent_data.get("intent", "general")
    logger.info(f"Intent detected: {intent} for question: '{request.message[:60]}'")

    # Step 2: Generate and execute code if needed
    code = None
    execution_result = None
    chart_b64 = None
    chart_url = None
    table_data = None

    code_intents = {"statistics", "visualization", "filtering", "aggregation",
                    "feature_engineering", "comparison", "prediction"}

    if intent in code_intents:
        code_data = await _generate_pandas_code(request.message, df_info, request.model)

        if code_data and code_data.get("code"):
            code = code_data["code"]
            execution_result = execute_code(code, df)

            if execution_result["success"]:
                if execution_result.get("chart_base64"):
                    chart_b64 = execution_result["chart_base64"]
                    chart_url = f"data:image/png;base64,{chart_b64}"
                if execution_result.get("result"):
                    table_data = execution_result["result"]
            else:
                # Try to self-heal: regenerate code with error context
                logger.warning(f"Code execution failed: {execution_result['error']}")
                fixed_code = await _fix_code(code, execution_result["error"], df_info)
                if fixed_code:
                    code = fixed_code
                    execution_result = execute_code(fixed_code, df)
                    if execution_result.get("chart_base64"):
                        chart_url = f"data:image/png;base64,{execution_result['chart_base64']}"
                    if execution_result.get("result"):
                        table_data = execution_result["result"]

    # Step 3: Generate AI explanation
    response_text = await _generate_response(
        question=request.message,
        intent=intent,
        df_info=df_info,
        execution_result=execution_result,
        history=history,
        dataset_name=meta.get("filename", "dataset"),
        model=request.model,
    )

    elapsed_ms = int((time.time() - start_time) * 1000)
    msg_id = str(uuid.uuid4())

    # Save assistant message
    await save_message(
        db, conv_id, "assistant", response_text,
        code=code,
        result_data={"table": table_data, "intent": intent} if table_data else {"intent": intent},
    )

    return ChatResponse(
        conversation_id=conv_id,
        message_id=msg_id,
        content=response_text,
        code=code,
        chart_url=chart_url,
        table_data=table_data,
        intent=intent,
        execution_time_ms=elapsed_ms,
    )


async def _detect_intent(question: str, df_info: dict) -> dict:
    """Detect intent of user question."""
    columns_str = ", ".join(df_info["columns"][:30])
    prompt = INTENT_DETECTION_PROMPT.format(
        question=question,
        columns=columns_str,
    )
    try:
        response = await call_ai(prompt, temperature=0.1)
        return extract_json(response)
    except Exception as e:
        logger.warning(f"Intent detection failed: {e}")
        return {"intent": "general", "confidence": 0.5}


async def _generate_pandas_code(question: str, df_info: dict, model: str = "gemini") -> dict:
    """Generate Pandas/visualization code from natural language."""
    import json

    sample_str = json.dumps(df_info["sample_data"][:3], default=str, indent=2)
    dtypes_str = json.dumps(df_info["dtypes"], indent=2)
    columns_str = json.dumps(df_info["columns"])

    prompt = NL_TO_PANDAS_PROMPT.format(
        columns=columns_str,
        sample_data=sample_str[:2000],
        dtypes=dtypes_str[:500],
        question=question,
    )
    try:
        response = await call_ai(prompt, system=SYSTEM_PROMPT, model=model, temperature=0.2)
        return extract_json(response)
    except Exception as e:
        logger.warning(f"Code generation failed: {e}")
        return None


async def _fix_code(code: str, error: str, df_info: dict) -> str:
    """Try to fix broken generated code."""
    prompt = f"""Fix this Python/Pandas code that produced an error.

Original code:
```python
{code}
```

Error: {error}

Available columns: {df_info['columns']}
Data types: {df_info['dtypes']}

Return ONLY the fixed Python code, no explanation, no markdown:"""
    try:
        response = await call_ai(prompt, temperature=0.1)
        # Extract code from markdown if wrapped
        import re
        code_match = re.search(r"```python\s*([\s\S]*?)\s*```", response)
        if code_match:
            return code_match.group(1)
        return response.strip()
    except Exception:
        return None


async def _generate_response(
    question: str,
    intent: str,
    df_info: dict,
    execution_result: dict,
    history: list,
    dataset_name: str,
    model: str = "gemini",
) -> str:
    """Generate the final natural language response."""
    import json

    results_str = ""
    if execution_result:
        if execution_result.get("success"):
            result = execution_result.get("result")
            if result:
                results_str = f"\nExecution results:\n{json.dumps(result, default=str)[:2000]}"
            if execution_result.get("chart_base64"):
                results_str += "\n[Chart was generated successfully]"
        else:
            results_str = f"\nNote: Code execution had an error: {execution_result.get('error', '')}"

    prompt = INSIGHT_GENERATION_PROMPT.format(
        dataset_name=dataset_name,
        analysis_type=intent,
        question=question,
        results=results_str or "No code was executed for this question.",
        stats_context=f"Columns: {df_info['columns'][:15]}, Rows: {df_info['shape']['rows']}",
    )

    try:
        return await call_ai(
            prompt,
            system=SYSTEM_PROMPT,
            model=model,
            temperature=0.3,
        )
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return f"I analyzed your dataset ({df_info['shape']['rows']} rows). {results_str}"


@router.get("/conversations/{dataset_id}")
async def get_conversations(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Get all conversations for a dataset."""
    from sqlalchemy import select
    from models.db_models import Conversation
    result = await db.execute(
        select(Conversation)
        .where(Conversation.dataset_id == dataset_id)
        .order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in convs
    ]


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get full message history for a conversation."""
    from sqlalchemy import select
    from models.db_models import Message
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "code": m.code,
            "chart_path": m.chart_path,
            "result_data": m.result_data,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]
