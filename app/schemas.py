from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ColumnMeta(BaseModel):
    name: str
    data_type: str | None = None
    description: str | None = None
    nullable: bool | None = None
    is_primary_key: bool = False
    ordinal_position: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RelationshipMeta(BaseModel):
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "foreign_key"
    confidence: float = 1.0


class TableMeta(BaseModel):
    name: str
    table_type: str = "table"
    description: str | None = None
    row_count_estimate: int | None = None
    columns: list[ColumnMeta] = Field(default_factory=list)
    relationships: list[RelationshipMeta] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class MetadataSyncRequest(BaseModel):
    superset_database_id: int
    database_name: str
    dialect: str
    engine: str | None = None
    catalog: str | None = None
    schema_name: str = Field(alias="schema")
    description: str | None = None
    metadata_version: str | None = None
    tables: list[TableMeta] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class MetadataSearchRequest(BaseModel):
    superset_database_id: int
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    question: str
    allowed_tables: list[str] | None = None
    allowed_columns: dict[str, list[str]] | None = None
    limit: int = 8


class GenerateSqlRequest(BaseModel):
    question: str
    superset_database_id: int | None = None
    database: str | None = None
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    dialect: str | None = None
    current_sql: str | None = None
    allowed_tables: list[str] | None = None
    allowed_columns: dict[str, list[str]] | None = None
    schema_context: dict[str, Any] | None = None
    limit: int = 8

    @model_validator(mode="before")
    @classmethod
    def fill_from_schema_context(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        context = data.get("schema_context") or {}
        if isinstance(context, dict):
            if data.get("superset_database_id") is None:
                data["superset_database_id"] = context.get("database_id") or context.get("superset_database_id")
            if data.get("dialect") is None:
                data["dialect"] = context.get("dialect")
            if data.get("catalog") is None:
                data["catalog"] = context.get("catalog")
            if data.get("schema") is None:
                data["schema"] = context.get("schema")
        return data


class FeedbackRequest(BaseModel):
    request_id: str
    user_id: str | None = None
    accepted: bool | None = None
    copied: bool | None = None
    inserted: bool | None = None
    executed_successfully: bool | None = None
    user_modified_sql: bool | None = None
    feedback_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateColumn(BaseModel):
    name: str
    data_type: str | None = None
    description: str | None = None


class CandidateTable(BaseModel):
    name: str
    schema_name: str | None = None
    score: float
    reason: str
    matched_columns: list[CandidateColumn] = Field(default_factory=list)


class SqlGenerateResult(BaseModel):
    sql: str
    tables: list[str] = Field(default_factory=list)
    explanation: str = ""
    warnings: list[str] = Field(default_factory=list)
    readonly: bool = True
    provider: Literal["deepseek"] = "deepseek"
    schema_context: dict[str, Any] = Field(default_factory=dict)
