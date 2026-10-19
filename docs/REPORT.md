# Informe técnico — modelo y serving

## Baseline y modelo incorporado

El checkpoint oficial de despliegue se incorporó desde `origin/master` en
`modelos/best.pt`; el export ONNX correspondiente es `modelos/best.onnx`. El
modelo expone las clases `object` y `missing`. Los pesos de entrenamiento y sus
runs continúan fuera de Git en `training/weights/`.

El run local `B_e35` queda como baseline histórico: `mAP50=0.40443`,
`mAP50-95=0.25002`, `precision=0.85140` y `recall=0.43405`. Estos valores son
referencia de la corrida registrada y no deben presentarse como evaluación
independiente del checkpoint de `master` sin volver a ejecutar su YAML de test.

## Flujo de missing

`labeling/generate_missing_labels.py` escribe como positivos de entrenamiento
solo los candidatos que superan `auto_score`; los rechazados permanecen en
`manifest.json` y `summary.json` para diagnóstico. En serving,
`app/backend/services/inference_service.py` extrae las dos clases del modelo,
calcula la heurística sobre objetos y combina los huecos aprendidos y
geométricos, eliminando coincidencias por IoU. Cada detección indica `source`.

## Contrato y operación

El contrato principal es `POST /api/v1/inference` con el campo multipart `image`.
La respuesta incluye detecciones, `model_version`, cajas en píxeles originales,
resumen y candidatos de heurística. `/predict` se conserva temporalmente para
compatibilidad local.

El notebook `training/pipeline_completo.ipynb` actualiza la rama `dev` en Colab,
instala `psutil`, registra commit y memoria, y resuelve el checkpoint mediante
`MODEL_PATH`. La evaluación definitiva debe usar un split independiente y
reportar métricas por clase, especialmente recall de `missing`.

## Limitaciones conocidas

- El `sdd.md` define infraestructura futura; los stubs de `app/backend/` todavía
	no implementan JWT/RBAC completo, PostgreSQL, S3 ni la UI.
- El modelo y la heurística pueden producir candidatos distintos; la
	deduplicación evita doble conteo, pero requiere calibración con overlays reales.
- La métrica baseline de `B_e35` no sustituye una evaluación reproducible del
	checkpoint de `master` sobre un split no usado durante el entrenamiento.
