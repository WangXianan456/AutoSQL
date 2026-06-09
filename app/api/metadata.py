from fastapi import APIRouter, Query

from app.schemas import MetadataSearchRequest, MetadataSyncRequest
from app.services.catalog import delete_metadata, search_metadata, sync_metadata

router = APIRouter(prefix="/v1/metadata", tags=["metadata"])


@router.post("/sync")
def metadata_sync(payload: MetadataSyncRequest) -> dict:
    return {"result": sync_metadata(payload)}


@router.post("/search")
def metadata_search(payload: MetadataSearchRequest) -> dict:
    return {"result": search_metadata(payload)}


@router.delete("/{superset_database_id}")
def metadata_delete(
    superset_database_id: int,
    schema: str | None = Query(default=None),
) -> dict:
    return {"result": delete_metadata(superset_database_id, schema)}
