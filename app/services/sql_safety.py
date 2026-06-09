import re

import sqlglot


DANGEROUS_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|merge|call|exec)\b",
    re.IGNORECASE,
)
SYSTEM_CATALOG_PATTERN = re.compile(
    r"\b(information_schema|pg_catalog|mysql\.|sys\.)\b",
    re.IGNORECASE,
)
SELECT_STAR_PATTERN = re.compile(r"(?is)\bselect\s+\*")


def validate_generated_sql(sql: str, dialect: str | None = None) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    normalized = (sql or "").strip()
    if not normalized:
        return False, ["Generated SQL is empty."]
    if DANGEROUS_SQL_PATTERN.search(normalized):
        return False, ["Generated SQL contains dangerous write or DDL keywords."]
    if SYSTEM_CATALOG_PATTERN.search(normalized):
        return False, ["Generated SQL queries system catalog tables."]

    try:
        expressions = sqlglot.parse(normalized, read=dialect or None)
    except Exception as exc:
        return False, [f"Generated SQL parse failed: {exc}"]

    if len(expressions) != 1:
        return False, ["Generated SQL must contain exactly one statement."]
    if expressions[0].key not in {"select"}:
        return False, ["Generated SQL must be a readonly SELECT statement."]
    if SELECT_STAR_PATTERN.search(normalized):
        warnings.append("Generated SQL contains SELECT *; prefer explicit columns.")
    return True, warnings
