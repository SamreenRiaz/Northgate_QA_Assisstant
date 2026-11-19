"""Answer evaluation: are the final answers right, cited and honest? (uses the LLM)

Asks the questions in the categories where the language model itself can fail, and grades:
  Facts     - every must_contain fact is present and no must_not_contain text (answerable questions)
  Citations - at least one cited passage comes from an expected document (answerable questions)
  Refusal   - unanswerable questions get "does not cover"; answerable ones are not refused
A question passes when all of its checks pass.

Answers are cached in eval/results/answers_<model>.json, keyed by model + exact prompt:
re-running costs no tokens, and an interrupted run continues where it stopped.
Needs the index (python -m scripts.ingest) and LLM_API_KEY in .env.
Run: python -m eval.run_answer_eval
"""
import hashlib
import json
import os
import statistics
import time
from datetime import date, datetime
from pathlib import Path

from app.config import LLM_MODEL, USAGE_LOG_PATH
from app.generation.answerer import Answer, Answerer
from app.generation.llm import LLM, Message, OpenAICompatibleLLM
from app.retrieval.embedder import BgeEmbedder
from app.retrieval.retriever import HybridRetriever
from app.retrieval.vector_store import VectorStore

EVAL_DIR = Path(__file__).parent
QUESTIONS_PATH = EVAL_DIR / "questions.json"
RESULTS_DIR = EVAL_DIR / "results"
EVAL_TODAY = "2026-11-19"  # the date the expected answers were written for
CATEGORIES = {"conflict", "date", "multi-doc", "table", "unanswerable"}

# Characters models use that look like "-" or " " but are different characters.
LOOKALIKES = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
                            "−": "-", " ": " ", " ": " "})


# --- Grading (pure functions, unit-tested) ------------------------------------


def normalize(text: str) -> str:
    """Lowercase, plain hyphens and spaces, no bold markers: so '2027‑01‑01' matches '2027-01-01'."""
    return text.translate(LOOKALIKES).replace("**", "").lower()


def contains(text: str, fact: str) -> bool:
    """True if the text contains the fact; 'a|b' means either alternative is enough."""
    normalized = normalize(text)
    return any(normalize(alternative) in normalized for alternative in fact.split("|"))


def is_refusal(text: str) -> bool:
    return "does not cover" in normalize(text)


def grade(question: dict, answer: Answer) -> dict:
    refused = is_refusal(answer.text)
    if not question["answerable"]:
        return {"facts_ok": None, "citations_ok": None, "refusal_ok": refused, "passed": refused}

    facts_ok = all(contains(answer.text, fact) for fact in question["must_contain"]) and not any(
        contains(answer.text, fact) for fact in question["must_not_contain"]
    )
    cited_docs = {citation.chunk.doc_id for citation in answer.citations}
    citations_ok = bool(cited_docs & set(question["expected_docs"]))
    refusal_ok = not refused
    return {
        "facts_ok": facts_ok,
        "citations_ok": citations_ok,
        "refusal_ok": refusal_ok,
        "passed": facts_ok and citations_ok and refusal_ok,
    }


# --- Answer cache ---------------------------------------------------------------


class CachingLLM:
    """Wraps a real LLM: answers already in the cache file are reused, new ones are saved right away."""

    def __init__(self, llm: LLM, model: str, path: Path) -> None:
        self._llm = llm
        self._model = model
        self._path = path
        self._cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.new_calls = 0
        self.last_seconds = 0.0  # time of the original model call for the last answer

    def complete(self, messages: list[Message]) -> str:
        key = hashlib.sha256(json.dumps([self._model, messages]).encode("utf-8")).hexdigest()
        if key not in self._cache:
            start = time.perf_counter()
            answer = self._llm.complete(messages)
            self._cache[key] = {"answer": answer, "seconds": round(time.perf_counter() - start, 2)}
            self.new_calls += 1
            self._save()
        self.last_seconds = self._cache[key]["seconds"]
        return self._cache[key]["answer"]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Running and reporting ----------------------------------------------------


def usage_line_count() -> int:
    return len(USAGE_LOG_PATH.read_text(encoding="utf-8").splitlines()) if USAGE_LOG_PATH.exists() else 0


