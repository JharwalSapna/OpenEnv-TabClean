from __future__ import annotations

import os

from openenv.core.env_server import create_fastapi_app
from fastapi.responses import HTMLResponse

from models import TabCleanAction, TabCleanObservation
from server.environment import TabCleanEnvironment

app = create_fastapi_app(TabCleanEnvironment, TabCleanAction, TabCleanObservation)

_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>OpenEnv TabClean</title>
    <style>
      :root{
        color-scheme: light dark;
        --bg: #0b0c10;
        --panel: rgba(255,255,255,.06);
        --panel2: rgba(255,255,255,.04);
        --border: rgba(255,255,255,.14);
        --muted: rgba(255,255,255,.70);
        --text: rgba(255,255,255,.92);
        --accent: #78a6ff;
        --accent2: #4fd1c5;
        --danger: #ff6b6b;
        --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      }
      @media (prefers-color-scheme: light){
        :root{
          --bg: #fafafa;
          --panel: rgba(0,0,0,.045);
          --panel2: rgba(0,0,0,.03);
          --border: rgba(0,0,0,.14);
          --muted: rgba(0,0,0,.70);
          --text: rgba(0,0,0,.88);
        }
      }
      body { font: 14px/1.45 var(--mono); margin: 26px; background: var(--bg); color: var(--text); }
      h1 { font-size: 18px; margin: 0 0 8px; }
      .muted { color: var(--muted); margin: 0 0 18px; max-width: 980px; }
      .grid { display: grid; grid-template-columns: 360px 1fr; gap: 14px; align-items: start; }
      @media (max-width: 980px){ .grid { grid-template-columns: 1fr; } }
      .card { border: 1px solid var(--border); border-radius: 14px; background: var(--panel2); padding: 12px; }
      .row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 10px 0; }
      .row.tight { margin: 6px 0; }
      label { color: var(--muted); }
      select, input, textarea, button {
        font: inherit;
        padding: 8px 10px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: var(--panel);
        color: inherit;
      }
      textarea { width: 100%; min-height: 120px; resize: vertical; }
      button { cursor: pointer; }
      button.primary { background: color-mix(in oklab, var(--accent) 22%, transparent); border-color: color-mix(in oklab, var(--accent) 60%, var(--border)); }
      button.secondary { background: color-mix(in oklab, var(--accent2) 16%, transparent); border-color: color-mix(in oklab, var(--accent2) 55%, var(--border)); }
      button.danger { background: color-mix(in oklab, var(--danger) 16%, transparent); border-color: color-mix(in oklab, var(--danger) 55%, var(--border)); }
      .pill { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 999px; border: 1px solid var(--border); background: var(--panel); color: var(--muted); }
      .mono { font-family: var(--mono); }
      a { color: inherit; }
      code { font-family: var(--mono); padding: 1px 6px; border-radius: 10px; border: 1px solid var(--border); background: var(--panel); }
      pre { padding: 12px; border-radius: 14px; border: 1px solid var(--border); background: rgba(0,0,0,.22); overflow: auto; max-height: 48vh; color: var(--text); }
      @media (prefers-color-scheme: light){ pre{ background: rgba(0,0,0,.04); } }
      table { width: 100%; border-collapse: collapse; font-size: 13px; }
      th, td { border-bottom: 1px solid var(--border); padding: 8px 8px; vertical-align: top; }
      th { text-align: left; color: var(--muted); font-weight: 600; position: sticky; top: 0; background: color-mix(in oklab, var(--bg) 86%, transparent); }
      .right { text-align: right; }
      .kpi { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      .k { border: 1px solid var(--border); border-radius: 14px; padding: 10px; background: var(--panel); }
      .k .name { color: var(--muted); font-size: 12px; }
      .k .val { font-size: 18px; margin-top: 2px; }
      .err { color: var(--danger); white-space: pre-wrap; }
    </style>
  </head>
  <body>
    <h1>OpenEnv TabClean</h1>
    <p class="muted">
      This is a <b>real OpenEnv environment</b> for tabular cleaning. The UI below demonstrates the core loop:
      <span class="mono"><code>/reset</code> → <code>/step</code>* → <code>/state</code></span>.
      API docs: <a href="/docs">/docs</a>.
    </p>

    <div class="grid">
      <div class="card">
        <div class="row tight">
          <span class="pill">Demo controls</span>
          <span class="pill">No secrets required</span>
        </div>

        <div class="row">
          <label>Task</label>
          <select id="task">
            <option value="easy_schemafix">easy_schemafix</option>
            <option value="medium_dedupe_normalize">medium_dedupe_normalize</option>
            <option value="hard_parse_normalize_filter">hard_parse_normalize_filter</option>
          </select>

          <label>Seed</label>
          <input id="seed" value="0" inputmode="numeric" size="6" />
        </div>

        <div class="row">
          <button class="primary" id="resetBtn">Reset</button>
          <button id="stateBtn">State</button>
          <button class="danger" id="clearBtn" title="Clear UI output (does not reset env)">Clear UI</button>
        </div>

        <div class="row">
          <label>Recommended actions</label>
        </div>
        <div class="row">
          <button class="secondary" data-act="easy_rename">easy: rename</button>
          <button class="secondary" data-act="easy_cast_user">easy: cast user</button>
          <button class="secondary" data-act="easy_cast_age">easy: cast age</button>
          <button class="secondary" data-act="easy_fill_age">easy: fill age</button>
          <button class="secondary" data-act="easy_norm_country">easy: normalize country</button>
        </div>
        <div class="row">
          <button class="secondary" data-act="med_norm_email">medium: norm email</button>
          <button class="secondary" data-act="med_norm_city">medium: norm city</button>
          <button class="secondary" data-act="med_cast_sub">medium: cast subscribed</button>
          <button class="secondary" data-act="med_fill_sub">medium: fill subscribed</button>
          <button class="secondary" data-act="med_dedupe">medium: dedupe</button>
        </div>
        <div class="row">
          <button class="secondary" data-act="hard_cast_id">hard: cast row_id</button>
          <button class="secondary" data-act="hard_rename_signup">hard: rename signup</button>
          <button class="secondary" data-act="hard_cast_date">hard: cast date</button>
          <button class="secondary" data-act="hard_split">hard: split name</button>
          <button class="secondary" data-act="hard_norm_names">hard: norm names</button>
          <button class="secondary" data-act="hard_norm_country">hard: norm country</button>
          <button class="secondary" data-act="hard_filter_country">hard: filter country</button>
        </div>

        <div class="row" style="margin-top:14px;">
          <label>Action JSON</label>
        </div>
        <textarea id="action">{ "op": "noop", "args": {} }</textarea>
        <div class="row">
          <button class="primary" id="stepBtn">Step</button>
        </div>

        <div class="row tight">
          <span class="pill">Tip</span>
          <span class="muted">Click a recommended action, then Step. Or edit JSON directly.</span>
        </div>
      </div>

      <div class="card">
        <div class="row tight">
          <span class="pill">Episode</span>
          <span class="pill mono" id="episodeId">episode: —</span>
          <span class="pill mono" id="stepInfo">step: —</span>
          <span class="pill mono" id="budgetInfo">budget: —</span>
        </div>

        <div class="kpi" style="margin: 10px 0;">
          <div class="k"><div class="name">Score</div><div class="val" id="scoreVal">—</div></div>
          <div class="k"><div class="name">Reward (Δ)</div><div class="val" id="rewardVal">—</div></div>
        </div>

        <div class="row tight">
          <span class="pill">Preview rows</span>
          <span class="pill">What changed after each step</span>
        </div>
        <div style="overflow:auto; max-height: 38vh; border: 1px solid var(--border); border-radius: 14px;">
          <table id="previewTable">
            <thead id="previewHead"></thead>
            <tbody id="previewBody"></tbody>
          </table>
        </div>

        <div class="row tight" style="margin-top:12px;">
          <span class="pill">Raw JSON</span>
          <span class="pill">For debugging / auditing</span>
        </div>
        <pre id="out">Ready.</pre>
        <div class="err" id="err"></div>
      </div>
    </div>

    <script>
      const out = document.getElementById("out");
      const err = document.getElementById("err");
      const task = document.getElementById("task");
      const seed = document.getElementById("seed");
      const action = document.getElementById("action");
      const episodeId = document.getElementById("episodeId");
      const stepInfo = document.getElementById("stepInfo");
      const budgetInfo = document.getElementById("budgetInfo");
      const scoreVal = document.getElementById("scoreVal");
      const rewardVal = document.getElementById("rewardVal");
      const previewHead = document.getElementById("previewHead");
      const previewBody = document.getElementById("previewBody");

      const ACTIONS = {
        easy_rename: { op: "rename_column", args: { from: "userId", to: "user_id" } },
        easy_cast_user: { op: "cast", args: { column: "user_id", type: "int" } },
        easy_cast_age: { op: "cast", args: { column: "age", type: "int" } },
        easy_fill_age: { op: "fill_missing", args: { column: "age", strategy: "constant", value: 0 } },
        easy_norm_country: { op: "normalize_text", args: { column: "country", mode: "country_iso2" } },

        med_norm_email: { op: "normalize_text", args: { column: "email", mode: "trim_lower" } },
        med_norm_city: { op: "normalize_text", args: { column: "city", mode: "trim_upper" } },
        med_cast_sub: { op: "cast", args: { column: "subscribed", type: "bool" } },
        med_fill_sub: { op: "fill_missing", args: { column: "subscribed", strategy: "constant", value: false } },
        med_dedupe: { op: "dedupe", args: { keys: ["email"] } },

        hard_cast_id: { op: "cast", args: { column: "row_id", type: "int" } },
        hard_rename_signup: { op: "rename_column", args: { from: "signup", to: "signup_date" } },
        hard_cast_date: { op: "cast", args: { column: "signup_date", type: "date_ymd" } },
        hard_split: { op: "split_column", args: { column: "full_name", sep: " ", into: ["first_name", "last_name"], take: "first_last" } },
        hard_norm_names: { op: "noop", args: {} }, // set dynamically (see handler)
        hard_norm_country: { op: "normalize_text", args: { column: "country", mode: "country_iso2" } },
        hard_filter_country: { op: "filter_rows", args: { column: "country", op: "in", value: ["IN", "US"] } },
      };

      function show(obj) {
        err.textContent = "";
        out.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
      }

      async function postJson(path, body) {
        const r = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body ?? {}),
        });
        const t = await r.text();
        let parsed;
        try { parsed = JSON.parse(t); } catch { parsed = t; }
        if (!r.ok) {
          err.textContent = typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2);
        }
        return parsed;
      }

      async function getJson(path) {
        const r = await fetch(path);
        const t = await r.text();
        let parsed;
        try { parsed = JSON.parse(t); } catch { parsed = t; }
        if (!r.ok) {
          err.textContent = typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2);
        }
        return parsed;
      }

      function setAction(a) {
        action.value = JSON.stringify(a, null, 2);
      }

      function renderPreview(obs) {
        if (!obs) return;
        const cols = obs.columns || [];
        const rows = obs.preview_rows || [];
        previewHead.innerHTML = "<tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr>";
        previewBody.innerHTML = rows.map(r => {
          return "<tr>" + cols.map(c => `<td>${(r && r[c] != null) ? String(r[c]) : ""}</td>`).join("") + "</tr>";
        }).join("");
      }

      function updateKpis(resp) {
        const obs = resp && (resp.observation || resp);
        if (!obs) return;
        if (obs.episode_id) episodeId.textContent = "episode: " + obs.episode_id;
        if (typeof obs.step_budget_remaining !== "undefined") budgetInfo.textContent = "budget: " + obs.step_budget_remaining;
        if (obs.task_name) stepInfo.textContent = "task: " + obs.task_name;
        const total = obs.validation_report && obs.validation_report.score_components && obs.validation_report.score_components.total;
        if (typeof total === "number") scoreVal.textContent = total.toFixed(3);
        if (typeof obs.reward === "number") rewardVal.textContent = obs.reward.toFixed(3);
        renderPreview(obs);
      }

      document.getElementById("resetBtn").addEventListener("click", async () => {
        show("Calling /reset ...");
        const body = { task: task.value, seed: Number(seed.value || 0) };
        const resp = await postJson("/reset", body);
        show(resp);
        updateKpis(resp);
      });

      document.getElementById("stepBtn").addEventListener("click", async () => {
        show("Calling /step ...");
        let parsed;
        try { parsed = JSON.parse(action.value); } catch (e) { err.textContent = "Invalid JSON: " + e; return; }
        const resp = await postJson("/step", { action: parsed, timeout_s: 30 });
        show(resp);
        updateKpis(resp);
      });

      document.getElementById("stateBtn").addEventListener("click", async () => {
        show("Calling /state ...");
        const resp = await getJson("/state");
        show(resp);
        updateKpis(resp);
      });

      document.getElementById("clearBtn").addEventListener("click", () => {
        out.textContent = "Ready.";
        err.textContent = "";
      });

      document.querySelectorAll("button[data-act]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const key = btn.getAttribute("data-act");
          if (key === "hard_norm_names") {
            // If columns exist, normalize both. Otherwise still useful as a hint.
            setAction({ op: "noop", args: {} });
            err.textContent = "For hard task: use normalize_text on first_name and last_name (trim_upper).";
            return;
          }
          setAction(ACTIONS[key] || { op: "noop", args: {} });
        });
      });
    </script>
  </body>
</html>
"""


@app.get("/", include_in_schema=False)
def home() -> HTMLResponse:
    return HTMLResponse(_UI_HTML)


@app.get("/ui", include_in_schema=False)
def ui() -> HTMLResponse:
    return HTMLResponse(_UI_HTML)


def main() -> None:
    """
    Entry point used by `openenv validate` and `uv run server`.
    """
    import uvicorn  # local import to keep import-time side effects minimal

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    uvicorn.run("server.app:app", host=host, port=port, workers=workers)


if __name__ == "__main__":
    main()

