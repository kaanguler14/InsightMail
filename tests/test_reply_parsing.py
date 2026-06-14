"""src/reply_suggester.py içindeki _parse_llm_replies fonksiyonunun testleri."""
from src.reply_suggester import _parse_llm_replies


def test_parse_three_well_formed_replies():
    text = (
        "REPLY 1:\n"
        "Subject: Re: Toplantı\n"
        "Body: Tabii, yarın 10:00 uygun.\n\n"
        "REPLY 2:\n"
        "Subject: Re: Toplantı\n"
        "Body: 11:00'a alabilir miyiz?\n\n"
        "REPLY 3:\n"
        "Subject: Re: Toplantı\n"
        "Body: Maalesef yarın müsait değilim.\n"
    )
    out = _parse_llm_replies(text)
    assert len(out) == 3
    assert out[0]["subject"] == "Re: Toplantı"
    assert "yarın 10:00 uygun" in out[0]["body"]
    assert "11:00" in out[1]["body"]


def test_parse_caps_at_three():
    text = "".join(
        f"REPLY {i}:\nSubject: S{i}\nBody: B{i}\n\n" for i in range(1, 6)
    )
    out = _parse_llm_replies(text)
    assert len(out) == 3


def test_parse_without_markers_uses_block_as_body():
    text = "Just a single freeform reply without markers."
    out = _parse_llm_replies(text)
    assert len(out) == 1
    assert out[0]["body"] == "Just a single freeform reply without markers."
    assert out[0]["subject"] == ""


def test_parse_empty_input():
    assert _parse_llm_replies("") == []
