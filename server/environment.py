from __future__ import annotations

import copy
import datetime as dt
import random
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from openenv.core.env_server import Environment

from models import ColumnType, TabCleanAction, TabCleanObservation, TabCleanState


@dataclass(frozen=True)
class TaskSpec:
    name: str
    step_budget: int
    id_column: str
    input_rows: List[Dict[str, Any]]
    target_rows: List[Dict[str, Any]]
    target_schema: Dict[str, ColumnType]
    constraints: List[Dict[str, Any]]


def _fixtures() -> Dict[str, TaskSpec]:
    # Small, deterministic fixtures. Keep them simple so grading stays rock-solid.
    # Easy: rename + cast + fill missing
    easy_input = [
        {"userId": "1", "age": "23", "country": "IN"},
        {"userId": "2", "age": "", "country": "in"},
        {"userId": "3", "age": " 41 ", "country": "US"},
        {"userId": "4", "age": "0", "country": "IN"},
    ]
    easy_target = [
        {"user_id": 1, "age": 23, "country": "IN"},
        {"user_id": 2, "age": 0, "country": "IN"},
        {"user_id": 3, "age": 41, "country": "US"},
        {"user_id": 4, "age": 0, "country": "IN"},
    ]
    easy_schema: Dict[str, ColumnType] = {"user_id": "int", "age": "int", "country": "string"}
    easy_constraints = [
        {"kind": "required", "column": "user_id"},
        {"kind": "required", "column": "age"},
        {"kind": "allowed_values", "column": "country", "params": {"values": ["IN", "US"]}},
        {"kind": "range", "column": "age", "params": {"min": 0, "max": 120}},
        {"kind": "unique", "column": "user_id"},
    ]

    # Medium: normalize + dedupe + enforce unique email + parse bool-ish inputs
    med_input = [
        {"id": "a1", "email": " Alice@Example.com ", "subscribed": "yes", "city": "bengaluru"},
        {"id": "a2", "email": "bob@example.com", "subscribed": "no", "city": "BENGALURU"},
        {"id": "a3", "email": "alice@example.com", "subscribed": "YES", "city": " Bengaluru "},
        {"id": "a4", "email": "carol@example.com", "subscribed": "", "city": "Delhi"},
    ]
    med_target = [
        {"id": "a1", "email": "alice@example.com", "subscribed": True, "city": "BENGALURU"},
        {"id": "a2", "email": "bob@example.com", "subscribed": False, "city": "BENGALURU"},
        {"id": "a4", "email": "carol@example.com", "subscribed": False, "city": "DELHI"},
    ]
    med_schema: Dict[str, ColumnType] = {
        "id": "string",
        "email": "string",
        "subscribed": "bool",
        "city": "string",
    }
    med_constraints = [
        {"kind": "required", "column": "id"},
        {"kind": "required", "column": "email"},
        {"kind": "unique", "column": "email"},
        {"kind": "allowed_values", "column": "subscribed", "params": {"values": [True, False]}},
    ]

    # Hard: split + date normalization + filtering invalid rows
    hard_input = [
        {"row_id": "1", "full_name": "Ada Lovelace", "signup": "2026/04/01", "country": "india"},
        {"row_id": "2", "full_name": " Alan  Turing ", "signup": "01-04-2026", "country": "IN"},
        {"row_id": "3", "full_name": "Grace Hopper", "signup": "2026-04-03", "country": "us"},
        {"row_id": "4", "full_name": "Bad Row", "signup": "not a date", "country": "??"},
    ]
    hard_target = [
        {"row_id": 1, "first_name": "ADA", "last_name": "LOVELACE", "signup_date": "2026-04-01", "country": "IN"},
        {"row_id": 2, "first_name": "ALAN", "last_name": "TURING", "signup_date": "2026-04-01", "country": "IN"},
        {"row_id": 3, "first_name": "GRACE", "last_name": "HOPPER", "signup_date": "2026-04-03", "country": "US"},
    ]
    hard_schema: Dict[str, ColumnType] = {
        "row_id": "int",
        "first_name": "string",
        "last_name": "string",
        "signup_date": "date_ymd",
        "country": "string",
    }
    hard_constraints = [
        {"kind": "required", "column": "row_id"},
        {"kind": "unique", "column": "row_id"},
        {"kind": "allowed_values", "column": "country", "params": {"values": ["IN", "US"]}},
        {"kind": "required", "column": "signup_date"},
    ]

    return {
        "easy_schemafix": TaskSpec(
            name="easy_schemafix",
            step_budget=6,
            id_column="user_id",
            input_rows=easy_input,
            target_rows=easy_target,
            target_schema=easy_schema,
            constraints=easy_constraints,
        ),
        "medium_dedupe_normalize": TaskSpec(
            name="medium_dedupe_normalize",
            step_budget=8,
            id_column="id",
            input_rows=med_input,
            target_rows=med_target,
            target_schema=med_schema,
            constraints=med_constraints,
        ),
        "hard_parse_normalize_filter": TaskSpec(
            name="hard_parse_normalize_filter",
            step_budget=10,
            id_column="row_id",
            input_rows=hard_input,
            target_rows=hard_target,
            target_schema=hard_schema,
            constraints=hard_constraints,
        ),
    }


