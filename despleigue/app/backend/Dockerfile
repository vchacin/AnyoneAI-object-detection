FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INFERENCE_BACKEND=lambda \
    EXPERIMENT_REPORT_DIR=/app/app/data/reports/inference \
    UPLOAD_ROOT=/app/app/data/uploads
WORKDIR /app
COPY app/backend/requirements-runtime.txt /tmp/requirements-runtime.txt
RUN pip install --no-cache-dir -r /tmp/requirements-runtime.txt \
 && useradd --create-home --uid 10001 appuser \
 && mkdir -p /app/app/data/reports/inference /app/app/data/uploads \
 && chown -R appuser:appuser /app/app/data
COPY --chown=appuser:appuser app/__init__.py /app/app/__init__.py
COPY --chown=appuser:appuser app/backend /app/app/backend
RUN sed -i 's/\r$//' /app/app/backend/entrypoint.sh
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=4)"
CMD ["sh", "/app/app/backend/entrypoint.sh"]
