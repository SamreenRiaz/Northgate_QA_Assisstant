# Northgate QA Assistant

A question-answering assistant for the Northgate Robotics employee handbook.
Employees ask a question in plain language and get an answer drawn from the
handbook, with the document and passage it comes from.

## Setup

Requires Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ingest the handbook

Reads every file listed in `data/raw/manifest.json`, parses and cleans it, and writes
one document per line to `data/processed/documents.jsonl` (generated, not committed).

```bash
python -m scripts.ingest
```

## Run the tests

```bash
pytest
```
