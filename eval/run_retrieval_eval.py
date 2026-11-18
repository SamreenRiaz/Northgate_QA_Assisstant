"""Retrieval-only evaluation: does search find the right documents? (no LLM calls)

Runs every answerable question in eval/questions.json through three methods
(vector only, BM25 only, hybrid) and reports, per method and per category:
  Hit@1  - share of questions whose top chunk comes from an expected document
  Hit@5  - share of questions with an expected document anywhere in the top 5
  MRR    - mean reciprocal rank of the first expected document (1st = 1, 2nd = 0.5, ... missing = 0)
  Leaks  - questions whose top 5 contains a deprecated or superseded document

Needs the index built first (python -m scripts.ingest).
Run: python -m eval.run_retrieval_eval
"""
import json
from datetime import date
from pathlib import Path

from app.config import EMBEDDING_MODEL
from app.retrieval.embedder import BgeEmbedder
from app.retrieval.keyword_search import KeywordIndex
from app.retrieval.retriever import HybridRetriever, outdated_doc_ids
from app.retrieval.vector_store import VectorStore

EVAL_DIR = Path(__file__).parent
QUESTIONS_PATH = EVAL_DIR / "questions.json"
RESULTS_DIR = EVAL_DIR / "results"
K = 5


# --- Scoring (pure functions, unit-tested) ------------------------------------


def first_hit_rank(retrieved_doc_ids: list[str], expected_docs: set[str]) -> int | None:
    """Position (1-based) of the first retrieved chunk from an expected document, or None."""
    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        if doc_id in expected_docs:
            return rank
    return None


def score_question(retrieved_doc_ids: list[str], expected_docs: set[str], outdated: set[str]) -> dict:
    rank = first_hit_rank(retrieved_doc_ids, expected_docs)
    return {
        "rank": rank,
        "hit1": rank == 1,
        "hit5": rank is not None,
        "reciprocal_rank": 1 / rank if rank else 0.0,
        "leak": any(doc_id in outdated for doc_id in retrieved_doc_ids),
    }


def summarize(rows: list[dict]) -> dict:
    """Average the per-question scores; leaks are a count."""
    n = len(rows) or 1
    return {
        "questions": len(rows),
        "hit1": sum(row["hit1"] for row in rows) / n,
        "hit5": sum(row["hit5"] for row in rows) / n,
        "mrr": sum(row["reciprocal_rank"] for row in rows) / n,
        "leaks": sum(row["leak"] for row in rows),
    }


# --- Running and reporting ----------------------------------------------------


def run(questions: list[dict], methods: dict, outdated: set[str]) -> dict[str, list[dict]]:
    """Ask every question with every method; return the scored rows per method."""
    results = {name: [] for name in methods}
    for question in questions:
        for name, search in methods.items():
            retrieved = [result.chunk.doc_id for result in search(question["question"], k=K)]
            scores = score_question(retrieved, set(question["expected_docs"]), outdated)
            results[name].append({"question": question, "retrieved": retrieved, **scores})
    return results


def build_report(results: dict[str, list[dict]], outdated: set[str], skipped: int) -> str:
    methods = list(results)
    categories = sorted({row["question"]["category"] for row in results[methods[0]]})
    lines = [
        f"# Retrieval evaluation, {date.today()}",
        "",
        f"- Questions: {len(results[methods[0]])} answerable ({skipped} unanswerable skipped: nothing to retrieve)",
        f"- Top-k: {K} chunks | Embedding model: {EMBEDDING_MODEL} | Outdated documents: {', '.join(sorted(outdated))}",
        "- Hit@k: an expected document is in the top k. MRR: 1/rank of the first expected document.",
        "- Leaks: questions whose top 5 contains a deprecated or superseded document.",
        "",
        "## Overall",
        "",
        "| Method | Hit@1 | Hit@5 | MRR | Leaks |",
        "|---|---|---|---|---|",
    ]
    for name in methods:
        s = summarize(results[name])
        lines.append(f"| {name} | {s['hit1']:.0%} | {s['hit5']:.0%} | {s['mrr']:.2f} | {s['leaks']} |")

    lines += ["", "## Hit@5 by category", "", "| Category | n | " + " | ".join(methods) + " |",
              "|---|---|" + "---|" * len(methods)]
    for category in categories:
        per_method = [summarize([r for r in results[name] if r["question"]["category"] == category]) for name in methods]
        lines.append(f"| {category} | {per_method[0]['questions']} | " + " | ".join(f"{s['hit5']:.0%}" for s in per_method) + " |")

    for name in methods:
        misses = [row for row in results[name] if not row["hit5"]]
        leaks = [row for row in results[name] if row["leak"]]
        lines += ["", f"## {name}: misses ({len(misses)}) and leaks ({len(leaks)})", ""]
        for row in misses:
            q = row["question"]
            lines.append(f"- MISS `{q['id']}`: expected {q['expected_docs']}, got {row['retrieved']}")
        for row in leaks:
            leaked = sorted({doc_id for doc_id in row["retrieved"] if doc_id in outdated})
            lines.append(f"- LEAK `{row['question']['id']}`: {leaked}")
        if not misses and not leaks:
            lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> None:
    all_questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = [q for q in all_questions if q["answerable"]]

    store = VectorStore(BgeEmbedder())
    if store.count() == 0:
        raise SystemExit("The index is empty. Build it first: python -m scripts.ingest")
    chunks = store.get_all_chunks()
    methods = {
        "vector": store.search,
        "bm25": KeywordIndex(chunks).search,
        "hybrid": HybridRetriever(store).search,
    }

    results = run(questions, methods, outdated_doc_ids(chunks))
    report = build_report(results, outdated_doc_ids(chunks), skipped=len(all_questions) - len(questions))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / f"retrieval_{date.today()}.md"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
