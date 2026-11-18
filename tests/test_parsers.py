"""Tests for the file parsers and the parser registry."""
import shutil
from pathlib import Path

import docx
import pytest

from app.config import RAW_DIR
from app.ingestion.parsers import UnsupportedFileType, parse_file
from app.ingestion.parsers.csv_parser import parse_csv
from app.ingestion.parsers.docx_parser import parse_docx
from app.ingestion.parsers.html_parser import parse_html
from app.ingestion.parsers.markdown_parser import parse_markdown, strip_front_matter
from app.ingestion.parsers.pdf_parser import parse_pdf, pdf_text_to_markdown
from app.ingestion.parsers.text_parser import add_title_heading, parse_text

FIXTURES = Path(__file__).parent / "fixtures"


# --- Markdown -----------------------------------------------------------------


def test_markdown_front_matter_removed():
    text = parse_markdown(FIXTURES / "sample.md")
    assert "doc_id:" not in text
    assert "status:" not in text
    assert text.strip().startswith("# Sample Policy")


def test_markdown_keeps_divider_in_body():
    text = parse_markdown(FIXTURES / "sample.md")
    assert "\n---\n" in text
    assert "## Section two" in text
    assert "Second section text." in text


def test_text_without_front_matter_unchanged():
    text = "# Title\n\nSome text.\n"
    assert strip_front_matter(text) == text


# --- Plain text ---------------------------------------------------------------


def test_text_first_line_becomes_heading():
    text = parse_text(FIXTURES / "sample.txt")
    assert "# SAMPLE NOTES" in text


def test_text_rest_unchanged():
    lines = parse_text(FIXTURES / "sample.txt").splitlines()
    assert "Decisions" in lines  # stays a plain line, no "#" added
    assert "- Keep the canary at ten minutes." in lines


def test_text_empty_input():
    assert add_title_heading("") == ""


# --- CSV ----------------------------------------------------------------------


def test_csv_each_row_is_one_line():
    lines = parse_csv(FIXTURES / "sample.csv").splitlines()
    assert len(lines) == 2


def test_csv_line_has_column_names():
    first = parse_csv(FIXTURES / "sample.csv").splitlines()[0]
    assert first == "- grade: L1 | city tier: 1 | example cities: New York; Boston | per diem usd: 70"


def test_csv_quoted_value_kept_whole():
    text = parse_csv(FIXTURES / "sample.csv")
    assert "example cities: New York; Boston |" in text


def test_csv_empty_cell_skipped_text_value_kept():
    second = parse_csv(FIXTURES / "sample.csv").splitlines()[1]
    assert "example cities" not in second
    assert "per diem usd: above 50" in second


# --- HTML ---------------------------------------------------------------------


def test_html_headings_become_markdown():
    lines = parse_html(FIXTURES / "sample.html").splitlines()
    assert "# Sample Page" in lines
    assert "## Links" in lines


def test_html_list_items_and_links():
    text = parse_html(FIXTURES / "sample.html")
    assert "- Travel Policy (current)" in text
    assert "hr-travel-policy.md" not in text  # link URL dropped, link text kept


def test_html_title_tag_skipped():
    text = parse_html(FIXTURES / "sample.html")
    assert "Browser Tab Title" not in text


def test_html_entities_decoded_and_spaces_tidied():
    text = parse_html(FIXTURES / "sample.html")
    assert "Questions go to Finance & Legal." in text


# --- PDF ----------------------------------------------------------------------
# sample.pdf is a copy of the real eng-deploy-runbook-2023.pdf.


def test_pdf_extracts_text():
    text = parse_pdf(FIXTURES / "sample.pdf")
    assert "36 hours" in text


def test_pdf_title_and_headings():
    lines = parse_pdf(FIXTURES / "sample.pdf").splitlines()
    assert lines[0] == "# Production Deploy Runbook (2023)"
    assert "## 1. When to deploy" in lines
    assert "## 4. Rollback window" in lines


def test_pdf_metadata_header_removed():
    text = parse_pdf(FIXTURES / "sample.pdf")
    assert "Document ID:" not in text
    assert "Deprecated. Retained for reference only." in text  # body text kept


def test_pdf_numbered_list_items():
    lines = parse_pdf(FIXTURES / "sample.pdf").splitlines()
    assert "1. The change has one approving review and a green CI pipeline." in lines
    assert "2. The deployer posts the change summary in #deploys." in lines


def test_pdf_header_wrapped_over_two_lines():
    raw = (
        "Leave Policy v2\n"
        "Document ID: hr-leave-policy-v2 | Owner: People Operations | Status: current | Supersedes:\n"
        "hr-leave-policy-v1\n"
        "This version supersedes Leave Policy v1.\n"
    )
    assert pdf_text_to_markdown(raw) == "# Leave Policy v2\nThis version supersedes Leave Policy v1."


