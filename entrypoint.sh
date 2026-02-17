#!/bin/sh
set -e

if command -v pybabel >/dev/null 2>&1; then
  pybabel compile -d app/locales || true
fi

python - <<'PY'
import os
import socket
import time

host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))

for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit(f"Postgres is not reachable at {host}:{port}")
PY

python -m alembic upgrade head

export PYTHONPATH=/app
exec python app/server/server.py
