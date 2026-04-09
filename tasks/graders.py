from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from client import TabCleanEnv
from models import TabCleanAction


@dataclass(frozen=True)
class Task:
    name: str
    seed: int
    max_steps: int
    task_param: str


TASKS: List[Task] = [
    Task(name="easy_schemafix", seed=0, max_steps=6, task_param="easy_schemafix"),
    Task(name="medium_dedupe_normalize", seed=0, max_steps=8, task_param="medium_dedupe_normalize"),
    Task(name="hard_parse_normalize_filter", seed=0, max_steps=9, task_param="hard_parse_normalize_filter"),
]


def grade_task(base_url: str, task: Task, policy: Callable[[dict], TabCleanAction]) -> float:
    with TabCleanEnv(base_url=base_url).sync() as env:
        result = env.reset(seed=task.seed, task=task.task_param)
        best = 0.0
        for _ in range(task.max_steps):
            if result.done:
                break
            action = policy(result.observation.model_dump())
            result = env.step(action)
            sc = float(result.observation.validation_report.get("score_components", {}).get("total", 0.0))
            if sc > best:
                best = sc
        _EPS = 1e-4
        return max(_EPS, min(1.0 - _EPS, best))


def list_tasks() -> List[str]:
    return [t.name for t in TASKS]

