# InsightMail

A RAG (Retrieval-Augmented Generation) system that enables semantic search and question-answering over your email inbox.

## Architecture

```
Email (IMAP) -> Parser -> Chunker (spaCy) -> Embeddings (Qwen3) -> Qdrant -> FastAPI -> LLM (Ollama)
```

1. **Email Receiver** — Fetches emails via IMAP (Gmail, Outlook, Yahoo, Yandex, iCloud)
2. **Email Parser** — Extracts subject, body, metadata; cleans HTML with BeautifulSoup
3. **Email Chunker** — Splits text into chunks using spaCy sentence segmentation (min 200 chars)
4. **Embedding** — Generates vector embeddings with `Qwen/Qwen3-Embedding-0.6B` (1024 dimensions)
5. **Vector Database** — Stores and searches embeddings in Qdrant
6. **API** — FastAPI endpoints for search and RAG-powered Q&A via Ollama (`llama3.1`)

## Prerequisites

- Python 3.10+
- [Qdrant](https://qdrant.tech/) running on `localhost:6333`
- [Ollama](https://ollama.ai/) running on `localhost:11434` with `llama3.1` model pulled
- A Gmail/Outlook/Yahoo/Yandex/iCloud account with an app-specific password

## Setup

```bash
# Clone the repository
git clone https://github.com/your-username/InsightMail.git
cd InsightMail

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# Edit .env with your email credentials
```

## Usage

### 1. Index your emails

```bash
python -m src.store_embeddings
```

This fetches your latest 100 emails, chunks them, generates embeddings, and stores them in Qdrant.

### 2. Start the API server

```bash
uvicorn src.main:app --reload
```

### 3. Query your emails

**Semantic search (no LLM):**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "meeting next week", "top_k": 5}'
```

**RAG-powered Q&A (with Ollama):**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What did John say about the project deadline?", "top_k": 3}'
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/ask` | Semantic search over emails |
| POST | `/search` | RAG Q&A with LLM-generated answer |

## Project Structure

```
InsightMail/
├── src/
│   ├── main.py              # FastAPI application
│   ├── Email_Receiver.py    # IMAP email fetching
│   ├── Email_Parser.py      # Email parsing and HTML cleaning
│   ├── Email_Chunker.py     # Text chunking with spaCy
│   ├── Email_Embedding.py   # Sentence transformer embeddings
│   ├── vector_database.py   # Qdrant vector database wrapper
│   ├── store_embeddings.py  # Email indexing script
│   ├── query_database.py    # RAG query with Ollama
│   ├── custom_types.py      # Pydantic models
│   └── global_model.py      # Global embedding model
├── Decorators/
│   └── perf_logger.py       # Performance logging decorator
├── .env.example              # Environment variable template
├── requirements.txt          # Python dependencies
└── README.md
```
