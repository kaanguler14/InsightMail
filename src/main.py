import os
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

load_dotenv()


global_embedder = Embedder(chunker=None)
print("embedder is ready")

QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "emails"
VECTOR_DIM = MODEL_DIMENSION

app = FastAPI(title="Email Rag App", version="1.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

try:
    qdrant_storage = QdrantStorage(
        url=QDRANT_URL,
        collection=QDRANT_COLLECTION,
        dim=VECTOR_DIM,
    )
    print("QDRANT_URL=", qdrant_storage)
except Exception as e:
    print(f"Qdrant bağlantı hatası {e}")
    qdrant_storage = None


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": GLOBAL_MODEL is not None}


@app.post("/ask", response_model=RAGResponse)
async def ask_email(request: SearchRequest):

    if qdrant_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Database couldn't connect"
        )
    if not request.query:
        raise HTTPException(status_code=400, detail="boş sorgu")

    query_vector = global_embedder.embed_anything(request.query).tolist()
    found = qdrant_storage.search(query_vector=query_vector, top_k=request.top_k)
    return RAGResponse(contexts=found["contexts"], sources=found["sources"])


@app.post("/search", response_model=RAGResponse)
async def search_emails(request: SearchRequest):

    if qdrant_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Veritabanı bağlanmadı"
        )

    if not request.query:
        raise HTTPException(status_code=400, detail="boş sorgu")

    result = query_database.local_api_llm(
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


@app.get("/recent-contacts", response_model=RecentContactsResponse)
async def recent_contacts():

    email_address = os.environ.get("EMAIL_ADDRESS")
    email_password = os.environ.get("EMAIL_PASSWORD")

    if not email_address or not email_password:
        raise HTTPException(status_code=500, detail="E-posta kimlik bilgileri ayarlanmamış (.env)")

    try:
        receiver = EmailReceiver(email_address, email_password)
        contacts_raw = receiver.fetch_recent_contacts(scan_limit=50, contact_count=5)
        receiver.close_connection()
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"IMAP bağlantı hatası: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_emails(request: SummarizeRequest):

    email_address = os.environ.get("EMAIL_ADDRESS")
    email_password = os.environ.get("EMAIL_PASSWORD")

    if not email_address or not email_password:
        raise HTTPException(status_code=500, detail="E-posta kimlik bilgileri ayarlanmamış (.env)")

    if not request.contact_email:
        raise HTTPException(status_code=400, detail="contact_email boş olamaz")

    try:
        receiver = EmailReceiver(email_address, email_password)
        result = summarize_conversation(
            contact_email=request.contact_email,
            receiver=receiver,
            limit=request.limit
        )
        receiver.close_connection()
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"IMAP bağlantı hatası: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


@app.post("/reply-suggest", response_model=ReplyResponse)
async def reply_suggest(request: ReplyRequest):

    email_address = os.environ.get("EMAIL_ADDRESS")
    email_password = os.environ.get("EMAIL_PASSWORD")

    if not email_address or not email_password:
        raise HTTPException(status_code=500, detail="E-posta kimlik bilgileri ayarlanmamış (.env)")

    if not request.contact_email:
        raise HTTPException(status_code=400, detail="contact_email boş olamaz")

    if request.tone not in ("formal", "friendly", "brief"):
        raise HTTPException(status_code=400, detail="tone must be: formal, friendly, or brief")

    try:
        receiver = EmailReceiver(email_address, email_password)
        result = suggest_replies(
            contact_email=request.contact_email,
            tone=request.tone,
            receiver=receiver,
        )
        receiver.close_connection()
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"IMAP bağlantı hatası: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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