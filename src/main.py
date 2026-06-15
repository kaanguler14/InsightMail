import os
# WHY: API sunucusu LLM (llama-cpp, CUDA) ile aynı süreçte çalışır. torch embedder
# de aynı GPU'da olursa ikisi çakışıp embedder çıktısını bozuyor: ya CUDA "illegal
# memory access" ile çöküyor, ya da sessizce NaN vektör üretip Qdrant 400 "Format
# error in JSON body" veriyor. Bu yüzden sunucuda embedder'ı varsayılan olarak CPU'ya
# sabitliyoruz (Qwen3-0.6B, sorgu başına ~0.1-0.3s). Toplu indeksleme ayrı bir süreçtir
# (store_embeddings) ve GPU'da kalır. Açık EMBED_DEVICE verilirse ona saygı gösterilir.
# NOT: src.* importlarından ÖNCE çalışmalı (config/global_model import anında okur).
os.environ.setdefault("EMBED_DEVICE", "cpu")

import asyncio
from pathlib import Path

from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from src import config
from src.custom_types import (
    SearchRequest, RAGResponse, SummarizeRequest, SummarizeResponse,
    EmailItem, RecentContactsResponse, ContactItem,
    ReplyRequest, ReplyResponse, ReplySuggestion
)
from src.global_model import MODEL_DIMENSION, GLOBAL_MODEL
from src.vector_database import QdrantStorage
from src.Email_Embedding import Email_Embedding as Embedder
from src.Email_Receiver import EmailReceiver
from src.conversation_summarizer import summarize_conversation
from src.reply_suggester import suggest_replies
import src.query_database as query_database


# WHY: Embedder, model yüklenemediyse RuntimeError fırlatır. Burada yakalamazsak
# import patlar ve uygulama hiç ayağa kalkmaz. Yakalayıp global_embedder=None'a
# düşürüyoruz; embedding gerektiren uçlar (/ask, /search) 503 döner, geri kalan
# uçlar (örn. /summarize, /reply-suggest, /health) çalışmaya devam eder.
try:
    global_embedder = Embedder(chunker=None)
    print("embedder is ready")
except Exception as e:
    print(f"Embedder init error: {e}")
    global_embedder = None

VECTOR_DIM = MODEL_DIMENSION

app = FastAPI(title="Email Rag App", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

try:
    qdrant_storage = QdrantStorage(
        url=config.QDRANT_URL,
        collection=config.QDRANT_COLLECTION,
        dim=VECTOR_DIM,
    )
    print("Qdrant OK:", config.QDRANT_URL)
except Exception as e:
    print(f"Qdrant connection error: {e}")
    qdrant_storage = None


def require_auth(authorization: Optional[str] = Header(default=None)):
    """Veri uçları için basit Bearer-token koruması.

    WHY: API uçları korumasızdı; :8000'e erişen herhangi bir yerel süreç özel
    e-posta verisini sorgulayabiliyordu. API_TOKEN ayarlıysa "Authorization:
    Bearer <token>" zorunlu kılınır. Ayarlı değilse (yerel geliştirme) auth
    devre dışıdır, davranış geriye dönük uyumludur.
    """
    if not config.API_TOKEN:
        return
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": GLOBAL_MODEL is not None}


@app.post("/ask", response_model=RAGResponse, dependencies=[Depends(require_auth)])
async def ask_email(request: SearchRequest):

    if qdrant_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Database couldn't connect"
        )
    if global_embedder is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    if not request.query:
        raise HTTPException(status_code=400, detail="Empty query")

    def _ask():
        query_vector = global_embedder.embed_anything(request.query, is_query=True).tolist()
        return qdrant_storage.search(query_vector=query_vector, top_k=request.top_k)

    found = await asyncio.to_thread(_ask)
    return RAGResponse(contexts=found["contexts"], sources=found["sources"])


@app.post("/search", response_model=RAGResponse, dependencies=[Depends(require_auth)])
async def search_emails(request: SearchRequest):

    if qdrant_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Database not connected"
        )
    if global_embedder is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")

    if not request.query:
        raise HTTPException(status_code=400, detail="Empty query")

    result = await asyncio.to_thread(
        query_database.local_api_llm,
        request.query,
        qdrant_storage=qdrant_storage,
        embedder=global_embedder,
        top_k=request.top_k
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=str(result["error"]))

    print("answer--->", result.get("answer"))
    return RAGResponse(
        answer=result.get("answer"),
        contexts=result.get("context_used"),
        sources=result.get("sources"),
    )


