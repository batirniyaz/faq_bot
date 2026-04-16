# 🤖 Smart FAQ Chatbot — RAG-powered Knowledge Base

An AI chatbot that turns your documents into an interactive FAQ assistant. Upload PDFs, Word files, or Markdown — and start asking questions in plain language. Powered by **Google Gemini** and **ChromaDB** semantic search.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Usage Guide](#usage-guide)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Author](#author)

---

## 🔍 Overview

Smart FAQ Chatbot is a **Retrieval-Augmented Generation (RAG)** application built for university knowledge bases, company FAQs, and document Q&A. It solves a real problem: instead of searching through long PDFs manually, you just ask a question and get a precise, sourced answer.

**What it does:**

- 📁 **Admin uploads documents** — PDF, DOCX, MD, TXT files are parsed, chunked, and embedded into a vector database
- 🔎 **Semantic search** — when a user asks a question, the most relevant chunks are retrieved using cosine similarity
- 🧠 **LLM answers** — Google Gemini reads the retrieved context and generates a concise, grounded answer
- 💬 **Chat interface** — full conversation history within the session, styled as a modern messenger

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI                             │
│                                                                 │
│   ┌──────────────────────┐     ┌──────────────────────────┐    │
│   │    💬 Chat Tab        │     │    📁 Files Tab           │    │
│   │  - Conversation UI   │     │  - Upload documents       │    │
│   │  - Source references │     │  - View / Delete files    │    │
│   └──────────┬───────────┘     └───────────┬──────────────┘    │
└──────────────┼──────────────────────────────┼───────────────────┘
               │ question                     │ file bytes
               ▼                              ▼
┌──────────────────────┐         ┌────────────────────────┐
│     vectorstore.py   │         │        rag.py           │
│                      │         │                         │
│  ChromaDB            │◄────────│  extract_text()         │
│  (cosine similarity) │         │  chunk_text()           │
│  persistent on disk  │         │  process_upload()       │
└──────────┬───────────┘         └────────────────────────┘
           │ top-k chunks
           ▼
┌──────────────────────┐         ┌────────────────────────┐
│       llm.py         │────────►│   Google Gemini API    │
│                      │         │   gemini-2.5-flash     │
│  build prompt        │◄────────│   gemini-embedding-001 │
│  send with history   │  answer └────────────────────────┘
└──────────────────────┘
```

### RAG Flow — step by step

1. **Ingest**: uploaded file → text extraction → sliding-window chunking (800 chars, 150 overlap)
2. **Embed**: each chunk is embedded using `gemini-embedding-001` (dim = 3072) and stored in ChromaDB
3. **Retrieve**: user question is embedded → cosine similarity search → top-5 chunks returned
4. **Generate**: Gemini receives system prompt + context chunks + chat history → produces answer
5. **Display**: answer shown in chat with source pills (filename + relevance score)

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **UI** | Streamlit | Interactive web interface, chat + file management |
| **LLM** | Google Gemini 2.5 Flash | Answer generation with conversation history |
| **Embeddings** | Gemini Embedding 001 | Semantic vector representation of text chunks |
| **Vector DB** | ChromaDB | Persistent local vector store, cosine similarity |
| **PDF parsing** | pypdf | Extract text from PDF files |
| **DOCX parsing** | python-docx | Extract text from Word documents |
| **Config** | python-dotenv | `.env`-based configuration management |
| **Containers** | Docker + Compose | Reproducible deployment with persistent volume |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Git**
- **Google Gemini API key** — [Get one free at Google AI Studio](https://aistudio.google.com/)
- *(Optional)* Docker & Docker Compose for containerized run

---

### Local Setup

#### Windows (PowerShell / Git Bash)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd faq_bot

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/Scripts/activate        # Git Bash
# OR: .\.venv\Scripts\Activate.ps1  # PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
# Open .env and fill in your GEMINI_API_KEY

# 5. Run the app
cd app
streamlit run app.py
```

#### macOS / Linux

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd faq_bot

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
# Open .env and fill in your GEMINI_API_KEY

# 5. Run the app
cd app
streamlit run app.py
```

App will be available at **http://localhost:8501**

---

### Docker Setup

```bash
# 1. Create your .env file
cp .env.example .env
# Fill in GEMINI_API_KEY

# 2. Build and run
docker compose up --build
```

App will be available at **http://localhost:8503**

ChromaDB data is persisted in a Docker named volume — your indexed documents survive container restarts.

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# ── Required ────────────────────────────────────────────────────
GEMINI_API_KEY=your_gemini_api_key_here   # From https://aistudio.google.com/

# ── Models (safe to leave as default) ───────────────────────────
GEMINI_MODEL=gemini-2.5-flash             # LLM for answer generation
EMBEDDING_MODEL=models/gemini-embedding-001  # Model for text embeddings

# ── Vector Store ─────────────────────────────────────────────────
CHROMA_PERSIST_DIR=./chroma_db            # Where ChromaDB stores data
COLLECTION_NAME=faq_collection            # Collection name inside ChromaDB

# ── Chunking & Retrieval ──────────────────────────────────────────
CHUNK_SIZE=800                            # Characters per chunk
CHUNK_OVERLAP=150                         # Overlap between adjacent chunks
TOP_K=5                                   # How many chunks to retrieve per query
```

> **Note:** Never commit your `.env` file. It is listed in `.gitignore`.

---

## 📖 Usage Guide

### Step 1 — Upload documents

1. Open the **Files** tab
2. Click the upload area and select one or more files (PDF, DOCX, MD, TXT)
3. Click **⚡ Embed & Add to Knowledge Base**
4. Wait for the progress bar — each file is chunked and embedded automatically
5. Uploaded documents appear in the **Indexed documents** list with chunk counts

### Step 2 — Ask questions

1. Switch to the **Chat** tab
2. Type your question in the input at the bottom
3. The bot retrieves the most relevant document chunks and generates a grounded answer
4. Expand **Sources** under the answer to see exactly which chunks were used

### Step 3 — Manage documents

- Click **👁 View** on any document to preview its content inline
- Click **🗑 Delete** to remove a document from the knowledge base (all its chunks are deleted)
- The stats row at the top shows live counts of documents, chunks, and file formats

---

## 📁 Project Structure

```
faq_bot/
├── Dockerfile               # Container image definition
├── compose.yml              # Docker Compose service + volume
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore
├── .dockerignore
│
└── app/                     # ← Source root (Streamlit working directory)
    ├── app.py               # Entry point — only sets page config and tabs
    ├── config.py            # Loads .env once, exports all settings
    │
    ├── chat_page.py         # 💬 Chat tab — conversation UI, session history
    ├── files_page.py        # 📁 Files tab — upload, list, preview, delete
    │
    ├── rag.py               # Document parsing (PDF/DOCX/MD/TXT) + chunking
    ├── vectorstore.py       # ChromaDB wrapper — add / query / delete / list
    ├── llm.py               # Gemini chat wrapper with retry logic (503/429)
    │
    ├── prompts/
    │   └── system_prompt.py # System prompt defining the bot's behaviour
    │
    └── uploads/             # Original uploaded files (for preview, gitignored)
```

**Key design rule:** `app.py` contains zero business logic — it only imports and calls `render()` from each page module. All configuration flows through `config.py` which is the single place calling `load_dotenv()`.

---

## ☁️ Deployment

### Streamlit Cloud (recommended for sharing)

1. Push your repo to GitHub (make sure `.env` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set **Main file path** to `app/app.py`
4. Under **Advanced settings → Secrets**, add your environment variables:

```toml
GEMINI_API_KEY = "your_key_here"
GEMINI_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"
CHROMA_PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "faq_collection"
CHUNK_SIZE = "800"
CHUNK_OVERLAP = "150"
TOP_K = "5"
```

5. Click **Deploy** — your app gets a public URL instantly

> **Note:** On Streamlit Cloud the `uploads/` folder and `chroma_db/` are ephemeral (reset on each deployment). For persistent storage in production, consider a cloud object store for uploads and a hosted vector DB.

---

## 👤 Author

**Batirniyaz Muratbaev**

---

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) — for making data apps this fast to build
- [Google Gemini](https://ai.google.dev/) — LLM and embedding models
- [ChromaDB](https://www.trychroma.com/) — lightweight embedded vector store
- [pypdf](https://pypdf.readthedocs.io/) & [python-docx](https://python-docx.readthedocs.io/) — document parsing
