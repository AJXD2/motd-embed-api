"""Tests for MOTD § code parser"""

from motd_embed_api.motd_parser import parse_motd, parse_motd_json


def test_empty_string_returns_empty():
    assert parse_motd("") == ""


def test_none_like_empty(monkeypatch):
    # The public API doesn't accept None but let's ensure falsy values work
    assert parse_motd("") == ""


def test_plain_text_wrapped_in_reset_span():
    result = parse_motd("Hello")
    assert "Hello" in result
    assert "mcformat-reset" in result


def test_color_code_green():
    result = parse_motd("§aGreen text")
    assert "mcformat-green" in result
    assert "Green text" in result


def test_bold_code():
    result = parse_motd("§lBold")
    assert "mcformat-bold" in result
    assert "Bold" in result


def test_reset_clears_all_classes():
    result = parse_motd("§aGreen§rReset")
    # After §r the text should be reset; the reset span must be present
    assert "mcformat-reset" in result


def test_color_code_changes_color_preserves_format():
    result = parse_motd("§l§aBoldGreen")
    assert "mcformat-bold" in result
    assert "mcformat-green" in result


def test_html_ampersand_escaped():
    result = parse_motd("A&B")
    assert "&amp;" in result
    assert "&B" not in result


def test_html_lt_gt_escaped():
    result = parse_motd("<script>alert(1)</script>")
    assert "&lt;script&gt;" in result
    assert "<script>" not in result


def test_html_quote_escaped():
    result = parse_motd('Say "hello"')
    assert "&quot;" in result


def test_max_length_truncation():
    long_text = "A" * 3000
    result = parse_motd(long_text, max_length=2048)
    # After escaping &→&amp; the output may be longer, but source was truncated
    assert "A" * 2049 not in result


def test_max_length_exact_passes():
    text = "B" * 2048
    result = parse_motd(text, max_length=2048)
    assert "B" in result


def test_multiple_lines_preserved():
    result = parse_motd("Line1\nLine2")
    assert "Line1" in result
    assert "Line2" in result


def test_all_color_codes_produce_spans():
    for code in "0123456789abcdef":
        result = parse_motd(f"§{code}text")
        assert "mcformat" in result


def test_all_format_codes_produce_spans():
    for code in "klmno":
        result = parse_motd(f"§{code}text")
        assert "mcformat" in result


# --- parse_motd_json ---


def test_parse_motd_json_string():
    result = parse_motd_json("plain text")
    assert "plain text" in result


def test_parse_motd_json_dict_text():
    result = parse_motd_json({"text": "Hello"})
    assert "Hello" in result


def test_parse_motd_json_dict_extra():
    result = parse_motd_json({"text": "Hello", "extra": [{"text": " World"}]})
    assert "Hello" in result
    assert "World" in result


def test_parse_motd_json_non_dict_returns_empty():
    assert parse_motd_json(42) == ""  # type: ignore[arg-type]
