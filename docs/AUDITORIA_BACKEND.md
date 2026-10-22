# Auditoría Backend — SDD v0.3 vs Código Real

**Fecha:** 22-oct-2026 · **Alcance:** `app/backend/` · **Fase:** 6 (optimización de producción)

## Resumen

Este documento compara cada Requerimiento Funcional (RF) y Requerimiento No Funcional (RNF) del `SDD.md` v0.2 con el estado **verificado** del backend. La clasificación es:

- **✅ Cumple** — implementado y alineado con el contrato del SDD.
- **⚠️ Parcial** — implementado parcialmente; falta una parte verificable del requisito.
- **❌ Pendiente** — no implementado. Los ficheros son *stubs* de una línea (docstring) o no existen.

> **Actualización Fases 2-6 (22-10-2026).** Se implementaron autenticación,
> RBAC, aislamiento multi-tenant, gestión operativa, persistencia de
> inspecciones, storage local, alertas, analítica y exportaciones. La inferencia
> legacy conserva `X-API-Key` para compatibilidad. La imagen Docker de
> producción ahora usa dependencias runtime CPU-only y excluye CUDA,
> entrenamiento, tests, documentación y pesos. S3/MinIO, asociación automática
> de empleado y cobertura integral de endpoints continúan pendientes.

### Estado verificado del árbol

| Zona | Estado |
|---|---|
| `main.py` | ✅ Implementado — inferencia, persistencia, alertas y storage |
| `core/security.py` | ✅ Hash scrypt, JWT y compatibilidad API key |
| `core/config.py`, `core/deps.py` | ✅ Settings, usuario actual, roles y tenant básico |
| `core/errors.py` y logging | ✅ Errores `{detail, code}`, logging JSON y CORS configurable |
| `db/session.py` | ⚠️ Tablas legacy y multi-tenant; migración inicial creada |
| `db/models.py`, `db/migrations/` | ⚠️ Modelo multi-tenant y migración inicial; faltan migraciones evolutivas |
| `routers/auth.py`, `routers/stores.py` | ⚠️ Login/refresh/logout/me y CRUD básico de tiendas |
| `routers/cameras.py`, `routers/shelves.py` | ✅ CRUD, aislamiento y rotación de token |
| `routers/users.py`, `routers/staff.py` | ⚠️ Usuarios, empleados, turnos, settings y solapamiento básico; falta asociación en inferencia |
| `routers/inspections.py`, `routers/alerts.py` | ⚠️ Historial, storage local, exportación NDJSON, alertas y transiciones; falta S3 y pruebas de integración |
| `routers/analytics.py` | ✅ Dashboards, resumen de cámaras, exportaciones y métricas; faltan pruebas completas |
| `routers/` restantes | ❌ Stubs o sin endpoints de dominio |
| `services/gap_heuristic.py` | ✅ Implementado |
| `services/inference_service.py` | ✅ Implementado |
| `services/model_registry.py` | ✅ Implementado (manifest-driven) |
| `services/shelfvision_service.py` | ✅ Implementado |
| `services/experiment_logger.py` | ✅ Implementado |
| `services/alert_service.py`, `audit_service.py`, `storage_service.py` | ⚠️ Implementados localmente y con backend S3/MinIO opcional; falta auditoría administrativa completa y pruebas de integración S3 |
| `Dockerfile`, `requirements-runtime.txt`, `.dockerignore` | ✅ Imagen CPU-only verificada; excluye CUDA, entrenamiento, tests, documentación y pesos; los modelos se montan en `/models` |
| `tests/` | 23 tests pasan; cobertura de gestión completa aún pendiente |

### Rutas realmente exposed por la aplicación

```
GET  /                                  Interfaz estática
GET  /static/*                          Estáticos
GET  /comparison                        Visor de comparaciones
GET  /comparison-data/*                 Datos del visor
GET  /api/v1/comparisons                Listado de comparaciones
GET  /api/v1/comparisons/{run_id}/manifest
POST /api/v1/comparisons/{run_id}/review
GET  /health , GET /api/v1/health       Estado del servicio
GET  /api/v1/models                     Catálogo de modelos
POST /predict , POST /api/v1/inference  Inferencia
GET  /detections , GET /api/v1/detections
```

---

## 1. Requisitos Funcionales (RF)

