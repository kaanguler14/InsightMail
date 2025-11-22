from src.Email_Parser import EmailParser
import time
import spacy
nlp = spacy.load("en_core_web_sm")

class EmailChunker():
    def __init__(self, parser: EmailParser):
        self.parser = parser

    def chunk_text_fixed_size(self,text,size,overlapping):
        for i in range(0, len(text), size - overlapping):
            yield text[i:i + size]


    #def chunk_text_sentence(self,text):
    #    sentences = sent_tokenize(text)
    #    for s in sentences:
    #        yield s.strip()

    def spacy_sentence_split(self,text):
        doc = nlp(text)
        for sent in doc.sents:
            yield sent.text.strip()

    def parse_and_chunk(self,size=512,overlapping=50):
        for mail in self.parser.parse():
            body=mail["body"]
            for chunk in self.spacy_sentence_split(body):
                yield  (
                    f"Subject: {mail['subject']}\n"
                    f"Date: {mail['date']}\n"
                    f"From: {mail['from']}\n"
                    f"To: {mail['to']}\n"
                    f"Body:\n{chunk}"
                )









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

end=time.time()
print("Total time Parser", endParser-startParser)
print("Total time Chunking", endChunking-startChunking)
print("Total time Chunker", endChunker-startChunker)
print("TOTAL TIME ELAPSED ",end-start)





