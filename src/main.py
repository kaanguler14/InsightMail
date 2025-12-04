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
from llama_cpp import Llama

# İndirdiğiniz GGUF dosyasının yolunu buraya yazın
MODEL_PATH = "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

print("Model yükleniyor...")
# n_gpu_layers=-1 -> Tüm katmanları GPU'ya atar (RTX 2060 için ideal)
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,          # Context penceresi
    n_gpu_layers=-1,     # GPU kullanımı (Hepsini GPU'ya yükle)
    verbose=True
)
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

@app.get("/ask",response_model=SearchResult)
async def ask_email(question:str,top_k,request: SearchRequest):
    if qdrant_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Database couldn't connect"
        )
    if not request.query:
        raise HTTPException(status_code=400,detail="boş sorgu")
    query_vec=Embedder.embed_anything(question)[0]
    found=qdrant_storage.search(query_vector=query_vec,top_k=top_k)
    return SearchResult(contexts=found["contexts"],sources=found["sources"])
    
    

@app.post("/search",response_model=SearchResult)
async def search_emails(request: SearchRequest):

    if qdrant_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Veritabanı bağlanmadı"
        )

    if not request.query:
        raise HTTPException(status_code=400,detail="boş sorgu")

    
    start_search=time.perf_counter()
    query_vector=GLOBAL_MODEL.encode(
        [request.query],
        convert_to_tensor=False
    )[0].tolist()

    results=qdrant_storage.search(query_vector=query_vector,top_k=request.top_k)
    
    search_time_ms = (time.perf_counter()-start_searh) * 1000

    #context
    context_text=""
    for idx , text in enumerate(results["contexts"]):
        #Prompt'a  eklenecek kaynak metin
        context_text+=f"-Kaynak {idx+1}, -{text}"
    
    #Prompt
    if context_text is None:
        prompt=f"""<|start_header_id|>system<|end_header_id|>
bununla ilgili bir mail bulunamadığını söyle
<|eot_id|>"""
    else:
        prompt=f"""<|start_header_id|>system<|end_header_id|>
Sen yardımsever bir asistansın. Aşağıdaki E-posta içeriklerine (Kaynaklar) dayanarak kullanıcının sorusunu **kesinlikle Türkçe** olarak cevapla. Cevabın Kaynaklarda bulunmuyorsa, "Bu e-postalarda sorunuzla ilgili bilgi bulunmamaktadır." diye yanıtla.
<|eot_id|>
<|start_header_id|>user<|end_header_id|>
Soru: {request.query}

Kaynaklar:
{context_text}
<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""
    gen_start=time.perf_counter()

    #call LLM
    output=llm(prompt,max_tokens=512,stop=["<|eot_id|>","Kaynaklar:"],
               temperature=0.2,echo=False)
    
    gen_time_ms=(time.perf_counter()-gen_start)*1000
    generated_text=output["choices"][0]["text"].strip()

    return SearchResult(
        answer=generated_text,
        contexts=results["contexts"],
        sources=results["sources"],
        search_time_ms=search_time_ms,
    
    )