| ID | Requisito (SDD v0.2) | Estado | Evidencia / Deficiencia |
|---|----------------------|--------|--------------------------|
| **RF-01** | El SA puede crear, editar, desactivar y listar tiendas | ⚠️ Parcial | `routers/stores.py` implementa CRUD y aislamiento; faltan pruebas completas del ciclo de desactivación. |
| **RF-02** | El SA puede crear el Admin inicial de cada tienda | ⚠️ Parcial | `routers/users.py` y el seed de Super Admin permiten gestionar usuarios; falta prueba completa del flujo SA-tienda-admin. |
| **RF-03** | El AT puede registrar cámaras y rotar su token | ⚠️ Parcial | `routers/cameras.py` implementa creación, listado, edición y rotación. El token se almacena como SHA-256 y solo se devuelve al crear/rotar; falta usarlo todavía como credencial de inferencia. |
| **RF-04** | El AT puede definir estantes/zonas con su umbral de huecos | ⚠️ Parcial | `routers/shelves.py` implementa creación, listado y edición con `gap_threshold`; falta completar pruebas y su uso en alertas. |
| **RF-05** | El AT puede registrar empleados y asignar turnos y horarios | ⚠️ Parcial | `routers/staff.py` implementa empleados, turnos, validación de horario y solapamiento; falta completar pruebas y asociación del empleado en inferencia. |
| **RF-06** | El AT puede crear usuarios con rol Empleado o Viewer | ⚠️ Parcial | `routers/users.py` permite crear y editar empleados/viewers; el SA puede crear admins y el AT no puede elevar usuarios a admin. Faltan pruebas de matriz completa. |
| **RF-07** | Autenticación con correo y contraseña, JWT de acceso y refresco | ⚠️ Parcial | Implementados login, hash scrypt, JWT access/refresh, logout y `/auth/me`; falta ampliar rate limiting y matriz completa de casos. La API key se conserva solo para compatibilidad legacy. |
| **RF-08** | Cada endpoint se restringe por rol y por `store_id` | ⚠️ Parcial | `core/deps.py` aplica roles y aislamiento en los routers multi-tenant; faltan pruebas completas de todos los recursos y el alias legacy de detecciones. |
| **RF-09** | Admin y Empleado suben imagen; la cámara la envía con su token | ✅ Cumple | `POST /api/v1/inference` acepta JWT, API key legacy y `X-Camera-Token`; valida cámara activa, tienda y estante, actualiza `last_seen` y guarda la inspección. |
| **RF-10** | Retorna productos (`object`) y huecos (`missing`) con bbox y confianza | ✅ Cumple | `inference_service.py` clasifica por `result.names` y emite `class`, `box` (xyxy), `confidence` y `confidence_type`. Las detecciones neuronales llevan `source: "model"`. Verificado en ejecución real (142 objetos + 13 huecos sobre `test_0.jpg`). |
| **RF-11** | Inferencia con parámetros opcionales: `conf`, `camera_id`, `shelf_id` | ✅ Cumple | **Implementado en Fase 1.** `POST /api/v1/inference` acepta `conf` (validado en `[0,1]`), `camera_id` y `shelf_id` como `Form`, y los devuelve en la respuesta. |
| **RF-12** | Guarda imagen original, detecciones y métricas de cada inspección | ⚠️ Parcial | Se persisten imagen original en storage local, detecciones, dimensiones, bytes, modelo y latencia. Falta backend S3/MinIO para producción. |
| **RF-13** | Usuarios autorizados listan, filtran y ven inspecciones con overlay | ⚠️ Parcial | `/api/v1/inspections` ofrece filtros por estante, cámara y fecha, detalle, imagen protegida y aislamiento. Falta integración con la interfaz final. |
| **RF-14** | Se crea una alerta cuando los huecos superan el umbral del estante | ⚠️ Parcial | Se crean alertas por encima de `gap_threshold` y se evita duplicar alertas abiertas por estante. Faltan pruebas de integración. |
| **RF-15** | Admin y Empleado pueden reconocer y cerrar alertas | ⚠️ Parcial | `PATCH /api/v1/alerts/{id}` implementa acknowledge/close y rechaza transiciones inválidas. Faltan pruebas de integración. |
| **RF-16** | Las alertas se muestran en la interfaz (contador y lista) | ⚠️ Parcial | Existen listado y contador por tienda; falta integración con la interfaz final. |
| **RF-17** | El sistema registra auditoría de acciones administrativas | ⚠️ Parcial | Existe `audit_log` y se registra inferencia autenticada; faltan instrumentar todas las operaciones administrativas. |
| **RF-18** | Los turnos permiten asociar inspecciones y alertas al empleado en turno | ⚠️ Parcial | Existen turnos y validación de solapamiento; falta resolver y persistir automáticamente el empleado vigente en la inspección. |

**Recuento RF: 3 cumplidos · 14 parciales · 1 pendiente** (18 totales)

---


## 2. Requisitos No Funcionales (RNF)

