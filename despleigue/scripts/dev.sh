#!/usr/bin/env bash
# Start both backend and frontend in dev mode (requires tmux or two terminals)
set -euo pipefail

cd "$(dirname "$0")/.."

BACKEND_DIR="app/backend"
FRONTEND_DIR="app/frontend/object-detection-front"

# Default env for local dev
export INFERENCE_BACKEND="${INFERENCE_BACKEND:-local}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./app/data/detections.db}"
export JWT_SECRET="${JWT_SECRET:-change-me-in-development-secret-32}"
export MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-10}"

echo "=== Starting ShelfVision Dev ==="
echo "Inference backend: $INFERENCE_BACKEND"
echo "Database: $DATABASE_URL"

if command -v tmux &>/dev/null; then
    SESSION="shelfvision"
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    tmux new-session -d -s "$SESSION" -n backend "cd $BACKEND_DIR && uv run uvicorn app.backend.main:app --reload --port 8000"
    tmux new-window -t "$SESSION" -n frontend "cd $FRONTEND_DIR && npm run dev"
    tmux attach -t "$SESSION"
else
    echo "tmux not found. Starting backend in foreground..."
    echo "Open another terminal and run: cd $FRONTEND_DIR && npm run dev"
    cd "$BACKEND_DIR" && uv run uvicorn app.backend.main:app --reload --port 8000
fi
