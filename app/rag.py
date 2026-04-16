"""Document parsing and chunking utilities."""

import io
import uuid
from typing import IO

import pypdf
import docx

import vectorstore
from config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)

    if ext == "docx":
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if ext in ("md", "txt"):
        return file_bytes.decode("utf-8", errors="replace")

    raise ValueError(f"Unsupported file type: .{ext}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += chunk_size - overlap
    return chunks


def process_upload(file_bytes: bytes, filename: str) -> tuple[str, int]:
    """Parse, chunk, and embed a document. Returns (doc_id, n_chunks)."""
    text = extract_text(file_bytes, filename)
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No text could be extracted from the file.")
    doc_id = str(uuid.uuid4())
    n = vectorstore.add_chunks(chunks, doc_id=doc_id, filename=filename)
    return doc_id, n
