from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.documents import list_documents, upload_document
from app.core.config import Settings
from app.db.models import Base
from app.db.repositories import DocumentRepository
from app.main import health


class FakeIngestionService:
    def index_document(self, document):
        return 0


def make_repository(tmp_path: Path) -> DocumentRepository:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return DocumentRepository(factory())


def test_health() -> None:
    assert health() == {"status": "ok"}


def test_documents_with_empty_database(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    assert list_documents(repository) == []


def test_unsupported_file_upload(tmp_path: Path) -> None:
    settings = Settings(upload_dir=tmp_path / "uploads")
    repository = make_repository(tmp_path)
    file = SimpleNamespace(filename="paper.pdf", content_type="application/pdf")

    with pytest.raises(HTTPException) as exc_info:
        upload_document(settings, repository, FakeIngestionService(), file)

    assert exc_info.value.status_code == 400
    assert "Unsupported file type" in exc_info.value.detail