@app.post("/search-stream", dependencies=[Depends(require_auth)])
async def search_stream(request: SearchRequest):
    # WHY: /search bloklayıp 5-15 sn boş ekran gösteriyordu. Bu uç aynı RAG akışını
    # SSE ile token token akıtır (önce sources, sonra token*, en son done).
    if qdrant_storage is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    if global_embedder is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    if not request.query:
        raise HTTPException(status_code=400, detail="Empty query")

    generator = query_database.local_api_llm_stream(
        request.query,
        qdrant_storage=qdrant_storage,
        embedder=global_embedder,
        top_k=request.top_k,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/recent-contacts", response_model=RecentContactsResponse, dependencies=[Depends(require_auth)])
async def recent_contacts():

    email_address = config.EMAIL_ADDRESS
    email_password = config.EMAIL_PASSWORD

    if not email_address or not email_password:
        raise HTTPException(status_code=500, detail="Email credentials not set (.env)")

    def _fetch_contacts():
        with EmailReceiver(email_address, email_password) as receiver:
            return receiver.fetch_recent_contacts(scan_limit=50, contact_count=10)

    try:
        contacts_raw = await asyncio.to_thread(_fetch_contacts)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"IMAP connection error: {e}")
    except Exception as e:
        # WHY: Ham exception mesajını istemciye dönmek iç ayrıntıları sızdırır.
        # Sunucuda logla, istemciye genel mesaj ver.
        print(f"Internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    contacts = [
        ContactItem(
            email=c["email"],
            name=c.get("name", c["email"]),
            last_date=c.get("last_date", ""),
            direction=c.get("direction", ""),
        )
        for c in contacts_raw
    ]

    return RecentContactsResponse(contacts=contacts)


@app.post("/summarize", response_model=SummarizeResponse, dependencies=[Depends(require_auth)])
async def summarize_emails(request: SummarizeRequest):

    email_address = config.EMAIL_ADDRESS
    email_password = config.EMAIL_PASSWORD

    if not email_address or not email_password:
        raise HTTPException(status_code=500, detail="Email credentials not set (.env)")

    if not request.contact_email:
        raise HTTPException(status_code=400, detail="contact_email is required")

    def _summarize():
        with EmailReceiver(email_address, email_password) as receiver:
            return summarize_conversation(
                contact_email=request.contact_email,
                receiver=receiver,
                limit=request.limit
            )

    try:
        result = await asyncio.to_thread(_summarize)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"IMAP connection error: {e}")
    except Exception as e:
        # WHY: Ham exception mesajını istemciye dönmek iç ayrıntıları sızdırır.
        # Sunucuda logla, istemciye genel mesaj ver.
        print(f"Internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    email_items = [
        EmailItem(
            subject=em.get("subject", ""),
            date=em.get("date", ""),
            direction=em.get("direction", ""),
            from_addr=em.get("from", ""),
            to_addr=em.get("to", ""),
            body_preview=em.get("body_preview", ""),
        )
        for em in result.get("emails", [])
    ]

    return SummarizeResponse(
        summary=result.get("summary", ""),
        emails=email_items,
    )


@app.post("/reply-suggest", response_model=ReplyResponse, dependencies=[Depends(require_auth)])
async def reply_suggest(request: ReplyRequest):

    email_address = config.EMAIL_ADDRESS
    email_password = config.EMAIL_PASSWORD

    if not email_address or not email_password:
        raise HTTPException(status_code=500, detail="Email credentials not set (.env)")

    if not request.contact_email:
        raise HTTPException(status_code=400, detail="contact_email is required")

    if request.tone not in ("formal", "friendly", "brief"):
        raise HTTPException(status_code=400, detail="tone must be: formal, friendly, or brief")

    def _suggest():
        with EmailReceiver(email_address, email_password) as receiver:
            return suggest_replies(
                contact_email=request.contact_email,
                tone=request.tone,
                receiver=receiver,
            )

    try:
        result = await asyncio.to_thread(_suggest)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"IMAP connection error: {e}")
    except Exception as e:
        # WHY: Ham exception mesajını istemciye dönmek iç ayrıntıları sızdırır.
        # Sunucuda logla, istemciye genel mesaj ver.
        print(f"Internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    orig = result.get("original_email", {})
    original_item = EmailItem(
        subject=orig.get("subject", ""),
        date=orig.get("date", ""),
        direction=orig.get("direction", ""),
        from_addr=orig.get("from", ""),
        to_addr=orig.get("to", ""),
        body_preview=orig.get("body_preview", ""),
    )

    suggestions = [
        ReplySuggestion(
            tone=s.get("tone", request.tone),
            subject=s.get("subject", ""),
            body=s.get("body", ""),
        )
        for s in result.get("suggestions", [])
    ]

    return ReplyResponse(original_email=original_item, suggestions=suggestions)