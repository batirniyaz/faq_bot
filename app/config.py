from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL")

CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR")
COLLECTION_NAME: str = os.getenv("COLLECTION_NAME")

CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP"))
TOP_K: int = int(os.getenv("TOP_K"))
