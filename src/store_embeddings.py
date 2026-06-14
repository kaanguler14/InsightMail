import uuid
from src import config
from src.global_model import MODEL_DIMENSION
from src.vector_database import QdrantStorage
from src.Email_Parser import EmailParser
from src.Email_Chunker import EmailChunker
from src.Email_Embedding import Email_Embedding

# WHY: uuid.uuid4() üretseydik, her indeksleme çalıştırmasında aynı e-posta
# farklı bir ID alır ve Qdrant'a KOPYA olarak eklenirdi (koleksiyon her seferinde
# şişer, arama sonuçları aynı maili tekrar tekrar döndürür).
# uuid.uuid5 ile ID'yi chunk içeriğinden TÜRETİYORUZ: aynı içerik -> aynı ID ->
# upsert üzerine yazar. Böylece store_embeddings'i tekrar çalıştırmak güvenlidir
# (idempotent).
INSIGHTMAIL_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "insightmail/emails")


def chunk_id(text: str) -> str:
    """Chunk içeriğinden türetilen deterministik (kararlı) point ID."""
    return str(uuid.uuid5(INSIGHTMAIL_NAMESPACE, text))

EMAIL_ADDRESS = config.EMAIL_ADDRESS
EMAIL_PASSWORD = config.EMAIL_PASSWORD

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise RuntimeError("EMAIL_ADDRESS and EMAIL_PASSWORD must be set in .env")

qdrant = QdrantStorage(
    url=config.QDRANT_URL,
    collection=config.QDRANT_COLLECTION,
    dim=MODEL_DIMENSION,
)

with EmailParser(EMAIL_ADDRESS, EMAIL_PASSWORD) as parser:
    chunker = EmailChunker(parser)
    embedder = Email_Embedding(chunker)

    ids = []
    vectors = []
    payloads = []

    for item in embedder.embedding(batch_size=1024):
        ids.append(chunk_id(item["text"]))
        vectors.append(item["embedding"])
        payloads.append({
            "text": item["text"],
            "subject": item.get("subject", ""),
            "from": item.get("from_addr", ""),
            "body": item.get("body", ""),
            "email_type": item.get("email_type", "email"),
        })

        if len(ids) >= 50:
            qdrant.upsert(ids, vectors, payloads)
            ids, vectors, payloads = [], [], []

    if ids:
        qdrant.upsert(ids, vectors, payloads)