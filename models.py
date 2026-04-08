from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from openenv.core.env_server import Action, Observation, State
from pydantic import Field


ColumnType = Literal["string", "int", "float", "bool", "date_ymd"]


class TabCleanAction(Action):
    op: Literal[
        "rename_column",
        "drop_columns",
        "cast",
        "fill_missing",
        "normalize_text",
        "split_column",
        "merge_columns",
        "dedupe",
        "filter_rows",
        "noop",
    ]
    args: Dict[str, Any] = Field(default_factory=dict)


class TabCleanObservation(Observation):
    dataset_name: str
    task_name: str
    step_budget_remaining: int

    columns: List[str]
    preview_rows: List[Dict[str, str]]

    target_schema: Dict[str, ColumnType]
    constraints: List[Dict[str, Any]]

    validation_report: Dict[str, Any]
    audit_trail: List[Dict[str, Any]]
    message: str = ""


class TabCleanState(State):
    task_name: str = ""
    dataset_name: str = ""
    step_budget: int = 0
    seed: int = 0

