from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

# WHY: llama_cpp ve Email_Embedding/QdrantStorage (torch + sentence-transformers
# zincirini ve model yüklemesini tetikler) modül seviyesinde import edilirse,
# bu dosyadaki saf fonksiyonları (build_prompt, format_sources vb.) test etmek
# için bu ağır bağımlılıkların kurulu olması gerekir. Importları tembelleştirip
# tip ipuçlarını TYPE_CHECKING altına alarak modülü hafif ve test edilebilir
# tutuyoruz.
if TYPE_CHECKING:
    from src.Email_Embedding import Email_Embedding
    from src.vector_database import QdrantStorage

from src.config import LLM_MODEL_PATH, LLM_N_CTX

_llm_instance = None


def get_llm():
    """Lazy-load the LLM singleton. First call loads the model (~3s), subsequent calls return cached instance."""
    global _llm_instance
    if _llm_instance is None:
        from llama_cpp import Llama  # ağır import: yalnızca gerçekten gerekince

        print("Loading local LLM...")
        _llm_instance = Llama(
            model_path=LLM_MODEL_PATH,
            n_ctx=LLM_N_CTX,
            n_gpu_layers=-1,
            n_batch=2048,
            n_threads=4,
            flash_attn=False,
            verbose=False,
        )
        print("Local LLM loaded.")
    return _llm_instance


