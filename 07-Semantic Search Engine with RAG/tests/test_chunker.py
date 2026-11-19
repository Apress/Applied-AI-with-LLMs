import pytest

from app.services.chunker import WordChunker


def test_splits_text_into_multiple_chunks() -> None:
    chunker = WordChunker(chunk_size=4, overlap=1)
    chunks = chunker.split("one two three four five six seven")
    assert [chunk.text for chunk in chunks] == ["one two three four", "four five six seven"]


def test_preserves_overlap() -> None:
    chunker = WordChunker(chunk_size=3, overlap=1)
    chunks = chunker.split("a b c d e")
    assert chunks[0].text.split()[-1] == chunks[1].text.split()[0]


def test_rejects_overlap_greater_than_or_equal_to_chunk_size() -> None:
    with pytest.raises(ValueError, match="overlap must be smaller"):
        WordChunker(chunk_size=10, overlap=10)


def test_rejects_negative_overlap() -> None:
    with pytest.raises(ValueError, match="overlap must be greater"):
        WordChunker(chunk_size=10, overlap=-1)


def test_rejects_non_positive_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        WordChunker(chunk_size=0, overlap=0)


def test_handles_short_text() -> None:
    chunks = WordChunker(chunk_size=10, overlap=2).split("short text")
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "short text"


def test_handles_empty_text() -> None:
    assert WordChunker().split("   ") == []

