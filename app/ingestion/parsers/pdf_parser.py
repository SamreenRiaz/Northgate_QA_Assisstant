"""Parse PDF files with pypdf and restore simple Markdown structure."""
import re
from pathlib import Path

from pypdf import PdfReader

# The metadata header these PDFs repeat from the manifest (may wrap onto a second line).
HEADER_LINE = re.compile(r"Document ID: .*?Status: \w+( \| Supersedes:\s*[\w-]+)?\n", re.DOTALL)
# "1. When to deploy": a number, a dot, short text, not ending in "."
NUMBERED_HEADING = re.compile(r"^\d+\. \S.{0,60}[^.]$")
# Characters PDFs use for bullet points ("\x7f" is what our code-of-conduct PDF produces).
BULLET_CHARS = {"\x7f", "•", "●", "▪"}


def parse_pdf(path: Path) -> str:
    reader = PdfReader(path)
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    return pdf_text_to_markdown(raw)


def pdf_text_to_markdown(raw: str) -> str:
    """Turn pypdf's raw lines into Markdown: title, headings, list items, joined lines."""
    raw = HEADER_LINE.sub("", raw, count=1)  # drop the duplicated manifest header
    out = []
    marker = None  # a list marker waiting for its text
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in BULLET_CHARS:  # bullet on its own line
            marker = "- "
        elif line.isdigit():  # list number on its own line
            marker = f"{line}. "
        elif marker:
            out.append(marker + line)  # attach the marker to the next text line
            marker = None
        elif not out:
            out.append("# " + line)  # first line is the title
        elif NUMBERED_HEADING.match(line):
            out.append("## " + line)  # numbered section heading
        elif out[-1].startswith("#"):
            out.append(line)  # first line after a heading starts a paragraph
        else:
            out[-1] += " " + line  # wrapped line: join it to the previous line
    return "\n".join(out)
