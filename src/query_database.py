from llama_cpp import Llama
from src.Email_Embedding import Email_Embedding
from src.vector_database import QdrantStorage

MODEL_PATH = "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

print("Loading local LLM...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_gpu_layers=-1,
    verbose=False
)
print("Local LLM loaded.")


def local_api_llm(query: str, qdrant_storage: QdrantStorage, embedder: Email_Embedding, top_k=3):

    try:
        query_vec = embedder.embed_anything(query).tolist()

        results = qdrant_storage.search(query_vector=query_vec, top_k=top_k)

        contexts = results["contexts"]
        sources = results["sources"]

        context_text = "\n".join(contexts) if contexts else "İlgili bir şey bulunamadı"

        prompt = (
            "<|start_header_id|>system<|end_header_id|>\n"
            "Sen yardımsever bir asistansın. Aşağıdaki bağlama göre kullanıcının sorusunu türkçe olarak yanıtla. "
            "Kaynaklara dayanarak tutarlı bir şekilde cevap ver.\n"
            "<|eot_id|>\n"
            "<|start_header_id|>user<|end_header_id|>\n"
            f"--Bağlam--\n{context_text}\n\n"
            f"--Soru--\n{query}\n"
            "<|eot_id|>\n"
            "<|start_header_id|>assistant<|end_header_id|>\n"
        )

        response = llm(
            prompt,
            max_tokens=512,
            stop=["<|eot_id|>"],
            echo=False
        )

        answer = response["choices"][0]["text"].strip()

        return {
            "answer": answer,
            "sources": sources,
            "context_used": contexts
        }

    except Exception as e:
        return {"error": e}
