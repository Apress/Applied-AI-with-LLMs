from sqlalchemy.orm import Session
from sqlalchemy import delete, select, text

from app.db.models import Document, DocumentChunk
from app.db.repositories import DocumentRepository
from app.services.chunker import TextChunk


def test_creates_document(session: Session) -> None:
    repository = DocumentRepository(session)
    document = repository.create_document("a.md", "text/markdown", "/tmp/a.md")
    assert document.id
    assert document.status == "uploaded"


def test_updates_document_status(session: Session) -> None:
    repository = DocumentRepository(session)
    document = repository.create_document(
        "a.md",
        "text/markdown",
        "/tmp/a.md",
    )

    repository.update_document_status(
        document.id,
        "indexed",
    )

    stored_document = repository.get_document(document.id)

    assert stored_document is not None
    assert stored_document.status == "indexed"


def test_creates_chunks(session: Session) -> None:
    repository = DocumentRepository(session)
    document = repository.create_document("a.md", "text/markdown", "/tmp/a.md")
    chunks = repository.create_chunks(document.id, [TextChunk(0, "one"), TextChunk(1, "two")])
    assert len(chunks) == 2
    assert chunks[0].qdrant_point_id == chunks[0].id


def test_lists_chunks_by_document(session: Session) -> None:
    repository = DocumentRepository(session)
    document = repository.create_document("a.md", "text/markdown", "/tmp/a.md")
    repository.create_chunks(document.id, [TextChunk(1, "two"), TextChunk(0, "one")])
    chunks = repository.list_chunks_by_document(document.id)
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]


def test_deletes_document_and_chunks(session: Session) -> None:
    repository = DocumentRepository(session)
    document = repository.create_document("a.md", "text/markdown", "/tmp/a.md")
    repository.create_chunks(document.id, [TextChunk(0, "one")])
    assert repository.delete_document(document.id) is True
    assert repository.get_document(document.id) is None
    assert repository.list_chunks_by_document(document.id) == []

def test_sqlite_foreign_keys_are_enabled(session: Session) -> None:
    assert session.scalar(text("PRAGMA foreign_keys")) == 1


def test_database_cascade_deletes_chunks(session: Session) -> None:
    repository = DocumentRepository(session)
    document = repository.create_document(
        "a.md",
        "text/markdown",
        "/tmp/a.md",
    )
    repository.create_chunks(
        document.id,
        [TextChunk(0, "one")],
    )

    session.execute(
        delete(Document).where(Document.id == document.id)
    )
    session.commit()

    chunk = session.scalar(
        select(DocumentChunk).where(
            DocumentChunk.document_id == document.id
        )
    )

    assert chunk is None
