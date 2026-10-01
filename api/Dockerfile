# Imagen de la API de deteccion. El repo se copia completo para que
# `api.gap_heuristic` sea importable como paquete (`api.*`).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Los pesos son el unico artifact pesado; se montan como volumen en compose.
ENV INFERENCE_WEIGHTS=/app/training/weights/best.pt

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
