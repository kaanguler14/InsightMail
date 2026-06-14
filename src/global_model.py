from sentence_transformers import SentenceTransformer
import torch
import time

from src.config import EMBED_MODEL_NAME

MODEL_NAME = EMBED_MODEL_NAME
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

try:
    print("Loading model...")
    start_time = time.time()
    GLOBAL_MODEL = SentenceTransformer(MODEL_NAME, device=DEVICE, model_kwargs={'torch_dtype': torch.float16})
    MODEL_DIMENSION = GLOBAL_MODEL.get_sentence_embedding_dimension()
    end_time = time.time()
    print(f"Model loaded in {end_time - start_time:.2f} seconds")
except Exception as e:
    print(f"Failed to load embedding model: {e}")
    GLOBAL_MODEL = None
    MODEL_DIMENSION = 1024