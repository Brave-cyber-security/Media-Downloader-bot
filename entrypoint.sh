#!/bin/sh
set -e

if command -v pybabel >/dev/null 2>&1; then
  pybabel compile -d app/locales || true
fi

python -m alembic upgrade head

export PYTHONPATH=/app
exec python app/server/server.py
