"""Format-independent text clean-up, applied to every parsed document."""
import re


def clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.rstrip()  # no spaces at the end of a line
        indent = line[: len(line) - len(line.lstrip())]  # keep leading spaces (nested lists)
        body = re.sub(r" {2,}", " ", line.lstrip())  # "SEV1  Customer" -> "SEV1 Customer"
        lines.append(indent + body)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line in a row
    return text.strip()  # no blank lines at start or end