def tokens_since(line_count: int) -> int:
    """Tokens logged by LLM calls made after the usage log had `line_count` lines."""
    if not USAGE_LOG_PATH.exists():
        return 0
    new_lines = USAGE_LOG_PATH.read_text(encoding="utf-8").splitlines()[line_count:]
    return sum(json.loads(line)["total_tokens"] for line in new_lines)


def rate(rows: list[dict], check: str) -> str:
    graded = [row[check] for row in rows if row[check] is not None]
    return f"{sum(graded)}/{len(graded)}" if graded else "-"


def build_report(rows: list[dict], new_calls: int, tokens: int) -> str:
    unanswerable = [row for row in rows if not row["question"]["answerable"]]
    wrongly_refused = sum(1 for row in rows if row["refusal_ok"] is False and row["question"]["answerable"])
    lines = [
        f"# Answer evaluation, {date.today()}",
        "",
        f"- Model: {LLM_MODEL} | Questions: {len(rows)} | Date used as today: {EVAL_TODAY}",
        f"- Model calls this run: {new_calls} (the rest came from the cache) | Tokens this run: {tokens:,}",
        f"- Median answer time (original call): {statistics.median(row['seconds'] for row in rows):.1f} s",
        "",
        "## Overall",
        "",
        "| Passed | Facts correct | Cites an expected source | Correct refusals | Answerable wrongly refused |",
        "|---|---|---|---|---|",
        f"| {rate(rows, 'passed')} | {rate(rows, 'facts_ok')} | {rate(rows, 'citations_ok')} "
        f"| {rate(unanswerable, 'refusal_ok')} | {wrongly_refused} |",
        "",
        "## By category",
        "",
        "| Category | Passed |",
        "|---|---|",
    ]
    for category in sorted({row["question"]["category"] for row in rows}):
        lines.append(f"| {category} | {rate([r for r in rows if r['question']['category'] == category], 'passed')} |")

    failures = [row for row in rows if not row["passed"]]
    lines += ["", f"## Failures ({len(failures)})", ""]
    for row in failures:
        q, answer = row["question"], row["answer"]
        checks = ", ".join(name for name in ("facts_ok", "citations_ok", "refusal_ok") if row[name] is False)
        cited = sorted({citation.chunk.doc_id for citation in answer.citations})
        lines += [
            f"### `{q['id']}` ({q['category']}): failed {checks}",
            f"- Question: {q['question']}",
            f"- Expected: {q['expected_answer']}",
            f"- Cited documents: {cited}",
            f"- Answer: {answer.text}",
            "",
        ]
    if not failures:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> None:
    os.environ["TODAY"] = EVAL_TODAY
    questions = [q for q in json.loads(QUESTIONS_PATH.read_text(encoding="utf-8")) if q["category"] in CATEGORIES]

    store = VectorStore(BgeEmbedder())
    if store.count() == 0:
        raise SystemExit("The index is empty. Build it first: python -m scripts.ingest")
    cache_path = RESULTS_DIR / f"answers_{LLM_MODEL.replace('/', '_')}.json"
    llm = CachingLLM(OpenAICompatibleLLM(), model=LLM_MODEL, path=cache_path)
    answerer = Answerer(HybridRetriever(store), llm)
    usage_before = usage_line_count()

    rows = []
    for number, question in enumerate(questions, start=1):
        answer = answerer.answer(question["question"])
        row = {"question": question, "answer": answer, "seconds": llm.last_seconds, **grade(question, answer)}
        rows.append(row)
        print(f"{number:2}/{len(questions)} {'PASS' if row['passed'] else 'FAIL'}  {question['id']}")

    report = build_report(rows, llm.new_calls, tokens_since(usage_before))
    report_path = RESULTS_DIR / f"answers_{datetime.now():%Y-%m-%d_%H%M}.md"  # one report per run, never overwritten
    report_path.write_text(report, encoding="utf-8")
    print()
    print(report)
    print(f"Report saved to {report_path}\nAnswers cached in {cache_path}")


if __name__ == "__main__":
    main()
