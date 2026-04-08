from __future__ import annotations

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from models import TabCleanAction, TabCleanObservation, TabCleanState


class TabCleanEnv(EnvClient[TabCleanAction, TabCleanObservation, TabCleanState]):
    def _step_payload(self, action: TabCleanAction) -> dict:
        return {"op": action.op, "args": action.args}

    def _parse_result(self, payload: dict) -> StepResult:
        obs_data = payload.get("observation", {}) or {}
        return StepResult(
            observation=TabCleanObservation(
                done=payload.get("done", False),
                reward=payload.get("reward"),
                dataset_name=obs_data.get("dataset_name", ""),
                task_name=obs_data.get("task_name", ""),
                step_budget_remaining=obs_data.get("step_budget_remaining", 0),
                columns=obs_data.get("columns", []),
                preview_rows=obs_data.get("preview_rows", []),
                target_schema=obs_data.get("target_schema", {}),
                constraints=obs_data.get("constraints", []),
                validation_report=obs_data.get("validation_report", {}),
                audit_trail=obs_data.get("audit_trail", []),
                message=obs_data.get("message", ""),
            ),
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> TabCleanState:
        return TabCleanState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_name=payload.get("task_name", ""),
            dataset_name=payload.get("dataset_name", ""),
            step_budget=payload.get("step_budget", 0),
            seed=payload.get("seed", 0),
        )

