from typing import Any

from psycopg.types.json import Jsonb

from app.core.config import settings
from app.db import get_conn
from app.schemas import MetadataSearchRequest, MetadataSyncRequest
from app.services.text import build_route_text, extract_tokens


def sync_metadata(payload: MetadataSyncRequest) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO autosql_connections (
                    superset_database_id, name, dialect, engine, description,
                    metadata_version, last_synced_at, is_active, extra_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, now(), true, %s)
                ON CONFLICT (superset_database_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    dialect = EXCLUDED.dialect,
                    engine = EXCLUDED.engine,
                    description = EXCLUDED.description,
                    metadata_version = EXCLUDED.metadata_version,
                    last_synced_at = now(),
                    is_active = true,
                    extra_json = EXCLUDED.extra_json
                RETURNING id
                """,
                (
                    payload.superset_database_id,
                    payload.database_name,
                    payload.dialect,
                    payload.engine,
                    payload.description,
                    payload.metadata_version,
                    Jsonb(payload.extra),
                ),
            )
            connection_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO autosql_schemas (
                    connection_id, catalog, name, description, metadata_version, last_synced_at
                )
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (connection_id, catalog, name) DO UPDATE SET
                    description = EXCLUDED.description,
                    metadata_version = EXCLUDED.metadata_version,
                    last_synced_at = now()
                RETURNING id
                """,
                (
                    connection_id,
                    payload.catalog or "",
                    payload.schema_name,
                    None,
                    payload.metadata_version,
                ),
            )
            schema_id = cur.fetchone()["id"]

            cur.execute(
                "DELETE FROM autosql_relationships WHERE connection_id = %s AND schema_id = %s",
                (connection_id, schema_id),
            )
            cur.execute("DELETE FROM autosql_route_index WHERE schema_id = %s", (schema_id,))
            cur.execute("DELETE FROM autosql_tables WHERE schema_id = %s", (schema_id,))

            table_count = 0
            column_count = 0
            for table in payload.tables:
                cur.execute(
                    """
                    INSERT INTO autosql_tables (
                        connection_id, schema_id, name, table_type, description,
                        row_count_estimate, metadata_version, last_synced_at, extra_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s)
                    RETURNING id
                    """,
                    (
                        connection_id,
                        schema_id,
                        table.name,
                        table.table_type,
                        table.description,
                        table.row_count_estimate,
                        payload.metadata_version,
                        Jsonb(table.extra),
                    ),
                )
                table_id = cur.fetchone()["id"]

                column_rows: list[dict[str, Any]] = []
                for column in table.columns:
                    cur.execute(
                        """
                        INSERT INTO autosql_columns (
                            table_id, name, data_type, description, nullable,
                            is_primary_key, ordinal_position, extra_json
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            table_id,
                            column.name,
                            column.data_type,
                            column.description,
                            column.nullable,
                            column.is_primary_key,
                            column.ordinal_position,
                            Jsonb(column.extra),
                        ),
                    )
                    column_count += 1
                    column_rows.append(column.model_dump())

                route_text = build_route_text(
                    database_name=payload.database_name,
                    dialect=payload.dialect,
                    catalog=payload.catalog,
                    schema=payload.schema_name,
                    table_name=table.name,
                    table_description=table.description,
                    columns=column_rows,
                )
                cur.execute(
                    """
                    INSERT INTO autosql_route_index (
                        connection_id, schema_id, table_id, object_type, route_text, keywords
                    )
                    VALUES (%s, %s, %s, 'table', %s, %s)
                    """,
                    (connection_id, schema_id, table_id, route_text, extract_tokens(route_text)),
                )

                for rel in table.relationships:
                    cur.execute(
                        """
                        INSERT INTO autosql_relationships (
                            connection_id, schema_id, source_table, source_column,
                            target_table, target_column, relationship_type, confidence
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            connection_id,
                            schema_id,
                            rel.source_table,
                            rel.source_column,
                            rel.target_table,
                            rel.target_column,
                            rel.relationship_type,
                            rel.confidence,
                        ),
                    )
                table_count += 1

            return {
                "connection_id": connection_id,
                "schema_id": schema_id,
                "superset_database_id": payload.superset_database_id,
                "schema": payload.schema_name,
                "table_count": table_count,
                "column_count": column_count,
                "metadata_version": payload.metadata_version,
            }


def _score_row(row: dict[str, Any], tokens: list[str]) -> tuple[float, list[str]]:
    text = str(row.get("route_text") or "").lower()
    table_name = str(row.get("table_name") or "").lower()
    matched: list[str] = []
    score = 0.0
    for token in tokens:
        if token == table_name:
            score += 20
        elif token in table_name:
            score += 10
        elif token in text:
            score += 3
        else:
            continue
        matched.append(token)
    return score, matched[:12]


