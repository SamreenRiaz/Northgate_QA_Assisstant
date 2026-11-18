"""Parse HTML files: keep headings, paragraphs and list items as Markdown-style text."""
from pathlib import Path

from bs4 import BeautifulSoup

# How each HTML tag starts its line in the output.
PREFIXES = {"h1": "# ", "h2": "## ", "h3": "### ", "p": "", "li": "- "}


def parse_html(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    return html_to_markdown(html)


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup  # skip <head>/<title>; fall back if there is no <body>
    lines = []
    for element in body.find_all(list(PREFIXES)):  # in document order
        text = " ".join(element.get_text().split())  # visible text, spaces tidied
        if text:
            lines.append(PREFIXES[element.name] + text)
    return "\n\n".join(lines)
