from src.Email_Parser import EmailParser
import time
import spacy
nlp = spacy.load("en_core_web_sm")
from Decorators.Email_Chunker_Decorator import auto_perf_logger

@auto_perf_logger
class EmailChunker():
    def __init__(self, parser: EmailParser):
        self.parser = parser
        self.parse_and_chunk()

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















