# ShelfVision — Local Setup (no Docker)

## Requisitos
- **uv** ≥ 0.5 — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Node.js 24.22.1 LTS** (parches de seguridad de octubre 2026) — instalar con `n 24.22.1`
  o vía nvm: `nvm install 24.22.1 && nvm use 24.22.1`
- **Python 3.12**

> ⚠️ **Node 22.x, 24.x ≤ 24.22.0 y 26.x ≤ 26.12.0 tienen vulnerabilidades críticas**
> (CVE-2026-111497 RCE en Brotli, CVE-2026-106069/105483 TLS bypass, CVE-2026-105482
> dns NUL truncation, entre otros). Usa **24.22.1 LTS** o **26.12.1+**.

---

## 1. Setup automático
```bash
chmod +x scripts/setup.sh scripts/run-backend.sh scripts/dev.sh
./scripts/setup.sh
```

El script:
1. Instala `uv` si no está
2. Crea `.venv` con Python 3.12 y `uv pip install -e ".[local,dev]"`
3. Instala Node 24.22.1 (vía `n`)
4. `npm install` en el frontend

---

## 2. Setup manual

### Backend (FastAPI + uv)
```bash
cd despleigue
uv venv --python 3.12
uv pip install -e ".[local,dev]"      # local model (YOLO)
# o para solo Lambda/RunPod:  uv pip install -e ".[dev]"

# Levantar
uv run uvicorn app.backend.main:app --reload --port 8000
# o:  ./scripts/run-backend.sh
```

Variables de entorno (`.env` en `despleigue/`):
```env
INFERENCE_BACKEND=local          # local | lambda | runpod
DATABASE_URL=sqlite:///./app/data/detections.db
JWT_SECRET=change-me-in-development-secret-32
MAX_UPLOAD_MB=10

# Si usas Lambda:
# INFERENCE_BACKEND=lambda
# LAMBDA_FUNCTION_NAME=tu-funcion
# AWS_REGION=us-east-1

# Si usas RunPod:
# INFERENCE_BACKEND=runpod
# RUNPOD_ENDPOINT_ID=tu-endpoint
# RUNPOD_API_KEY=tu-api-key
```

### Frontend (Next.js + React)
```bash
cd despleigue/app/frontend/object-detection-front
npm install
npm run dev
# http://localhost:3000  →  /demo  (pitch de 10 min)
```

El frontend habla con el backend vía rewrites de Next (`/backend/*` → `localhost:8000/api/v1/*`).

---

## 3. Demo pitch (10 min)
1. Abre `http://localhost:3000/demo`
2. Sube 6 capturas (08:00–18:00) o usa las de referencia
3. Elige backend de inferencia (Lambda por defecto / RunPod)
4. Click **Analizar captura**
5. Click **Generar reporte** → reporte ejecutivo Walmart ficticio

---

## 4. Producción (Docker)
```bash
cd despleigue/deploy
docker compose up --build
```
Ver `deploy/compose.yaml` para variables (ECR images, S3, secrets).
