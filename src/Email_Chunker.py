from src.Email_Parser import EmailParser
import spacy
from Decorators.perf_logger import auto_perf_logger

ONE_WAY_KEYWORDS = [
    "welcome", "no-reply", "noreply", "donotreply",
    "newsletter", "notification", "verify", "confirm",
    "unsubscribe", "promotion", "offer",
]


def detect_email_type(subject: str, sender: str) -> str:
    text = (subject + " " + sender).lower()
    if any(kw in text for kw in ONE_WAY_KEYWORDS):
        return "one-directional"
    return "conversational"


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
            subject = mail["subject"] or ""
            from_addr = mail["from"] or ""
            body = mail["body"]
            email_type = detect_email_type(subject, from_addr)
            sentences = list(self.spacy_sentence_split(body))

            current_chunk = ""
            for sent in sentences:
                current_chunk += sent + " "
                if len(current_chunk) >= min_chunk_size:
                    body_part = current_chunk.strip()
                    text = (
                        f"Subject: {subject}\n"
                        f"From: {from_addr}\n"
                        f"Body:\n{body_part}"
                    )
                    yield {
                        "subject": subject,
                        "from_addr": from_addr,
                        "body": body_part,
                        "text": text,
                        "email_type": email_type,
                    }
                    current_chunk = ""

            if current_chunk.strip():
                body_part = current_chunk.strip()
                text = (
                    f"Subject: {subject}\n"
                    f"From: {from_addr}\n"
                    f"Body:\n{body_part}"
                )
                yield {
                    "subject": subject,
                    "from_addr": from_addr,
                    "body": body_part,
                    "text": text,
                    "email_type": email_type,
                }








