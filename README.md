# Vera bot — magicpin AI Challenge

A merchant-messaging bot for the magicpin AI Challenge: it receives category / merchant /
customer / trigger context from the judge harness and decides what (and whether) to send.

**Status:** step 2 of 6 — HTTP skeleton, versioned context store, tests. The composer
(trigger routing, Gemini drafting, fact validation, reply state machine) comes next.

## Layout

```
vera/
  app.py       the 5 endpoints (/v1/context, /tick, /reply, /healthz, /metadata)
  store.py     versioned in-memory context store (idempotent, thread-safe)
  models.py    lenient request bodies
  config.py    settings from environment / .env
tests/         pytest contract tests for the store and the endpoints
scripts/
  load_dataset.py   push the expanded dataset into a running bot (warm-up rehearsal)
```

## Setup

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt     # Windows
cp .env.example .env                                                 # then fill in the values
```

Get the organizer's pack from the challenge page into `challenge-zip/`, then build the dataset:

```bash
.venv/Scripts/python.exe -I challenge-zip/dataset/generate_dataset.py --seed-dir challenge-zip/dataset --out data/expanded
```

## Run

```bash
.venv/Scripts/python.exe -m uvicorn vera.app:app --host 0.0.0.0 --port 8080
.venv/Scripts/python.exe scripts/load_dataset.py --url http://localhost:8080      # in another terminal
```

Run **one worker only**: all context and conversation state lives in process memory.

## Test

```bash
.venv/Scripts/python.exe -m pytest -q
```

## Secrets

`.env` holds the Gemini API key and is git-ignored. Never commit it or paste a key into code.
