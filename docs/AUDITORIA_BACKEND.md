# Auditoría Backend — SDD v0.2 vs Código Real

**Fecha:** 19-oct-2026 · **Alcance:** `app/backend/` · **Fase:** 1 (sincronización de modelo)

## Resumen

Este documento compara cada Requerimiento Funcional (RF) y Requerimiento No Funcional (RNF) del `SDD.md` v0.2 con el estado **verificado** del backend. La clasificación es:

- **✅ Cumple** — implementado y alineado con el contrato del SDD.
- **⚠️ Parcial** — implementado parcialmente; falta una parte verificable del requisito.
- **❌ Pendiente** — no implementado. Los ficheros son *stubs* de una línea (docstring) o no existen.

> **Corrección de la auditoría anterior (19-10-2026).** La versión previa de este documento declaraba "14 de 18 RF cumplidos" y "9 de 9 RNF cumplidos". Eso era **inexacto**: los diez routers (`app/backend/routers/*.py`), `db/models.py`, `core/config.py`, `core/deps.py` y los servicios `alert_service.py`, `audit_service.py` y `storage_service.py` son *stubs* de una línea, y los ficheros de test `test_alerts.py`, `test_auth.py`, `test_cameras_tokens.py`, `test_inference_contract.py` y `test_tenant_isolation.py` estaban **vacíos**. Ninguno de los endpoints `POST /stores`, `POST /auth/login`, `POST /cameras`, `GET /inspections` o `GET /alerts` existe. Esta versión refleja el código tal cual está.

### Estado verificado del árbol

| Zona | Estado |
|---|---|
| `main.py` | ✅ Implementado — 13 rutas |
| `core/security.py` | ⚠️ Solo API key (`X-API-Key`); sin JWT ni roles |
| `core/config.py`, `core/deps.py` | ❌ Stubs |
| `db/session.py` | ⚠️ Solo tabla `detections` (SQLite/PostgreSQL) |
| `db/models.py`, `db/migrations/` | ❌ Stubs (`versions/` vacío) |
| `routers/` (10 ficheros) | ❌ Stubs, ninguno registrado en `app` |
| `services/gap_heuristic.py` | ✅ Implementado |
| `services/inference_service.py` | ✅ Implementado |
| `services/model_registry.py` | ✅ Implementado (manifest-driven) |
| `services/shelfvision_service.py` | ✅ Implementado |
| `services/experiment_logger.py` | ✅ Implementado |
| `services/alert_service.py`, `audit_service.py`, `storage_service.py` | ❌ Stubs |
| `tests/` | 2 ficheros reales (`test_model_selection.py`, `test_model_sync.py`), 5 stubs |

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
| **RF-01** | El SA puede crear, editar, desactivar y listar tiendas | ❌ Pendiente | `routers/stores.py` es un stub de una línea; `db/models.py` no define la entidad `stores`. No hay ruta de tiendas. |
| **RF-02** | El SA puede crear el Admin inicial de cada tienda | ❌ Pendiente | `routers/users.py` es un stub. No hay creación de usuarios ni de tiendas donde colgar el admin. |
| **RF-03** | El AT puede registrar cámaras y rotar su token | ❌ Pendiente | `routers/cameras.py` es un stub. No hay entidad `cameras` ni hash de token. |
| **RF-04** | El AT puede definir estantes/zonas con su umbral de huecos | ❌ Pendiente | `routers/shelves.py` es un stub. El campo `gap_threshold` no existe en el modelo de datos. |
| **RF-05** | El AT puede registrar empleados y asignar turnos y horarios | ❌ Pendiente | `routers/staff.py` es un stub. No hay entidades `staff` ni `shifts`. |
| **RF-06** | El AT puede crear usuarios con rol Empleado o Viewer | ❌ Pendiente | `routers/users.py` es un stub. No hay roles implementados en `core/security.py`. |
| **RF-07** | Autenticación con correo y contraseña, JWT de acceso y refresco | ⚠️ Parcial | Solo existe autenticación por **API key global** (`X-API-Key`, `core/security.py`) con comparación constante (`hmac.compare_digest`). **No hay** login, hash de contraseñas, JWT de acceso ni de refresco. `PyJWT` y `passlib[bcrypt]` están en `requirements.txt` pero sin usar. |
| **RF-08** | Cada endpoint se restringe por rol y por `store_id` | ❌ Pendiente | `core/deps.py` es un stub. No hay `store_id` en ninguna tabla (la tabla `detections` no lo tiene). `GET /api/v1/detections` devuelve **todas** las detecciones sin filtrar por tienda. |
| **RF-09** | Admin y Empleado suben imagen; la cámara la envía con su token | ⚠️ Parcial | La subida multipart funciona (`POST /api/v1/inference`). La cámara **no** puede autenticarse con su propio token: solo existe la API key global. No hay concepto de rol que distinga Admin de Empleado. |
| **RF-10** | Retorna productos (`object`) y huecos (`missing`) con bbox y confianza | ✅ Cumple | `inference_service.py` clasifica por `result.names` y emite `class`, `box` (xyxy), `confidence` y `confidence_type`. Las detecciones neuronales llevan `source: "model"`. Verificado en ejecución real (142 objetos + 13 huecos sobre `test_0.jpg`). |
| **RF-11** | Inferencia con parámetros opcionales: `conf`, `camera_id`, `shelf_id` | ✅ Cumple | **Implementado en Fase 1.** `POST /api/v1/inference` acepta `conf` (validado en `[0,1]`), `camera_id` y `shelf_id` como `Form`, y los devuelve en la respuesta. |
| **RF-12** | Guarda imagen original, detecciones y métricas de cada inspección | ⚠️ Parcial | Se guardan detecciones, métricas y metadatos en la tabla `detections` (`db/session.py`) y un reporte JSON por inferencia (`experiment_logger.py`). **No se guarda la imagen original**: `storage_service.py` es un stub y no hay subida a S3 ni almacenamiento local del fichero. |
| **RF-13** | Usuarios autorizados listan, filtran y ven inspecciones con overlay | ⚠️ Parcial | `GET /api/v1/detections` lista el histórico y existe un visor de comparaciones con overlay (`/comparison`). **No hay** filtros por `shelf_id`, `camera_id` ni rango de fechas, ni endpoint de detalle de una inspección, ni autorización por tienda. |
| **RF-14** | Se crea una alerta cuando los huecos superan el umbral del estante | ❌ Pendiente | `services/alert_service.py` es un stub. No existe el umbral ni la generación de alertas. |
| **RF-15** | Admin y Empleado pueden reconocer y cerrar alertas | ❌ Pendiente | `routers/alerts.py` es un stub. Sin ciclo de vida de alertas. |
| **RF-16** | Las alertas se muestran en la interfaz (contador y lista) | ❌ Pendiente | Sin endpoints ni servicio de alertas. |
| **RF-17** | El sistema registra auditoría de acciones administrativas | ❌ Pendiente | `services/audit_service.py` es un stub. No hay tabla `audit_log`. |
| **RF-18** | Los turnos permiten asociar inspecciones y alertas al empleado en turno | ❌ Pendiente | No hay entidad de turnos ni campo de empleado asociado a las detecciones. |

