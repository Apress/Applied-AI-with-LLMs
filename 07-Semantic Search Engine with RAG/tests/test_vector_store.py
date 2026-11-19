from dataclasses import dataclass

from app.services.vector_store import VectorStore


@dataclass
class FakePoint:
    score: float
    payload: dict


@dataclass
class FakeQueryResponse:
    points: list[FakePoint]


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collection_name: str | None = None
        self.query: list[float] | None = None
        self.limit: int | None = None
        self.with_payload: bool | None = None

    def query_points(self, collection_name: str, query: list[float], limit: int, with_payload: bool) -> FakeQueryResponse:
        self.collection_name = collection_name
        self.query = query
        self.limit = limit
        self.with_payload = with_payload
        return FakeQueryResponse(
            points=[
                FakePoint(
                    score=0.87,
                    payload={
                        "document_id": "doc-1",
                        "chunk_id": "chunk-1",
                        "filename": "travel_policy.md",
                        "chunk_index": 2,
                        "text": "International travel requires manager approval.",
                    },
                )
            ]
        )


def test_search_uses_query_points_and_normalizes_results() -> None:
    client = FakeQdrantClient()
    vector_store = VectorStore(
        host="localhost",
        port=6333,
        collection_name="documents",
        vector_size=384,
        client=client,
    )

    results = vector_store.search([0.1, 0.2, 0.3], top_k=5)

    assert client.collection_name == "documents"
    assert client.query == [0.1, 0.2, 0.3]
    assert client.limit == 5
    assert client.with_payload is True
    assert results == [
        {
            "document_id": "doc-1",
            "chunk_id": "chunk-1",
            "filename": "travel_policy.md",
            "chunk_index": 2,
            "score": 0.87,
            "text": "International travel requires manager approval.",
        }
    ]
