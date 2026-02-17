from src.Email_Parser import EmailParser
import spacy
from Decorators.perf_logger import auto_perf_logger


@auto_perf_logger
class EmailChunker():
    _nlp = None

    def __init__(self, parser: EmailParser):
        self.parser = parser
        if EmailChunker._nlp is None:
            EmailChunker._nlp = spacy.load("en_core_web_sm")

    def spacy_sentence_split(self, text):
        doc = self._nlp(text)
        for sent in doc.sents:
            yield sent.text.strip()

    def parse_and_chunk(self, min_chunk_size=200):
        for mail in self.parser.parse():
            body = mail["body"]
            sentences = list(self.spacy_sentence_split(body))

            current_chunk = ""
            for sent in sentences:
                current_chunk += sent + " "
                if len(current_chunk) >= min_chunk_size:
                    yield (
                        f"Subject: {mail['subject']}\n"
                        f"From: {mail['from']}\n"
                        f"Body:\n{current_chunk.strip()}"
                    )
                    current_chunk = ""

            if current_chunk.strip():
                yield (
                    f"Subject: {mail['subject']}\n"
                    f"From: {mail['from']}\n"
                    f"Body:\n{current_chunk.strip()}"
                )












