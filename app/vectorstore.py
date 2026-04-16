"""ChromaDB wrapper with Gemini embedding function."""

from typing import Optional
import chromadb
from chromadb import EmbeddingFunction, Embeddings
from google import genai

from config import (
    GEMINI_API_KEY,
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
)

_genai_client = genai.Client(api_key=GEMINI_API_KEY)


class GeminiEmbeddings(EmbeddingFunction):
    """ChromaDB-compatible embedding function using Gemini."""

    def __call__(self, input: list[str]) -> Embeddings:
        results = []
        for text in input:
            response = _genai_client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
            )
            results.append(response.embeddings[0].values)
        return results


_chroma_client: Optional[chromadb.PersistentClient] = None
_collection = None


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=GeminiEmbeddings(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(chunks: list[str], doc_id: str, filename: str) -> int:
    """Add text chunks from a document to the vector store. Returns chunk count."""
    col = _get_collection()
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id, "filename": filename, "chunk": i} for i in range(len(chunks))]
    col.add(documents=chunks, ids=ids, metadatas=metadatas)
    return len(chunks)


def query(question: str, top_k: int = 5) -> list[dict]:
    """Return top-k relevant chunks for a question.

    Each result: {"text": str, "filename": str, "score": float}
    """
    col = _get_collection()
    response = _genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
    )
    query_embedding = response.embeddings[0].values

    results = col.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, col.count() or 1),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if results["documents"]:
        for text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append(
                {
                    "text": text,
                    "filename": meta.get("filename", "unknown"),
                    "score": round(1 - dist, 3),
                }
            )
    return output


def delete_document(doc_id: str) -> int:
    """Delete all chunks belonging to a document. Returns deleted count."""
    col = _get_collection()
    existing = col.get(where={"doc_id": doc_id})
    ids = existing["ids"]
    if ids:
        col.delete(ids=ids)
    return len(ids)


def list_documents() -> list[dict]:
    """Return unique documents stored in the collection.

    Each item: {"doc_id": str, "filename": str, "chunks": int}
    """
    col = _get_collection()
    all_items = col.get(include=["metadatas"])
    seen: dict[str, dict] = {}
    for meta in all_items["metadatas"]:
        doc_id = meta.get("doc_id", "")
        if doc_id not in seen:
            seen[doc_id] = {"doc_id": doc_id, "filename": meta.get("filename", ""), "chunks": 0}
        seen[doc_id]["chunks"] += 1
    return list(seen.values())


def collection_count() -> int:
    return _get_collection().count()
