# Vera bot — magicpin AI Challenge

A merchant-messaging bot for the magicpin AI Challenge: it receives category / merchant /
customer / trigger context from the judge harness and decides what (and whether) to send.

**Status:** step 3 of 6 — the decision layer (which triggers to act on, what each message
leads with, who it goes to) is done and tested, with no language model involved. Next:
Gemini drafting plus a fact validator (step 4), then the reply state machine (step 5).

## How a decision is made

```
trigger ──► router ──► lead builder ──► Brief ──► planner ──► (step 4: composer) ──► action
            kind →      one "why now"    facts,     which ones
            Strategy    fact + ≤3        notes,     go out this
                        supporting       who to     tick
                        facts            address
```

Everything in the Brief comes from the pushed contexts; nothing is invented. When a trigger
carries no usable details (75 of the 100 sample triggers are bare placeholders), the lead
comes from the merchant's own data and the Brief carries a note saying what must not be claimed.

## Layout

```
vera/
  app.py        the 5 endpoints (/v1/context, /tick, /reply, /healthz, /metadata)
  store.py      versioned in-memory context store (idempotent, thread-safe)
  models.py     lenient request bodies
  config.py     settings from environment / .env
  router.py     trigger kind -> Strategy (audience, call-to-action, levers, goal); 26 kinds + 2 generic fallbacks
  facts.py      small, checked statements about a merchant / category / customer (numbers, offers, peers, digest items)
  leads.py      per-kind builders that pick the one "why now" fact plus supporting facts and cautions
  signals.py    assembles the Brief: recipient, salutation, language, call-to-action, facts, notes
  ledger.py     what has been sent / opted out, so nothing is sent twice
  planner.py    picks which triggers to act on in a tick (priority, one message per person, cooldown, cap of 20)
  dataset.py    loads data/expanded straight into a store (used by the report and tests)
tests/          pytest: store, endpoints, facts, router, briefs, ledger, planner
scripts/
  load_dataset.py     push the expanded dataset into a running bot (warm-up rehearsal)
  decision_report.py  print what the bot would decide for the 30 canonical test pairs
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

## See the decisions

```bash
.venv/Scripts/python.exe -I -X utf8 scripts/decision_report.py --data data/expanded            # the 30 test pairs
.venv/Scripts/python.exe -I -X utf8 scripts/decision_report.py --data data/expanded --only T05,T24
.venv/Scripts/python.exe -I -X utf8 scripts/decision_report.py --data data/expanded --all       # all 100 triggers, summary
```

## Test

```bash
.venv/Scripts/python.exe -m pytest -q
```

## Secrets

`.env` holds the Gemini API key and is git-ignored. Never commit it or paste a key into code.
