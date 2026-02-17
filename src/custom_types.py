from pydantic import BaseModel
from typing import List, Optional


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    answer: str
    contexts: List[str]
    sources: List[str]
    search_time_ms: float


class RAGResponse(BaseModel):
    answer: Optional[str] = None
    contexts: List[str] = []
    sources: List[str] = []


class SummarizeRequest(BaseModel):
    contact_email: str
    limit: int = 15


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
    
