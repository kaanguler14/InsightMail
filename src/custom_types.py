from pydantic import BaseModel, Field
from typing import List, Optional

# WHY: top_k / limit kullanıcı girdisidir ve doğrudan retrieval/IMAP yüküne dönüşür.
# Üst sınır olmadan çok büyük bir değer bellek/işlem tüketimine veya IMAP sağlayıcısını
# zorlamaya (DoS sınıfı) yol açabilir. Pydantic ile makul aralıklara sıkıştırıyoruz.


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


class RAGResponse(BaseModel):
    answer: Optional[str] = None
    contexts: List[str] = []
    sources: List[str] = []


class SummarizeRequest(BaseModel):
    contact_email: str
    limit: int = Field(default=15, ge=1, le=100)


class EmailItem(BaseModel):
    subject: str = ""
    date: str = ""
    direction: str = ""
    from_addr: str = ""
    to_addr: str = ""
    body_preview: str = ""


class SummarizeResponse(BaseModel):
    summary: str = ""
    emails: List[EmailItem] = []


class ContactItem(BaseModel):
    email: str
    name: str = ""
    last_date: str = ""
    direction: str = ""


class RecentContactsResponse(BaseModel):
    contacts: List[ContactItem] = []


class ReplyRequest(BaseModel):
    contact_email: str
    tone: str = "friendly"


class ReplySuggestion(BaseModel):
    tone: str = ""
    subject: str = ""
    body: str = ""


class ReplyResponse(BaseModel):
    original_email: EmailItem = EmailItem()
    suggestions: List[ReplySuggestion] = []
    
