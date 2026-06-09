import re


def extract_tokens(text: str) -> list[str]:
    raw = (text or "").lower()
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", raw):
        cleaned = token.strip("_")
        if len(cleaned) < 2:
            continue
        if cleaned not in tokens:
            tokens.append(cleaned)
        if re.fullmatch(r"[\u4e00-\u9fff]+", cleaned) and len(cleaned) > 4:
            for index in range(0, len(cleaned) - 1):
                chunk = cleaned[index : index + 2]
                if chunk not in tokens:
                    tokens.append(chunk)
    return tokens[:64]


def build_route_text(
    database_name: str,
    dialect: str,
    catalog: str | None,
    schema: str,
    table_name: str,
    table_description: str | None,
    columns: list[dict],
) -> str:
    parts = [
        f"database {database_name}",
        f"dialect {dialect}",
        f"catalog {catalog or ''}",
        f"schema {schema}",
        f"table {table_name}",
        table_description or "",
    ]
    for column in columns:
        parts.extend(
            [
                str(column.get("name") or ""),
                str(column.get("data_type") or ""),
                str(column.get("description") or ""),
            ]
        )
    return " ".join(part for part in parts if part).lower()
