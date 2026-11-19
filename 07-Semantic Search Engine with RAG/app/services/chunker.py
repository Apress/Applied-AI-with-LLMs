from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str


class WordChunker:
    def __init__(self, chunk_size: int = 100, overlap: int =20):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be greater than or equal to 0")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[TextChunk]:
        words = text.split()
        if not words:
            return []

        chunks: list[TextChunk] = []
        start = 0
        step = self.chunk_size - self.overlap
        while start < len(words):
            chunk_words = words[start : start + self.chunk_size]
            chunks.append(TextChunk(chunk_index=len(chunks), text=" ".join(chunk_words)))
            if start + self.chunk_size >= len(words):
                break
            start += step
        return chunks

