from src.Email_Chunker import EmailChunker
import torch

from src.Email_Parser import EmailParser
from src.global_model import GLOBAL_MODEL
import time


class Email_Embedding:
    def __init__(self,chunker: EmailChunker =None):
        startINITEmail=time.time()
        self.chunker = chunker
        self.model = GLOBAL_MODEL
        # WHY: global_model.py model yüklenemezse GLOBAL_MODEL = None bırakıyor.
        # Bunu kontrol etmezsek bir sonraki satırdaki self.model.max_seq_length
        # 'NoneType has no attribute' ile patlar; main.py bunu import sırasında
        # oluşturduğu için TÜM uygulama hiç açılmaz. Net bir hata fırlatıp
        # main.py'nin bunu yakalayıp servisi yine de ayağa kaldırmasına izin veriyoruz.
        if self.model is None:
            raise RuntimeError(
                "Embedding model yüklenemedi (GLOBAL_MODEL=None). "
                "global_model.py loglarını ve CUDA/torch kurulumunu kontrol edin."
            )
        # Gerçek model cihazını (global_model.py / EMBED_DEVICE belirler) yansıt;
        # torch.cuda.is_available() yanıltıcıydı (model CPU'da olsa bile cuda basıyordu).
        # API sunucusunda bu "cpu" olmalı: LLM (llama-cpp) ile aynı GPU'da çalışınca
        # embedder bozuk/NaN vektör üretiyor.
        self.device = str(self.model.device)
        print("Embedder device:", self.device)

        self.model.max_seq_length = 1024

        torch.set_float32_matmul_precision('high')

        endINITEmail=time.time()
        print("Total time INIT email embed:",endINITEmail-startINITEmail)


    def embedding(self, batch_size):
        current_batch = []

        for email_chunk in self.chunker.parse_and_chunk():
            current_batch.append(email_chunk)

            if len(current_batch) >= batch_size:
                texts = [c["text"] for c in current_batch]
                embeddings = self.model.encode(texts, convert_to_tensor=False)
                for chunk, embedding in zip(current_batch, embeddings):
                    yield {
                        **chunk,
                        "embedding": embedding.tolist(),
                    }
                current_batch = []

        if current_batch:
            texts = [c["text"] for c in current_batch]
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            for chunk, embedding in zip(current_batch, embeddings):
                yield {
                    **chunk,
                    "embedding": embedding.tolist(),
                }
    
    def embed_anything(self, text: str, is_query: bool = False):
        # WHY: Qwen3-Embedding ASİMETRİK bir retrieval modelidir. Sorgular için
        # "query" instruction prompt'u kullanmak (Instruct: ... \nQuery: ...),
        # sorgu ve döküman vektörlerini doğru hizalar ve retrieval isabetini
        # belirgin artırır. is_query kullanmazsak alakalı chunk'lar 0.5 skor
        # eşiğinin altında kalıp hiç dönmeyebilir.
        # Dökümanlar (indeksleme) prompt'suz gömülür -> embedding() metodu.
        if is_query:
            try:
                return self.model.encode(
                    text, convert_to_tensor=False, prompt_name="query"
                )
            except (KeyError, ValueError):
                # Model "query" prompt'u tanımlamıyorsa düz encode'a düş.
                return self.model.encode(text, convert_to_tensor=False)
        return self.model.encode(text, convert_to_tensor=False)


if __name__=="__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

    start=time.time()
    startParser=time.time()
    parser = EmailParser(EMAIL_ADDRESS, EMAIL_PASSWORD)
    endParser=time.time()
    startChunking=time.time()
    chunker = EmailChunker(parser)
    endChunking=time.time()
    startChunker=time.time()
    i=0
    for chunk in chunker.parse_and_chunk(min_chunk_size=400):
        print("------------CHUNK--------------")
        print(chunk)
        i=i+1
    print("Total Chunk=",i)
    endChunker=time.time()

    startinitembed=time.time()
    embedder=Email_Embedding(chunker)
    endinitembed=time.time()
    startEmbedder=time.time()
    for item in embedder.embedding(batch_size=1024):
        print(item)
    endEmbedder=time.time()
    print("Total Embedder=",endEmbedder-startEmbedder)
    print("init embed time: ",endinitembed-startinitembed)
    end=time.time()
    print("Total time Parser", endParser-startParser)
    print("Total time Chunking", endChunking-startChunking)
    print("Total time Chunker", endChunker-startChunker)
    print("TOTAL TIME ELAPSED ",end-start)






