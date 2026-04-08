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
      :root { color-scheme: light dark; }
      body { font: 14px/1.45 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; margin: 28px; }
      h1 { font-size: 18px; margin: 0 0 6px; }
      .muted { opacity: .75; margin: 0 0 18px; }
      .row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 14px 0; }
      select, input, button { font: inherit; padding: 8px 10px; border-radius: 10px; border: 1px solid rgba(127,127,127,.35); background: transparent; }
      button { cursor: pointer; }
      button.primary { background: rgba(80,140,255,.18); border-color: rgba(80,140,255,.45); }
      pre { padding: 12px; border-radius: 12px; border: 1px solid rgba(127,127,127,.25); overflow: auto; max-height: 58vh; }
      a { color: inherit; }
      code { padding: 1px 6px; border-radius: 8px; border: 1px solid rgba(127,127,127,.25); }
    </style>
  </head>
  <body>
    <h1>OpenEnv TabClean</h1>
    <p class="muted">
      This Space hosts an <b>API-based</b> OpenEnv environment. Use the controls below to call <code>/reset</code>, <code>/step</code>, and <code>/state</code>.
      For full API docs, open <a href="/docs">/docs</a>.
    </p>

    <div class="row">
      <label>Task</label>
      <select id="task">
        <option value="easy_schemafix">easy_schemafix</option>
        <option value="medium_dedupe_normalize">medium_dedupe_normalize</option>
        <option value="hard_parse_normalize_filter">hard_parse_normalize_filter</option>
      </select>

      <label>Seed</label>
      <input id="seed" value="0" size="6" />

      <button class="primary" id="resetBtn">Reset</button>
      <button id="stateBtn">State</button>
    </div>

    <div class="row">
      <label>Action JSON</label>
      <input id="action" size="62" value='{"op":"noop","args":{}}' />
      <button class="primary" id="stepBtn">Step</button>
    </div>

    <pre id="out">Ready.</pre>

    <script>
      const out = document.getElementById("out");
      const task = document.getElementById("task");
      const seed = document.getElementById("seed");
      const action = document.getElementById("action");

      function show(obj) {
        out.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
      }

      async function postJson(path, body) {
        const r = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body ?? {}),
        });
        const t = await r.text();
        try { return JSON.parse(t); } catch { return t; }
      }

      async function getJson(path) {
        const r = await fetch(path);
        const t = await r.text();
        try { return JSON.parse(t); } catch { return t; }
      }

      document.getElementById("resetBtn").addEventListener("click", async () => {
        show("Calling /reset ...");
        const body = { task: task.value, seed: Number(seed.value || 0) };
        show(await postJson("/reset", body));
      });

      document.getElementById("stepBtn").addEventListener("click", async () => {
        show("Calling /step ...");
        let parsed;
        try { parsed = JSON.parse(action.value); } catch (e) { show("Invalid JSON: " + e); return; }
        show(await postJson("/step", parsed));
      });

      document.getElementById("stateBtn").addEventListener("click", async () => {
        show("Calling /state ...");
        show(await getJson("/state"));
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

