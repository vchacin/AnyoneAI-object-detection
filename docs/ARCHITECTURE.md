# Arquitectura — AnyoneAI Object Detection

Monolito modular: un repositorio, un despliegue, módulos con frontera explícita.
Este documento es la referencia de qué depende de qué.

## Vista de módulos

```mermaid
flowchart TB
    %% ---- fuentes externas
    S3[("S3\nanyoneai-datasets/SKU-110K")]
    GH[("GitHub\nvchacin/AnyoneAI-object-detection")]
    Colab["Google Colab\n(GPU)"]
    Local["PC local\n(CPU/GPU)"]

    %% ---- data_pipeline
    subgraph DP["data_pipeline — Datos"]
        DL["download_dataset.py\n• S3 → dataset_sku110k\n• credenciales por env"]
        CI["clean_images.py\n• escaneo de corruptas\n• reporte"]
        TY["to_yolo_format.py\n• CSV SKU110K → YOLO\n• normaliza a [0,1]"]
        EDA["notebooks/eda.ipynb\n• distribuciones, densidades"]
    end

    %% ---- labeling
    subgraph LB["labeling — Etiquetas"]
        GM["generate_missing_labels.py\n• CLI offline\n• escribe candidates.csv"]
    end

    %% ---- heuristica (modulo compartido)
    subgraph GH2["app/backend/services/gap_heuristic.py — Núcleo geométrico"]
        GEO["group_rows → row_pitch → row_slots\nrow_edges (Theil-Sen) → overlaps_object"]
        APP["appearance\n• score [0,1] por intensidad + bordes"]
        SCO["score_candidates\n• pipeline compartido"]
    end

    EXE["export_empty_class/\n• Brazo A (nc=1) + Brazo B (nc=2)\n• escribe training/configs/*.yaml"]

    %% ---- training
    subgraph TR["training — Modelo"]
        NB["pipeline_completo.ipynb\n• setup Colab/local\n• orquesta todo el flujo"]
        EV["evaluate.ipynb\n• mAP50 / mAP50-95 por clase"]
        TN["train.py\n• CLI equivalente al notebook"]
        CFG["configs/\n• data_arm_a.yaml, data_arm_b.yaml\n• test_obj.yaml, test_2cls.yaml"]
        W["weights/ (gitignored)\n• yolo26s.pt base\n• best.pt / last.pt"]
    end

    %% ---- backend
    subgraph API["app/backend — Servicio"]
        MAIN["main.py\n• POST /api/v1/inference\n• GET /api/v1/health"]
        INF["services/inference_service.py\n• modelo B + heurística\n• deduplicación"]
        AU["core/security.py\n• X-API-Key + JWT futuro"]
        DB["db/session.py\n• detections (transitorio)"]
        UI["static/index.html"]
    end

    %% ---- dependencias
    S3 --> DL
    GH --> Colab
    DL --> CI --> TY --> EDA
    TY --> GM
    GM --> GEO
    GM --> APP
    SCO --> GEO
    SCO --> APP
    GM --> SCO
    GM --> EXE
    TY --> EXE
    EXE --> CFG
    CFG --> TN
    CFG --> NB
    NB --> TN
    TN --> W
    W --> EV
    W --> INF
    NB --> SCO
    INF --> SCO
    MAIN --> INF
    MAIN --> AU
    MAIN --> DB
    MAIN --> UI
    Local --> NB
    Colab --> NB
```

## Frontera de módulos

| Módulo | Responsabilidad | No hace |
|--------|-----------------|---------|
| `data_pipeline` | Conseguir y limpiar datos crudos | No entrena, no sirve |
| `labeling` | Derivar etiquetas (`missing`) y `data.yaml` | No entrena |
| `app/backend/services/gap_heuristic.py` | Geometría pura de huecos | No conoce FastAPI ni Ultralytics |
| `training` | Entrenar y evaluar | No lee S3 directamente (utiliza el notebook) |
| `app/backend` | Servir predicciones e infraestructura | No accede al dataset |

La regla que hace que esto funcione: **`app/backend/services/gap_heuristic.py` no importa nada
de `app/backend/`, `ultralytics` ni `fastapi`**. Es geometría pura sobre listas de
cajas. Esto permite que el etiquetado offline y el servicio en producción usen
literalmente el mismo código, y que la heurística se pruebe con `pytest` sin
GPU.

## Flujo de datos

