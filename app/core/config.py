import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("AUTOSQL_DATABASE_URL", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_chat_completions_path: str = os.getenv(
        "DEEPSEEK_CHAT_COMPLETIONS_PATH",
        "/chat/completions",
    )
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_timeout_seconds: int = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
    default_search_limit: int = int(os.getenv("AUTOSQL_DEFAULT_SEARCH_LIMIT", "8"))
    max_context_tables: int = int(os.getenv("AUTOSQL_MAX_CONTEXT_TABLES", "10"))
    max_columns_per_table: int = int(os.getenv("AUTOSQL_MAX_COLUMNS_PER_TABLE", "80"))
    default_sql_limit: int = int(os.getenv("AUTOSQL_DEFAULT_SQL_LIMIT", "100"))
    max_sql_limit: int = int(os.getenv("AUTOSQL_MAX_SQL_LIMIT", "1000"))


settings = Settings()
