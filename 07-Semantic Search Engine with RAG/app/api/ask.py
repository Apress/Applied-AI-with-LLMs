from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_rag_service
from app.schemas.ask import AskRequest, AskResponse
from app.services.llm_service import (
    OllamaRequestError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.services.rag_service import RAGService

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> AskResponse:
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question must not be empty.",
        )

    try:
        result = rag_service.ask(
            question,
            top_k=request.top_k,
        )
        return AskResponse(**result)

    except OllamaTimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=str(exc),
        ) from exc

    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except OllamaRequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Question answering failed.",
        ) from exc
