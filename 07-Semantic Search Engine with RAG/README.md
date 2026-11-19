# semantic-search-mvp

`semantic-search-mvp` is a small local semantic search API for documents.

It lets you upload `.txt` and `.md` files, extracts their text, splits the text
into chunks, creates embeddings, stores metadata in SQLite, stores vectors in
Qdrant, and searches those chunks through a FastAPI API. It can also answer a
question with a local Ollama model, grounded on the retrieved chunks.

The project is intentionally simple. It is meant to be easy to run, test, and
explain in a practical AI book.

## Architecture

```text
Client
  |
  | HTTP
  v
FastAPI routes
  |
  +--> SQLite repository -----> SQLite metadata database
  |
  +--> IngestionService
  |       |
  |       +--> DocumentLoader
  |       +--> WordChunker
  |       +--> EmbeddingService
  |       +--> VectorStore ----> Qdrant vectors
  |
  +--> RetrievalService
  |       |
  |       +--> EmbeddingService
  |       +--> VectorStore ----> Qdrant search
  |
  +--> RAGService
          |
          +--> RetrievalService
          +--> LLMService -----> Ollama
```

## Requirements

- Python 3.12 or newer
- `uv`
- Docker Compose or a Podman-compatible Compose command
- Ollama, only if you want to use `/ask`

## Setup

Install dependencies:

```bash
uv sync
```

Start Qdrant:

```bash
docker compose up -d
```

If you use Podman Compose, run the equivalent command for your environment.

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

The API will create the local `data/` directory, SQLite tables, and upload
directory automatically. It will also ensure that the Qdrant collection exists
at startup.

## Configuration

The app works without a `.env` file. To customize it, copy `.env.example` to
`.env` and edit the values.

Default values:

```text
DATABASE_URL=sqlite:///./data/app.db
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=documents
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_VECTOR_SIZE=384
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=120
UPLOAD_DIR=app/storage/uploaded_docs
```

The default embedding model produces 384-dimensional vectors.

## API Examples

Health check:

```bash
curl http://localhost:8000/health
```

Upload a document:

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@example_documents/travel_policy.md"
```

List documents:

```bash
curl http://localhost:8000/documents
```

Get one document and its chunks:

```bash
curl http://localhost:8000/documents/<document_id>
```

Search:

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Can I get reimbursed for an international business trip?","top_k":5}'
```

Ask a grounded question with Ollama:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What should I do after a security incident?","top_k":5}'
```

Delete a document:

```bash
curl -X DELETE http://localhost:8000/documents/<document_id>
```

## Ollama

The `/ask` endpoint calls Ollama at `OLLAMA_BASE_URL` using `OLLAMA_MODEL`.

Example:

```bash
ollama pull qwen2.5:7b
ollama serve
```

If Ollama cannot be reached, `/ask` returns HTTP 503. If generation exceeds the
configured timeout, it returns HTTP 504. Other upstream Ollama request failures
return HTTP 502. The semantic `/search` endpoint does not require Ollama.

## Ingestion Pipeline

When a file is uploaded:

1. The route saves the file under `app/storage/uploaded_docs/`.
2. A document row is created in SQLite with status `uploaded`.
3. `DocumentLoader` reads UTF-8 text from `.txt` or `.md`.
4. `WordChunker` splits text into ordered overlapping chunks.
5. `EmbeddingService` lazily loads the sentence-transformers model and embeds chunks.
6. Chunk metadata is written to SQLite.
7. Vectors and payloads are upserted into Qdrant.
8. The document status is updated to `indexed`.

If ingestion fails, the document is marked `failed`. If vector indexing fails
after chunks were written, the SQLite chunks are removed.

## Query Pipeline

For `/search`:

1. The query is embedded with the same embedding model.
2. Qdrant searches the vector collection with cosine similarity.
3. The API returns ranked chunks with scores and metadata.

For `/ask`:

1. `RAGService` uses `RetrievalService` to get relevant chunks.
2. The chunks are formatted into a grounded prompt.
3. `LLMService` calls Ollama `/api/generate` with `stream=false`.
4. The response includes the answer and the source chunks.

## Tests

Run the test suite:

```bash
uv run pytest
```

Unit tests use temporary SQLite databases and fakes for heavy services. They do
not require Qdrant, Ollama, or a downloaded embedding model.

## Limitations

- Only `.txt` and `.md` files are supported.
- Indexing runs in the request path.
- There is no authentication or multi-user permission model.
- There is no frontend.
- There are no database migrations.
- The default SQLite database is local to one machine.

## Production Evolution

A production system could add background indexing, file type expansion, proper
migrations, authentication, observability, retry policies, richer deletion and
reindexing workflows, model version tracking, and stronger operational controls.
Those pieces are deliberately left out of this MVP so the core semantic search
flow stays clear.

