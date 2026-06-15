from sentence_transformers import SentenceTransformer
import torch
import time

from src.config import EMBED_MODEL_NAME, EMBED_DEVICE

MODEL_NAME = EMBED_MODEL_NAME
# EMBED_DEVICE override edilmişse ona uy; yoksa otomatik (cuda varsa cuda).
if EMBED_DEVICE:
    DEVICE = torch.device(EMBED_DEVICE)
else:
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# fp16 yalnızca CUDA'da hızlı/anlamlı; CPU'da fp32 kullan (fp16 CPU'da yavaş ve
# bazı op'lar desteklenmez).
_EMBED_DTYPE = torch.float16 if DEVICE.type == "cuda" else torch.float32

try:
    print("Loading model...")
    start_time = time.time()
    GLOBAL_MODEL = SentenceTransformer(MODEL_NAME, device=DEVICE, model_kwargs={'torch_dtype': _EMBED_DTYPE})
    MODEL_DIMENSION = GLOBAL_MODEL.get_sentence_embedding_dimension()
    end_time = time.time()
    print(f"Model loaded in {end_time - start_time:.2f} seconds")
except Exception as e:
    print(f"Failed to load embedding model: {e}")
    GLOBAL_MODEL = None
    MODEL_DIMENSION = 1024