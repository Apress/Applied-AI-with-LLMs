from pathlib import Path
from shutil import copyfileobj
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import get_document_repository, get_ingestion_service, get_settings, get_vector_store
from app.core.config import Settings
from app.db.repositories import DocumentRepository
from app.schemas.documents import DocumentDetail, DocumentRead, DocumentUploadResponse
from app.services.ingestion_service import IngestionError, IngestionService
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    filename = Path(file.filename or "uploaded_document").name
    if Path(filename).suffix.lower() not in {".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only .txt and .md files are supported.")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    document = repository.create_document(
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        file_path="",
        status="uploaded",
    )
    file_path = settings.upload_dir / f"{document.id}_{filename}"
    try:
        with file_path.open("wb") as destination:
            copyfileobj(file.file, destination)
        document.file_path = str(file_path)
        repository.session.commit()
        repository.session.refresh(document)

        chunks_indexed = ingestion_service.index_document(document)
        indexed = repository.get_document(document.id)
        return DocumentUploadResponse(
            document_id=document.id,
            filename=filename,
            chunks_indexed=chunks_indexed,
            status=indexed.status if indexed else "indexed",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IngestionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        repository.update_document_status(document.id, "failed")
        raise HTTPException(status_code=500, detail="Document upload failed.") from exc


@router.get("", response_model=list[DocumentRead])
def list_documents(repository: Annotated[DocumentRepository, Depends(get_document_repository)]) -> list[DocumentRead]:
    return repository.list_documents()


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentDetail:
    document = repository.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    document.chunks.sort(key=lambda chunk: chunk.chunk_index)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> None:
    document = repository.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        vector_store.delete_by_document_id(document_id)
        file_path = Path(document.file_path)
        repository.delete_document(document_id)
        if file_path.exists():
            file_path.unlink()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Document deletion failed.") from exc

