from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentCategory(str, Enum):
    LECTURE_NOTES = "lecture_notes"
    PAST_PAPER = "past_paper"
    OTHER = "other"


class SourceMetadata(BaseModel):
    document_id: str
    document_title: str
    category: DocumentCategory
    unit_id: str
    page_number: int = Field(..., ge=1)
    chunk_index: int = Field(..., ge=0)


class DocumentChunkRecord(BaseModel):
    chunk_id: str
    user_id: str
    unit_id: str
    document_id: str
    document_title: str
    category: DocumentCategory
    page_number: int = Field(..., ge=1)
    chunk_index: int = Field(..., ge=0)
    content: str = Field(..., min_length=1)


class UploadedDocumentSummary(BaseModel):
    document_id: str
    user_id: str
    unit_id: str
    title: str
    filename: str
    category: DocumentCategory
    page_count: int = Field(..., ge=0)
    extracted_chars: int = Field(..., ge=0)
    chunk_count: int = Field(..., ge=0)
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScannedPdfErrorDetail(BaseModel):
    code: str = "SCANNED_PDF_UNSUPPORTED"
    message: str = (
        "This PDF appears to be scanned or image-based with no extractable text. "
        "Scanned PDFs are not supported yet until OCR is implemented."
    )
    filename: str
    page_count: int


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    category: Optional[DocumentCategory] = None


class RetrievedChunkResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    source: SourceMetadata


class RetrieveResponse(BaseModel):
    unit_id: str
    query: str
    results: List[RetrievedChunkResult]
