import json
from typing import Any

import httpx

from app.core.config import settings


class LlmError(RuntimeError):
    pass


def build_messages(question: str, schema_context: dict[str, Any], current_sql: str | None = None) -> list[dict[str, str]]:
    system = "\n".join(
        [
            "You are AutoSQL, a Text-to-SQL engine.",
            "Use only the provided schema_context. Do not invent tables or columns.",
            "Return STRICT JSON only: {\"sql\":\"...\",\"tables\":[\"...\"],\"explanation\":\"...\",\"warnings\":[\"...\"]}.",
            "The SQL must be one readonly SELECT statement.",
            "Avoid SELECT *. Use explicit columns.",
            "Do not query information_schema, pg_catalog, mysql.sys, or system tables.",
        ]
    )
    user = "\n\n".join(
        [
            f"Question:\n{question}",
            f"Current SQL:\n{current_sql or ''}",
            "schema_context:",
            json.dumps(schema_context, ensure_ascii=False, default=str),
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generate_with_deepseek(question: str, schema_context: dict[str, Any], current_sql: str | None = None) -> dict[str, Any]:
    if not settings.deepseek_api_key:
        raise LlmError("DEEPSEEK_API_KEY is not configured.")

    endpoint = settings.deepseek_base_url.rstrip("/") + "/" + settings.deepseek_chat_completions_path.strip("/")
    payload = {
        "model": settings.deepseek_model,
        "messages": build_messages(question, schema_context, current_sql),
        "temperature": 0.1,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=settings.deepseek_timeout_seconds) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
    except Exception as exc:
        raise LlmError(f"DeepSeek response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict) or not str(parsed.get("sql") or "").strip():
        raise LlmError("DeepSeek response does not contain non-empty sql.")
    return parsed
