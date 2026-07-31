"""
LangGraph Agent — orchestrates the data analysis workflow.
Implements intent detection → code generation → execution → explanation pipeline.
"""
import logging
from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State passed through the LangGraph workflow."""
    dataset_id: str
    question: str
    intent: Optional[str]
    generated_code: Optional[str]
    execution_result: Optional[dict]
    chart_url: Optional[str]
    table_data: Optional[Any]
    response: Optional[str]
    error: Optional[str]
    df_info: Optional[dict]
    dataset_name: Optional[str]
    model: str


async def intent_node(state: AgentState) -> AgentState:
    """Detect the intent of the user's question."""
    from services.ai_service import call_ai, extract_json
    from prompts.system_prompts import INTENT_DETECTION_PROMPT

    df_info = state.get("df_info", {})
    columns_str = ", ".join(df_info.get("columns", [])[:30])

    prompt = INTENT_DETECTION_PROMPT.format(
        question=state["question"],
        columns=columns_str,
    )

    try:
        response = await call_ai(prompt, temperature=0.1, model=state.get("model", "gemini"))
        data = extract_json(response)
        state["intent"] = data.get("intent", "general")
    except Exception as e:
        logger.warning(f"Intent detection failed: {e}")
        state["intent"] = "general"

    return state


async def code_generation_node(state: AgentState) -> AgentState:
    """Generate Pandas/visualization code for the question."""
    from services.ai_service import call_ai, extract_json
    from prompts.system_prompts import NL_TO_PANDAS_PROMPT, SYSTEM_PROMPT
    import json

    df_info = state.get("df_info", {})
    sample_str = json.dumps(df_info.get("sample_data", [])[:3], default=str, indent=2)
    dtypes_str = json.dumps(df_info.get("dtypes", {}), indent=2)
    columns_str = json.dumps(df_info.get("columns", []))

    prompt = NL_TO_PANDAS_PROMPT.format(
        columns=columns_str,
        sample_data=sample_str[:2000],
        dtypes=dtypes_str[:500],
        question=state["question"],
    )

    try:
        response = await call_ai(
            prompt, system=SYSTEM_PROMPT,
            temperature=0.2, model=state.get("model", "gemini")
        )
        data = extract_json(response)
        state["generated_code"] = data.get("code")
    except Exception as e:
        logger.warning(f"Code generation failed: {e}")
        state["generated_code"] = None

    return state


async def execution_node(state: AgentState) -> AgentState:
    """Execute the generated code safely."""
    from services.data_service import get_dataframe
    from services.executor import execute_code

    if not state.get("generated_code"):
        return state

    df = get_dataframe(state["dataset_id"])
    if df is None:
        state["error"] = "Dataset not found in memory"
        return state

    result = execute_code(state["generated_code"], df)
    state["execution_result"] = result

    if result.get("success"):
        if result.get("chart_base64"):
            state["chart_url"] = f"data:image/png;base64,{result['chart_base64']}"
        if result.get("result"):
            state["table_data"] = result["result"]
    else:
        # Try self-healing
        logger.warning(f"Execution failed: {result.get('error')}")
        state["error"] = result.get("error")

    return state


async def response_node(state: AgentState) -> AgentState:
    """Generate natural language explanation of results."""
    from services.ai_service import call_ai
    from prompts.system_prompts import INSIGHT_GENERATION_PROMPT, SYSTEM_PROMPT
    import json

    execution_result = state.get("execution_result")
    results_str = ""

    if execution_result and execution_result.get("success"):
        result = execution_result.get("result")
        if result:
            results_str = f"\nResults:\n{json.dumps(result, default=str)[:2000]}"
        if execution_result.get("chart_base64"):
            results_str += "\n[Chart generated successfully]"
    elif state.get("error"):
        results_str = f"\nNote: Code execution had an issue: {state['error']}"

    df_info = state.get("df_info", {})
    prompt = INSIGHT_GENERATION_PROMPT.format(
        dataset_name=state.get("dataset_name", "dataset"),
        analysis_type=state.get("intent", "general"),
        question=state["question"],
        results=results_str or "No computation was needed.",
        stats_context=f"Columns: {df_info.get('columns', [])[:10]}, Rows: {df_info.get('shape', {}).get('rows', 0)}",
    )

    try:
        response = await call_ai(
            prompt, system=SYSTEM_PROMPT,
            temperature=0.3, model=state.get("model", "gemini")
        )
        state["response"] = response
    except Exception as e:
        state["response"] = f"Analysis complete. {results_str}"

    return state


def should_generate_code(state: AgentState) -> str:
    """Routing logic — decide whether to generate code or go straight to response."""
    code_intents = {"statistics", "visualization", "filtering", "aggregation",
                    "feature_engineering", "comparison", "prediction"}
    if state.get("intent") in code_intents:
        return "generate_code"
    return "respond"


def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph agent."""
    graph = StateGraph(AgentState)

    graph.add_node("detect_intent", intent_node)
    graph.add_node("generate_code", code_generation_node)
    graph.add_node("execute", execution_node)
    graph.add_node("respond", response_node)

    graph.set_entry_point("detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        should_generate_code,
        {"generate_code": "generate_code", "respond": "respond"},
    )
    graph.add_edge("generate_code", "execute")
    graph.add_edge("execute", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


# Singleton compiled graph
_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent_graph()
    return _agent
