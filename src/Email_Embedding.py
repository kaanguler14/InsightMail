from torch.fx.experimental.unification.unification_tools import first

from src.Email_Chunker import EmailChunker
from sentence_transformers import SentenceTransformer
import torch

from src.Email_Parser import EmailParser
from src.global_model import  GLOBAL_MODEL
from src.global_model import  t
MODEL_NAME="Qwen/Qwen3-Embedding-0.6B"
import time


class Email_Embedding:
    def __init__(self,chunker: EmailChunker,model_name):
        startINITEmail=time.time()
        self.chunker = chunker
        self.device="cuda" if torch.cuda.is_available() else "cpu"
        print("Device:",self.device)
        print(torch.cuda.is_available())
        self.model = GLOBAL_MODEL
        self.model.max_seq_length = 1024

        torch.set_float32_matmul_precision('high')
        #LINUX
        #transformer = self.model[0]  # (0): Transformer
        #hf_model = transformer.auto_model  # gerçek Qwen3 HF modeli
#
        ## ---- Compile ONLY HF model ----
        #hf_model.forward = torch.compile(hf_model.forward)
#

        endINITEmail=time.time()
        print("Total time INIT emal embed:",endINITEmail-startINITEmail)


    def embedding(self,batch_size):

        current_email=[]

        for email_chunk in self.chunker.parse_and_chunk():
            current_email.append(email_chunk)

            if len(current_email) >= batch_size:
                embeddings = self.model.encode(current_email,convert_to_tensor=False)

                for text , embedding in zip(current_email, embeddings):
                    yield {
                        "text": text,
                        "embedding": embedding.tolist()
                    }

                current_email=[]

        if current_email:
            embeddings = self.model.encode(current_email,convert_to_tensor=False)
            for text , embedding in zip(current_email, embeddings):
                yield {
                    "text": text,
                    "embedding": embedding.tolist()

                }



start=time.time()
startParser=time.time()
parser = EmailParser("kaangulergs@gmail.com", "ioue gqpu aekc zcbj")
endParser=time.time()
startChunking=time.time()
chunker = EmailChunker(parser)
endChunking=time.time()
startChunker=time.time()
i=0
for chunk in chunker.parse_and_chunk(size=400):
    print("------------CHUNK--------------")
    print(chunk)
    i=i+1
print("Total Chunk=",i)
endChunker=time.time()

startinitembed=time.time()
embedder=Email_Embedding(chunker,MODEL_NAME)
endinitembed=time.time()
startEmbedder=time.time()
for item in embedder.embedding(batch_size=1024):
    print(item)
endEmbedder=time.time()
print("Total Embedder=",endEmbedder-startEmbedder)
print("init embed time: ",endinitembed-startinitembed)
end=time.time()
print("total loader",t)
print("Total time Parser", endParser-startParser)
print("Total time Chunking", endChunking-startChunking)
print("Total time Chunker", endChunker-startChunker)
print("TOTAL TIME ELAPSED ",end-start)






