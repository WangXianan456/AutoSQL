from fastapi import FastAPI

from app.api.compat import router as compat_router
from app.api.feedback import router as feedback_router
from app.api.generate import router as generate_router
from app.api.health import router as health_router
from app.api.metadata import router as metadata_router

app = FastAPI(
    title="AutoSQL Catalog Service",
    version="0.1.0",
    description="Metadata catalog and DeepSeek-powered SQL generation service for Superset AI SQL Assistant.",
)

app.include_router(health_router)
app.include_router(compat_router)
app.include_router(metadata_router)
app.include_router(generate_router)
app.include_router(feedback_router)