def test_pdf_bullet_glyph_becomes_dash():
    raw = "Code of Conduct\n\x7f\nTreat colleagues with courtesy.\n"
    assert pdf_text_to_markdown(raw).splitlines()[1] == "- Treat colleagues with courtesy."


def test_pdf_wrapped_lines_joined():
    raw = (
        "Title\n"
        "1. Rules\n"
        "A deploy\n"
        "freeze starts 36 hours before.\n"
        "\x7f\n"
        "Harassment of any\n"
        "kind is not allowed.\n"
    )
    assert pdf_text_to_markdown(raw).splitlines() == [
        "# Title",
        "## 1. Rules",
        "A deploy freeze starts 36 hours before.",
        "- Harassment of any kind is not allowed.",
    ]


# --- Word (.docx) -------------------------------------------------------------


def make_docx(folder):
    """Build a small .docx with every case we handle; return its path."""
    document = docx.Document()
    document.add_heading("Sample Travel Policy", level=0)  # level 0 = "Title" style
    document.add_paragraph("Document ID: sample | Owner: People Operations | Status: current")
    document.add_heading("1. Hotels", level=1)
    document.add_heading("1.1 Rates", level=2)
    document.add_paragraph("Tier 1: New York, Boston", style="List Bullet")
    document.add_paragraph("Room rates are capped per night:")
    table = document.add_table(rows=3, cols=2)
    for row, values in zip(table.rows, [("City tier", "Max rate"), ("Tier 1", "$275"), ("Tier 2", "$200")]):
        row.cells[0].text, row.cells[1].text = values
    document.add_paragraph("Per-diem is in the Per-Diem Table.")
    path = folder / "sample.docx"
    document.save(path)
    return path


def test_docx_headings_from_styles(tmp_path):
    lines = parse_docx(make_docx(tmp_path)).splitlines()
    assert lines[0] == "# Sample Travel Policy"
    assert "## 1. Hotels" in lines
    assert "### 1.1 Rates" in lines


def test_docx_list_bullet(tmp_path):
    lines = parse_docx(make_docx(tmp_path)).splitlines()
    assert "- Tier 1: New York, Boston" in lines


def test_docx_header_line_removed(tmp_path):
    assert "Document ID:" not in parse_docx(make_docx(tmp_path))


def test_docx_table_rows_with_column_names(tmp_path):
    lines = parse_docx(make_docx(tmp_path)).splitlines()
    assert "- City tier: Tier 1 | Max rate: $275" in lines
    assert "- City tier: Tier 2 | Max rate: $200" in lines


def test_docx_table_stays_in_place(tmp_path):
    lines = parse_docx(make_docx(tmp_path)).splitlines()
    before = lines.index("Room rates are capped per night:")
    table_row = lines.index("- City tier: Tier 1 | Max rate: $275")
    after = lines.index("Per-diem is in the Per-Diem Table.")
    assert before < table_row < after


def test_docx_real_travel_policy_has_hotel_rates():
    """The real file's hotel rates live only in a Word table: they must survive, inside 4.2."""
    lines = parse_docx(RAW_DIR / "hr-travel-policy.docx").splitlines()
    section_start = lines.index("### 4.2 Hotels and daily spending limits")
    section_end = lines.index("### 4.3 Ground transport")
    section = "\n".join(lines[section_start:section_end])
    for rate in ("$275", "$200", "$150"):
        assert rate in section


# --- Registry -----------------------------------------------------------------


def test_parse_file_uses_markdown_parser():
    path = FIXTURES / "sample.md"
    assert parse_file(path) == parse_markdown(path)


def test_parse_file_uses_text_parser():
    path = FIXTURES / "sample.txt"
    assert parse_file(path) == parse_text(path)


def test_parse_file_uses_csv_parser():
    path = FIXTURES / "sample.csv"
    assert parse_file(path) == parse_csv(path)


def test_parse_file_uses_html_parser():
    path = FIXTURES / "sample.html"
    assert parse_file(path) == parse_html(path)


def test_parse_file_uses_pdf_parser():
    path = FIXTURES / "sample.pdf"
    assert parse_file(path) == parse_pdf(path)


def test_parse_file_uses_docx_parser(tmp_path):
    path = make_docx(tmp_path)
    assert parse_file(path) == parse_docx(path)


def test_parse_file_unknown_extension_raises(tmp_path):
    path = tmp_path / "slides.xyz"
    path.write_text("anything", encoding="utf-8")
    with pytest.raises(UnsupportedFileType, match="no parser for '.xyz'"):
        parse_file(path)


def test_parse_file_extension_case_insensitive(tmp_path):
    upper = tmp_path / "SAMPLE.MD"
    shutil.copy(FIXTURES / "sample.md", upper)
    assert parse_file(upper) == parse_markdown(FIXTURES / "sample.md")
