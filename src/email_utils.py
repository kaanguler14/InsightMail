import re
from bs4 import BeautifulSoup
from email.header import decode_header

MAX_BODY_CHARS = 400


def decode_email_header(header_value):
    """Decode an email header (subject, from, to)."""
    if not header_value:
        return ""
    try:
        parts = []
        for s, charset in decode_header(header_value):
            if isinstance(s, bytes):
                charset = charset or "utf-8"
                parts.append(s.decode(charset, errors="ignore"))
            else:
                parts.append(s)
        return "".join(parts)
    except Exception:
        return str(header_value)


def clean_html(html):
    """Strip HTML tags and clean whitespace."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r'[\xad\u200b\u200c\u200d\uFEFF]', '', text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_body(mail_item):
    """Extract plain text body from an email message."""
    html_content = None
    plain_content = None

    if mail_item.is_multipart():
        for part in mail_item.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            cd = part.get('Content-Disposition')
            if cd and cd.startswith('attachment'):
                continue
            content_type = part.get_content_type()
            try:
                raw = part.get_payload(decode=True)
                if raw is None:
                    continue
                payload = raw.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue
            if content_type == "text/html":
                html_content = payload
            elif content_type == "text/plain" and not plain_content:
                plain_content = payload

    if html_content:
        return clean_html(html_content)
    if plain_content:
        return clean_html(plain_content)
    try:
        raw = mail_item.get_payload(decode=True)
        if raw:
            return clean_html(raw.decode("utf-8", errors="ignore").strip())
    except Exception:
        pass
    return ""


def parse_contact_emails(raw_emails, max_body_chars=MAX_BODY_CHARS):
    """Parse raw email messages into structured dicts with direction info."""
    parsed = []
    for item in raw_emails:
        msg = item["message"]
        direction = item["direction"]

        subject = decode_email_header(msg.get("Subject", ""))
        from_addr = decode_email_header(msg.get("From", ""))
        to_addr = decode_email_header(msg.get("To", ""))
        date = msg.get("Date", "")
        body = extract_body(msg)

        if len(body) > max_body_chars:
            body = body[:max_body_chars] + "..."

        parsed.append({
            "subject": subject,
            "from": from_addr,
            "to": to_addr,
            "date": date,
            "body": body,
            "direction": direction,
        })

    return parsed


def build_conversation_text(parsed_emails):
    """Build a chronological conversation string for LLM context (oldest first)."""
    lines = []
    for m in reversed(parsed_emails):
        arrow = ">>" if m["direction"] == "giden" else "<<"
        lines.append(f"[{m['date']}] {arrow} Subject: {m['subject']}\n{m['body']}")
    return "\n---\n".join(lines)


def build_reply_context(parsed_emails, my_email, contact_email):
    """Build conversation text with clear ME/THEM labels for reply generation (oldest first)."""
    lines = []
    for m in reversed(parsed_emails):
        if m["direction"] == "giden":
            sender_label = f"[ME ({my_email})]"
        else:
            sender_label = f"[THEM ({contact_email})]"
        lines.append(
            f"{sender_label} Date: {m['date']}\n"
            f"Subject: {m['subject']}\n"
            f"{m['body']}"
        )
    return "\n---\n".join(lines)
