from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import ask, documents, search
from app.api.dependencies import get_engine, get_settings, get_vector_store
from app.core.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    create_tables(get_engine())
    get_vector_store().ensure_collection()
    yield


app = FastAPI(title="semantic-search-mvp", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(documents.router)
app.include_router(search.router)
app.include_router(ask.router)

