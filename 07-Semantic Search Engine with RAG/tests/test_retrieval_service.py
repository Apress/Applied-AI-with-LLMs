from app.services.retrieval_service import RetrievalService


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.1, 0.2]


class FakeVectorStore:
    def __init__(self) -> None:
        self.query_vector: list[float] | None = None
        self.top_k: int | None = None

    def search(self, query_vector: list[float], top_k: int):
        self.query_vector = query_vector
        self.top_k = top_k
        return [
            {
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "filename": "policy.md",
                "chunk_index": 0,
                "score": 0.9,
                "text": "policy text",
            }
        ]


def test_retrieval_service_embeds_query_passes_top_k_and_returns_results() -> None:
    embedding_service = FakeEmbeddingService()
    vector_store = FakeVectorStore()
    service = RetrievalService(embedding_service, vector_store)

    results = service.search("hello", top_k=7)

    assert embedding_service.queries == ["hello"]
    assert vector_store.query_vector == [0.1, 0.2]
    assert vector_store.top_k == 7
    assert results[0]["filename"] == "policy.md"

