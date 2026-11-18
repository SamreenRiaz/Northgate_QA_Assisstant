"""Parse CSV files: each row becomes one line that repeats the column names."""
import csv
from pathlib import Path


def parse_csv(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return "\n".join(row_to_line(row) for row in rows)


def row_to_line(row: dict) -> str:
    """{'per_diem_usd': '70', ...} -> '- per diem usd: 70 | ...' (empty cells skipped)."""
    parts = []
    for column, value in row.items():
        value = (value or "").strip()
        if value:
            parts.append(f"{column.replace('_', ' ')}: {value}")
    return "- " + " | ".join(parts)
