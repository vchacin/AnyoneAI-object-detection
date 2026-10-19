# AGENTS.md — Lineamientos para Kilo

Este archivo guía a los agentes de Kilo sobre cómo trabajar en este repositorio.

## Comandos

| Acción | Comando |
|--------|---------|
| Instalar dependencias | `pip install -r requirements.txt` |
| Ejecutar tests | `pytest data_pipeline/tests/ -v` |
| Iniciar API local | `uvicorn app.backend.main:app --reload` |
| Entrenar brazo A | `python training/train.py --which A --epochs 35` |
| Entrenar brazo B | `python training/train.py --which B --epochs 35 --batch 8` |
| Construir API con Docker | `docker compose up --build` |
| Generar reporte | Ver `docs/REPORT.md` |

## Estándares de código

1. **Lenguaje de comentarios**: tercera persona, general, técnico. Se evita el
   trato formal o informal de segunda persona ("tú", "usar", "subir"). Los
   comentarios deben explicar *por qué* el código hace algo, no *qué* hace (el
   código ya lo dice).

2. **Docstrings**: todas las funciones y módulos deben tener docstring que
   describa propósito, argumentos y valores de retorno. Formato Google/NumPy.

3. **Imports**: se permite importar `ultralytics` dentro de funciones
   (`from ultralytics import YOLO`) para evitar dependencias pesadas en import
   de módulos ligeros como `gap_heuristic.py`.

4. **Naming**: `snake_case` para funciones y variables; `PascalCase` para clases.
   Constantes en `UPPER_SNAKE_CASE` (ej. `ROW_TOL`, `AUTO_SCORE`).

5. **Sin comentarios triviales**: no se añaden comentarios que repitan el código.
   Se eliminan comentarios que usan emojis o lenguaje coloquial.

6. **Separadores de sección**: se usan bloques de comentarios como
   `# ---------------------------------------------------------------- nombre`
   para organizar funciones relacionadas en archivos grandes.

## Estructura del repositorio

```
data_pipeline/   # Adquisición, limpieza y preprocesamiento de datos
labeling/        # Generación de etiquetas con heurística geométrica
training/        # Entrenamiento, evaluación y notebooks orquestadores
app/backend/     # Servicio FastAPI de inferencia e infraestructura
app/frontend/    # Reservado para la interfaz futura
docs/            # Documentación técnica (arquitectura, informe)
```

## Principios de diseño

- **Sin duplicación de heurística**: `app/backend/services/gap_heuristic.py` es la única fuente de
   verdad. Tanto `labeling/` como `app/backend/services/inference_service.py` lo importan. Cualquier cambio
  en la lógica geométrica debe hacerse en un solo lugar.

- **data.yaml con ruta absoluta**: Ultralytics resuelve `path` relativo contra la
  carpeta del propio yaml, no contra la raíz del repositorio. Siempre usar rutas
  absolutas o regenerar el yaml con `ROOT_DIR` del entorno.

- **Singleton de modelo**: `app/backend/services/inference_service.py` mantiene un singleton `Detector`
  protegido por lock para uso concurrente en FastAPI.

- **Gitignore estricto**: `.env`, pesos de entrenamiento, `training/reports/`,
  `data_pipeline/dataset_sku110k/` y `app/data/` están excluidos. El checkpoint
  oficial de despliegue se mantiene en `modelos/` y se monta en Docker.
