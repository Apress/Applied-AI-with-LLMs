from pathlib import Path


class DocumentLoader:
    supported_extensions = {".txt", ".md"}

    def load(self, file_path: str | Path) -> str:
        path = Path(file_path)
        if path.suffix.lower() not in self.supported_extensions:
            raise ValueError("Unsupported file type. Only .txt and .md files are supported.")

        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError("Document is empty.")
        return text

