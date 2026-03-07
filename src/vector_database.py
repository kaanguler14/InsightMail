import logging

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams , Distance , PointStruct

logger = logging.getLogger(__name__)


class QdrantStorage:
    def __init__(self, url="http://localhost:6333", collection="emails", dim=1024):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        
        # Check if collection exists
        if self.client.collection_exists(self.collection):
            # Get existing config
            collection_info = self.client.get_collection(self.collection)
            existing_dim = collection_info.config.params.vectors.size
            
            # If dimensions don't match, DELETE the collection to avoid errors
            if existing_dim != dim:
                logger.warning(
                    "DIMENSION MISMATCH: deleting collection '%s' (old=%d, new=%d). All data will be lost!",
                    self.collection, existing_dim, dim,
                )
                self.client.delete_collection(self.collection)
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
                )
        else:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def upsert(self,ids,vectors,payloads):
        points=[PointStruct(id=ids[i],vector=vectors[i],payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(self.collection,points=points)


    def _deduplicate_by_email(self, points: list) -> list:
        """Keep only the highest-scoring point per (subject, from)."""
        seen = {}
        for point in points:
            payload = getattr(point, "payload", None) or {}
            key = (payload.get("subject", ""), payload.get("from", ""))
            score = getattr(point, "score", 0.0) or 0.0
            if key not in seen or score > getattr(seen[key], "score", 0.0):
                seen[key] = point
        return list(seen.values())

    def search(self, query_vector, top_k: int = 5):
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k * 3,
            with_payload=True,
            score_threshold=0.5,
        )
        points = self._deduplicate_by_email(response.points)
        points = points[:top_k]

        contexts = []
        sources = set()
        sources_structured = []
        for i, point in enumerate(points):
            payload = getattr(point, "payload", None) or {}
            text = payload.get("text", "")
            subject = payload.get("subject", "")
            from_addr = payload.get("from", "")
            body = payload.get("body", "")
            # Eski index: payload'da sadece text var; Subject:/From:/Body: formatından çıkar
            if text and (not subject or not from_addr):
                lines = text.split("\n")
                for line in lines:
                    if line.startswith("Subject:"):
                        subject = line[8:].strip()
                    elif line.startswith("From:"):
                        from_addr = line[5:].strip()
                if "Body:" in text:
                    body = text.split("Body:", 1)[-1].strip()
            if text:
                contexts.append(text)
                sources.add(from_addr)
                sources_structured.append({
                    "id": i + 1,
                    "subject": subject,
                    "from": from_addr,
                    "body": body or text,
                    "text": text,
                    "email_type": payload.get("email_type", "email"),
                })
        return {
            "contexts": contexts,
            "sources": list(sources),
            "sources_structured": sources_structured,
        }