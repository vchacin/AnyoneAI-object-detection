#!/bin/sh
set -eu
alembic -c /app/app/backend/alembic.ini upgrade head
exec uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --workers 1
