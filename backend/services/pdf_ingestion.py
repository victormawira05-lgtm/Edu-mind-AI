from __future__ import annotations

import io
from typing import List, Tuple
from uuid import uuid4

from pypdf import PdfReader

from backend.schemas.documents import DocumentCategory, DocumentChunkRecord


SCANNED_PDF_MESSAGE = (
    "This PDF appears to be scanned or image-based with no extractable text. "
    "Scanned PDFs are not supported yet until OCR is implemented."
)

MIN_EXTRACTABLE_CHARS = 25


class ScannedPdfUnsupportedError(Exception):
    """Raised when a PDF has insufficient extractable text and requires OCR."""

    def __init__(self, filename: str, page_count: int, message: str = SCANNED_PDF_MESSAGE) -> None:
        super().__init__(message)
        self.filename = filename
        self.page_count = page_count
        self.message = message


def extract_pdf_pages(pdf_bytes: bytes) -> Tuple[int, List[Tuple[int, str]]]:
    """Extract (page_number, cleaned_text) pairs from raw PDF bytes."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    pages: List[Tuple[int, str]] = []

    for idx, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        normalized = " ".join(raw.split())
        if normalized:
            pages.append((idx, normalized))

    return page_count, pages


def chunk_page_text(
    text: str,
    *,
    chunk_size: int = 700,
    overlap: int = 100,
) -> List[str]:
    """Split text into bounded overlapping chunks without splitting words awkwardly."""
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    step = max(1, chunk_size - overlap)
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start + (chunk_size // 2):
                end = last_space
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start += step

    return chunks


def ingest_pdf_document(
    *,
    pdf_bytes: bytes,
    filename: str,
    title: str,
    category: DocumentCategory,
    unit_id: str,
    user_id: str,
    document_id: str | None = None,
    chunk_size: int = 700,
    overlap: int = 100,
) -> Tuple[str, int, int, List[DocumentChunkRecord]]:
    """
    Validate text extractability (rejecting scanned/empty PDFs clearly until OCR is added)
    and produce chunk records carrying full source metadata.
    """
    page_count, pages = extract_pdf_pages(pdf_bytes)
    total_chars = sum(len(t) for _, t in pages)

    if page_count == 0 or total_chars < MIN_EXTRACTABLE_CHARS:
        raise ScannedPdfUnsupportedError(filename=filename, page_count=page_count)

    doc_id = document_id or str(uuid4())
    records: List[DocumentChunkRecord] = []
    chunk_idx = 0

    for page_num, page_text in pages:
        for piece in chunk_page_text(page_text, chunk_size=chunk_size, overlap=overlap):
            records.append(
                DocumentChunkRecord(
                    chunk_id=f"{doc_id}-c{chunk_idx}",
                    user_id=user_id,
                    unit_id=unit_id,
                    document_id=doc_id,
                    document_title=title,
                    category=category,
                    page_number=page_num,
                    chunk_index=chunk_idx,
                    content=piece,
                )
            )
            chunk_idx += 1

    return doc_id, page_count, total_chars, records
