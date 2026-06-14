"""src/query_database.py içindeki saf prompt/yardımcı fonksiyon testleri.

query_database modülü artık llama_cpp ve torch'u tembel import ettiği için
bu testler ağır ML bağımlılıkları olmadan çalışır.
"""
from src.query_database import (
    extract_llm_text,
    _is_one_directional,
    format_sources,
    _clean_one_directional_answer,
    build_prompt,
)


def test_extract_llm_text_valid():
    resp = {"choices": [{"text": "  hello  "}]}
    assert extract_llm_text(resp) == "hello"


def test_extract_llm_text_malformed_returns_empty():
    assert extract_llm_text({}) == ""
    assert extract_llm_text({"choices": []}) == ""
    assert extract_llm_text(None) == ""


def test_is_one_directional_by_explicit_type():
    assert _is_one_directional({"email_type": "one-directional"}) is True
    assert _is_one_directional({"email_type": "conversational"}) is False


def test_is_one_directional_by_keyword_fallback():
    # type yok -> subject/from'dan çıkarım
    assert _is_one_directional({"subject": "Newsletter: weekly digest"}) is True
    assert _is_one_directional({"from": "no-reply@shop.com"}) is True
    assert _is_one_directional({"subject": "Re: project meeting", "from": "ali@firma.com"}) is False


def test_format_sources_empty():
    assert format_sources([]) == ""


def test_format_sources_contains_fields():
    out = format_sources([
        {"id": 1, "subject": "Hi", "from": "a@x.com", "body": "Body text", "email_type": "email"},
    ])
    assert "[SOURCE 1]" in out
    assert "Subject: Hi" in out
    assert "From: a@x.com" in out
    assert "Body text" in out


def test_build_prompt_no_sources():
    prompt, all_one = build_prompt([], "ne zaman?")
    assert all_one is False
    assert "do not contain enough information" in prompt
    assert "ne zaman?" in prompt


def test_build_prompt_conversational():
    sources = [{"id": 1, "subject": "Re: toplantı", "from": "ali@firma.com", "body": "Yarın 10'da", "email_type": "conversational"}]
    prompt, all_one = build_prompt(sources, "toplantı kaçta?")
    assert all_one is False
    assert "Answer the question using only the sources" in prompt
    assert "[SOURCE 1]" in prompt


def test_build_prompt_all_one_directional():
    sources = [{"id": 1, "subject": "Welcome to Acme", "from": "no-reply@acme.com", "body": "Hoş geldiniz", "email_type": "one-directional"}]
    prompt, all_one = build_prompt(sources, "ne diyor?")
    assert all_one is True
    assert "one-directional" in prompt


def test_clean_one_directional_answer_reformats_citation():
    raw = "[SOURCE 1] is a welcome email from Acme. It greets the user."
    out = _clean_one_directional_answer(raw)
    assert out.startswith("• Acme:")
    assert "It greets the user." in out


def test_clean_one_directional_answer_passthrough_when_no_match():
    raw = "Some unrelated answer."
    assert _clean_one_directional_answer(raw) == "Some unrelated answer."
