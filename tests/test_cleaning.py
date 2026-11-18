"""Tests for format-independent text cleaning."""
from app.ingestion.cleaning import clean_text


def test_strips_blank_lines_at_ends():
    assert clean_text("\n# Title\nText\n") == "# Title\nText"


def test_collapses_double_spaces_inside_line():
    assert clean_text("SEV1  Customer-facing outage") == "SEV1 Customer-facing outage"


def test_keeps_leading_indentation():
    text = "- item\n  - sub item"
    assert clean_text(text) == text


def test_removes_trailing_spaces():
    assert clean_text("Text   \nMore") == "Text\nMore"


def test_collapses_many_blank_lines():
    assert clean_text("A\n\n\n\nB") == "A\n\nB"


def test_keeps_single_blank_line():
    assert clean_text("A\n\nB") == "A\n\nB"


def test_keeps_bold_markers():
    text = "Employees accrue **12 days** of leave."
    assert clean_text(text) == text


def test_clean_text_is_idempotent():
    messy = "\n\n# Title   \n\n\n\nSEV1  text\n  - sub  item\n"
    once = clean_text(messy)
    assert clean_text(once) == once
