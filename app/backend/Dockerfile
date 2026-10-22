# CPU-only production image for the FastAPI inference service.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_ROOT=/models \
    MODEL_MANIFEST=/app/modelos/manifest.json \
    MODEL_PATH=/models/best.pt \
    INFERENCE_WEIGHTS=/models/best.pt \
    EXPERIMENT_REPORT_DIR=/app/app/data/reports/inference \
    UPLOAD_ROOT=/app/app/data/uploads

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 appuser \
 && mkdir -p /app/app/data/uploads /app/app/data/reports/inference /app/modelos

COPY app/backend/requirements-runtime.txt /tmp/requirements-runtime.txt
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r /tmp/requirements-runtime.txt \
 && rm -rf /usr/local/lib/python3.11/site-packages/torch/include \
           /usr/local/lib/python3.11/site-packages/torch/test \
 && find /usr/local/lib/python3.11/site-packages/torch/bin -type f \
           ! -name torch_shm_manager -delete \
 && rm -f /tmp/requirements-runtime.txt

COPY --chown=appuser:appuser app/backend /app/app/backend
COPY --chown=appuser:appuser modelos/manifest.json /app/modelos/manifest.json
RUN chown -R appuser:appuser /app/app/data /home/appuser

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
