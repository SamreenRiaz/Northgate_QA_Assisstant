"""Parse plain-text files: the first non-empty line is the document title."""
from pathlib import Path


def parse_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return add_title_heading(text)


def add_title_heading(text: str) -> str:
    """Turn the first non-empty line into a '# ' Markdown heading."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip():  # skip blank lines at the top
            lines[i] = "# " + line.strip()
            break  # only the first one
    return "\n".join(lines)
