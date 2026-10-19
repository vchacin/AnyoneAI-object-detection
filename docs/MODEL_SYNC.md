# Sincronización del Modelo `best` — Fase 1

**Proyecto:** AnyoneAI-object-detection (Cohort 26-03)
**Fecha:** 19-oct-2026
**Objetivo:** dejar el backend usando el detector de dos clases (`object` / `missing`) del checkpoint de `origin/master`, con metadata centralizada en `modelos/manifest.json`.

---

## 1. Origen de los artefactos

| Dato | Valor |
|---|---|
| Remoto | `https://github.com/vchacin/AnyoneAI-object-detection.git` |
| Rama | `master` |
| Commit | `be7936e` — *Track YOLO model with Git LFS* (13-oct-2026) |
| Método de extracción | `git checkout origin/master -- modelos/best.pt` (sin merge ni pull) |

> **Nota operativa:** en PowerShell, `git show origin/master:modelos/best.pt > modelos/best.pt` **corrompe el binario** porque la redirección de PowerShell trabaja con texto y altera los bytes. Hay que usar `git checkout origin/master -- <ruta>` (o `cmd /c`) para ficheros binarios.

## 2. Hashes SHA256

| Artefacto | Ruta | Tamaño | SHA256 |
|---|---|---|---|
| **Modelo activo** | `modelos/best.pt` | 20 295 365 B | `f8a0740c3ba70a386fd3a87dc06a2bfb3ac639886b48d388521cb735e566b7c1` |
| Export ONNX | `modelos/best.onnx` | 38 142 528 B | `03f24f190d641a445a8ea3b85283fd8bfcee95e88791e0b1142a0ec4cb7037cf` |
| Legacy `B_e35` | `training/weights/B_e35/weights/best.pt` | 20 334 462 B | `f023d9971a82ad568acaca6df2ab43b5321e51c2d48d5a5e047632f82d850e31` |

### Respaldo del modelo anterior

El `best.pt` que ya estaba en el árbol local **era byte-idéntico** al de `origin/master` (mismo SHA256 `f8a0740c…`), por lo que **no existía un checkpoint distinto que respaldar**: la copia de seguridad natural es el `B_e35` de `training/weights/B_e35/weights/best.pt`, que se conserva y queda registrado en el manifiesto con `"source": "legacy"`.

> **TO DO> `modelos/legacy/`**: la carpeta quedó vacía porque no hubo un `best.pt` distinto que archivar. Si en el futuro se sincroniza un checkpoint nuevo, respaldar el anterior en `modelos/legacy/best_<origen>.pt` **antes** de sobrescribir.

## 3. Metadata auditada del checkpoint activo

Verificada con `app/backend/scripts/inspect_model.py` (Ultralytics):

| Campo | Valor |
|---|---|
| `names` | `{0: object, 1: missing}` |
| `nc` | 2 |
| `task` | `detect` |
| `imgsz` de inferencia | **640** (ver P1) |
| `max_det` | 750 |
| `default_conf` | 0.25 |
| Versión de Ultralytics | 8.4.170 (entorno local) |
| Dataset de entrenamiento | `dataset8k_geo/data_3k.yaml` (run `b8k_geo3k_e100`, 100 épocas) |

## 4. Manifiesto de modelos

`modelos/manifest.json` es ahora la **fuente de verdad**: rutas, SHA256, mapa de clases y parámetros de inferencia. Estructura:

```json
{
  "active": "yolo26s-b8k_geo3k_e100",
  "models": {
    "yolo26s-b8k_geo3k_e100": { "path": "modelos/best.pt", "sha256": "f8a0740c…", "imgsz": 640, "max_det": 750, "default_conf": 0.25, "classes": {"0": "object", "1": "missing"} },
    "yolo26s-b8k_geo3k_e100-onnx": { "path": "modelos/best.onnx", "format": "onnx" },
    "yolo26s-B_e35": { "path": "training/weights/B_e35/weights/best.pt", "source": "legacy" }
  }
}
```

## 5. Cambios en el código

