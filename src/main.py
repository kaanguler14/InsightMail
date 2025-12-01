import os
import time
from typing import List ,Dict,Any

from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from starlette.responses import HTMLResponse
from src.custom_types import SearchRequest,SearchResult

from src.global_model import GLOBAL_MODEL
from src.custom_types import SearchResult
from src.vector_database import QdrantStorage
from src.Email_Embedding import Email_Embedding as Embedder

QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "emails"
VECTOR_DIM=1024

app = FastAPI(title="Email Rag App",version="1.0")

try:
    qdrant_storage = QdrantStorage(
        url=QDRANT_URL,
        collection=QDRANT_COLLECTION,
        dim=VECTOR_DIM,
    )
    print("QDRANT_URL=",qdrant_storage)
except Exception as e:
    print(f"Qdrant bağlantı hatası {e}")
    qdrant_storage = None


#Endpoint
@app.get("/")
async def root():
    return {"status": "ok","model_loaded": GLOBAL_MODEL is not None}

@app.post("/search",response_model=SearchResult)
async def search_emails(request: SearchRequest):

    if qdrant_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Veritabanı bağlanmadı"
        )

    if not request.query:
        raise HTTPException(status_code=400,detail="boş sorgu")

    start_time=time.perf_counter()

    try:
        query_vector = GLOBAL_MODEL.encode(
            [request.query],
            convert_to_tensor=False
        )[0].tolist()

        results=qdrant_storage.search(  query_vector=query_vector,top_k=request.top_k)
        end_time=time.perf_counter()
        search_time_ms=(end_time-start_time)*1000

        return SearchResult(
            contexts=results["contexts"],
            sources=results["sources"],
            search_time_ms=search_time_ms,
        )
    except Exception as e:
        print("ARAMA HATASI:", e)
        raise HTTPException(status_code=500, detail=f"sunucu arama hatası: {e}")