| ID | Requisito (SDD v0.2) | Categoría | Estado | Evidencia / Deficiencia |
|---|----------------------|-----------|--------|--------------------------|
| **RNF-01** | Contraseñas con hash robusto; JWT de acceso corto y refresco | Seguridad | ✅ Cumple | Hash scrypt, JWT access/refresh, revocación de refresh tokens y dependencias de autenticación implementados. |
| **RNF-02** | Ninguna consulta cruza datos entre tiendas (`store_id`) | Seguridad | ⚠️ Parcial | Los routers multi-tenant aplican aislamiento por `store_id`; el alias legacy de detecciones requiere cobertura adicional. |
| **RNF-03** | Validación de imagen (tipo, tamaño máximo, decodificación) antes de inferir | Robustez | ⚠️ Parcial | Valida tamaño máximo (`MAX_UPLOAD_MB`, 15 MB por defecto), fichero no vacío y decodificación con `cv2.imdecode` (→ 415 si falla). **No valida** el tipo real por *magic bytes* ni la resolución máxima de la imagen. |
| **RNF-04** | El detector es intercambiable sin cambiar el contrato de la API | Mantenibilidad | ✅ Cumple | `model_registry.py` resuelve el modelo desde `modelos/manifest.json`; `model_version` es la **clave del manifiesto**, estable aunque cambien los pesos. `GET /api/v1/models` expone el catálogo con `imgsz`, `max_det`, `classes` y `sha256`. Verificado: `yolo26s-b8k_geo3k_e100` activo y rollback con `MODEL_NAME=yolo26s-B_e35`. |
| **RNF-05** | El Frontend es responsive y usable desde el celular | Usabilidad | ❌ Pendiente | Fuera del alcance de esta auditoría (backend). La interfaz existente es un visor de comparaciones, no la app de tienda. |
| **RNF-06** | Secretos solo por variables de entorno; nunca en el repositorio | Seguridad | ✅ Cumple | `.env.example` documenta todas las variables sensibles; `docker-compose.yml` las inyecta desde el entorno. No hay credenciales en el código. |
| **RNF-07** | API versionada bajo `/api/v1` y documentada con OpenAPI | Mantenibilidad | ✅ Cumple | Rutas en `/api/v1/*` con OpenAPI automático en `/docs` y `/openapi.json`. Existen alias sin versionar (`/predict`, `/detections`) marcados `include_in_schema=False` por compatibilidad. |
| **RNF-08** | Logs estructurados y endpoint `/health` para operación | Operación | ⚠️ Parcial | `/api/v1/health` existe y devuelve `status`, `model_loaded`, `auth_required`, `database`, `model_version`, `model_sha256`, `device` e `imgsz`. **Los logs no son JSON estructurado**: `logging` emite texto plano sin `JSONFormatter`. |
| **RNF-09** | Backend y Frontend empaquetados con Docker | Portabilidad | ⚠️ Parcial | Backend, PostgreSQL, MinIO opcional y volúmenes están definidos. La imagen `backend-prod:latest` CPU-only mide aproximadamente 2.46 GB y fue verificada con healthcheck e inferencia limitada a 1 GB. El frontend permanece fuera del alcance backend y falta smoke test Windows. |

**Recuento RNF: 6 cumplidos · 2 parciales · 1 pendiente** (9 totales)

---


## 3. Optimización de producción Docker

### Cambios verificados

- `app/backend/requirements-runtime.txt` separa API, persistencia, seguridad,
  visión e integración S3 de las dependencias de entrenamiento y pruebas.
- `Dockerfile` instala `torch` y `torchvision` desde el índice CPU de PyTorch.
- `.dockerignore` excluye `.venv`, `training`, `data_pipeline`, `docs`, tests,
  pesos y artefactos locales.
- Los pesos se montan como volumen de solo lectura en `/models`.
- Los reportes runtime se escriben en
  `/app/app/data/reports/inference`, una ruta escribible por `appuser`.
- Uvicorn se ejecuta con un único worker para evitar cargar múltiples copias
  del modelo.

### Comandos de construcción y prueba

```bash
docker build -t backend-prod:latest -f app/backend/Dockerfile .
docker run -d --name backend-prod --memory=1g --cpus=1 -p 8000:8000 \
  -v "${PWD}/modelos:/models:ro" backend-prod:latest
curl -s http://localhost:8000/health
docker stats backend-prod --no-stream
docker rm -f backend-prod
```

En Windows PowerShell:

