from fastapi import APIRouter

from app.api.generate import generate_sql
from app.schemas import GenerateSqlRequest

router = APIRouter(tags=["compat"])


@router.post("/generate")
def generate_sql_compat(payload: GenerateSqlRequest) -> dict:
    """Compatibility endpoint for clients configured with request_format=generate."""
    return generate_sql(payload)
