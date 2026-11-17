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

## Run the tests

```bash
pytest
```
