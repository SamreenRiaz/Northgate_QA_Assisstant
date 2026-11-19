# Decision log

## 1. Approach in five lines

Employees ask the same handbook questions every day, and someone looks up the answers by hand. I built a RAG (retrieval-augmented generation) assistant that answers only from the handbook and shows the passage behind every answer. Ingestion parses the 64 files (six formats) into clean Markdown-style text, splits it at headings and stores the chunks in a local vector index. For each question, hybrid search (vector + BM25) finds 5 passages after removing deprecated and superseded documents, and an LLM answers from them with numbered citations that the web page turns into clickable sources.
## 2. Key decisions

| Decision | What else I considered | Why I chose this |
|---|---|---|
| Plain Python, no framework | LangChain | Every step is visible and testable, and I can explain each line. The pipeline is small enough not to need a framework. |
| Chunk at Markdown headings, max 200 words, CSV and Word table rows repeat their column names | Fixed-size chunks with overlap | Sections stay whole and citations point to a real section ("Travel Policy > 4.2 Hotels"). A table row still makes sense on its own. |
| `bge-small-en-v1.5`, run locally with fastembed (ONNX) | OpenAI `text-embedding-3-small`, Chroma's built-in MiniLM, sentence-transformers | Free, and no handbook text leaves the machine for indexing. MiniLM reads only 256 tokens (I measured: 1 chunk would be cut off). sentence-transformers needs PyTorch, which no longer supports Intel Macs. |
| ChromaDB, stored on disk | Pinecone, FAISS | Local, no account, and it keeps metadata next to each vector. Pinecone needs a cloud account; FAISS would need a separate metadata store. |
| Hybrid search: vector + BM25, combined with Reciprocal Rank Fusion | Vector only, BM25 only | Vectors find meaning ("hotel in Boston" → "room rates"); BM25 finds exact codes (L3, SEV2, 2026.22, extension 304). RRF combines rankings without tuning weights. |
| Remove deprecated and superseded documents before ranking | Demote them, or keep them with a label | The handbook says deprecated documents "must not be followed". Vector-only search put an outdated document in the top 5 for 15 of 49 questions |
| LLM: `gpt-oss-120b` on Groq's free tier; `gpt-oss-20b` as backup | Gemini, OpenAI and Anthropic APIs (paid), smaller Llama models | A free reasoning model, which the date and multi-document questions need. 200k tokens/day, ~900 tokens per question. The backup is the same model family with its own daily limit. Any OpenAI-compatible provider works by changing `.env`. |
| FastAPI + a single HTML/CSS/JS page | Flask, Streamlit | In FastAPI, validation, response shapes and the `/docs` page come from type hints, with no extra libraries. I needed only one page, so plain HTML gives full control with no build step. |

## 3. Things in the data that surprised me

- **Leave Policy v1 says "current", but v2 supersedes it.** I trust `supersedes`: v1 is excluded from search.
- **The 2027 parental leave revision is marked "current" but takes effect on 2027-01-01.** The prompt labels it "NOT YET IN EFFECT"; answers give today's rule (12 weeks) and mention the change.
- **The deprecated 2023 deploy runbook contradicts the current one** on four facts (freeze 36 vs 72 h, rollback 10 vs 45 min, 1 vs 2 reviews, no canary). It is excluded from search.
- **The hotel rates exist only in a Word table**, so the Word parser reads tables in document order. A test checks that the rates stay inside section 4.2.
- **PDFs repeat the manifest in a header line, lose their headings, and turn bullets into a control character (`\x7f`).** The PDF parser removes the header line, rebuilds numbered headings and fixes bullets.
- **Contradictions and gaps:** the approval matrix says VP approval above $2,500 but the Expense Policy exempts VoyageHub travel; Denver is in no city tier ("any city not listed" means Tier 3); the handbook refers to a Holiday Calendar and an Anti-Harassment Policy that are not included.
- **Meeting notes repeat or update policies.** Passages from them are labelled as weaker sources.

## 4. What I tried that did not work

- **Citations disappeared with gpt-oss.** The model cites as `【1】` instead of `[1]`, so the first answer eval scored 13/29, and the web page would have shown no sources. The eval caught it; I rewrite that style to `[1]` before parsing. The score rose to 24/29, re-graded from cached answers with no new model calls.
- **sentence-transformers would not install cleanly on my Intel Mac** (PyTorch dropped Intel Mac builds). I switched to fastembed, which runs the same bge-small model on ONNX Runtime.
- **The model got the weekday wrong** ("2026-11-19 is a Saturday"; it is a Thursday). Date facts should come from code, not the model.

## 5. Results

No dev set was provided. I wrote 55 questions and checked every expected answer against the documents (`eval/questions.json`). Model: `gpt-oss-120b` (open-weight, by OpenAI). Provider: Groq. Reports are in `eval/results/`.

| Evaluation | Result |
|---|---|
| Retrieval, 49 answerable questions, no LLM calls | Hit@1: vector 88%, BM25 65%, **hybrid 92%**. Hit@5: 98% for all three. Outdated document in the top 5: 15 / 12 / **0** |
| Answers, 29 hardest questions (conflict, date, multi-document, table, unanswerable) | **24/29 fully correct**: conflicts 8/8, unanswerable 6/6 refused, tables 5/6, multi-document 4/6, dates 1/3 |
| The 5 misses | None invented an answer. Three need a second lookup that single-step retrieval did not do (Denver → city tier, "Security Lead" → name, "data loss" → RPO), so the model refused or answered partially. Two are date questions (wrong weekday, release calendar not retrieved). |
| Cost of the full answer run | 29 model calls, 27,442 tokens, median 3.7 s per answer |

## 6. What I would do with one more week

1. **Multi-step retrieval (query rewriting, or a second search based on the first results).** It would fix most of the remaining misses, which need one fact to know what to look up next.
2. **Conversation history in SQLite, with follow-up questions.** Employees naturally ask "and for L3?" after a first answer.
3. **Document upload and deployment.** HR could add or replace a document without a developer, and employees would get a URL instead of a local setup.

## 7. Time spent

| Part | Hours |
|---|---|
| Reading the brief and the data, planning | 2 |
| Parsing (six formats, data traps) | 3.5 |
| Cleaning | 0.5 |
| Chunking | 1.5 |
| Retrieval (embeddings, Chroma, BM25, hybrid) | 3 |
| Question set, retrieval and answer evaluation | 2.5 |
| LLM client, prompt, answerer | 2 |
| API and web page | 2 |
| README, DECISIONS.md, AI_USAGE.md | 1 |
| **Total** | **18** |
