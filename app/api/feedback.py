from fastapi import APIRouter
from psycopg.types.json import Jsonb

from app.db import get_conn
from app.schemas import FeedbackRequest

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


@router.post("")
def create_feedback(payload: FeedbackRequest) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO autosql_feedback (
                    request_id, user_id, accepted, copied, inserted,
                    executed_successfully, user_modified_sql, feedback_text, metadata_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload.request_id,
                    payload.user_id,
                    payload.accepted,
                    payload.copied,
                    payload.inserted,
                    payload.executed_successfully,
                    payload.user_modified_sql,
                    payload.feedback_text,
                    Jsonb(payload.metadata),
                ),
            )
            return {"result": {"id": cur.fetchone()["id"]}}
