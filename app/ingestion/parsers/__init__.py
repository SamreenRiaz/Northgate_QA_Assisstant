"""Pick the right parser for a file based on its extension."""
from pathlib import Path

from app.ingestion.parsers.csv_parser import parse_csv
from app.ingestion.parsers.docx_parser import parse_docx
from app.ingestion.parsers.html_parser import parse_html
from app.ingestion.parsers.markdown_parser import parse_markdown
from app.ingestion.parsers.pdf_parser import parse_pdf
from app.ingestion.parsers.text_parser import parse_text

# Maps file extension -> function that turns that file into Markdown-style text.
PARSERS = {
    ".md": parse_markdown,
    ".txt": parse_text,
    ".csv": parse_csv,
    ".html": parse_html,
    ".pdf": parse_pdf,
    ".docx": parse_docx,
}


class UnsupportedFileType(Exception):
    """Raised when no parser exists for a file's extension."""


def parse_file(path: Path) -> str:
    """Parse any supported file into Markdown-style text."""
    extension = path.suffix.lower()  # "Policy.MD" -> ".md"
    parser = PARSERS.get(extension)
    if parser is None:
        raise UnsupportedFileType(f"no parser for '{extension}' files: {path.name}")
    return parser(path)
