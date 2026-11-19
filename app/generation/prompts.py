"""The instructions and passages we send to the language model."""
from datetime import date

from app.generation.llm import Message
from app.ingestion.models import Chunk
from app.retrieval.models import SearchResult

NOT_COVERED = "The handbook does not cover this."

SYSTEM_PROMPT = f"""You are the Northgate Robotics handbook assistant. Employees ask you questions, and you answer using ONLY the numbered handbook passages given with each question.

Rules:
1. Base every statement on the passages. Do not use outside knowledge and do not guess.
2. Cite the passage numbers in square brackets right after the facts they support, like [1] or [2][3].
3. If the passages do not answer the question, reply "{NOT_COVERED}" and, if helpful, mention the closest related information you do have. Never invent an answer.
4. Today is {{today}}. A passage marked "NOT YET IN EFFECT" describes a future change: answer with the rule that applies today, then mention the upcoming change and its date.
5. Passages marked "meeting notes" are weaker sources than policies. Prefer the policy; if the notes add something newer, say it comes from meeting notes.
6. If passages disagree, say so briefly and follow the more specific rule.
7. Be concise: one to four sentences or a short list, with exact numbers, names and dates from the passages."""


def build_messages(question: str, results: list[SearchResult], today: date) -> list[Message]:
    """System message with the rules, user message with numbered passages and the question."""
    passages = "\n\n".join(
        format_passage(number, result.chunk, today) for number, result in enumerate(results, start=1)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(today=today.isoformat())},
        {"role": "user", "content": f"Handbook passages:\n\n{passages}\n\nQuestion: {question}"},
    ]


def format_passage(number: int, chunk: Chunk, today: date) -> str:
    """'[1] Travel Policy > 4.2 Hotels (effective 2024-06-01)' followed by the passage text."""
    effective = date.fromisoformat(chunk.metadata["effective_date"])
    labels = [f"effective {effective.isoformat()}"]
    if effective > today:
        labels.append(f"NOT YET IN EFFECT until {effective.isoformat()}")
    if chunk.metadata.get("category") == "Meeting Notes":
        labels.append("meeting notes")
    return f"[{number}] {chunk.section} ({'; '.join(labels)})\n{chunk.text}"
