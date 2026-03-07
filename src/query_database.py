import re

from llama_cpp import Llama
from src.Email_Embedding import Email_Embedding
from src.vector_database import QdrantStorage

MODEL_PATH = "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

_llm_instance = None


def get_llm():
    """Lazy-load the LLM singleton. First call loads the model (~3s), subsequent calls return cached instance."""
    global _llm_instance
    if _llm_instance is None:
        print("Loading local LLM...")
        _llm_instance = Llama(
            model_path=MODEL_PATH,
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose=False
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
        else:
            task = (
                "Answer the question using only the sources. "
                "Cite sources inline like [SOURCE 1]. "
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
        query_vec = embedder.embed_anything(query).tolist()

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
