from vector_database import QdrantStorage
from src.Email_Parser import EmailParser
from src.Email_Chunker import EmailChunker
from src.Email_Embedding import Email_Embedding

qdrant = QdrantStorage(
    url="http://localhost:6333",
    collection="emails",
    dim=1024
)
parser = EmailParser("","")
chunker = EmailChunker(parser)
embedder = Email_Embedding(chunker,'Qwen/Qwen3-Embedding-0.6B')


ids =[]
vector=[]
payloads=[]

counter=0

for item in embedder.embedding(batch_size=1024):

    ids.append(counter)
    vector.append(item["embedding"])
    payloads.append({"text":item["text"],
                     "source":item["source"]})
    counter+=1

    if len(ids)>=100:
        qdrant.upsert(ids,vector,payloads)
        ids,vectors,payloads=[],[],[]

if ids:
    qdrant.upsert(ids,vector,payloads)