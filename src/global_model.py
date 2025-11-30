from sentence_transformers import SentenceTransformer
import torch
import time
MODEL_NAME = 'Qwen/Qwen3-Embedding-0.6B'
DEVICE  = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print("Loading model...")
start_time = time.time()
GLOBAL_MODEL=SentenceTransformer(MODEL_NAME,device = DEVICE ,model_kwargs={'torch_dtype': torch.float16})
end_time = time.time()
t=end_time-start_time
print("Model loaded in {:.2f} seconds".format(end_time - start_time))