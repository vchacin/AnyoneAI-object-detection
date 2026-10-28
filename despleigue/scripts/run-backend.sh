#!/usr/bin/env bash
# Run the backend with uv (no Docker). Executed from despleigue/ root.
set -euo pipefail

cd "$(dirname "$0")/.."

# Default env for local dev (override via .env or exported vars)
export INFERENCE_BACKEND="${INFERENCE_BACKEND:-local}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./app/data/detections.db}"
export JWT_SECRET="${JWT_SECRET:-change-me-in-development-secret-32}"
export MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-10}"

# Ensure uv-managed venv exists
if [ ! -d ".venv" ]; then
    echo "No .venv found. Run ./scripts/setup.sh first (or: uv venv && uv pip install -e '.[local,dev]')"
    exit 1
fi

echo "=== ShelfVision Backend (uv) ==="
echo "Inference backend: $INFERENCE_BACKEND"
echo "Database: $DATABASE_URL"

exec env PYTHONPATH=. uv run uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000
