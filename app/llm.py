"""Gemini LLM wrapper for RAG-based chat."""

import time

from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

from config import GEMINI_API_KEY, GEMINI_MODEL
from prompts.system_prompt import SYSTEM_PROMPT

_client = genai.Client(api_key=GEMINI_API_KEY)

_RETRYABLE_CODES = {429, 503}
_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds between retries


def _history_to_gemini(chat_history: list[dict]) -> list[types.Content]:
    """Convert {'role': 'user'|'assistant', 'content': str} to Gemini Content format."""
    result = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        result.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    return result


def ask(question: str, chunks: list[dict], chat_history: list[dict]) -> str:
    """Generate an answer using retrieved chunks and conversation history.

    Retries up to _MAX_RETRIES times on 429 / 503 errors.
    """
    if chunks:
        context_parts = [
            f"[{i}] (from: {c['filename']})\n{c['text']}"
            for i, c in enumerate(chunks, 1)
        ]
        context_block = "\n\n---\n\n".join(context_parts)
        user_message = (
            f"{SYSTEM_PROMPT}\n\n"
            f"## Context\n{context_block}\n\n"
            f"## Question\n{question}"
        )
    else:
        user_message = (
            f"{SYSTEM_PROMPT}\n\n"
            "## Context\nNo relevant documents were found in the knowledge base.\n\n"
            f"## Question\n{question}"
        )

    history = _history_to_gemini(chat_history)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            chat = _client.chats.create(model=GEMINI_MODEL, history=history)
            response = chat.send_message(user_message)
            return response.text
        except (ServerError, ClientError) as e:
            status = getattr(e, "status_code", None) or getattr(e, "code", None)
            if status in _RETRYABLE_CODES and attempt < _MAX_RETRIES:
                last_error = e
                time.sleep(_RETRY_DELAY * attempt)
                continue
            raise
    raise last_error  # type: ignore[misc]
