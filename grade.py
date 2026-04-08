from __future__ import annotations

import os
from typing import Any, Dict

from models import TabCleanAction
from tasks.graders import TASKS, grade_task

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def noop_policy(_obs: Dict[str, Any]) -> TabCleanAction:
    return TabCleanAction(op="noop", args={})


def main() -> None:
    """
    Local scoring helper for smoke tests.

    This isn't the official evaluator; it's just a quick way to confirm:
    - tasks enumerate
    - scores land in [0, 1]
    - repeated runs are stable
    """
    base_url = os.getenv("TAB_CLEAN_BASE_URL", "http://localhost:8000")

    print(f"Grading against base_url={base_url}")
    for t in TASKS:
        score = grade_task(base_url=base_url, task=t, policy=noop_policy)
        print(f"{t.name}\tscore={score:.3f}")


if __name__ == "__main__":
    main()

