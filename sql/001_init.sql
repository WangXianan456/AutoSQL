CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS autosql_connections (
    id BIGSERIAL PRIMARY KEY,
    superset_database_id BIGINT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    dialect TEXT NOT NULL,
    engine TEXT,
    description TEXT,
    metadata_version TEXT,
    last_synced_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autosql_schemas (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES autosql_connections(id) ON DELETE CASCADE,
    catalog TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    description TEXT,
    metadata_version TEXT,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (connection_id, catalog, name)
);

CREATE TABLE IF NOT EXISTS autosql_tables (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES autosql_connections(id) ON DELETE CASCADE,
    schema_id BIGINT NOT NULL REFERENCES autosql_schemas(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    table_type TEXT NOT NULL DEFAULT 'table',
    description TEXT,
    row_count_estimate BIGINT,
    metadata_version TEXT,
    last_synced_at TIMESTAMPTZ,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_id, name)
);

CREATE TABLE IF NOT EXISTS autosql_columns (
    id BIGSERIAL PRIMARY KEY,
    table_id BIGINT NOT NULL REFERENCES autosql_tables(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    data_type TEXT,
    description TEXT,
    nullable BOOLEAN,
    is_primary_key BOOLEAN NOT NULL DEFAULT FALSE,
    ordinal_position INTEGER,
    sample_values_summary JSONB,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (table_id, name)
);

CREATE TABLE IF NOT EXISTS autosql_relationships (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES autosql_connections(id) ON DELETE CASCADE,
    schema_id BIGINT REFERENCES autosql_schemas(id) ON DELETE CASCADE,
    source_table TEXT NOT NULL,
    source_column TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_column TEXT NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'foreign_key',
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autosql_business_terms (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES autosql_connections(id) ON DELETE CASCADE,
    schema_id BIGINT REFERENCES autosql_schemas(id) ON DELETE CASCADE,
    term TEXT NOT NULL,
    definition TEXT,
    mapped_table_id BIGINT REFERENCES autosql_tables(id) ON DELETE SET NULL,
    mapped_column_id BIGINT REFERENCES autosql_columns(id) ON DELETE SET NULL,
    expression TEXT,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autosql_metrics (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES autosql_connections(id) ON DELETE CASCADE,
    schema_id BIGINT REFERENCES autosql_schemas(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    expression TEXT NOT NULL,
    base_table_id BIGINT REFERENCES autosql_tables(id) ON DELETE SET NULL,
    time_column TEXT,
    filters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autosql_sql_examples (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES autosql_connections(id) ON DELETE CASCADE,
    schema_id BIGINT REFERENCES autosql_schemas(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    sql_text TEXT NOT NULL,
    tables_used TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autosql_route_index (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES autosql_connections(id) ON DELETE CASCADE,
    schema_id BIGINT REFERENCES autosql_schemas(id) ON DELETE CASCADE,
    table_id BIGINT REFERENCES autosql_tables(id) ON DELETE CASCADE,
    column_id BIGINT REFERENCES autosql_columns(id) ON DELETE CASCADE,
    object_type TEXT NOT NULL,
    route_text TEXT NOT NULL,
    keywords TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', coalesce(route_text, ''))) STORED,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autosql_route_index_vector ON autosql_route_index USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_autosql_route_index_trgm ON autosql_route_index USING GIN (route_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_autosql_route_index_scope ON autosql_route_index (connection_id, schema_id, object_type);

CREATE TABLE IF NOT EXISTS autosql_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,
    connection_id BIGINT REFERENCES autosql_connections(id) ON DELETE SET NULL,
    schema_id BIGINT REFERENCES autosql_schemas(id) ON DELETE SET NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS autosql_messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES autosql_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sql_text TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autosql_generation_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL,
    user_id TEXT,
    superset_database_id BIGINT,
    schema_name TEXT,
    question TEXT NOT NULL,
    selected_tables TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    generated_sql TEXT,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    model_name TEXT,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autosql_generation_logs_request_id ON autosql_generation_logs (request_id);
CREATE INDEX IF NOT EXISTS idx_autosql_generation_logs_created_at ON autosql_generation_logs (created_at);

CREATE TABLE IF NOT EXISTS autosql_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id TEXT,
    action TEXT NOT NULL,
    superset_database_id BIGINT,
    schema_name TEXT,
    resource_type TEXT,
    resource_id TEXT,
    ip_address TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autosql_feedback (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL,
    user_id TEXT,
    accepted BOOLEAN,
    copied BOOLEAN,
    inserted BOOLEAN,
    executed_successfully BOOLEAN,
    user_modified_sql BOOLEAN,
    feedback_text TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autosql_feedback_request_id ON autosql_feedback (request_id);
