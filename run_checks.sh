#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements.txt >/dev/null

echo "[1/5] openenv validate"
openenv validate

echo "[2/5] start server"
uvicorn server.app:app --host 0.0.0.0 --port 8000 >/tmp/tabclean-checks.log 2>&1 &
pid="$!"
sleep 2

cleanup() {
  kill "$pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[3/5] demo + grade"
python3 demo.py
python3 grade.py

echo "[4/5] docker build"
docker build -t tabclean-env:local . >/dev/null

echo "[5/5] docker run + ping"
docker rm -f tabclean-env-test >/dev/null 2>&1 || true
docker run -d --name tabclean-env-test -p 8001:8000 tabclean-env:local >/dev/null
sleep 2

retry() {
  local name="$1"
  shift
  local tries=10
  local delay_s=1
  local i
  for ((i=1; i<=tries; i++)); do
    if "$@"; then
      return 0
    fi
    echo "  retry($name) $i/$tries"
    sleep "$delay_s"
  done
  return 1
}

retry "health" curl -fsS -o /dev/null http://localhost:8001/health
retry "reset" curl -fsS -o /dev/null -X POST -H "Content-Type: application/json" -d '{}' http://localhost:8001/reset
docker rm -f tabclean-env-test >/dev/null

echo "OK"

