from pydantic import BaseModel
from typing import List, Dict, Any

class SearchRequest(BaseModel):
    query: str
    top_k: int =5

class SearchResult(BaseModel):
    answer:str
    contexts: List[str]
    sources: List[str]
    search_time_ms:float

