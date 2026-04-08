from __future__ import annotations

import os

from client import TabCleanEnv
from models import TabCleanAction

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def main() -> None:
    """
    Small demo run for the submission checklist.
    """
    base_url = os.getenv("TAB_CLEAN_BASE_URL", "http://localhost:8000")
    task = os.getenv("TAB_CLEAN_TASK", "easy_schemafix")
    seed = int(os.getenv("TAB_CLEAN_SEED", "0"))

    print(f"Connecting to {base_url} task={task} seed={seed}")
    with TabCleanEnv(base_url=base_url).sync() as env:
        r = env.reset(task=task, seed=seed)
        print("Reset message:", r.observation.message)
        print("Columns:", r.observation.columns)
        print("Preview:", r.observation.preview_rows[:2])

        # One step, just to show the interface end-to-end.
        r = env.step(TabCleanAction(op="noop", args={}))
        print("Step message:", r.observation.message)
        print("Reward:", r.reward, "Done:", r.done)


if __name__ == "__main__":
    main()

