from __future__ import annotations

import asyncio
import os
import textwrap
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from client import TabCleanEnv
from models import TabCleanAction
from tasks.graders import TASKS

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # `.env` is a local convenience; don't fail if it's missing.
    pass


# Platform injects proxy credentials; default to HF router if missing.
API_BASE_URL = (os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
# Platform docs say HF_TOKEN is the injected key; fall back to API_KEY.
API_KEY = (os.getenv("HF_TOKEN") or "").strip() or (os.getenv("API_KEY") or "").strip()
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("LOCAL_IMAGE") or ""

TASK_NAME = os.getenv("TAB_CLEAN_TASK", "")
BENCHMARK = os.getenv("TAB_CLEAN_BENCHMARK", "tabclean_env")

MAX_STEPS_DEFAULT = int(os.getenv("MAX_STEPS", "10"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "250"))

# Consider the run a "success" above this score.
SUCCESS_SCORE_THRESHOLD = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "0.95"))


SYSTEM_PROMPT = textwrap.dedent(
    """
    You are operating a data-cleaning environment.

    You must output the NEXT action as strict JSON with keys:
      - op: one of rename_column|drop_columns|cast|fill_missing|normalize_text|split_column|merge_columns|dedupe|filter_rows|noop
      - args: an object of parameters for that op

    Exact args schemas (use these keys exactly):
    - rename_column: {"from": "<old>", "to": "<new>"}
    - drop_columns: {"columns": ["c1", "c2"]}
    - cast: {"column": "<name>", "type": "string|int|float|bool|date_ymd"}
    - fill_missing: {"column": "<name>", "strategy": "constant|mode", "value": <any>}
    - normalize_text: {"column": "<name>", "mode": "trim_lower|trim_upper|country_iso2"}
    - split_column: {"column": "<name>", "sep": "<sep>", "into": ["col1","col2",...]}
      - optional: {"take": "first_last"} to map into[0]=first token, into[1]=last token
    - merge_columns: {"into": "<name>", "columns": ["c1","c2"], "sep": "<sep>"}
    - dedupe: {"keys": ["k1","k2"]}
    - filter_rows: {"column": "<name>", "op": "eq|neq|in|not_in", "value": <any>}

    Constraints:
    - Output JSON only (no markdown).
    - Prefer small, safe steps that improve schema validity and constraint satisfaction.
    - Avoid dropping rows/columns unless required.
    """
).strip()


def _sanitize_error(err: str) -> str:
    """
    Keep `[STEP] ... error=` single-line and reasonably small.
    """
    s = (err or "").replace("\n", " ").replace("\r", " ").strip()
    if not s:
        return "error"
    if "<!DOCTYPE html" in s or "<html" in s:
        return "unauthorized"
    if len(s) > 180:
        s = s[:180].rstrip() + "..."
    return s


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    _EPS = 1e-4
    score = max(_EPS, min(1.0 - _EPS, score))
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def _build_user_prompt(obs: Dict[str, Any]) -> str:
    cols = obs.get("columns", [])
    preview = obs.get("preview_rows", [])
    schema = obs.get("target_schema", {})
    constraints = obs.get("constraints", [])
    report = obs.get("validation_report", {})
    audit = obs.get("audit_trail", [])
    budget = obs.get("step_budget_remaining", 0)

    return textwrap.dedent(
        f"""
        Task: {obs.get('task_name')}
        Step budget remaining: {budget}

        Current columns: {cols}
        Target schema: {schema}
        Constraints: {constraints}

        Validation report: {report}
        Recent audit trail (last 5): {audit[-5:]}

        Dataset preview (first rows):
        {preview}

        Output the next action JSON now.
        """
    ).strip()


def _llm_next_action(client: OpenAI, obs: Dict[str, Any]) -> Tuple[TabCleanAction, Optional[str]]:
    """
    Always attempts an LLM call when credentials are present.
    Never raises: on failure, returns a safe noop and an error string.
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(obs)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        # Minimal JSON parsing without extra deps
        import json  # noqa: PLC0415

        obj = json.loads(text)
        op = obj.get("op", "noop")
        args = obj.get("args", {}) or {}
        return TabCleanAction(op=op, args=args), None
    except Exception as exc:
        return TabCleanAction(op="noop", args={}), _sanitize_error(str(exc))


async def _make_env() -> Any:
    # If a local docker image name is provided, let the client manage the container.
    if LOCAL_IMAGE_NAME:
        from_docker = getattr(TabCleanEnv, "from_docker_image", None)
        if callable(from_docker):
            return await from_docker(LOCAL_IMAGE_NAME)
    base_url = os.getenv("TAB_CLEAN_BASE_URL", f"http://localhost:{os.getenv('PORT', '8000')}")
    return TabCleanEnv(base_url=base_url)


async def run_task(task_name: str) -> None:
    if not API_KEY:
        log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
        print(f"CRITICAL: Missing credentials! API_BASE_URL={bool(API_BASE_URL)} API_KEY={bool(API_KEY)}", flush=True)
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return

    client = OpenAI(
        base_url=API_BASE_URL.strip().rstrip("/"),
        api_key=API_KEY.strip(),
    )
    env = await _make_env()

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        async with env:
            result = await env.reset(seed=0, task=task_name)

            for step in range(1, MAX_STEPS_DEFAULT + 1):
                if result.done:
                    break
                obs = result.observation.model_dump()

                action, err = _llm_next_action(client, obs)
                if err:
                    # If the proxy call fails, stop early (otherwise we'd keep running with no proxy traffic).
                    result = await env.step(TabCleanAction(op="noop", args={}))
                    steps_taken = step
                    r = float(result.reward or 0.0)
                    rewards.append(r)
                    score = float(
                        result.observation.validation_report.get("score_components", {}).get("total", score)
                    )
                    log_step(step=step, action=str({"op": "noop", "args": {}}), reward=r, done=True, error=err)
                    break

                result = await env.step(action)
                steps_taken = step
                r = float(result.reward or 0.0)
                rewards.append(r)

                # Server-side score proxy (0..1), included in the observation.
                score = float(
                    result.observation.validation_report.get("score_components", {}).get("total", score)
                )
                log_step(step=step, action=str(action.model_dump()), reward=r, done=bool(result.done), error=err)

                if result.done:
                    break

        success = score >= SUCCESS_SCORE_THRESHOLD
    except Exception as exc:
        print(f"ERROR in run_task({task_name}): {str(exc)[:200]}", flush=True)
        success = False
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main() -> None:
    if TASK_NAME:
        await run_task(TASK_NAME)
        return
    for t in TASKS:
        await run_task(t.name)


if __name__ == "__main__":
    asyncio.run(main())