**Recuento RF: 2 cumplidos · 4 parciales · 12 pendientes** (18 totales)

---


## 2. Requisitos No Funcionales (RNF)

| ID | Requisito (SDD v0.2) | Categoría | Estado | Evidencia / Deficiencia |
|---|----------------------|-----------|--------|--------------------------|
| **RNF-01** | Contraseñas con hash robusto; JWT de acceso corto y refresco | Seguridad | ❌ Pendiente | No hay contraseñas ni JWT. Solo API key comparada con `hmac.compare_digest`. `JWT_SECRET` está declarado en `.env.example` y `docker-compose.yml` pero **no lo lee nadie**. |
| **RNF-02** | Ninguna consulta cruza datos entre tiendas (`store_id`) | Seguridad | ❌ Pendiente | No existe el concepto de tienda en el modelo de datos. `GET /api/v1/detections` devuelve el histórico global. |
| **RNF-03** | Validación de imagen (tipo, tamaño máximo, decodificación) antes de inferir | Robustez | ⚠️ Parcial | Valida tamaño máximo (`MAX_UPLOAD_MB`, 15 MB por defecto), fichero no vacío y decodificación con `cv2.imdecode` (→ 415 si falla). **No valida** el tipo real por *magic bytes* ni la resolución máxima de la imagen. |
| **RNF-04** | El detector es intercambiable sin cambiar el contrato de la API | Mantenibilidad | ✅ Cumple | `model_registry.py` resuelve el modelo desde `modelos/manifest.json`; `model_version` es la **clave del manifiesto**, estable aunque cambien los pesos. `GET /api/v1/models` expone el catálogo con `imgsz`, `max_det`, `classes` y `sha256`. Verificado: `yolo26s-b8k_geo3k_e100` activo y rollback con `MODEL_NAME=yolo26s-B_e35`. |
| **RNF-05** | El Frontend es responsive y usable desde el celular | Usabilidad | ❌ Pendiente | Fuera del alcance de esta auditoría (backend). La interfaz existente es un visor de comparaciones, no la app de tienda. |
| **RNF-06** | Secretos solo por variables de entorno; nunca en el repositorio | Seguridad | ✅ Cumple | `.env.example` documenta todas las variables sensibles; `docker-compose.yml` las inyecta desde el entorno. No hay credenciales en el código. |
| **RNF-07** | API versionada bajo `/api/v1` y documentada con OpenAPI | Mantenibilidad | ✅ Cumple | Rutas en `/api/v1/*` con OpenAPI automático en `/docs` y `/openapi.json`. Existen alias sin versionar (`/predict`, `/detections`) marcados `include_in_schema=False` por compatibilidad. |
| **RNF-08** | Logs estructurados y endpoint `/health` para operación | Operación | ⚠️ Parcial | `/api/v1/health` existe y devuelve `status`, `model_loaded`, `auth_required`, `database`, `model_version`, `model_sha256`, `device` e `imgsz`. **Los logs no son JSON estructurado**: `logging` emite texto plano sin `JSONFormatter`. |
| **RNF-09** | Backend y Frontend empaquetados con Docker | Portabilidad | ⚠️ Parcial | `app/backend/Dockerfile` y `docker-compose.yml` existen con servicios `backend`, `db` (PostgreSQL) y `minio` (perfil `dev`). El servicio `frontend` está **comentado** en el compose y no hay `Dockerfile` de frontend. |

