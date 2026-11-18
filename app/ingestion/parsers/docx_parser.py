"""Parse Word files: styles give headings and lists; tables are read in place."""
from pathlib import Path

from docx import Document
from docx.table import Table

from app.ingestion.parsers.csv_parser import row_to_line

# Word style name -> Markdown prefix. Any other style is a normal paragraph.
STYLE_PREFIXES = {
    "Title": "# ",
    "Heading 1": "## ",
    "Heading 2": "### ",
    "Heading 3": "#### ",
    "List Bullet": "- ",
}
HEADER_PREFIX = "Document ID:"  # the manifest copy these files repeat


def parse_docx(path: Path) -> str:
    doc = Document(path)
    blocks = []
    for item in doc.iter_inner_content():  # paragraphs AND tables, in document order
        if isinstance(item, Table):
            blocks.append(table_to_text(item))
            continue
        text = item.text.strip()
        if not text or text.startswith(HEADER_PREFIX):
            continue
        blocks.append(STYLE_PREFIXES.get(item.style.name, "") + text)
    return "\n".join(blocks)


def table_to_text(table: Table) -> str:
    """First row is the header; each other row becomes '- column: value | ...'."""
    rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
    header, body = rows[0], rows[1:]
    return "\n".join(row_to_line(dict(zip(header, row))) for row in body)
