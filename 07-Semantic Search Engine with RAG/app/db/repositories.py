from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Document, DocumentChunk, utc_now
from app.services.chunker import TextChunk


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_document(self, filename: str, content_type: str, file_path: str, status: str = "uploaded") -> Document:
        document = Document(
            id=str(uuid4()),
            filename=filename,
            content_type=content_type,
            file_path=file_path,
            status=status,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def update_document_status(self, document_id: str, status: str) -> Document | None:
        document = self.get_document(document_id)
        if document is None:
            return None
        document.status = status
        document.updated_at = utc_now()
        self.session.commit()
        self.session.refresh(document)
        return document

    def list_documents(self) -> list[Document]:
        return list(self.session.scalars(select(Document).order_by(Document.created_at.desc())).all())

    def get_document(self, document_id: str) -> Document | None:
        statement = select(Document).where(Document.id == document_id).options(selectinload(Document.chunks))
        return self.session.scalar(statement)

    def delete_document(self, document_id: str) -> bool:
        document = self.get_document(document_id)
        if document is None:
            return False
        self.session.delete(document)
        self.session.commit()
        return True

    def create_chunks(self, document_id: str, chunks: list[TextChunk]) -> list[DocumentChunk]:
        db_chunks = [
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                qdrant_point_id="",
            )
            for chunk in chunks
        ]
        for chunk in db_chunks:
            chunk.qdrant_point_id = chunk.id
        self.session.add_all(db_chunks)
        self.session.commit()
        for chunk in db_chunks:
            self.session.refresh(chunk)
        return db_chunks

    def list_chunks_by_document(self, document_id: str) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.session.scalars(statement).all())

    def delete_chunks_by_document(self, document_id: str) -> int:
        chunks = self.list_chunks_by_document(document_id)
        count = len(chunks)
        for chunk in chunks:
            self.session.delete(chunk)
        self.session.commit()
        return count

