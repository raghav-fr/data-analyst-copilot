"""
Chat route — AI-powered natural language data analysis.
Uses LangGraph intent detection → code generation → safe execution → AI explanation.
"""
import uuid
import time
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import firestore

from models.schemas import ChatRequest, ChatResponse
from services.data_service import get_dataframe, get_df_info, get_dataset_meta
from services.ai_service import call_ai, extract_json
from services.executor import execute_code
from services.auth_service import get_current_user
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
async def chat(
    request: ChatRequest, 
    current_user = Depends(get_current_user),
):
    """Main chat endpoint — processes natural language questions about datasets."""
    start_time = time.time()

    # Get dataset
    df = get_dataframe(request.dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload a dataset first.")

    meta = get_dataset_meta(request.dataset_id, current_user.uid) or {}
    df_info = get_df_info(df)

    # Get/create conversation
    conv_id = await get_or_create_conversation(request.dataset_id, current_user.uid, request.conversation_id)

    # Save user message
    await save_message(conv_id, current_user.uid, "user", request.message)
    await update_conversation_title(conv_id, current_user.uid, request.message)

    # Get conversation history for context
    history = await get_conversation_history(conv_id, current_user.uid, limit=8)

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
                    "feature_engineering", "comparison", "prediction", "cleaning", "dataset_info"}

    if intent in code_intents:
        code_data = await _generate_pandas_code(request.message, df_info, request.model)

        if code_data and code_data.get("code"):
            code = code_data["code"]
            execution_result = execute_code(code, df)

            if execution_result["success"]:
                if execution_result.get("chart_base64"):
                    chart_b64 = execution_result["chart_base64"]
                    chart_url = f"data:image/png;base64,{chart_b64}"
                if execution_result.get("result") is not None:
                    table_data = execution_result["result"]
                elif execution_result.get("stdout"):
                    table_data = {"type": "text", "value": execution_result["stdout"].strip()}
            else:
                # Try to self-heal: regenerate code with error context
                logger.warning(f"Code execution failed: {execution_result['error']}")
                fixed_code = await _fix_code(code, execution_result["error"], df_info)
                if fixed_code:
                    code = fixed_code
                    execution_result = execute_code(fixed_code, df)
                    if execution_result.get("chart_base64"):
                        chart_url = f"data:image/png;base64,{execution_result['chart_base64']}"
                    if execution_result.get("result") is not None:
                        table_data = execution_result["result"]
                    elif execution_result.get("stdout"):
                        table_data = {"type": "text", "value": execution_result["stdout"].strip()}

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
    
    # Save assistant message
    msg_id = await save_message(
        conv_id, current_user.uid, "assistant", response_text,
        code=code,
        chart_path=chart_url,
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
async def get_conversations(
    dataset_id: str, 
    current_user = Depends(get_current_user),
):
    """Get all conversations for a dataset."""
    db = firestore.client()
    convs_ref = db.collection('users').document(current_user.uid).collection('conversations')
    query = convs_ref.where('dataset_id', '==', dataset_id).order_by('updated_at', direction=firestore.Query.DESCENDING)
    docs = query.stream()
    
    convs = []
    for doc in docs:
        c = doc.to_dict()
        created_at = c.get('created_at')
        updated_at = c.get('updated_at')
        if created_at:
            created_at = created_at.isoformat()
        else:
            created_at = ""
        if updated_at:
            updated_at = updated_at.isoformat()
        else:
            updated_at = ""
            
        convs.append({
            "id": c.get("id"),
            "title": c.get("title", "Conversation"),
            "created_at": created_at,
            "updated_at": updated_at,
        })
    return convs


@router.get("/history/{conversation_id}")
async def get_history(
    conversation_id: str, 
    current_user = Depends(get_current_user),
):
    """Get full message history for a conversation."""
    db = firestore.client()
    # First verify user owns the conversation
    conv_doc = db.collection('users').document(current_user.uid).collection('conversations').document(conversation_id).get()
    if not conv_doc.exists:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    messages_ref = db.collection('users').document(current_user.uid).collection('conversations').document(conversation_id).collection('messages')
    query = messages_ref.order_by('created_at', direction=firestore.Query.ASCENDING)
    docs = query.stream()
    
    msgs = []
    for doc in docs:
        m = doc.to_dict()
        created_at = m.get('created_at')
        if created_at:
            created_at = created_at.isoformat()
        else:
            created_at = ""
            
        msgs.append({
            "id": m.get("id"),
            "role": m.get("role"),
            "content": m.get("content"),
            "code": m.get("code"),
            "chart_path": m.get("chart_path"),
            "result_data": m.get("result_data"),
            "created_at": created_at,
        })
    return msgs


@router.get("/history/by_dataset/{dataset_id}")
async def get_history_by_dataset(
    dataset_id: str, 
    current_user = Depends(get_current_user),
):
    """Get full message history for the most recent conversation of a dataset in a single call."""
    db = firestore.client()
    convs_ref = db.collection('users').document(current_user.uid).collection('conversations')
    query = convs_ref.where('dataset_id', '==', dataset_id).order_by('updated_at', direction=firestore.Query.DESCENDING).limit(1)
    docs = query.stream()
    
    conv_id = None
    for doc in docs:
        conv_id = doc.id
        break
        
    if not conv_id:
        return {"conversation_id": None, "messages": []}
        
    messages_ref = db.collection('users').document(current_user.uid).collection('conversations').document(conv_id).collection('messages')
    query = messages_ref.order_by('created_at', direction=firestore.Query.ASCENDING)
    docs = query.stream()
    
    msgs = []
    for doc in docs:
        m = doc.to_dict()
        created_at = m.get('created_at')
        if created_at:
            created_at = created_at.isoformat()
        else:
            created_at = ""
            
        msgs.append({
            "id": m.get("id"),
            "role": m.get("role"),
            "content": m.get("content"),
            "code": m.get("code"),
            "chart_path": m.get("chart_path"),
            "result_data": m.get("result_data"),
            "created_at": created_at,
        })
    return {"conversation_id": conv_id, "messages": msgs}
