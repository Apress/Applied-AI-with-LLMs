from app.services.embedding_service import EmbeddingService
from app.services.vector_store import SearchResult, VectorStore


class RetrievalService:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        query_vector = self.embedding_service.embed_text(query)
        return self.vector_store.search(query_vector, top_k=top_k)

