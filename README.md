# AnyoneAI — Object Detection

Detección de producto faltante en estanterías de retail sobre SKU-110K.

Monolito modular: un repositorio, un despliegue. El pipeline de ML se ejecuta en
un notebook que funciona igual en Colab (GPU) y en local (CPU/GPU). La heurística
geométrica de huecos (`app/backend/services/gap_heuristic.py`) es la fuente de verdad compartida
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
├── app/
│   ├── backend/               # Servicio FastAPI e infraestructura SDD
│   └── frontend/.gitkeep      # Reservado para la interfaz futura
├── modelos/                   # Checkpoint oficial de master
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
├── app/backend/requirements-runtime.txt
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
(`app/backend/services/gap_heuristic.py`) que genera las etiquetas se ejecuta en la API, de modo
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
# Con SQLite local (sin PostgreSQL externo, ideal para pruebas rápidas):
DATABASE_URL=sqlite:///./app/data/detections.db uvicorn app.backend.main:app --reload
# http://localhost:8000                 interfaz web
# http://localhost:8000/api/v1/health   estado del servicio
# http://localhost:8000/docs            OpenAPI / Swagger

# Con PostgreSQL (Neon o local):
uvicorn app.backend.main:app --reload
```

Con Docker:

```bash
docker compose up --build
```

Para la imagen de producción CPU-only, sin dependencias de entrenamiento ni
CUDA:

```bash
docker build -t backend-prod:latest -f app/backend/Dockerfile .
docker run -d --name backend-prod \
  --memory=1g --cpus=1 -p 8000:8000 \
  -v "${PWD}/modelos:/models:ro" \
  backend-prod:latest
```

En PowerShell:

```powershell
docker build -t backend-prod:latest -f app\backend\Dockerfile .
docker run -d --name backend-prod `
  --memory=1g --cpus=1 -p 8000:8000 `
  -v "${PWD}\modelos:/models:ro" `
  backend-prod:latest
```

La imagen no contiene los pesos `.pt`/`.onnx`; deben montarse en `/models`.
El contenedor usa un único worker y PyTorch CPU. Verificación rápida:

```bash
docker images backend-prod:latest
curl -s http://localhost:8000/health
docker stats backend-prod --no-stream
```

La prueba de inferencia requiere una imagen local:

```bash
curl -X POST "http://localhost:8000/api/v1/inference" \
  -H "accept: application/json" \
  -F "file=@ruta/a/estanteria.jpg"
```

Para detener y eliminar el contenedor de prueba:

```bash
docker rm -f backend-prod
```

La documentación OpenAPI está disponible en `/docs`. La referencia de rutas
del backend está en [`docs/API.md`](docs/API.md). La base de datos se prepara
con:

```bash
python -m alembic upgrade head
```

Las imágenes de desarrollo se guardan en `app/data/uploads/`, excluidas del
control de versiones. En Docker se usan los volúmenes `uploads-data`,
`postgres-data` y, opcionalmente, `minio-data`. Los reportes runtime se
guardan en `/app/app/data/reports/inference`.

### 5. Runtime y desarrollo

`requirements.txt` conserva las dependencias completas para entrenamiento,
análisis y pruebas. La imagen de producción instala únicamente
`app/backend/requirements-runtime.txt`; excluye `pandas`, `matplotlib`,
`tqdm`, `pytest` y `httpx`.

La imagen runtime está optimizada para CPU:

```text
backend-prod:latest  ~2.46 GB
PyTorch              CPU-only
CUDA                 deshabilitado
```

Para liberar caché de construcción sin eliminar volúmenes:

```bash
docker builder prune -f
docker container prune -f
```

No ejecutar `docker system prune --volumes` en un entorno con datos
persistentes.

### 5. Seleccion de modelos y bitacora

La explicacion detallada de diferencias de entrenamiento, pesos y flujo de
inferencia esta en [`docs/MODEL_COMPARISON.md`](docs/MODEL_COMPARISON.md). El
analisis de la primera revision humana esta en
[`docs/REVIEW_ANALYSIS.md`](docs/REVIEW_ANALYSIS.md).

El backend conserva `official` como modelo predeterminado y tambien incluye
`shelfvision`, el pipeline compuesto entregado por el companero. ShelfVision
usa dos pesos (`product_best.pt` y `missing_best.pt`), agrupacion geometrica de
filas, analisis OpenCV y fusion de scores. Los pesos se encuentran en
`modelos/shelfvision/` y sus hashes corresponden a `MODEL_MANIFEST.json` del
proyecto de origen.

Consultar modelos disponibles sin cargar pesos:

```bash
curl http://localhost:8000/api/v1/models
```

