# OpenEnv-TabClean — Tabular data cleaning & schema repair

TabClean is an OpenEnv environment for evaluating an agent’s ability to **clean messy tabular data into a target schema** using a safe transformation DSL and deterministic scoring.

## Live demo (Hugging Face Space)

- UI: `https://sapana1234-openenv-tabclean.hf.space/`
- API docs: `https://sapana1234-openenv-tabclean.hf.space/docs`

## Why this is useful

Data cleaning and schema repair is a common real-world bottleneck in analytics/ETL. TabClean provides deterministic tasks + graders for agent evaluation.

## API

This environment implements the standard OpenEnv interface:

- `reset(seed=..., task=...)`
- `step(action)`
- `state()`

Typed models:

- `TabCleanAction` in `models.py`
- `TabCleanObservation` in `models.py`
- `TabCleanState` in `models.py`

## Tasks

Three tasks are included (easy → medium → hard):

- `easy_schemafix`
- `medium_dedupe_normalize`
- `hard_parse_normalize_filter`

## Run locally (environment server)

Install deps (recommended: virtual env):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Start server:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Or (OpenEnv/uv workflow):

```bash
uv run server
```

## Demo script (submission requirement)

Run the required demo script:

```bash
python3 demo.py
```

## Baseline agent (`inference.py`) + required env vars

`inference.py` uses the OpenAI client and reads configuration from environment variables:

- `API_BASE_URL` (default set in code)
- `MODEL_NAME` (default set in code)
- `HF_TOKEN` (no default; required to use the Hugging Face router)
- `LOCAL_IMAGE_NAME` (optional)

If `HF_TOKEN` is not set, `inference.py` falls back to a deterministic heuristic policy (still prints the required `[START]`, `[STEP]`, `[END]` logs).

Run:

```bash
python3 inference.py
```

## Local `.env` convenience

Copy:

```bash
cp .env.example .env
```

Then edit `.env` and set `HF_TOKEN`, etc. (`.env` is gitignored).

## Smoke test (sync client)

```python
from client import TabCleanEnv
from models import TabCleanAction

with TabCleanEnv(base_url="http://localhost:8000").sync() as env:
    r = env.reset(task="easy_schemafix", seed=0)
    r = env.step(TabCleanAction(op="noop", args={}))
    print(r.observation.message)
```

## Local score sanity check

`grade.py` is a simple helper that runs through the task list and prints deterministic scores in `[0, 1]` against a running server:

```bash
python3 grade.py
```

## Docker

The validator may check for `Dockerfile` in repo root or `server/Dockerfile`. This repo includes **both**.

Build and run:

```bash
docker build -t tabclean-env:local .
docker run --rm -p 8001:8000 tabclean-env:local
```

Then point the client at `TAB_CLEAN_BASE_URL=http://localhost:8001`.

## OpenEnv validation

```bash
openenv validate
```

## What you need to submit (per FAQ)

- A **public GitHub repo** with:
  - environment code
  - `requirements.txt`
  - a demo script (this repo: `demo.py`)
  - `README.md`
- A deployed **Hugging Face Space URL** showcasing the working demo