def _to_str_cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _normalize_country(x: str) -> str:
    s = x.strip().upper()
    if s in {"INDIA", "IN"}:
        return "IN"
    if s in {"US", "USA", "UNITED STATES"}:
        return "US"
    return s


def _parse_date_ymd(s: str) -> Optional[str]:
    raw = s.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            d = dt.datetime.strptime(raw, fmt).date()
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _cast_value(v: Any, typ: ColumnType) -> Any:
    if v is None:
        return None
    if typ == "string":
        return str(v)
    if typ == "int":
        s = str(v).strip()
        if s == "":
            return None
        return int(float(s))
    if typ == "float":
        s = str(v).strip()
        if s == "":
            return None
        return float(s)
    if typ == "bool":
        s = str(v).strip().lower()
        if s in {"true", "t", "1", "yes", "y"}:
            return True
        if s in {"false", "f", "0", "no", "n", ""}:
            return False
        return None
    if typ == "date_ymd":
        return _parse_date_ymd(str(v))
    raise ValueError(f"unknown type: {typ}")


def _score_against_target(
    *,
    rows: List[Dict[str, Any]],
    target_rows: List[Dict[str, Any]],
    id_column: str,
    schema: Dict[str, ColumnType],
    constraints: List[Dict[str, Any]],
) -> Tuple[float, Dict[str, float], Dict[str, Any]]:
    # Align rows by id when we can.
    target_by_id = {r.get(id_column): r for r in target_rows if id_column in r}
    by_id = {r.get(id_column): r for r in rows if id_column in r}

    # Schema: required columns present
    required_cols = list(schema.keys())
    present = sum(1 for c in required_cols if all(c in r for r in rows)) / max(len(required_cols), 1)

    # Value correctness: exact match after casting to the target schema.
    total_cells = 0
    correct_cells = 0
    for tid, trow in target_by_id.items():
        row = by_id.get(tid)
        if row is None:
            continue
        for col, typ in schema.items():
            total_cells += 1
            try:
                v = _cast_value(row.get(col), typ)
            except Exception:
                v = None
            if v == trow.get(col):
                correct_cells += 1
    value_score = (correct_cells / total_cells) if total_cells else 0.0

    # Constraints: simple deterministic checks (required/unique/allowed/range)
    constraint_pass = 0
    for c in constraints:
        kind = c.get("kind")
        col = c.get("column")
        params = c.get("params", {}) or {}
        if kind == "required":
            ok = all((col in r) and (r.get(col) not in (None, "")) for r in rows)
        elif kind == "unique":
            seen = set()
            ok = True
            for r in rows:
                v = r.get(col)
                if v in seen:
                    ok = False
                    break
                seen.add(v)
        elif kind == "allowed_values":
            allowed = set(params.get("values", []))
            ok = all(r.get(col) in allowed for r in rows)
        elif kind == "range":
            mn = params.get("min")
            mx = params.get("max")
            ok = True
            for r in rows:
                v = r.get(col)
                if v in (None, ""):
                    continue
                try:
                    fv = float(v)
                except Exception:
                    ok = False
                    break
                if mn is not None and fv < mn:
                    ok = False
                    break
                if mx is not None and fv > mx:
                    ok = False
                    break
        else:
            ok = True
        constraint_pass += 1 if ok else 0
    constraint_score = constraint_pass / max(len(constraints), 1)

    schema_score = present
    total = max(0.0, min(1.0, 0.25 * schema_score + 0.25 * constraint_score + 0.50 * value_score))
    debug = {
        "total": total,
        "schema_score": schema_score,
        "constraint_score": constraint_score,
        "value_score": value_score,
    }
    report = {
        "missing_columns": [c for c in schema.keys() if any(c not in r for r in rows)],
        "rows_count": len(rows),
        "target_rows_count": len(target_rows),
    }
    return total, debug, report


class TabCleanEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._rng = random.Random(0)
        self._state = TabCleanState()
        self._task: Optional[TaskSpec] = None
        self._rows: List[Dict[str, Any]] = []
        self._audit: List[Dict[str, Any]] = []
        self._last_score: float = 0.0

    def reset(self, seed: int = 0, task: str = "easy_schemafix", episode_id: Optional[str] = None, **kwargs):
        tasks = _fixtures()
        if task not in tasks:
            task = "easy_schemafix"
        self._task = tasks[task]
        self._rng = random.Random(int(seed or 0))
        self._rows = copy.deepcopy(self._task.input_rows)
        self._audit = []
        self._last_score = 0.0
        self._state = TabCleanState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_name=self._task.name,
            dataset_name=self._task.name,
            step_budget=self._task.step_budget,
            seed=int(seed or 0),
        )
        obs = self._make_obs(done=False, reward=None, message="Episode started.")
        return obs

    def step(self, action: TabCleanAction, timeout_s: Optional[float] = None, **kwargs):
        assert self._task is not None, "reset() must be called first"
        self._state.step_count += 1

        msg = self._apply_action(action)

        # Reward is the score delta (clipped); score itself stays in the observation report.
        score, debug, report = _score_against_target(
            rows=self._rows,
            target_rows=self._task.target_rows,
            id_column=self._task.id_column,
            schema=self._task.target_schema,
            constraints=self._task.constraints,
        )
        delta = score - self._last_score
        self._last_score = score

        step_budget_remaining = max(0, self._task.step_budget - self._state.step_count)
        done = score >= 0.999 or step_budget_remaining <= 0
        # Dense reward: just progress for now.
        reward = max(0.0, min(1.0, delta))
        obs = self._make_obs(done=done, reward=reward, message=msg, debug=debug, report=report)
        return obs

    @property
    def state(self) -> TabCleanState:
        return self._state

    def _make_obs(
        self,
        *,
        done: bool,
        reward: Optional[float],
        message: str,
        debug: Optional[Dict[str, float]] = None,
        report: Optional[Dict[str, Any]] = None,
    ) -> TabCleanObservation:
        assert self._task is not None
        cols = sorted({k for r in self._rows for k in r.keys()})
        preview = []
        for r in self._rows[: min(10, len(self._rows))]:
            preview.append({c: _to_str_cell(r.get(c)) for c in cols})

        step_budget_remaining = max(0, self._task.step_budget - self._state.step_count)
        validation_report: Dict[str, Any] = {
            "score_components": debug or {},
            "report": report or {},
        }
        return TabCleanObservation(
            done=done,
            reward=reward,
            dataset_name=self._task.name,
            task_name=self._task.name,
            step_budget_remaining=step_budget_remaining,
            columns=cols,
            preview_rows=preview,
            target_schema=self._task.target_schema,
            constraints=self._task.constraints,
            validation_report=validation_report,
            audit_trail=list(self._audit),
            message=message,
        )

    def _apply_action(self, action: TabCleanAction) -> str:
        op = action.op
        args = action.args or {}

        if op == "noop":
            self._audit.append({"op": op, "args": args})
            return "No-op."

        if op == "rename_column":
            # Accept common aliases produced by LLMs.
            src = str(args.get("from") or args.get("old_name") or args.get("source") or "")
            dst = str(args.get("to") or args.get("new_name") or args.get("dest") or "")
            for r in self._rows:
                if src in r and dst not in r:
                    r[dst] = r.pop(src)
            self._audit.append({"op": op, "args": {"from": src, "to": dst}})
            return f"Renamed column {src!r} -> {dst!r}."

        if op == "drop_columns":
            cols = list(args.get("columns", []))
            for r in self._rows:
                for c in cols:
                    r.pop(c, None)
            self._audit.append({"op": op, "args": {"columns": cols}})
            return f"Dropped columns: {cols}."

        if op == "cast":
            col = str(args.get("column", ""))
            typ = args.get("type")
            if col and typ:
                for r in self._rows:
                    r[col] = _cast_value(r.get(col), typ)
            self._audit.append({"op": op, "args": {"column": col, "type": typ}})
            return f"Casted {col!r} to {typ!r}."

        if op == "fill_missing":
            col = str(args.get("column", ""))
            strategy = str(args.get("strategy", "constant"))
            constant = args.get("value", 0)
            vals = [r.get(col) for r in self._rows if r.get(col) not in (None, "", [])]
            fill = constant
            if strategy == "mode" and vals:
                fill = max(set(vals), key=vals.count)
            for r in self._rows:
                if r.get(col) in (None, ""):
                    r[col] = fill
            self._audit.append({"op": op, "args": {"column": col, "strategy": strategy, "value": constant}})
            return f"Filled missing for {col!r} using {strategy!r}."

        if op == "normalize_text":
            col = str(args.get("column", ""))
            mode = str(args.get("mode", "trim_lower"))
            for r in self._rows:
                v = r.get(col)
                if v is None:
                    continue
                s = str(v)
                if "trim" in mode:
                    s = s.strip()
                if "lower" in mode:
                    s = s.lower()
                if "upper" in mode:
                    s = s.upper()
                if mode == "country_iso2":
                    s = _normalize_country(s)
                r[col] = s
            self._audit.append({"op": op, "args": {"column": col, "mode": mode}})
            return f"Normalized text in {col!r} ({mode})."

        if op == "split_column":
            col = str(args.get("column", ""))
            sep = str(args.get("sep", " "))
            into = list(args.get("into", []))
            for r in self._rows:
                s = str(r.get(col, "")).strip()
                parts = [p for p in s.split(sep) if p]
                for i, new_col in enumerate(into):
                    r[new_col] = parts[i] if i < len(parts) else ""
            self._audit.append({"op": op, "args": {"column": col, "sep": sep, "into": into}})
            return f"Split {col!r} into {into}."

        if op == "merge_columns":
            into = str(args.get("into", ""))
            cols = list(args.get("columns", []))
            sep = str(args.get("sep", " "))
            for r in self._rows:
                r[into] = sep.join(str(r.get(c, "")).strip() for c in cols).strip()
            self._audit.append({"op": op, "args": {"into": into, "columns": cols, "sep": sep}})
            return f"Merged {cols} into {into!r}."

        if op == "dedupe":
            keys = list(args.get("keys", []))
            seen = set()
            new_rows = []
            for r in self._rows:
                k = tuple(r.get(x) for x in keys) if keys else tuple(sorted(r.items()))
                if k in seen:
                    continue
                seen.add(k)
                new_rows.append(r)
            self._rows = new_rows
            self._audit.append({"op": op, "args": {"keys": keys}})
            return f"Deduped by keys: {keys}."

        if op == "filter_rows":
            col = str(args.get("column", ""))
            op2 = str(args.get("op", "neq"))
            value = args.get("value")
            def keep(r: Dict[str, Any]) -> bool:
                v = r.get(col)
                if op2 == "neq":
                    return v != value
                if op2 == "eq":
                    return v == value
                if op2 == "in":
                    return v in set(value or [])
                if op2 == "not_in":
                    return v not in set(value or [])
                return True
            before = len(self._rows)
            self._rows = [r for r in self._rows if keep(r)]
            self._audit.append({"op": op, "args": {"column": col, "op": op2, "value": value}})
            return f"Filtered rows ({before} -> {len(self._rows)})."

        self._audit.append({"op": "noop", "args": {"unknown_op": op, "args": args}})
        return f"Unknown op {op!r}; treated as noop."

