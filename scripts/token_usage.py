"""Show how many LLM tokens were used today, per model.  Run: python -m scripts.token_usage"""
import json
from collections import Counter
from datetime import date

from app.config import USAGE_LOG_PATH


def main() -> None:
    if not USAGE_LOG_PATH.exists():
        print("No LLM calls logged yet.")
        return
    today = date.today().isoformat()
    totals: Counter[str] = Counter()
    calls: Counter[str] = Counter()
    for line in USAGE_LOG_PATH.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry["time"].startswith(today):
            totals[entry["model"]] += entry["total_tokens"]
            calls[entry["model"]] += 1
    if not totals:
        print("No LLM calls logged today.")
    for model, tokens in totals.items():
        print(f"{model}: {tokens:,} tokens in {calls[model]} calls today")


if __name__ == "__main__":
    main()
