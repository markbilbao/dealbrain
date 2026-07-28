"""Unit tests for product title tokenization."""

from app.intelligence.product_parser.tokenizer import normalize_text, tokenize


def test_normalize_collapses_whitespace() -> None:
    assert normalize_text("  Apple   IP17PM  ") == "Apple IP17PM"


def test_tokenize_keeps_compound_codes_intact() -> None:
    tokens = tokenize("Apple IP17PM 256 BT")
    assert [t.normalized for t in tokens] == ["apple", "ip17pm", "256", "bt"]


def test_tokenize_splits_on_separators() -> None:
    tokens = tokenize("Apple / iPhone 17, 256GB | Black")
    assert [t.normalized for t in tokens] == [
        "apple",
        "iphone",
        "17",
        "256gb",
        "black",
    ]


def test_tokenize_empty_string() -> None:
    assert tokenize("") == []
    assert tokenize("   ") == []
