import time
import uuid

from fastapi import APIRouter, HTTPException
from psycopg.types.json import Jsonb

from app.db import get_conn
from app.schemas import GenerateSqlRequest, MetadataSearchRequest
from app.services.catalog import build_schema_context
from app.services.llm import LlmError, generate_with_deepseek
from app.services.sql_safety import validate_generated_sql

router = APIRouter(prefix="/v1/sql", tags=["sql"])


def _log_generation(
    request_id: str,
    payload: GenerateSqlRequest,
    schema_context: dict,
    result: dict | None,
    success: bool,
    latency_ms: int,
    error_message: str | None = None,
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO autosql_generation_logs (
                    request_id, superset_database_id, schema_name, question,
                    selected_tables, generated_sql, warnings, latency_ms,
                    model_name, success, error_message, request_payload, response_payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request_id,
                    payload.superset_database_id,
                    payload.schema_name,
                    payload.question,
                    [table.get("name") for table in schema_context.get("tables", [])],
                    (result or {}).get("sql"),
                    Jsonb((result or {}).get("warnings", [])),
                    latency_ms,
                    "deepseek",
                    success,
                    error_message,
                    Jsonb(payload.model_dump(by_alias=True)),
                    Jsonb(result or {}),
                ),
            )


@router.post("/generate")
def generate_sql(payload: GenerateSqlRequest) -> dict:
    request_id = str(uuid.uuid4())
    started = time.monotonic()
    schema_context = payload.schema_context
    if schema_context is None:
        if payload.superset_database_id is None:
            raise HTTPException(status_code=422, detail="superset_database_id is required when schema_context is absent.")
        schema_context = build_schema_context(
            MetadataSearchRequest(
                superset_database_id=payload.superset_database_id,
                catalog=payload.catalog,
                schema=payload.schema_name,
                question=payload.question,
                allowed_tables=payload.allowed_tables,
                allowed_columns=payload.allowed_columns,
                limit=payload.limit,
            )
        )

    if not schema_context.get("tables"):
        raise HTTPException(status_code=422, detail="No candidate tables were found in AutoSQL catalog.")

    try:
        raw_result = generate_with_deepseek(
            question=payload.question,
            schema_context=schema_context,
            current_sql=payload.current_sql,
        )
        sql = str(raw_result.get("sql") or "").strip()
        ok, safety_warnings = validate_generated_sql(sql, payload.dialect or schema_context.get("dialect"))
        warnings = [str(item) for item in raw_result.get("warnings", []) if item]
        warnings.extend(safety_warnings)
        if not ok:
            raise HTTPException(
                status_code=422,
                detail={"message": "Generated SQL failed safety check.", "warnings": warnings},
            )

        result = {
            "request_id": request_id,
            "sql": sql,
            "tables": [str(item) for item in raw_result.get("tables", []) if item],
            "explanation": str(raw_result.get("explanation") or ""),
            "warnings": warnings,
            "readonly": True,
            "provider": "deepseek",
            "schema_context": schema_context,
        }
        _log_generation(
            request_id=request_id,
            payload=payload,
            schema_context=schema_context,
            result=result,
            success=True,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        return {"result": result}
    except LlmError as exc:
        _log_generation(
            request_id=request_id,
            payload=payload,
            schema_context=schema_context,
            result=None,
            success=False,
            latency_ms=int((time.monotonic() - started) * 1000),
            error_message=str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