def search_metadata(payload: MetadataSearchRequest) -> dict[str, Any]:
    limit = max(1, min(50, payload.limit or settings.default_search_limit))
    tokens = extract_tokens(payload.question)
    allowed_tables = set(payload.allowed_tables or [])

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.name AS database_name,
                    c.dialect,
                    s.name AS schema_name,
                    t.id AS table_id,
                    t.name AS table_name,
                    t.description AS table_description,
                    r.route_text
                FROM autosql_route_index r
                JOIN autosql_connections c ON c.id = r.connection_id
                JOIN autosql_schemas s ON s.id = r.schema_id
                JOIN autosql_tables t ON t.id = r.table_id
                WHERE c.superset_database_id = %s
                  AND (%s IS NULL OR s.catalog = %s)
                  AND (%s IS NULL OR s.name = %s)
                  AND r.object_type = 'table'
                """,
                (
                    payload.superset_database_id,
                    payload.catalog,
                    payload.catalog or "",
                    payload.schema_name,
                    payload.schema_name,
                ),
            )
            rows = cur.fetchall()

            scored = []
            for row in rows:
                table_name = str(row["table_name"])
                if allowed_tables and table_name not in allowed_tables:
                    continue
                score, matched = _score_row(row, tokens)
                if score <= 0:
                    continue
                scored.append((score, matched, row))

            scored.sort(key=lambda item: (-item[0], str(item[2]["table_name"])))
            candidates = []
            for score, matched, row in scored[:limit]:
                cur.execute(
                    """
                    SELECT name, data_type, description
                    FROM autosql_columns
                    WHERE table_id = %s
                    ORDER BY ordinal_position NULLS LAST, name
                    LIMIT %s
                    """,
                    (row["table_id"], settings.max_columns_per_table),
                )
                columns = cur.fetchall()
                allowed_columns = (payload.allowed_columns or {}).get(str(row["table_name"]))
                if allowed_columns:
                    allowed_set = set(allowed_columns)
                    columns = [col for col in columns if col["name"] in allowed_set]
                matched_columns = [
                    col
                    for col in columns
                    if any(token in str(col["name"]).lower() for token in tokens)
                ][:12]
                candidates.append(
                    {
                        "name": row["table_name"],
                        "schema": row["schema_name"],
                        "score": score,
                        "reason": f"Matched tokens: {', '.join(matched)}",
                        "matched_columns": matched_columns,
                    }
                )

            return {
                "superset_database_id": payload.superset_database_id,
                "catalog": payload.catalog,
                "schema": payload.schema_name,
                "tokens": tokens,
                "tables": candidates,
                "match_count": len(scored),
            }


def build_schema_context(payload: MetadataSearchRequest) -> dict[str, Any]:
    search_result = search_metadata(payload)
    table_names = [item["name"] for item in search_result["tables"][: settings.max_context_tables]]
    if not table_names:
        return {
            "superset_database_id": payload.superset_database_id,
            "catalog": payload.catalog,
            "schema": payload.schema_name,
            "tables": [],
            "table_selection": {"mode": "catalog_search", "match_count": 0},
        }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name AS database_name, c.dialect, s.name AS schema_name,
                       t.id AS table_id, t.name AS table_name, t.description AS table_description
                FROM autosql_connections c
                JOIN autosql_schemas s ON s.connection_id = c.id
                JOIN autosql_tables t ON t.schema_id = s.id
                WHERE c.superset_database_id = %s
                  AND (%s IS NULL OR s.catalog = %s)
                  AND (%s IS NULL OR s.name = %s)
                  AND t.name = ANY(%s)
                ORDER BY t.name
                """,
                (
                    payload.superset_database_id,
                    payload.catalog,
                    payload.catalog or "",
                    payload.schema_name,
                    payload.schema_name,
                    table_names,
                ),
            )
            rows = cur.fetchall()
            database_name = rows[0]["database_name"] if rows else None
            dialect = rows[0]["dialect"] if rows else None
            tables = []
            for row in rows:
                cur.execute(
                    """
                    SELECT name, data_type, description, nullable, is_primary_key, ordinal_position
                    FROM autosql_columns
                    WHERE table_id = %s
                    ORDER BY ordinal_position NULLS LAST, name
                    LIMIT %s
                    """,
                    (row["table_id"], settings.max_columns_per_table),
                )
                columns = cur.fetchall()
                allowed_columns = (payload.allowed_columns or {}).get(str(row["table_name"]))
                if allowed_columns:
                    allowed_set = set(allowed_columns)
                    columns = [col for col in columns if col["name"] in allowed_set]
                tables.append(
                    {
                        "name": row["table_name"],
                        "description": row["table_description"],
                        "columns": columns,
                    }
                )
            return {
                "superset_database_id": payload.superset_database_id,
                "database_name": database_name,
                "dialect": dialect,
                "catalog": payload.catalog,
                "schema": payload.schema_name,
                "tables": tables,
                "table_selection": {
                    "mode": "catalog_search",
                    "match_count": search_result["match_count"],
                    "candidates": search_result["tables"],
                },
            }


def delete_metadata(superset_database_id: int, schema_name: str | None = None) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if schema_name:
                cur.execute(
                    """
                    DELETE FROM autosql_schemas s
                    USING autosql_connections c
                    WHERE s.connection_id = c.id
                      AND c.superset_database_id = %s
                      AND s.name = %s
                    """,
                    (superset_database_id, schema_name),
                )
            else:
                cur.execute(
                    "DELETE FROM autosql_connections WHERE superset_database_id = %s",
                    (superset_database_id,),
                )
            return {"deleted": cur.rowcount, "superset_database_id": superset_database_id, "schema": schema_name}