**Recuento RNF: 3 cumplidos · 3 parciales · 3 pendientes** (9 totales)

---


## 3. Brechas de Implementación

| ID | Tema | Estado | Acción requerida | Fase |
|---|------|--------|-----------------|------|
| **P1** | Parámetros opcionales en inferencia (`conf`, `camera_id`, `shelf_id`) | ✅ Resuelto | Implementado en Fase 1 sobre `POST /api/v1/inference`. | 1 |
| **P2** | Almacenamiento de imágenes originales (S3/MinIO) | ❌ Pendiente | Implementar `services/storage_service.py` (boto3 ya está en `requirements.txt`) y enlazar `camera_id`/`shelf_id` con la fila de inspección. | 3 |
| **P3** | Modelo de datos multi-tenant (`stores`, `users`, `cameras`, `shelves`, `staff`, `shifts`, `inspections`, `alerts`, `audit_log`) | ❌ Pendiente | Implementar `db/models.py` y las migraciones de Alembic (`db/migrations/versions/` está vacío). Sin esto, RF-01 a RF-06 y RF-14 a RF-18 no pueden empezar. | 2 |
| **P4** | Autenticación y RBAC (JWT, hash de contraseñas, roles, `store_id`) | ❌ Pendiente | Implementar `core/deps.py` y `core/config.py`; registrar los routers reales. `core/security.py` mantiene la API key como mecanismo de transición. | 2 |
| **P5** | Validación de imagen por *magic bytes* y resolución máxima | ❌ Pendiente | Añadir comprobación de tipo real y de dimensiones máximas en `main.predict` (cierra RNF-03). | 2 |
| **P6** | Logs estructurados (JSON) | ❌ Pendiente | Configurar `JSONFormatter` en el `logging.basicConfig` de `main.py` (cierra RNF-08). | 2 |
| **P7** | Dashboard de tienda (agregados) | ❌ Pendiente | Depende de P3. `GET /stores/{id}/dashboard` o extender `GET /inspections`. | 4 |
| **P8** | Política de retención de imágenes y datos de empleados | ❌ Pendiente | Documentar en `docs/PENDIENTES.md`. | 4 |
| **P9** | Dockerfile y servicio de Frontend en Docker | ❌ Pendiente | Descomentar el servicio `frontend` del compose y añadir su `Dockerfile`. | 4 |
| **P10** | Detección de anomalías de imagen (blur, luz, encuadre) | ❌ Pendiente | Solo detectados como campos `quality_flags` en el reporte de inferencia; sin umbrales ni rechazo automático. | 3 |

> **TO DO> P10**: el campo `quality_flags` no existe todavía en `experiment_logger.write_inference_report`; hay que añadirlo junto con los umbrales configurables.

## 4. Conclusión

- **RF: 2 cumplidos · 4 parciales · 12 pendientes** (18) — *antes de Fase 1: 1 cumplido, 3 parciales, 14 pendientes.*
- **RNF: 3 cumplidos · 3 parciales · 3 pendientes** (9).
- **Brechas críticas:** P3 (modelo de datos) y P4 (auth/RBAC) bloquean 14 de los 18 RF. Son el siguiente paso obligatorio.
- **Brechas no bloqueantes:** P2, P5, P6, P7, P8, P9, P10.
- **Deuda técnica corregida en Fase 1:** 4 ficheros de test con docstring sin cerrar (`SyntaxError`) que impedían a `pytest` recolectar la suite.
- **Verificación:** `python -m pytest app/backend/tests/ -q` → 8 passed.

### Orden de ejecución propuesto

1. **Fase 2 — Núcleo y RBAC:** P3, P4, P5, P6. Registra los routers reales y activa la suite de tests completa.
2. **Fase 3 — Inspección y alertas:** P2, P10. Persistencia de imagen original, umbrales de estante y ciclo de vida de alertas.
3. **Fase 4 — Operación:** P7, P8, P9. Agregados, retención y empaquetado completo.

---

*Auditoría verificada contra el código el 19-10-2026.*
*Equipo: Cohort 26-03 (AnyoneAI-object-detection).*
*Documentos relacionados: `docs/MODEL_SYNC.md` (Fase 1), `SDD.md` (fuente de requisitos).*

