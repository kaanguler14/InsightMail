"""src/email_utils.py içindeki saf yardımcı fonksiyonların testleri.

Bu testler ağır ML bağımlılıkları (torch, sentence-transformers, llama_cpp)
gerektirmez; yalnızca stdlib + beautifulsoup4 yeterlidir.
"""
from email.message import EmailMessage

from src.email_utils import (
    decode_email_header,
    clean_html,
    extract_body,
    parse_contact_emails,
    build_reply_context,
    is_valid_email,
)


def test_is_valid_email_accepts_normal_addresses():
    assert is_valid_email("ali@firma.com")
    assert is_valid_email("a.b+tag@sub.example.co.uk")
    assert is_valid_email("  spaced@x.com  ")  # strip edilir


def test_is_valid_email_rejects_malformed_and_injection():
    assert not is_valid_email("")
    assert not is_valid_email(None)
    assert not is_valid_email("notanemail")
    assert not is_valid_email("no-domain@")
    assert not is_valid_email("a b@x.com")          # boşluk
    # IMAP arama enjeksiyonu denemeleri: tırnak/kontrol karakteri reddedilmeli
    assert not is_valid_email('x" BODY "secret@x.com')
    assert not is_valid_email('a@x.com" OR "1"="1')
    assert not is_valid_email('a@x.com\r\nX-Inject: 1')


def test_decode_email_header_plain():
    assert decode_email_header("Hello World") == "Hello World"


def test_decode_email_header_empty():
    assert decode_email_header("") == ""
    assert decode_email_header(None) == ""


def test_decode_email_header_encoded_utf8():
    # RFC 2047 encoded-word (Türkçe karakterli konu)
    encoded = "=?utf-8?b?TWVyaGFiYSBEw7xueWE=?="  # "Merhaba Dünya"
    assert decode_email_header(encoded) == "Merhaba Dünya"


def test_clean_html_strips_tags_and_scripts():
    html = "<html><body><p>Hello</p><script>alert(1)</script> world</body></html>"
    out = clean_html(html)
    assert "Hello" in out
    assert "world" in out
    assert "alert" not in out
    assert "<" not in out


def test_clean_html_collapses_whitespace_and_nbsp():
    html = "a\xa0\xa0b   c\n\n\nd"
    assert clean_html(html) == "a b c d"


def test_clean_html_empty():
    assert clean_html("") == ""
    assert clean_html(None) == ""


def _make_message(from_addr, to_addr, subject, body, content_type="plain"):
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = "Mon, 01 Jan 2024 12:00:00 +0000"
    if content_type == "html":
        msg.set_content("fallback")
        msg.add_alternative(f"<p>{body}</p>", subtype="html")
    else:
        msg.set_content(body)
    return msg


def test_extract_body_plain():
    msg = _make_message("a@x.com", "b@y.com", "Hi", "This is the body.")
    assert "This is the body." in extract_body(msg)


def test_extract_body_html_prefers_html_cleaned():
    msg = _make_message("a@x.com", "b@y.com", "Hi", "Bold body", content_type="html")
    out = extract_body(msg)
    assert "Bold body" in out
    assert "<p>" not in out


def test_parse_contact_emails_truncates_body():
    long_body = "x" * 1000
    msg = _make_message("a@x.com", "b@y.com", "Subj", long_body)
    parsed = parse_contact_emails(
        [{"message": msg, "direction": "gelen"}], max_body_chars=100
    )
    assert len(parsed) == 1
    item = parsed[0]
    assert item["direction"] == "gelen"
    assert item["subject"] == "Subj"
    assert item["body"].endswith("...")
    # 100 karakter + "..." eki
    assert len(item["body"]) == 103


def test_build_reply_context_labels_me_and_them():
    parsed = [
        {"direction": "gelen", "date": "d2", "subject": "s2", "body": "Soru?"},
        {"direction": "giden", "date": "d1", "subject": "s1", "body": "Cevap."},
    ]
    ctx = build_reply_context(parsed, my_email="me@x.com", contact_email="them@y.com")
    assert "[ME (me@x.com)]" in ctx
    assert "[THEM (them@y.com)]" in ctx
    # build_reply_context en eskiden yeniye (reversed) sıralar:
    # listenin son elemanı (giden) önce gelmeli
    assert ctx.index("[ME (me@x.com)]") < ctx.index("[THEM (them@y.com)]")
    assert "---" in ctx
