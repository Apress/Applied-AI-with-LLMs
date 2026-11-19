from pydantic import BaseModel, Field

from app.schemas.search import SearchResultRead


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=50)


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResultRead]
