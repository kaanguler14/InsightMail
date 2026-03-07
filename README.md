# InsightMail

A locally-hosted RAG pipeline that turns your email inbox into a queryable knowledge base with conversation summarization and AI-powered reply generation. No data leaves your machine.

<img width="1919" height="943" alt="image" src="https://github.com/user-attachments/assets/9b9747eb-39dd-469b-a85f-4eedf9f7c253" />

## Why This Exists

Email is the largest unstructured knowledge base most professionals have, yet it's locked behind keyword search. InsightMail applies retrieval-augmented generation to your inbox: it indexes emails as vector embeddings, retrieves relevant context via semantic similarity, and generates answers, summaries, and reply drafts using a local LLM. Everything runs on your hardware . no API keys, no cloud inference, no data leakage.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INGESTION PIPELINE                            │
│                                                                             │
│  IMAP (Gmail/Outlook/Yahoo)                                                 │
│       │                                                                     │
│       ▼                                                                     │
│  Email Receiver ──► Email Parser ──► Chunker (spaCy) ──► Embedder (Qwen3)  │
│  (IPv4-forced)     (HTML strip)     (sentence-aware)    (1024-dim, FP16)   │
│                                                              │              │
│                                                              ▼              │
│                                                         Qdrant (cosine)    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                               QUERY PIPELINE                               │
│                                                                             │
│  User Query ──► Embed ──► Qdrant Search ──► Context Assembly ──► LLM       │
│                           (top-k, 0.5       (ranked chunks)     (Llama 3.2)│
│                            threshold)                               │       │
│                                                                     ▼       │
│                                                              JSON Response  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONVERSATION PIPELINE                              │
│                                                                             │
│  Contact Email ──► IMAP Fetch (inbox + sent) ──► Parse & Label ──► LLM     │
│                    (dynamic sent folder          ([ME]/[THEM]       │       │
│                     discovery via \Sent flag)      role tags)       ▼       │
│                                                              Summary /     │
│                                                              Reply Drafts  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVING LAYER                                  │
│                                                                             │
│  FastAPI ◄── React (Vite) ◄── Browser                                      │
│  :8000       :5173 (dev)                                                    │
│              proxy /api → :8000                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```



## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **LLM** | Llama 3.2 3B Instruct (Q4_K_M GGUF) | 4-bit quantized, runs on consumer GPU with ~2GB VRAM. Good instruction-following at small size |
| **Embeddings** | Qwen3-Embedding-0.6B (1024-dim) | Compact model with strong multilingual retrieval quality. FP16 on CUDA |
| **Vector DB** | Qdrant | Production-grade, supports filtering, payload storage, and cosine similarity out of the box |
| **Chunking** | spaCy `en_core_web_sm` | Sentence-boundary-aware splitting avoids mid-sentence breaks that degrade retrieval quality |
| **Email** | IMAP via `imaplib` | Direct protocol access . no third-party wrappers. Custom IPv4-forced socket for network reliability |
| **API** | FastAPI + Pydantic | Typed request/response validation, async-ready, auto-generated OpenAPI docs |
| **Frontend** | React 19 + Vite + CSS Modules | Component-based UI with design token system, no CSS framework dependency |

## Key Features

**RAG Q&A** : Ask natural language questions about your emails. The system retrieves semantically relevant chunks from Qdrant and generates grounded answers via the local LLM. Score threshold (0.5) filters low-relevance noise.

**Semantic Search** : Vector similarity search without LLM generation. Returns the top-k most relevant email chunks ranked by cosine distance. Useful for finding context fast.

**Conversation Summarization** : Fetches the last N emails with a specific contact (both sent and received), labels each message with `[ME]`/`[THEM]` role markers, and generates a structured summary (topics, outcomes, current status).

**Reply Suggestions** : Generates 3 contextual reply drafts for the latest incoming email from a contact. Supports tone control: `formal`, `friendly`, or `brief`. Dynamic body truncation scales per-email context allocation based on thread length to stay within the 4096-token context window.

**Multi-Provider IMAP** : Supports Gmail, Outlook, Yahoo, Yandex, and iCloud. Dynamically discovers the sent-mail folder via IMAP `LIST` + `\Sent` flag parsing, with localized folder name fallbacks (including Turkish Gmail).

## Technical Decisions & Trade-offs

### Local-first inference vs cloud APIs

All inference runs locally. This means zero per-query cost and full data privacy, but requires a CUDA-capable GPU. The Llama 3.2 3B Q4_K_M model loads in ~8s and fits in ~2GB VRAM. For teams needing higher quality, the architecture supports swapping in any GGUF model by changing one path in `query_database.py`.

### Sentence-aware chunking vs fixed-size

Fixed-size chunking (split every N characters) is simpler but produces chunks that break mid-sentence, degrading retrieval precision. spaCy's sentence segmenter produces linguistically coherent chunks with a configurable minimum size (200 chars default). The trade-off is a spaCy model load on startup (~1s).

### Dynamic context allocation

When summarizing or generating replies, the system dynamically adjusts `max_body_chars` per email based on thread length: `max(300, min(1200, 10000 / email_count))`. This prevents long threads from exceeding the context window while maximizing content for short threads.

### Explicit role labeling for LLM accuracy

Conversation context is built with `[ME (user@email)]` and `[THEM (contact@email)]` prefixes on each message. Without this, the LLM frequently confuses who sent what, especially in reply generation. This was validated empirically.  unlabeled context produced replies written from the wrong perspective.

### IMAP sent folder discovery

Different providers use different sent folder names (Gmail: `[Gmail]/Sent Mail`, Turkish Gmail: `[Gmail]/Gönderilmiş Postalar`, Outlook: `Sent`, etc.) and encode them differently in IMAP. The system first checks the `\Sent` flag in `LIST` responses (most reliable), falls back to matching known folder names, and finally uses a static provider map. Folder names with special characters are properly quoted for the IMAP `SELECT` command.

## API Reference

| Method | Endpoint | Description | Body |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | — |
| `GET` | `/recent-contacts` | Last 5 contacts with name + email | — |
| `POST` | `/ask` | Semantic search (no LLM) | `{ query, top_k }` |
| `POST` | `/search` | RAG Q&A with LLM answer | `{ query, top_k }` |
| `POST` | `/summarize` | Conversation summary | `{ contact_email, limit }` |
| `POST` | `/reply-suggest` | Reply draft generation | `{ contact_email, tone }` |

All endpoints return typed JSON via Pydantic response models. Errors follow FastAPI's `HTTPException` pattern with structured `detail` messages.

## Getting Started

### Prerequisites

- Python 3.10+
- CUDA-capable GPU (for LLM and embedding inference)
- [Qdrant](https://qdrant.tech/) running on `localhost:6333`
- Node.js 18+ (for the frontend)
- An email account with an app-specific password enabled

### Setup

```bash
git clone https://github.com/your-username/InsightMail.git
cd InsightMail

# Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Download LLM (place in models/)
# Llama-3.2-3B-Instruct-Q4_K_M.gguf → models/

# Environment
cp .env.example .env
# Edit .env:
#   EMAIL_ADDRESS=you@gmail.com
#   EMAIL_PASSWORD=your-app-specific-password

# Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# Index emails
python -m src.store_embeddings

# Start API
uvicorn src.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The app is available at `http://localhost:5173`. The Vite dev server proxies API calls to the FastAPI backend at `:8000`.

### Production Build

```bash
cd frontend
npm run build  # outputs to static/react/
```

The FastAPI server serves the built frontend from `/static`.

## Project Structure

```
InsightMail/
├── src/
│   ├── main.py                  # FastAPI app, endpoint definitions, CORS
│   ├── Email_Receiver.py        # IMAP client, multi-provider, sent folder discovery
│   ├── Email_Parser.py          # Header decoding, HTML→text, body extraction
│   ├── Email_Chunker.py         # spaCy sentence-aware text chunking
│   ├── Email_Embedding.py       # Batch embedding generation, single-text embed
│   ├── vector_database.py       # Qdrant wrapper (upsert, search, auto-collection)
│   ├── store_embeddings.py      # Indexing pipeline (fetch→chunk→embed→store)
│   ├── query_database.py        # RAG query with local Llama LLM
│   ├── conversation_summarizer.py  # Email thread summarization
│   ├── reply_suggester.py       # Reply draft generation with tone control
│   ├── email_utils.py           # Shared parsing/formatting utilities
│   ├── custom_types.py          # Pydantic request/response models
│   └── global_model.py          # Singleton embedding model loader
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/              # Button, Input, Tabs, Badge, Spinner, etc.
│   │   │   ├── layout/          # Shell, Sidebar
│   │   │   └── features/        # SummaryView, ReplyView, SearchView, SemanticView
│   │   ├── api/client.js        # API client (typed fetch wrappers)
│   │   ├── hooks/useAsync.js    # Async state management hook
│   │   └── styles/              # Design tokens (CSS custom properties), globals
│   └── vite.config.js           # Vite config with API proxy rules
├── Decorators/
│   └── perf_logger.py           # Class decorator for method-level timing logs
├── models/                      # Local GGUF model files (git-ignored)
├── requirements.txt
└── .env                         # Email credentials (git-ignored)
```

## Performance Characteristics

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Embedding model load | ~8s | One-time at startup, FP16 on CUDA |
| LLM load | ~3s | One-time at startup, Q4_K_M quantization |
| Single text embedding | <50ms | 1024-dim vector via Qwen3-0.6B |
| Qdrant search (top-5) | <10ms | Cosine similarity with 0.5 score threshold |
| RAG Q&A (end-to-end) | 5-15s | Dominated by LLM generation (512 max tokens) |
| Conversation summary | 15-30s | IMAP fetch + LLM generation |
| Reply suggestions | 20-40s | IMAP fetch + 3x reply generation |
