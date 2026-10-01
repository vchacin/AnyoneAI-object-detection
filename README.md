# AnyoneAI — Object Detection

Detección de producto faltante en estanterías de retail sobre SKU-110K.

Monolito modular: un repositorio, un despliegue. El pipeline de ML se ejecuta en
un notebook que funciona igual en Colab (GPU) y en local (CPU/GPU). La heurística
geométrica de huecos (`api/gap_heuristic.py`) es la fuente de verdad compartida
entre el etiquetado offline y el serving.

## Estructura

```
.
├── data_pipeline/            # Datos: descarga, limpieza, conversión, EDA
│   ├── notebooks/eda.ipynb
│   ├── scripts/
│   │   ├── download_dataset.py    # S3 → data_pipeline/dataset_sku110k/{images,annotations}/
│   │   ├── clean_images.py        # verificación de imágenes corruptas
│   │   └── to_yolo_format.py      # CSV SKU-110K → labels YOLO
│   └── tests/
│
├── labeling/                  # Generación de etiquetas de la clase `missing`
│   ├── generate_missing_labels.py     # heurística geométrica offline
│   └── export_empty_class/
│       └── export_empty_class.py      # Brazo A (nc=1) y Brazo B (nc=2)
│
├── training/                  # Entrenamiento y evaluación
│   ├── pipeline_completo.ipynb  # notebook orquestador (Colab + local)
│   ├── evaluate.ipynb
│   ├── train.py                  # CLI equivalente al notebook
│   ├── configs/                  # data.yaml por brazo + YAMLs de validación
│   ├── weights/                  # .pt y runs (gitignored)
│   └── reports/                  # métricas y overlays (gitignored)
│
├── api/                       # Servicio FastAPI
│   ├── main.py                  # endpoints
│   ├── inference.py             # carga del modelo + predicción
│   ├── gap_heuristic.py         # heurística geométrica (fuente de verdad)
│   ├── auth.py                  # X-API-Key
│   ├── db.py                    # persistencia de detecciones
│   ├── static/index.html        # interfaz web
│   └── Dockerfile
│
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Los dos brazos del modelo

| Brazo | Clases | Qué aprende |
|-------|--------|-------------|
| **A** | `object` (nc=1) | Detecta los productos presentes |
| **B** | `object`, `missing` (nc=2) | Detecta productos y huecos |

El etiquetado de `missing` no es manual: `labeling/generate_missing_labels.py`
agrupa los productos en repisas, mide el *pitch* (ancho mediano de producto) y
propone como hueco todo espacio de ~1 producto. La misma heurística
(`api/gap_heuristic.py`) que genera las etiquetas se ejecuta en la API, de modo
que lo validado offline es exactamente lo que se sirve.

## Inicio rápido

### 1. Entorno

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### 2. Credenciales

```bash
cp .env.example .env        # rellenar AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
```

> El archivo `.env` contiene credenciales y está en `.gitignore`; nunca commitear.

### 3. Pipeline completo (Colab o local)

Abrir `training/pipeline_completo.ipynb` y ejecutar las celdas en orden:

| # | Celda | Acción |
|---|-------|--------|
| 1 | Setup | Resuelve `ROOT_DIR` (Colab o local) |
| 2 | Config | Hiperparametros, credenciales, detección automática de split |
| 3 | S3 | Descarga SKU-110K (salta si ya existe localmente) |
| 4 | Limpieza | Verifica imágenes corruptas con PIL |
| 5 | YOLO | CSV → formato YOLO (labels `.txt`) |
| 6 | Etiquetas | Heurística geométrica de `missing` (con barra de progreso) |
| 7 | Export | Genera configs YAML para Brazo A (nc=1) y Brazo B (nc=2) |
| 8 | Train | Entrenamiento con `YOLOv8` (incluye temporizador) |
| 9 | Eval | mAP50, mAP50-95, precisión, recall por clase |
| 10 | Post | Valida heurística sobre predicciones del modelo |

**Colab**: subir el ZIP a `/content/`, cambiar a GPU en *Runtime → Change runtime type*,
ejecutar celdas 1-2, luego 3-10.

**Local**: el primer celda detecta el entorno local y resuelve el directorio raíz
automáticamente. Las credenciales AWS se leen de `.env` en la raíz del repositorio.

### 4. API

```bash
uvicorn api.main:app --reload
# http://localhost:8000        interfaz web
# http://localhost:8000/docs   OpenAPI / Swagger
```

Con Docker:

```bash
docker compose up --build
```

## Uso por CLI (alternativa al notebook)

```bash
# 1. Descargar dataset (organiza automáticamente en images/ y annotations/)
python data_pipeline/scripts/download_dataset.py --limit 200

# Reorganizar archivos ya descargados sin volver a descargar:
python data_pipeline/scripts/download_dataset.py --skip-download --organize-existing

# 2. Verificar integridad de imágenes
python data_pipeline/scripts/clean_images.py \
  --input data_pipeline/dataset_sku110k/images \
  --report data_pipeline/dataset_sku110k/revision_imagenes.txt

# 3. Convertir CSV de SKU-110K a formato YOLO
python data_pipeline/scripts/to_yolo_format.py \
  --csv data_pipeline/dataset_sku110k/annotations/annotations_train.csv \
  --images-dir data_pipeline/dataset_sku110k/images \
  --out data_pipeline/dataset_sku110k/yolo/train

# 4. Generar etiquetas de `missing` con la heurística geométrica
#    --no-coco omite el detector de oclusión (requiere yolo26n.pt)
python labeling/generate_missing_labels.py \
  --images-dir data_pipeline/dataset_sku110k/images \
  --csv data_pipeline/dataset_sku110k/annotations/annotations_train.csv \
  --glob "train_*.jpg" --limit 200 \
  --out data_pipeline/dataset_sku110k/missing_poc \
  --auto-score 0.5 --no-coco

# 5. Exportar Brazo A (nc=1) y Brazo B (nc=2)
python labeling/export_empty_class/export_empty_class.py \
  --yolo-dir data_pipeline/dataset_sku110k/yolo/train \
  --images-dir data_pipeline/dataset_sku110k/images \
  --candidates data_pipeline/dataset_sku110k/missing_poc/candidates.csv \
  --arm both

# 6. Entrenar
python training/train.py --which A --epochs 35
python training/train.py --which B --epochs 35 --batch 8
```

## Pruebas

```bash
pytest data_pipeline/tests/ -v    # tests de la heurística de huecos (sin GPU)
```

Los tests verifican: agrupación de repisas, cálculo de pitch, detección de huecos
interiores y de borde, filtrado de candidatos solapantes, puntuación por apariencia
y robustez del ajuste Theil-Sen. 23 tests, 0.1s, no requieren GPU ni datos.

## Distribución de responsabilidades

| Área | Módulo |
|------|--------|
| Datos / EDA | `data_pipeline/` |
| Etiquetado | `labeling/` |
| Entrenamiento | `training/` |
| Servicio | `api/`, `docker-compose.yml` |
| Orquestación | `training/pipeline_completo.ipynb` |
| Heurística (fuente de verdad) | `api/gap_heuristic.py` |

## Documentación técnica

- `docs/ARCHITECTURE.md` — diagramas de módulos y dependencias
- `docs/REPORT.md` — informe técnico completo: flujo de datos, parámetros
  calibrados, rubricas de evaluación y resultados