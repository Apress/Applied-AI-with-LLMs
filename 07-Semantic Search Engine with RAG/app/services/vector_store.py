from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.db.models import Document, DocumentChunk


SearchResult = dict[str, str | int | float]


class VectorStore:
    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str,
        vector_size: int,
        client: QdrantClient | None = None,
    ):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = client or QdrantClient(host=host, port=port)

    def ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
        )

    def upsert_chunks(self, document: Document, chunks: list[DocumentChunk], vectors: list[list[float]]) -> None:
        points = [
            models.PointStruct(
                id=chunk.qdrant_point_id,
                vector=vector,
                payload={
                    "document_id": document.id,
                    "chunk_id": chunk.id,
                    "filename": document.filename,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_vector: list[float], top_k: int) -> list[SearchResult]:
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        results: list[SearchResult] = []
        for point in response.points:
            payload = point.payload or {}
            results.append(
                {
                    "document_id": str(payload.get("document_id", "")),
                    "chunk_id": str(payload.get("chunk_id", "")),
                    "filename": str(payload.get("filename", "")),
                    "chunk_index": int(payload.get("chunk_index", 0)),
                    "score": float(point.score),
                    "text": str(payload.get("text", "")),
                }
            )
        return results

    def delete_by_document_id(self, document_id: str) -> None:
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