| Fichero | Cambio |
|---|---|
| `app/backend/scripts/inspect_model.py` | **Nuevo.** Audita un checkpoint y regenera `modelos/manifest.json` (hash, clases, `imgsz`, `max_det`). |
| `app/backend/scripts/compare_models.py` | **Nuevo.** Compara modelos registrados sobre una carpeta de imágenes (conteos y latencia; sin métricas de precisión inventadas). |
| `app/backend/services/model_registry.py` | Lee el manifiesto en vez de rutas hardcodeadas. `ModelSpec` ahora lleva `imgsz`, `max_det`, `default_conf`, `classes`, `sha256`. Añadidos `active_model_name()` y `verify_checksum()`. `MODEL_NAME` sobrescribe la clave `active`. |
| `app/backend/services/inference_service.py` | Consume `imgsz`/`max_det`/`conf` del manifiesto. Añadido `GAP_MODE=model\|heuristic\|hybrid`. Añadidos `latency_ms`, `gap_mode`, `device` al resultado. `predict()` acepta `conf` por llamada. Nueva `preload_active_model()` para evitar *cold start*. |
| `app/backend/services/shelfvision_service.py` | Añadidos `latency_ms` y `gap_mode` para mantener el contrato uniforme entre pipelines. |
| `app/backend/main.py` | `/health` reporta `model_version`, `model_sha256` (12 chars), `device` e `imgsz`. `POST /api/v1/inference` acepta `camera_id`, `shelf_id` y `conf` (multipart) — cierra la brecha RF-11. Preload del modelo en el startup. |
| `app/backend/tests/test_model_sync.py` | **Nuevo.** Valida manifiesto, clave activa, checksum, catálogo público y error de modelo desconocido. |
| `app/backend/tests/test_alerts.py`, `test_cameras_tokens.py`, `test_inference_contract.py`, `test_tenant_isolation.py` | Corregido error de sintaxis preexistente: docstring sin cerrar (`"""`), que impedía a `pytest` recolectar la suite. |
| `.env.example` | Documentadas `MODEL_MANIFEST`, `MODEL_NAME`, `GAP_MODE`, `DEVICE`. |

## 6. Comparativa de modelos (conteos y latencia)

Ejecutada con `python app/backend/scripts/compare_models.py data_pipeline/dataset_sku110k/images --limit 8`:

| model | images | n_objects | n_missing | p50 ms | mean ms |
|---|---|---|---|---|---|
| `yolo26s-b8k_geo3k_e100` (activo) | 8 | 1331 | 50 | 197.13 | 563.88 |
| `yolo26s-b8k_geo3k_e100-onnx` | 8 | 1308 | 43 | 238.89 | 6970.83 |
| `yolo26s-B_e35` (legacy) | 8 | 828 | 0 | 184.69 | 195.75 |

> Estos números son **conteos y latencias**, no métricas de calidad. No hay ground truth etiquetado en este repositorio, así que no se reportan precisión/recall; esas métricas salen de los reportes de entrenamiento en `training/`.

**Lectura:** el detector activo reconoce muchos más objetos que el legacy (1331 vs 828) y es el único que produce la clase `missing` aprendida. El legacy detectaba solo `object` y se apoyaba en la heurística geométrica para los huecos.

## 7. Cómo volver al modelo anterior

1. **Sin recompilar nada:** `MODEL_NAME=yolo26s-B_e35` en `.env` → el registro resuelve ese checkpoint del manifiesto.
2. **Restaurando el fichero:** `git checkout <commit-anterior> -- modelos/best.pt`.
3. **Cambiando la clave activa:** editar `"active"` en `modelos/manifest.json` y reiniciar el servicio.

## 8. Verificación

```bash
# Auditoría del modelo + regeneración del manifiesto
python app/backend/scripts/inspect_model.py

# Comparativa entre modelos registrados
python app/backend/scripts/compare_models.py data_pipeline/dataset_sku110k/images --limit 8

# Suite de pruebas
python -m pytest app/backend/tests/ -q
```

Estado del endpoint de salud:

```json
GET /api/v1/health
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "yolo26s-b8k_geo3k_e100",
  "model_sha256": "f8a0740c3ba7",
  "device": "cpu",
  "imgsz": 640
}
```

## 9. Limitaciones conocidas

- **Límite del producto:** el detector responde *hueco visible*, **no** SKU faltante. No hay planograma en v1.
- **`missing` es "hueco candidato"**: la red de dos clases predice espacios vacíos; la heurística geométrica queda como fallback configurable (`GAP_MODE=heuristic` / `hybrid`).
- **Sin métricas de calidad en este repositorio:** el conteo y la latencia no sustituyen una evaluación con etiquetas.
- **Resolución fija a 640:** el modelo se entrenó a 640. Inferir a otra resolución degrada la precisión; `imgsz` es configurable en el manifiesto si se entrena un checkpoint nuevo.
- **YOLO26m no descargado** (decisión por defecto P2): el puntero LFS de `modelos/yolo26m/best.pt` (~175 MB) no se descargó; solo se trabaja con YOLO26s para mantener la ligereza en CPU.
- **ONNX con peor latencia media en esta máquina** (6.9 s vs 0.56 s) por la primera inicialización del runtime; no se evaluó en producción.

## 10. Decisiones por defecto aplicadas (pendientes de confirmación)

| # | Decisión | Valor por defecto |
|---|---|---|
| **P1** | Resolución de inferencia | **640** (la del checkpoint) |
| **P2** | Descargar YOLO26m | **No** |
| **P3** | Selección de modelo por petición | **Desactivada** (`ALLOW_MODEL_OVERRIDE=false`; pendiente de implementar en Fase 2) |
| **P4** | Modelo oficial de la demo | `yolo26s-b8k_geo3k_e100` con `GAP_MODE=model` |

> **TO DO> P3**: `POST /api/v1/inference` acepta hoy un parámetro `model` sin restricción de rol. Restringirlo a `super_admin` y activarlo solo con `ALLOW_MODEL_OVERRIDE=true` (Fase 2, núcleo/RBAC).
