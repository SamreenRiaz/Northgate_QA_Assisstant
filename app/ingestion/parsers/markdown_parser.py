"""Parse Markdown files: read the text and remove the front-matter block."""
from pathlib import Path


def parse_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return strip_front_matter(text)


def strip_front_matter(text: str) -> str:
    """Remove a leading '---' ... '---' block (YAML front matter), if there is one."""
    if not text.startswith("---\n"):
        return text  # no front matter: leave the text unchanged
    end = text.find("\n---\n", 4)  # find the closing '---' after the opening one
    if end == -1:
        return text  # opening '---' but no closing one: not front matter
    return text[end + len("\n---\n"):]