def extract_llm_text(response: dict) -> str:
    """Safely extract text from llama-cpp response."""
    try:
        return response["choices"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        return ""


# Chunker ile aynı mantık — eski index'te email_type yoksa subject/from'dan çıkarım
ONE_WAY_KEYWORDS = [
    "welcome", "no-reply", "noreply", "donotreply",
    "newsletter", "notification", "verify", "confirm",
    "unsubscribe", "promotion", "offer",
]


def _is_one_directional(source: dict) -> bool:
    """Payload'daki email_type varsa ona göre, yoksa subject+from'dan çıkar."""
    t = source.get("email_type", "").strip().lower()
    if t == "one-directional":
        return True
    if t == "conversational":
        return False
    subject = (source.get("subject") or "").lower()
    from_addr = (source.get("from") or "").lower()
    text = subject + " " + from_addr
    return any(kw in text for kw in ONE_WAY_KEYWORDS)


def format_sources(sources: list[dict]) -> str:
    """
    Each source is a dict with id, subject, from, body, text, email_type.
    """
    if not sources:
        return ""
    chunks = []
    for s in sources:
        email_type = s.get("email_type", "email")
        subject = s.get("subject", "")
        from_addr = s.get("from", "")
        body = s.get("body", s.get("text", ""))
        chunks.append(
            f"[SOURCE {s['id']}] (type: {email_type})\n"
            f"Subject: {subject}\n"
            f"From: {from_addr}\n"
            f"Body:\n{body}"
        )
    return "\n\n".join(chunks)


def _clean_one_directional_answer(answer: str) -> str:
    """Reformat [SOURCE N] citation into a readable bullet point."""
    pattern = r"\[SOURCE \d+\]\s*is a\s+(?:welcome email|promotional email|newsletter)\s+from\s+([^\.]+)\.\s*"
    return re.sub(pattern, r"• \1: ", answer, count=1).strip() or answer


# Soru mu yoksa salt konu/anahtar-kelime mi? "football" gibi kısa girdilerde model
# "soruyu cevapla" modunda kalıp bazen "yeterli bilgi yok" diyordu (sampling non-deterministik).
# Kararı Python verir: konu sorgularına reddetme seçeneği OLMAYAN "özetle" görevi verilir.
_QUESTION_WORDS = {
    "what", "why", "how", "when", "who", "where", "which", "whose", "whom",
    "is", "are", "was", "were", "do", "does", "did", "can", "could", "should",
    "would", "will", "may", "might", "summarize", "summarise", "list", "tell",
    "give", "show", "find", "explain", "describe",
}


def _looks_like_topic(query: str) -> bool:
    """Salt konu/anahtar-kelime (ör. 'football') mi, yoksa gerçek soru/komut mu?"""
    q = query.strip()
    if not q or "?" in q:
        return False
    words = re.findall(r"\w+", q.lower())
    if not words or len(words) > 4:
        return False
    return not any(w in _QUESTION_WORDS for w in words)


def build_prompt(sources: list[dict], query: str) -> tuple[str, bool]:
    """Python decides the task from email_type; model gets one simple instruction. Returns (prompt, all_one_directional)."""
    all_one_directional = False
    if not sources:
        task = (
            "Say: 'The provided sources do not contain enough information to answer this question.'"
        )
        context_text = ""
    else:
        all_one_directional = all(_is_one_directional(s) for s in sources)
        context_text = format_sources(sources)

        if all_one_directional:
            task = (
                "The sources are one-directional emails (welcome emails, promotions, etc.). "
                "For each source, write exactly: '[SOURCE X] is a [welcome email / promotional email / newsletter] "
                "from [sender]. ' followed by one sentence summarizing what it says. "
                "Do not answer the question directly."
            )
        elif _looks_like_topic(query):
            task = (
                "The input is a topic or keyword, not a full question. Write a few sentences "
                "summarizing what the sources say about this topic, citing them inline like "
                "[SOURCE 1]. Start your very first sentence with a concrete fact from the "
                "sources. Do NOT open with any preamble, hedge, or meta-commentary — for "
                "example do not begin with phrases like 'There is no clear answer', 'Based on "
                "the sources', 'The sources discuss', or 'It appears that'. Never add a "
                "disclaimer about missing information."
            )
        else:
            task = (
                "Answer the question using only the sources, citing them inline like [SOURCE 1]. "
                "If the answer is not in the sources, say: "
                "'The provided sources do not contain enough information to answer this question.'"
            )

    prompt = (
        "<|start_header_id|>system<|end_header_id|>\n\n"
        f"You are a precise question-answering assistant. {task}\n"
        "<|eot_id|>\n"
        "<|start_header_id|>user<|end_header_id|>\n\n"
        "## Sources\n"
        f"{context_text}\n\n"
        "## Question\n"
        f"{query}\n\n"
        "## Answer:\n"
        "<|eot_id|>\n"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    return prompt, all_one_directional


def local_api_llm(query: str, qdrant_storage: QdrantStorage, embedder: Email_Embedding, top_k=3):

    try:
        query_vec = embedder.embed_anything(query, is_query=True).tolist()

        results = qdrant_storage.search(query_vector=query_vec, top_k=top_k)

        contexts = results["contexts"]
        sources = results["sources"]
        sources_structured = results.get("sources_structured", [])

        prompt, all_one_directional = build_prompt(sources_structured, query)

        response = get_llm()(
            prompt,
            max_tokens=512,
            stop=["<|eot_id|>"],
            echo=False
        )

        answer = extract_llm_text(response)
        if not answer:
            answer = "Could not generate a response."
        elif all_one_directional:
            answer = _clean_one_directional_answer(answer)

        return {
            "answer": answer,
            "sources": sources,
            "context_used": contexts
        }

    except ConnectionError as e:
        return {"error": f"Database connection error: {e}"}
    except Exception as e:
        return {"error": f"LLM query error: {e}"}


def _sse(event: str, data: dict) -> str:
    """Server-Sent Events tek mesaj biçimi."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def local_api_llm_stream(query: str, qdrant_storage: QdrantStorage, embedder: Email_Embedding, top_k=3):
    """RAG cevabını token token (SSE) akıtan jeneratör.

    WHY: Bloklayan /search ucu 5-15 sn boyunca kullanıcıya boş ekran gösteriyordu.
    Streaming ile önce kaynaklar, ardından cevap token token gönderilir; kullanıcı
    ilerlemeyi anında görür. Olay sırası: sources -> token* -> done (veya error).
    'done' olayında, doğruluk için nihai (gerekirse temizlenmiş) cevabın tamamı
    yollanır; frontend canlı akışı bununla değiştirir.
    """
    try:
        query_vec = embedder.embed_anything(query, is_query=True).tolist()
        results = qdrant_storage.search(query_vector=query_vec, top_k=top_k)

        contexts = results["contexts"]
        sources = results["sources"]
        sources_structured = results.get("sources_structured", [])

        yield _sse("sources", {"contexts": contexts, "sources": sources})

        prompt, all_one_directional = build_prompt(sources_structured, query)

        stream = get_llm()(
            prompt,
            max_tokens=512,
            stop=["<|eot_id|>"],
            echo=False,
            stream=True,
        )

        parts = []
        for chunk in stream:
            # Akışta her parça bir delta'dır; strip ETME (anlamlı boşluklar kaybolur).
            try:
                piece = chunk["choices"][0]["text"]
            except (KeyError, IndexError, TypeError):
                piece = ""
            if piece:
                parts.append(piece)
                yield _sse("token", {"text": piece})

        answer = "".join(parts).strip()
        if not answer:
            answer = "Could not generate a response."
        elif all_one_directional:
            answer = _clean_one_directional_answer(answer)

        yield _sse("done", {"answer": answer, "sources": sources, "contexts": contexts})

    except ConnectionError as e:
        yield _sse("error", {"detail": f"Database connection error: {e}"})
    except Exception as e:
        yield _sse("error", {"detail": f"LLM query error: {e}"})