Seleccionar un modelo por solicitud:

```bash
curl -X POST \
  -F "image=@C:/ruta/estanteria.jpg" \
  "http://localhost:8000/api/v1/inference?model=official"

curl -X POST \
  -F "image=@C:/ruta/estanteria.jpg" \
  "http://localhost:8000/api/v1/inference?model=shelfvision"
```

Tambien se puede cambiar el valor predeterminado con `DEFAULT_MODEL`. Los
modelos se cargan de forma perezosa y la respuesta incluye `model_name`,
`model_version` y `experiment_id`.

Cada inferencia genera un JSON unico en `training/reports/inference/` con el
modelo, version, hashes de pesos, parametros, conteos, latencia y dimensiones
de la imagen. Estos reportes son bitacora operativa; para afirmar que un
modelo es mejor se deben ejecutar ambos sobre el mismo conjunto de prueba
etiquetado y comparar precision, recall, mAP, falsos positivos/negativos y
latencia P50/P95. Una imagen aislada como `001.jpg` sirve como smoke test, no
como evaluacion estadistica.

#### Comparacion visual sin labels de `missing`

Cuando no hay etiquetas humanas de faltantes, se puede generar una corrida
para revision manual. El comando toma una muestra aleatoria reproducible,
ejecuta ambos modelos y guarda dos imagenes anotadas por caso:

```bash
python training/compare_models.py --count 538 --seed 42
```

Luego iniciar la API y abrir:

```text
http://localhost:8000/comparison
```

La interfaz muestra los resultados lado a lado y permite marcar `Gana oficial`,
`Gana ShelfVision`, `Empate` o `No claro`, además de una nota. Las respuestas
se guardan en `app/data/comparisons/<run_id>/reviews.jsonl`; el manifest y las
imagenes anotadas quedan en la misma corrida. Este procedimiento mide la
preferencia visual humana sobre las mismas imagenes, pero no sustituye mAP ni
precision/recall hasta disponer de labels revisados.

## Uso por CLI (alternativa al notebook)

### Reentrenamiento desde Colab

Para crear una nueva versión después de la revisión visual, abrir
`training/pipeline_completo.ipynb` y ejecutar las 11 celdas en orden. La
configuración recomendada parte del checkpoint oficial y conserva el brazo B:

```python
import os
os.environ["EXPERIMENT_NAME"] = "B_hard_examples_v1"
os.environ["INIT_WEIGHTS"] = "modelos/best.pt"
os.environ["TRAIN_ARM"] = "B"
os.environ["TRAIN_EPOCHS"] = "50"
```

Antes de entrenar, añadir al dataset ejemplos etiquetados de las fallas
observadas: bebidas lejanas, perspectiva, productos pequeños y faltantes fuera
de margen. `reviews.jsonl` sirve para priorizar imágenes, pero sus veredictos
no son labels de entrenamiento; las cajas `missing` deben revisarse y marcarse
manualmente.

Para conservar intactos los labels `object`, exporta desde CVAT, Label Studio
o Roboflow sólo las cajas `missing` en YOLO (una clase, normalmente id `0`) y
guárdalas como `data_pipeline/manual_missing/labels/*.txt`. Convierte esas
cajas al formato usado por el pipeline:

```bash
python labeling/manual_yolo_to_candidates.py \
  --images-dir data_pipeline/dataset_sku110k/images \
  --labels-dir data_pipeline/manual_missing/labels \
  --out data_pipeline/manual_missing/candidates.csv
```

Después configura `MANUAL_MISSING_CSV` con ese CSV antes de ejecutar la celda
7. El pipeline añadirá esas cajas como clase `missing` al brazo B sin borrar ni
reemplazar ninguna caja `object`.

La última celda genera y descarga un paquete con `best.pt`, `metrics.json`,
`train_config.json` y `MODEL_MANIFEST.json`. Para probarlo localmente se puede
copiar el checkpoint a `modelos/experiments/<run_name>/best.pt` y configurarlo
como `SHELFVISION_*` sólo si corresponde al pipeline ShelfVision; un nuevo
checkpoint del oficial debe conservar su contrato de clases y reemplazarse de
forma controlada como `MODEL_PATH`.

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
| Servicio | `app/backend/`, `docker-compose.yml` |
| Orquestación | `training/pipeline_completo.ipynb` |
| Heurística (fuente de verdad) | `app/backend/services/gap_heuristic.py` |

## Documentación técnica

- `docs/ARCHITECTURE.md` — diagramas de módulos y dependencias
- `docs/REPORT.md` — informe técnico completo: flujo de datos, parámetros
  calibrados, rubricas de evaluación y resultados