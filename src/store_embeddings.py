import os
import uuid
from dotenv import load_dotenv
from src.global_model import MODEL_DIMENSION
from src.vector_database import QdrantStorage
from src.Email_Parser import EmailParser
from src.Email_Chunker import EmailChunker
from src.Email_Embedding import Email_Embedding

load_dotenv()

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise RuntimeError("EMAIL_ADDRESS and EMAIL_PASSWORD must be set in .env")

qdrant = QdrantStorage(
    url="http://localhost:6333",
    collection="emails",
    dim=MODEL_DIMENSION,
)

with EmailParser(EMAIL_ADDRESS, EMAIL_PASSWORD) as parser:
    chunker = EmailChunker(parser)
    embedder = Email_Embedding(chunker)

    ids = []
    vectors = []
    payloads = []

    for item in embedder.embedding(batch_size=1024):
        ids.append(str(uuid.uuid4()))
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