```mermaid
flowchart LR
    S3[("S3<br/>SKU-110K")] -->|download_dataset| RAW["dataset_sku110k/<br/>images + annotations"]
    RAW -->|clean_images| CLEAN["imágenes verificadas"]
    RAW -->|to_yolo_format| YOLO["yolo/train/labels<br/>object"]
    CLEAN -->|generate_missing_labels| CAND["missing_poc/<br/>candidates.csv"]
    YOLO --> GEO{{"gap_heuristic<br/>(geometry)"}}
    CAND --> GEO
    GEO -->|export_empty_class| ARM["data_arm_a.yaml (nc=1)<br/>data_arm_b.yaml (nc=2)"]
    ARM -->|train| W["best.pt"]
    W -->|val| M["mAP50 / mAP50-95"]
    W -->|inference| SVC["POST /api/v1/inference"]
    W -.->|misos pesos| GEO
```

## Strategy params

Todos los parámetros de la heurística se definen al inicio de
`app/backend/services/gap_heuristic.py` y se calibraron sobre 50 imágenes con ground truth humano:

| Knob | Valor | Significado |
|------|-------|-------------|
| `ROW_TOL` | 0.5 | Tolerancia de `y2` para agrupar en la misma repisa |
| `GAP_MIN_FRAC` | 0.6 | Hueco mínimo como fracción del pitch |
| `MAX_SLOTS` | 4 | Máximo de productos faltantes consecutivos por hueco |
| `EDGE_MIN_ROW` | 6 | Densidad mínima de una fila para emitir huecos de borde |
| `DARK` / `BRIGHT` | 30 / 90 | Rango de intensidad gris que puntúa como "fondo" |
| `EDGE_LOW` / `EDGE_HIGH` | 2 / 10 | Rango de magnitud de gradiente |
| `AUTO_SCORE` | 0.5 | Umbral para aceptar un hueco |

Se modifican en un único lugar y afectan por igual al etiquetado y a la API.

## Dependencias internas

```mermaid
graph LR
    Main["app/backend/main.py"] --> Auth["app/backend/core/security.py"]
    Main --> DB["app/backend/db/session.py"]
    Main --> Inf["app/backend/services/inference_service.py"]
    Inf --> Gap["app/backend/services/gap_heuristic.py"]
    Gap --> NP["numpy"]
    Gen["labeling/generate_missing_labels.py"] --> Gap
    Gen --> CV2["cv2"]
    Exp["labeling/export_empty_class/"] --> Gap
    Exp --> YAML["pyyaml"]
    Train["training/train.py"] --> UL["ultralytics.YOLO"]
    NB["training/pipeline_completo.ipynb"] --> Train
    NB --> Gen
    NB --> Exp
    NB --> DL["data_pipeline/scripts/"]
```

## Arquitectura objetivo

El checkpoint oficial incorporado desde `master` vive en `modelos/best.pt` y se
monta como solo lectura en Docker. El serving utiliza la clase aprendida
`missing` cuando está disponible, conserva la heurística como complemento y
deduplica candidatos coincidentes por IoU. `app/frontend/` queda reservado para
la interfaz futura; routers, schemas y servicios aún no implementados son stubs
documentales definidos por el SDD.

## Decisiones

**Notebook todo terreno en lugar de scripts sueltos.** Colab y local ejecutan el
mismo flujo porque la celda 1 resuelve el entorno, dependencias y `ROOT_DIR`.
Los archivos `.py` existen igual (el notebook los invoca por subprocess) para
que el pipeline sea testeable y utilizable desde CI.

**La heurística no se reimplementa en la API.** `app/backend/services/gap_heuristic.py` es
geometría pura; tanto el etiquetador como el servicio la importan. Si divergieran,
un candidato aceptado por el notebook desaparecería en producción.

**`data.yaml` con ruta absoluta.** Ultralytics resuelve `path` relativo contra la
carpeta del propio yaml, no contra la raíz del repositorio, por lo que relativo
sería silenciosamente incorrecto. `export_empty_class.py` y el notebook
regeneran el yaml con la ruta real en cada entorno.

**`missing` se etiqueta por geometría, no manualmente.** El pitch de una repisa
es estable; los huecos de ≈1 producto se deducen. Esto permite escalar el brazo B
a las 8 000+ imágenes de entrenamiento.

## Seleccion de pipelines

El servicio mantiene un catalogo en `app/backend/services/model_registry.py`.
`official` conserva el flujo existente: un detector YOLO con la heuristica
compartida. `shelfvision` es un adaptador aislado que combina los pesos de
productos y faltantes del proyecto ShelfVision con agrupacion geometrica y
OpenCV. Ambos devuelven el contrato de `PredictResponse`; el pipeline
seleccionado se indica con `model` en `/api/v1/inference` y se anuncia en
`/api/v1/models`.

La carga es perezosa y cacheada por nombre. `DEFAULT_MODEL=official` mantiene
compatibilidad con despliegues existentes. Cada inferencia escribe un reporte
JSON versionado en `training/reports/inference/`, incluyendo identidad y hash
de pesos, configuracion, conteos y latencia. La bitacora no sustituye una
evaluacion: la comparacion debe usar las mismas imagenes y etiquetas para ambos
pipelines.
