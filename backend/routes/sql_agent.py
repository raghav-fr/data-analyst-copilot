"""SQL Agent route — DuckDB-powered SQL queries over uploaded datasets."""
import time
import logging
import duckdb
from fastapi import APIRouter, HTTPException
from models.schemas import SQLRequest, SQLResponse
from services.data_service import get_dataframe

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=SQLResponse)
async def run_sql_query(request: SQLRequest):
    """Execute SQL query against the dataset using DuckDB."""
    df = get_dataframe(request.dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Safety check — block dangerous SQL
    blocked_keywords = ["drop", "delete", "insert", "update", "create", "alter", "truncate",
                        "exec", "execute", "xp_", "sp_", "pragma", "attach"]
    query_lower = request.query.lower()
    for kw in blocked_keywords:
        if kw in query_lower:
            raise HTTPException(
                status_code=400,
                detail=f"SQL keyword '{kw}' is not allowed. Only SELECT queries are permitted."
            )

    start = time.time()
    try:
        # Register DataFrame as 'data' table in DuckDB
        conn = duckdb.connect()
        conn.register("data", df)

        result_df = conn.execute(request.query).df()
        elapsed_ms = int((time.time() - start) * 1000)

        return SQLResponse(
            query=request.query,
            rows=len(result_df),
            columns=result_df.columns.tolist(),
            data=result_df.head(500).fillna("").to_dict("records"),
            execution_time_ms=elapsed_ms,
        )

    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=f"SQL Error: {str(e)}")
    except Exception as e:
        logger.error(f"SQL query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nl-to-sql")
async def natural_language_to_sql(dataset_id: str, question: str, model: str = "gemini"):
    """Convert natural language to SQL and execute it."""
    df = get_dataframe(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    from services.ai_service import call_ai, extract_json
    import json

    # Build schema info
    schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
    sample = df.head(3).fillna("").to_dict("records")

    prompt = f"""Convert this question to a DuckDB SQL query for a table named 'data'.

Table schema:
{json.dumps(schema, indent=2)}

Sample data:
{json.dumps(sample[:2], default=str, indent=2)}

Question: {question}

Rules:
- Table name is ALWAYS 'data'
- Only SELECT queries
- Return top 100 rows maximum (use LIMIT 100)
- Use DuckDB SQL syntax

Respond ONLY with a JSON object:
{{"sql": "SELECT ...", "explanation": "brief explanation"}}"""

    try:
        response = await call_ai(prompt, temperature=0.1, model=model)
        data = extract_json(response)
        sql = data.get("sql", "")

        # Execute the generated SQL
        result = await run_sql_query(SQLRequest(dataset_id=dataset_id, query=sql))
        return {
            "question": question,
            "sql": sql,
            "explanation": data.get("explanation", ""),
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/{dataset_id}")
async def get_sql_schema(dataset_id: str):
    """Get the DuckDB-compatible schema for a dataset."""
    df = get_dataframe(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    conn = duckdb.connect()
    conn.register("data", df)

    schema_result = conn.execute("DESCRIBE data").df()
    return {
        "table_name": "data",
        "columns": schema_result.to_dict("records"),
        "row_count": len(df),
        "sample_query": f"SELECT * FROM data LIMIT 10",
    }
