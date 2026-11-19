from pathlib import Path

import pytest

from app.services.document_loader import DocumentLoader


def test_loads_txt(tmp_path: Path) -> None:
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    assert DocumentLoader().load(file_path) == "hello"


def test_loads_md(tmp_path: Path) -> None:
    file_path = tmp_path / "note.md"
    file_path.write_text("# Hello", encoding="utf-8")
    assert DocumentLoader().load(file_path) == "# Hello"


def test_rejects_unsupported_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "note.pdf"
    file_path.write_text("content", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        DocumentLoader().load(file_path)


def test_rejects_empty_file(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.md"
    file_path.write_text("  ", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        DocumentLoader().load(file_path)

