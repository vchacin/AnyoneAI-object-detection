#!/usr/bin/env bash
# Setup script: uv + Node 24 LTS + dependencies
# Run: chmod +x scripts/setup.sh && ./scripts/setup.sh

set -euo pipefail

cd "$(dirname "$0")/.."

NODE_TARGET="24.22.1"
PYTHON_TARGET="3.12"

echo "=== ShelfVision Local Setup ==="

# --- uv ---
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

# --- Python venv ---
echo "Creating Python $PYTHON_TARGET venv with uv..."
uv venv --python "$PYTHON_TARGET"

echo "Installing backend dependencies..."
# Install deps directly (no editable build — sandbox-safe).
# For local inference (YOLO model runs locally), also add: ultralytics>=8.3.0
uv pip install \
    "fastapi>=0.110" "uvicorn[standard]>=0.29" "python-multipart>=0.0.9" \
    "pydantic>=2.6" "pydantic-settings>=2.2" "sqlalchemy>=2.0,<2.1" \
    "psycopg2-binary>=2.9" "alembic>=1.13" "PyJWT>=2.8" \
    "opencv-python-headless>=4.9" "numpy>=1.26" "pillow>=10.0" "pyyaml>=6.0" \
    "boto3>=1.34" "pytest>=8" "httpx>=0.27"

# --- Node ---
echo "Installing Node $NODE_TARGET via n..."
if ! command -v n &>/dev/null; then
    # Install n (Node version manager) if not present
    if command -v npm &>/dev/null; then
        npm install -g n
    else
        echo "npm not found. Install Node.js first or use nvm."
        exit 1
    fi
fi
n "$NODE_TARGET"
node -v
npm -v

echo "Installing frontend dependencies..."
cd app/frontend/object-detection-front
npm install

echo "=== Setup complete ==="
echo ""
echo "Backend: ./scripts/run-backend.sh   (or: uv run uvicorn app.backend.main:app --reload)"
echo "Frontend: cd app/frontend/object-detection-front && npm run dev"