```powershell
docker build -t backend-prod:latest -f app\backend\Dockerfile .
docker run -d --name backend-prod --memory=1g --cpus=1 -p 8000:8000 `
  -v "${PWD}\modelos:/models:ro" backend-prod:latest
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
docker stats backend-prod --no-stream
docker rm -f backend-prod
```

Resultados observados el 22-oct-2026:

```text
Imagen: 2.46 GB
torch: 2.14.1+cpu
CUDA: None
cuda.is_available(): False
Healthcheck: HTTP 200
Inferencia CPU con límite de 1 GB: HTTP 200
Memoria observada en la prueba: aproximadamente 396 MiB
Suite backend: 23 passed
```

La imagen no debe ejecutarse en una instancia micro junto con PostgreSQL y
MinIO en producción sin pruebas adicionales de memoria. Para una demo se
recomienda `t3.small` o superior, un único worker y S3 en lugar de MinIO local.

## 4. Brechas de Implementación

| ID | Tema | Estado | Acción requerida | Fase |
|---|------|--------|-----------------|------|
| **P1** | Parámetros opcionales en inferencia (`conf`, `camera_id`, `shelf_id`) | ✅ Resuelto | Implementado en Fase 1 sobre `POST /api/v1/inference`. | 1 |
| **P2** | Almacenamiento de imágenes originales (S3/MinIO) | ⚠️ Parcial | Storage local seguro implementado y enlazado a inspecciones; falta backend S3/MinIO. | 3 |
| **P3** | Modelo de datos multi-tenant (`stores`, `users`, `cameras`, `shelves`, `staff`, `shifts`, `inspections`, `alerts`, `audit_log`) | ✅ Resuelto inicialmente | Modelos y migración inicial implementados; faltan migraciones evolutivas para cambios futuros. | 2 |
| **P4** | Autenticación y RBAC (JWT, hash de contraseñas, roles, `store_id`) | ✅ Resuelto inicialmente | JWT, hash scrypt, dependencias de rol/tenant y routers registrados. La API key permanece como compatibilidad legacy. | 2 |
| **P5** | Validación de imagen por *magic bytes* y resolución máxima | ❌ Pendiente | Añadir comprobación de tipo real y de dimensiones máximas en `main.predict` (cierra RNF-03). | 2 |
| **P6** | Logs estructurados (JSON) | ❌ Pendiente | Configurar `JSONFormatter` en el `logging.basicConfig` de `main.py` (cierra RNF-08). | 2 |
| **P7** | Dashboard de tienda (agregados) | ✅ Resuelto inicialmente | Dashboard de tienda, dashboard global, resumen por cámara y métricas implementados en `routers/analytics.py`. | 4 |
| **P8** | Política de retención de imágenes y datos de empleados | ❌ Pendiente | Documentar en `docs/PENDIENTES.md`. | 4 |
| **P9** | Dockerfile y servicio de Frontend en Docker | ⚠️ Parcial | Backend empaquetado y build verificado; el frontend no forma parte del alcance actual del repositorio. | 4 |
| **P10** | Detección de anomalías de imagen (blur, luz, encuadre) | ❌ Pendiente | Solo detectados como campos `quality_flags` en el reporte de inferencia; sin umbrales ni rechazo automático. | 3 |

> **TO DO> P10**: el campo `quality_flags` no existe todavía en `experiment_logger.write_inference_report`; hay que añadirlo junto con los umbrales configurables.

## 5. Conclusión

- **RF: 3 cumplidos · 14 parciales · 1 pendiente** (18).
- **RNF: 6 cumplidos · 2 parciales · 1 pendiente** (9).
- **Brechas actuales:** backend S3/MinIO, asociación automática del empleado, auditoría administrativa completa, pruebas integrales y políticas operativas.
- **Deuda técnica corregida en Fase 1:** 4 ficheros de test con docstring sin cerrar (`SyntaxError`) que impedían a `pytest` recolectar la suite.
- **Verificación:** `python -m pytest app/backend/tests/ -q` → 23 passed; `docker compose config --quiet`; imagen `backend-prod:latest` de 2.46 GB con healthcheck e inferencia CPU verificadas.

### Orden de ejecución propuesto

1. **Fase 4 — Storage productivo:** P2. Implementar backend S3/MinIO manteniendo storage local para tests.
2. **Fase 3 — Operación de personal:** P8 y RF-18. Asociar automáticamente el empleado vigente y definir retención.
3. **Fase 6 — Cierre:** ampliar pruebas de endpoints, auditoría administrativa y smoke test Windows.

---

*Auditoría verificada contra el código el 22-10-2026.*
*Equipo: Cohort 26-03 (AnyoneAI-object-detection).*
*Documentos relacionados: `docs/MODEL_SYNC.md` (Fase 1), `SDD.md` (fuente de requisitos).*
