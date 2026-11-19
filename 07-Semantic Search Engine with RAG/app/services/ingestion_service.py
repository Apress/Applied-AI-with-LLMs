from app.db.models import Document
from app.db.repositories import DocumentRepository
from app.services.chunker import WordChunker
from app.services.document_loader import DocumentLoader
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


class IngestionError(Exception):
    pass


class IngestionService:
    def __init__(
        self,
        repository: DocumentRepository,
        document_loader: DocumentLoader,
        chunker: WordChunker,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self.repository = repository
        self.document_loader = document_loader
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def index_document(self, document: Document) -> int:
        try:
            text = self.document_loader.load(document.file_path)
            chunks = self.chunker.split(text)
            if not chunks:
                raise ValueError("Document does not contain any indexable text.")

            vectors = self.embedding_service.embed_texts([chunk.text for chunk in chunks])
            db_chunks = self.repository.create_chunks(document.id, chunks)
            try:
                self.vector_store.upsert_chunks(document, db_chunks, vectors)
            except Exception as exc:
                self.repository.delete_chunks_by_document(document.id)
                raise IngestionError("Vector indexing failed.") from exc

            self.repository.update_document_status(document.id, "indexed")
            return len(db_chunks)
        except ValueError:
            self.repository.update_document_status(document.id, "failed")
            raise
        except IngestionError:
            self.repository.update_document_status(document.id, "failed")
            raise
        except Exception as exc:
            self.repository.update_document_status(document.id, "failed")
            raise IngestionError("Document ingestion failed.") from exc

