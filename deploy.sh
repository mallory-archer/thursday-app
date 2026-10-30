#!/usr/bin/env bash
# Apply schema.sql and load class_dataset.csv using the project virtualenv.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/venv/bin/python" ]]; then
  python3 -m venv "$ROOT/venv"
fi

"$ROOT/venv/bin/pip" install -q -r "$ROOT/requirements.txt"
exec "$ROOT/venv/bin/python" "$ROOT/deploy.py"
