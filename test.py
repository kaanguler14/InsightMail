from sentence_transformers import SentenceTransformer
import torch
import time


MODEL_NAME = 'Qwen/Qwen3-Embedding-0.6B'
DEVICE  = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print("Loading model...")
start_time = time.time()
GLOBAL_MODEL=SentenceTransformer(MODEL_NAME,device = DEVICE )

print(GLOBAL_MODEL)