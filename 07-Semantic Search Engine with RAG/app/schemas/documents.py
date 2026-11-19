from datetime import datetime

from pydantic import BaseModel


class ChunkRead(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    qdrant_point_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: str
    filename: str
    content_type: str
    file_path: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentRead):
    chunks: list[ChunkRead]


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int
    status: str

