from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings as get_cached_settings
from app.core.database import create_db_engine, create_session_factory, get_session
from app.db.repositories import DocumentRepository
from app.services.chunker import WordChunker
from app.services.document_loader import DocumentLoader
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from app.services.vector_store import VectorStore


def get_settings() -> Settings:
    return get_cached_settings()


@lru_cache
def get_engine():
    return create_db_engine(get_cached_settings())


@lru_cache
def get_session_factory():
    return create_session_factory(get_engine())


def get_db_session():
    yield from get_session(get_session_factory())


def get_document_repository(session: Annotated[Session, Depends(get_db_session)]) -> DocumentRepository:
    return DocumentRepository(session)


def get_document_loader() -> DocumentLoader:
    return DocumentLoader()


def get_chunker() -> WordChunker:
    return WordChunker()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    settings = get_cached_settings()
    return EmbeddingService(model_name=settings.embedding_model)


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_cached_settings()
    return VectorStore(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection_name=settings.qdrant_collection,
        vector_size=settings.embedding_vector_size,
    )


def get_ingestion_service(
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    document_loader: Annotated[DocumentLoader, Depends(get_document_loader)],
    chunker: Annotated[WordChunker, Depends(get_chunker)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> IngestionService:
    return IngestionService(repository, document_loader, chunker, embedding_service, vector_store)


def get_retrieval_service(
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> RetrievalService:
    return RetrievalService(embedding_service, vector_store)


def get_llm_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LLMService:
    return LLMService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout_seconds,
    )


def get_rag_service(
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
) -> RAGService:
    return RAGService(retrieval_service, llm_service)

