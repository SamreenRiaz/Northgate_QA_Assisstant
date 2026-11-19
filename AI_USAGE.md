# AI usage

## Tools I used

- **Claude**: the desktop app for planning, and Claude Code in VS Code for implementation.

## What I used them for

| Task | Tool | How much of the result I kept |
|---|---|---|
| Planning: stack, folder structure, ingestion approach | Claude | Used Claude to explore alternatives (LangChain vs. plain Python, embedding models, vector stores). I made the final technology and architecture decisions after considering project requirements, data characteristics, and my machine's compatibility. |
| Code implementation, step by step | Claude | Used Claude extensively for code generation, working file by file. I reviewed the implementation, cross-checked it against the data and requirements, and requested changes wherever needed. |
| Tests | Claude | Used Claude to help develop the tests. I ran them after each implementation step, reviewed the results, and used them to verify changes. |
| Evaluation question set | Claude | Used Claude to draft questions from the source documents. I reviewed the questions and independently verified the expected answers against the original documents. |
| Debugging and understanding concepts (RRF, BM25, embeddings, FastAPI lifespan) | Claude | Used Claude to investigate issues and explain technical concepts. I evaluated the suggested fixes, applied relevant changes, and tested them to confirm they worked. |

## One thing the AI got wrong

- **Citations disappeared with the real model.** The AI-written citation parser only understood `[1]`, but gpt-oss cites as `【1】`. The first answer evaluation scored 13/29, and the web page would have shown no sources. The parser now rewrites that style to `[1]`, and the score rose to 24/29.
- **The source panel could not be closed.** In the browser, the panel was open on page load and the ✕ did nothing. The AI's CSS set `display: flex` on the panel, which overrides the HTML `hidden` attribute. One CSS rule fixed it.

## What I did without AI

- Decided the scope: which stretch goals to skip, and which features to cut before the deadline.
- Managed the git history myself: branches per feature, small commits, merges.
- Read the parsed documents by hand, and checked the evaluation's expected answers against the source files.
- Planned the LLM token budget: one model for development, evaluation and the demo, and 29 questions instead of 55.
- Tested the web page myself, found the source panel bug and directed the design.
- Questioned suggestions instead of accepting them: whether the number of tests was justified, and a type annotation the AI said was fine until VS Code showed it was deprecated.
