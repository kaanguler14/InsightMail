"""Merkezi yapılandırma (single source of truth).

WHY: Qdrant URL'i, koleksiyon adı, model yolları gibi değerler önceden main.py,
store_embeddings.py, query_database.py ve global_model.py içinde ayrı ayrı sabit
kodluydu. Bir değeri değiştirmek için birden çok dosyayı elle güncellemek gerekiyordu
ve biri unutulunca tutarsızlık oluşuyordu. Ayrıca farklı bir ortama (ör. uzak Qdrant)
taşımak kodu değiştirmeyi gerektiriyordu.

Artık tüm yapılandırma burada toplanır ve ortam değişkenlerinden (opsiyonel,
varsayılanlı) okunur.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Qdrant ---
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "emails")
# Retrieval: bu cosine skorunun altındaki sonuçlar elenir. Qwen3 kısa/diller-arası
# sorgularda düşük mutlak benzerlik verir; 0.5 çok katıydı (alakalı e-postalar ~0.45'te
# eleniyordu, ör. "what temu says"). 0.4 daha iyi recall/precision dengesi; env ile ayarlanır.
RETRIEVAL_SCORE_THRESHOLD = float(os.environ.get("RETRIEVAL_SCORE_THRESHOLD", "0.4"))

# --- Embedding modeli ---
EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "Qwen/Qwen3-Embedding-0.6B")
# Embedder cihazı: "cpu" | "cuda" | None(=otomatik: cuda varsa cuda).
# WHY: API sunucusu llama-cpp (LLM, CUDA) ile aynı süreçte çalışır; embedder de
# aynı GPU'da olursa ikisi çakışıp embedder çıktısını bozuyor. main.py bunu
# sunucu için varsayılan "cpu" yapar; toplu indeksleme GPU'da kalır.
EMBED_DEVICE = os.environ.get("EMBED_DEVICE")

# --- LLM ---
LLM_MODEL_PATH = os.environ.get(
    "LLM_MODEL_PATH", "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
)
LLM_N_CTX = int(os.environ.get("LLM_N_CTX", "4096"))

# --- E-posta / IMAP kimlik bilgileri (zorunlu, varsayılan yok) ---
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# --- API erişim token'ı (opsiyonel) ---
# Ayarlıysa veri uçları "Authorization: Bearer <token>" zorunlu kılar.
# Ayarlı değilse auth devre dışıdır (yerel tek-kullanıcı geliştirme kolaylığı).
API_TOKEN = os.environ.get("API_TOKEN")

# --- CORS ---
# Virgülle ayrılmış origin listesi.
FRONTEND_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
