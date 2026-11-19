from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_retrieval_service
from app.schemas.search import SearchRequest, SearchResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["search"])
logger = logging.getLogger(__name__)


@router.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> SearchResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty.")
    try:
        results = retrieval_service.search(query, top_k=request.top_k)
        return SearchResponse(query=query, results=results)
    except Exception as exc:
        logger.exception("Search failed for query=%r top_k=%s", query, request.top_k)
        raise HTTPException(status_code=500, detail="Search failed.") from exc
